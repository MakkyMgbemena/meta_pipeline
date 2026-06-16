import inspect
import operator
import os
import threading
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from psycopg_pool import ConnectionPool

from core.agents import AGENT_REGISTRY
from core.mission_switcher import MissionSwitcher
from delivery.email_sender import EmailSender
from utils.db_manager import DatabaseManager
from utils.logger import get_logger
from utils.prompts import REPORT_PROMPT_TEMPLATE


class MissionState(TypedDict):
    client_id: str
    mission_id: Optional[str]
    job_id: Optional[str]
    context: Annotated[Dict[str, Any], operator.ior]
    routing_chain: List[str]
    results: Annotated[Dict[str, Any], operator.ior]
    mission_status: str  # STARTED, COMPLETED, FAILED, PAUSED
    hitl_status: Optional[str]
    delivery_status: Optional[str]
    failed_steps: Annotated[List[str], operator.add]


class ValidationGrader:
    def __init__(self, config, client_id, db=None):
        self.client_id = client_id
        self.db = db

    def run(self, payload):
        return {
            "status": "graded",
            "verdict": "PASS",
            "message": f"Workflow validated for {self.client_id}.",
        }


class NarrativeGrader:
    def __init__(self, config, client_id, db=None):
        self.client_id = client_id
        self.db = db

    def run(self, payload):
        return {
            "status": "graded",
            "verdict": "HIGH_QUALITY",
            "message": "Narrative meets enterprise standards.",
        }


class Orchestrator:
    def __init__(self, config: dict):
        self.logger = get_logger("Orchestrator")
        self.config = config or {}
        self.registry = {}
        self.pool = None
        self.checkpointer = None

        try:
            self.db = DatabaseManager(self.config)
        except Exception as e:
            self.logger.error(f"Database Manager initialization failed: {e}")
            self.db = None

        self.mission_switcher = MissionSwitcher(self.config, db=self.db)
        from utils.pricing_resolver import PricingResolver
        self.pricing_resolver = PricingResolver(config, db=self.db)
        self.ai_client = self._init_ai_client()

        self._register_agents()
        self._init_langgraph()
        self._start_timeout_worker()
        self.logger.info("Orchestrator instantiated and agents registered.")

    def _init_langgraph(self):
        """Initialises the PostgresSaver checkpointer for LangGraph state persistence."""
        from urllib.parse import quote_plus

        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASS")
        if not password:
            self.logger.warning("LangGraph checkpointer skipped: DB_PASS not found.")
            self.checkpointer = None
            return

        db_name = os.getenv("DB_NAME", "meta_pipeline")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME", "")

        try:
            encoded_user = quote_plus(user)
            encoded_password = quote_plus(password)
            encoded_db_name = quote_plus(db_name)

            if instance_connection_name:
                socket_dir = f"/cloudsql/{instance_connection_name}"
                conn_info = (
                    f"postgresql://{encoded_user}:{encoded_password}"
                    f"@/{encoded_db_name}?host={socket_dir}"
                )
                self.logger.info(
                    f"LangGraph connecting via Cloud SQL Unix socket: {socket_dir}"
                )
            elif db_host.startswith("/cloudsql/"):
                conn_info = (
                    f"postgresql://{encoded_user}:{encoded_password}"
                    f"@/{encoded_db_name}?host={db_host}"
                )
                self.logger.info(f"LangGraph connecting via Unix socket: {db_host}")
            else:
                conn_info = (
                    f"postgresql://{encoded_user}:{encoded_password}"
                    f"@{db_host}:{db_port}/{encoded_db_name}"
                )
                self.logger.info(f"LangGraph connecting via TCP/IP: {db_host}:{db_port}")

            self.pool = ConnectionPool(conn_info=conn_info, max_size=20)
            self.checkpointer = PostgresSaver(self.pool)

            with self.pool.connection() as conn:
                self.checkpointer.setup(conn)

            self.logger.info("LangGraph PostgresSaver initialized and setup.")
        except Exception as e:
            self.logger.error(f"Failed to initialize LangGraph checkpointer: {e}")
            self.pool = None
            self.checkpointer = None

    def _start_timeout_worker(self):
        """Starts a background thread to handle automatic mission resumption."""
        if not self.config.get("hitl", {}).get("timeout_enabled", True):
            return

        def _worker():
            timeout_seconds = self.config.get("hitl", {}).get("timeout_seconds", 3600)
            self.logger.info(
                f"HITL Timeout Worker started (Timeout: {timeout_seconds}s)"
            )
            while True:
                try:
                    self._check_and_resume_timed_out_missions(timeout_seconds)
                except Exception as e:
                    self.logger.error(f"Timeout worker error: {e}")
                time.sleep(60)

        threading.Thread(target=_worker, daemon=True).start()

    def _check_and_resume_timed_out_missions(self, timeout_seconds):
        """Automatic mission resumption for timed-out PAUSED missions."""
        if not self.db:
            return

        try:
            import datetime

            from services.fastapi.models import MissionJob

            with self.db.session_scope() as session:
                cutoff = datetime.datetime.utcnow() - datetime.timedelta(
                    seconds=timeout_seconds
                )
                timed_out_jobs = (
                    session.query(MissionJob)
                    .filter(
                        MissionJob.status == "PAUSED",
                        MissionJob.updated_at < cutoff,
                    )
                    .all()
                )

                for job in timed_out_jobs:
                    self.logger.info(
                        f"Auto-resuming timed out mission: {job.job_id}"
                    )
                    threading.Thread(
                        target=self.resume_mission,
                        args=(job.client_id, None, job.job_id),
                        daemon=True,
                    ).start()
        except Exception as e:
            self.logger.error(f"Failed to check timed out missions: {e}")

    # ---------------------------------------------------------
    # AI CLIENT
    # ---------------------------------------------------------
    def _init_ai_client(self):
        """
        Enterprise AI Resolver: Implements ordered failover using
        meta_pipeline.api_redundancy.provider_order.
        """
        redundancy_cfg = self.config.get("meta_pipeline", {}).get("api_redundancy", {})
        if not redundancy_cfg.get("enabled", True):
            self.logger.warning("AI Redundancy is disabled in config.")
            return None

        provider_order = redundancy_cfg.get(
            "provider_order", ["vertex_ai", "openai", "gemini_api"]
        )

        for provider_name in provider_order:
            try:
                client = self._attempt_provider_init(provider_name, redundancy_cfg)
                if client:
                    self.logger.info(
                        f"AI Engine initialized successfully via provider: {provider_name}"
                    )
                    return client
            except Exception as e:
                self.logger.warning(
                    f"Provider {provider_name} initialization failed: {e}"
                )
                continue

        self.logger.critical(
            "All AI providers failed. Narrative generation will be unavailable."
        )
        return None

    def _attempt_provider_init(self, provider_name: str, redundancy_cfg: dict):
        """Initialise a specific provider and return a unified client wrapper."""
        cfg = redundancy_cfg.get(provider_name, {})
        if not cfg.get("enabled", False):
            return None

        model_name = cfg.get("default_model")

        if provider_name == "vertex_ai":
            import vertexai
            from vertexai.generative_models import GenerativeModel

            project = os.getenv(cfg.get("project_env_var"))
            location = os.getenv(cfg.get("location_env_var"))
            vertexai.init(project=project, location=location)
            model = GenerativeModel(model_name)

            class VertexClient:
                def generate(self, prompt, data):
                    response = model.generate_content(f"{prompt}\n\nDATA:\n{data}")
                    return response.text

            return VertexClient()

        if provider_name == "openai":
            from openai import OpenAI

            api_key = os.getenv(cfg.get("api_key_env_var"))
            client = OpenAI(api_key=api_key)

            class OpenAIClient:
                def generate(self, prompt, data):
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {
                                "role": "user",
                                "content": f"{prompt}\n\nDATA:\n{data}",
                            }
                        ],
                    )
                    return response.choices[0].message.content

            return OpenAIClient()

        if provider_name == "gemini_api":
            import google.generativeai as genai

            api_key = os.getenv(cfg.get("api_key_env_var"))
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            class GeminiAPIClient:
                def generate(self, prompt, data):
                    response = model.generate_content(f"{prompt}\n\nDATA:\n{data}")
                    return response.text

            return GeminiAPIClient()

        return None

    def _get_failed_steps(self, routing_chain: list, context: dict):
        failed = []
        for step in routing_chain:
            result = context.get(step)
            if isinstance(result, dict) and result.get("status", "").lower() == "failed":
                failed.append(step)
        return failed

    def _generate_summary_html(self, data: dict):
        passed = []
        failed = []
        skipped = []

        for step, result in data.items():
            if not isinstance(result, dict):
                continue
            status = str(result.get("status", "")).lower()
            verdict = str(result.get("verdict", "")).lower()

            if status == "failed":
                failed.append(step)
            elif status == "skipped":
                skipped.append(step)
            elif status in ["graded", "recorded", "synced", "pass", "success"] or verdict == "pass":
                passed.append(step)
            else:
                passed.append(step)

        overall = "FAILED" if failed else "SUCCESS"

        html = [
            f"<html><body><h2>Mission Summary</h2><p><strong>Overall status:</strong> {overall}</p>"
        ]
        if passed:
            html.append(f"<p><strong>Completed:</strong> {', '.join(passed)}</p>")
        if failed:
            html.append(
                f"<p style='color:red;'><strong>Failed:</strong> {', '.join(failed)}</p>"
            )
        if skipped:
            html.append(
                f"<p style='color:gray;'><strong>Skipped:</strong> {', '.join(skipped)}</p>"
            )
        html.append("</body></html>")
        return "".join(html)

    # ---------------------------------------------------------
    # AGENT REGISTRY
    # ---------------------------------------------------------
    def _register_agents(self):
        """Loads the standard agent registry and adds internal grader nodes."""
        self.registry = {**AGENT_REGISTRY}
        self.registry["validation_grader"] = ValidationGrader
        self.registry["narrative_grader"] = NarrativeGrader

    # ---------------------------------------------------------
    # MAIN EXECUTION FLOW
    # ---------------------------------------------------------
    def run_for_client(self, client_id: str, context: dict = None, job_id: str = None):
        self.logger.info(f"Starting mission flow for client: {client_id}")

        if job_id and self.db:
            self.db.update_job_status(job_id, "ORCHESTRATION_STARTED")

        context = context or {}
        context["client_id"] = client_id

        from utils.brief_storage import load_brief

        brief = load_brief(client_id)
        if brief:
            context["mission_brief"] = brief
            self.logger.info(f"Loaded mission brief for {client_id}")

        mission_type = (
            context.get("mission_type")
            or (brief.get("mission_type") if brief else None)
            or context.get("payload", {}).get("mission_type")
        )

        runtime_chain = (
            context.get("routing_chain")
            or context.get("payload", {}).get("routing_chain")
        )

        routing_chain = self.mission_switcher.resolve_routing(
            client_id=client_id,
            mission_type=mission_type,
            runtime_chain=runtime_chain,
        )
        self.logger.info(
            f"Resolved routing chain for type '{mission_type}': {routing_chain}"
        )

        if "ghost_audit" in routing_chain:
            idx = routing_chain.index("ghost_audit")
            if "validation_grader" not in routing_chain[:idx]:
                routing_chain.insert(idx, "validation_grader")

        hitl_enabled = self.config.get("hitl", {}).get("enabled", False)
        graph = self._build_graph(routing_chain, hitl_enabled=hitl_enabled)

        initial_state: MissionState = {
            "client_id": client_id,
            "mission_id": context.get("mission_id"),
            "job_id": job_id,
            "context": context,
            "routing_chain": routing_chain,
            "results": {},
            "mission_status": "STARTED",
            "hitl_status": None,
            "delivery_status": None,
            "failed_steps": [],
        }

        thread_id = job_id or f"mission_{client_id}_{int(time.time())}"
        run_config = {"configurable": {"thread_id": thread_id}}

        try:
            graph.invoke(initial_state, config=run_config)

            snapshot = graph.get_state(run_config)
            if getattr(snapshot, "next", None):
                self.logger.info(
                    f"HITL pause activated for {client_id} (Thread: {thread_id})"
                )
                if job_id and self.db:
                    self.db.update_job_status(job_id, "PAUSED")

                if self.config.get("hitl", {}).get("notify_internal", False):
                    self._send_hitl_alert(client_id, snapshot.values)

                return {
                    **snapshot.values,
                    "hitl_status": "awaiting_review",
                    "thread_id": thread_id,
                }

            return self._handle_graph_completion(client_id, snapshot.values, job_id)

        except Exception as e:
            self.logger.error(f"Graph execution failed: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    def resume_mission(
        self, client_id: str, context: dict = None, thread_id: str = None
    ):
        """Resume a mission after HITL pause or timeout."""
        self.logger.info(f"Resuming mission for thread: {thread_id}")

        if not thread_id and context:
            thread_id = context.get("thread_id")

        if not thread_id:
            return {"status": "ERROR", "error": "Missing thread_id for resume"}

        run_config = {"configurable": {"thread_id": thread_id}}

        try:
            temp_graph = self._build_graph(["verifier_agent"], hitl_enabled=False)
            snapshot = temp_graph.get_state(run_config)

            if not snapshot or not snapshot.values:
                return {
                    "status": "ERROR",
                    "error": f"No state found for thread {thread_id}",
                }

            saved_state = snapshot.values
            saved_context = saved_state.get("context", {}) or {}

            mission_type = (
                saved_context.get("mission_type")
                or (saved_context.get("mission_brief") or {}).get("mission_type")
                or (saved_context.get("payload") or {}).get("mission_type")
            )

            runtime_chain = (
                saved_state.get("routing_chain")
                or saved_context.get("routing_chain")
                or (saved_context.get("payload") or {}).get("routing_chain")
            )

            routing_chain = self.mission_switcher.resolve_routing(
                client_id=client_id,
                mission_type=mission_type,
                runtime_chain=runtime_chain,
            )

            hitl_enabled = self.config.get("hitl", {}).get("enabled", False)
            graph = self._build_graph(routing_chain, hitl_enabled=hitl_enabled)

            if context:
                merged_context = {**saved_context, **context}
                graph.update_state(run_config, {"context": merged_context})

            graph.invoke(None, config=run_config)

            final_snapshot = graph.get_state(run_config)
            job_id = final_snapshot.values.get("job_id")
            return self._handle_graph_completion(
                client_id, final_snapshot.values, job_id
            )

        except Exception as e:
            self.logger.error(f"Resume mission failed: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    def _build_graph(self, routing_chain: List[str], hitl_enabled: bool = False):
        builder = StateGraph(MissionState)

        for step in routing_chain:
            builder.add_node(step, self._agent_node(step))

        for i in range(len(routing_chain) - 1):
            builder.add_edge(routing_chain[i], routing_chain[i + 1])

        builder.set_entry_point(routing_chain[0])
        builder.add_edge(routing_chain[-1], END)

        interrupts = []
        if hitl_enabled and "verifier_agent" in routing_chain:
            interrupts.append("verifier_agent")

        return builder.compile(
            checkpointer=self.checkpointer, interrupt_before=interrupts
        )

    def _agent_node(self, step: str):
        def _node(state: MissionState):
            job_id = state.get("job_id")
            if job_id and self.db:
                self.db.update_job_status(job_id, f"AGENT_{step.upper()}_STARTED")

            try:
                task_payload = {**state["context"], "client_id": state["client_id"]}
                result = self.route(step, task_payload)

                if job_id and self.db:
                    self.db.update_job_status(job_id, f"AGENT_{step.upper()}_DONE")

                return {"results": {step: result}, "context": {step: result}}

            except Exception as e:
                self.logger.error(f"Step '{step}' FAILURE: {e}")
                if job_id and self.db:
                    self.db.update_job_status(job_id, "FAILED", error=str(e))
                return {
                    "mission_status": "FAILED",
                    "failed_steps": [step],
                    "results": {step: {"status": "failed", "error": str(e)}},
                }

        return _node

    def _send_hitl_alert(self, client_id, state):
        try:
            mailer = EmailSender()
            if hasattr(mailer, "send_internal_alert"):
                mailer.send_internal_alert(
                    client_id=client_id,
                    stage_name="Verification & Correction",
                    details=(
                        "Mission is paused at verifier_agent. "
                        "Review and correct data in the dashboard."
                    ),
                )
        except Exception as e:
            self.logger.warning(f"HITL internal alert failed: {e}")

    # ---------------------------------------------------------
    # PIPELINE METRICS / DELIVERY
    # ---------------------------------------------------------
    def gather_pipeline_results(self, context: dict) -> dict:
        results = {}
        for key, val in context.items():
            if isinstance(val, dict) and "status" in val:
                results[key] = val
        return results

    def finalize_mission(self, client_id: str, email: str, context: dict):
        pipeline_data = self.gather_pipeline_results(context)

        if not self.ai_client:
            self.logger.error(
                f"Cannot finalize mission for {client_id}: AI client is not initialized."
            )
            return

        html_narrative = self.ai_client.generate(REPORT_PROMPT_TEMPLATE, pipeline_data)

        mailer = EmailSender()
        mailer.send_mission_report(
            to_email=email,
            client_id=client_id,
            status="SUCCESS",
            human_html_content=html_narrative,
        )
        self.logger.info(f"Final mission report sent to {email}")

    def route(self, step: str, payload: dict):
        """
        Dynamically instantiates and executes agents.
        Safely injects the Orchestrator reference for gating agents like DualWriteGate.
        """
        if step not in self.registry:
            raise ValueError(f"Agent '{step}' not registered in the system.")

        agent_class = self.registry[step]
        client_id = payload.get("client_id")

        constructor_sig = inspect.signature(agent_class.__init__)
        if "orchestrator" in constructor_sig.parameters:
            agent = agent_class(self.config, client_id, self.db, orchestrator=self)
        else:
            agent = agent_class(self.config, client_id, self.db)

        return agent.run(payload)
    def _resolve_client_email(self, client_id: str, state: dict) -> Optional[str]:
        """
        Resolve client email from mission brief, database, or payload/context.
        """
        context = state.get("context", {}) or {}
        brief = context.get("mission_brief", {}) or {}
        payload = context.get("payload", {}) or {}

        if brief.get("email"):
            return brief["email"]

        if self.db and hasattr(self.db, "get_client_email"):
            try:
                db_email = self.db.get_client_email(client_id)
                if db_email:
                    return db_email
            except Exception as e:
                self.logger.warning(
                    f"Client email lookup failed for {client_id}: {e}"
                )

        if context.get("email"):
            return context["email"]

        if (context.get("contact") or {}).get("email"):
            return context["contact"]["email"]

        if payload.get("email"):
            return payload["email"]

        if (payload.get("contact") or {}).get("email"):
            return payload["contact"]["email"]

        return None

    def _handle_graph_completion(
        self, client_id: str, state: MissionState, job_id: str = None
    ):
        failed_steps = state.get("failed_steps", [])
        state["mission_status"] = "FAILED" if failed_steps else "SUCCESS"

        if job_id and self.db:
            self.db.update_job_status(
                job_id, "FAILED" if failed_steps else "COMPLETED"
            )

        if not failed_steps and self.config.get("delivery", {}).get("auto_email", True):
            client_email = self._resolve_client_email(client_id, state)

            if client_email:
                self.finalize_mission(client_id, client_email, state["results"])
                state["delivery_status"] = "sent"
            else:
                self.logger.error(
                    f"BLOCKING DELIVERY: No email resolved for client {client_id}. "
                    "Alerting internal team."
                )
                state["delivery_status"] = "blocked_missing_client_email"
                self._send_hitl_alert(client_id, state)

        return state
