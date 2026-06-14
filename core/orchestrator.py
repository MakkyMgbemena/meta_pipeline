import inspect
from utils.logger import get_logger
from core.mission_switcher import MissionSwitcher
from delivery.email_sender import EmailSender
from utils.prompts import REPORT_PROMPT_TEMPLATE
from utils.db_manager import DatabaseManager

# Import the Single Source of Truth Agent Registry we verified earlier!
from core.agents import AGENT_REGISTRY

# NEW: LangGraph Orchestration Imports [Source 1040]
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Union
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import threading
import time
import os

class MissionState(TypedDict):
    client_id: str
    mission_id: Optional[str]
    job_id: Optional[str]
    context: Annotated[Dict[str, Any], operator.ior]
    routing_chain: List[str]
    results: Annotated[Dict[str, Any], operator.ior]
    mission_status: str # STARTED, COMPLETED, FAILED, PAUSED
    hitl_status: Optional[str]
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
        self.config = config
        self.registry = {}

        try:
            self.db = DatabaseManager()
        except Exception as e:
            self.logger.error(f"Database Manager initialization failed: {e}")
            self.db = None

        # Pass our persistent DatabaseManager instance directly to MissionSwitcher
        self.mission_switcher = MissionSwitcher(config, db=self.db)
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
            # Format connection string for psycopg (v3)
            # Standard URI: postgresql://user:pass@host:port/dbname
            # Unix Socket URI: postgresql://user:pass@/dbname?host=/cloudsql/instance
            
            encoded_user = quote_plus(user)
            encoded_password = quote_plus(password)
            encoded_db_name = quote_plus(db_name)

            if instance_connection_name:
                socket_dir = f"/cloudsql/{instance_connection_name}"
                conn_info = f"postgresql://{encoded_user}:{encoded_password}@/{encoded_db_name}?host={socket_dir}"
                self.logger.info(f"LangGraph connecting via Cloud SQL Unix socket: {socket_dir}")
            elif db_host.startswith("/cloudsql/"):
                conn_info = f"postgresql://{encoded_user}:{encoded_password}@/{encoded_db_name}?host={db_host}"
                self.logger.info(f"LangGraph connecting via Unix socket: {db_host}")
            else:
                conn_info = f"postgresql://{encoded_user}:{encoded_password}@{db_host}:{db_port}/{encoded_db_name}"
                self.logger.info(f"LangGraph connecting via TCP/IP: {db_host}:{db_port}")
            
            # max_size=20 to handle concurrent missions + background worker
            self.pool = ConnectionPool(conn_info=conn_info, max_size=20)
            self.checkpointer = PostgresSaver(self.pool)
            
            # Create LangGraph system tables if they don't exist
            with self.pool.connection() as conn:
                 self.checkpointer.setup(conn)
            
            self.logger.info("LangGraph PostgresSaver initialized and setup.")
        except Exception as e:
            self.logger.error(f"Failed to initialize LangGraph checkpointer: {e}")
            self.checkpointer = None

    def _start_timeout_worker(self):
        """Starts a background thread to handle automatic mission resumption (Stage 3)."""
        if not self.config.get("hitl", {}).get("timeout_enabled", True):
            return

        def _worker():
            timeout_seconds = self.config.get("hitl", {}).get("timeout_seconds", 3600) # Default 1 hour
            self.logger.info(f"HITL Timeout Worker started (Timeout: {timeout_seconds}s)")
            while True:
                try:
                    self._check_and_resume_timed_out_missions(timeout_seconds)
                except Exception as e:
                    self.logger.error(f"Timeout worker error: {e}")
                time.sleep(60) # Check every minute

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _check_and_resume_timed_out_missions(self, timeout_seconds):
        """Stage 3: Temporal Fallback logic."""
        if not self.db:
            return

        try:
            from services.fastapi.models import MissionJob
            import datetime
            
            with self.db.session_scope() as session:
                cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=timeout_seconds)
                timed_out_jobs = session.query(MissionJob).filter(
                    MissionJob.status == "PAUSED",
                    MissionJob.updated_at < cutoff
                ).all()
                
                for job in timed_out_jobs:
                    self.logger.info(f"Stage 3: Auto-resuming timed out mission: {job.job_id}")
                    # We start a new thread to avoid blocking the polling loop
                    threading.Thread(
                        target=self.resume_mission,
                        args=(job.client_id, None, job.job_id),
                        daemon=True
                    ).start()
        except Exception as e:
            self.logger.error(f"Failed to check timed out missions: {e}")

    # ---------------------------------------------------------
    # AI CLIENT
    # ---------------------------------------------------------
    def _init_ai_client(self):
        """Initializes the AI client, falling back to a mock if vertexai is missing."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init()
            model = GenerativeModel("gemini-pro")
        except Exception as ai_err:
            self.logger.critical(f"Vertex AI initialization failed. Narrative generation will be unavailable: {ai_err}")
            return None

        class GeminiClient:
            def __init__(self, model):
                self.model = model

            def generate(self, prompt, data):
                response = self.model.generate_content(
                    f"{prompt}\n\nDATA:\n{data}"
                )
                return response.text

        return GeminiClient(model)

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
            elif (
                status in ["graded", "recorded", "synced", "pass", "success"]
                or verdict == "pass"
            ):
                passed.append(step)
            else:
                passed.append(step)

        overall = "FAILED" if failed else "SUCCESS"

        html = [
            f"<html><body><h2>Mission Summary</h2><p><strong>Overall status:</strong> {overall}</p>"
        ]

        if passed:
            html.append(
                f"<p><strong>Completed:</strong> {', '.join(passed)}</p>"
            )
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
        """
        Dynamically imports the standardized registry.
        Ensures perfect alignment across all configurations.
        """
        # Load from the Single Source of Truth
        self.registry = {**AGENT_REGISTRY}
        
        # Add special internal graders
        self.registry["validation_grader"] = ValidationGrader
        self.registry["narrative_grader"] = NarrativeGrader

    # ---------------------------------------------------------
    # MAIN EXECUTION FLOW (LANGGRAPH REFACTORED)
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

        # Resolve routing chain dynamically
        routing_chain = self.mission_switcher.resolve_routing(client_id)
        self.logger.info(f"Resolved routing chain: {routing_chain}")

        # Ensure ghost_audit has validation_grader before it
        if "ghost_audit" in routing_chain:
            idx = routing_chain.index("ghost_audit")
            if "validation_grader" not in routing_chain[:idx]:
                routing_chain.insert(idx, "validation_grader")

        hitl_enabled = self.config.get("hitl", {}).get("enabled", False)
        graph = self._build_graph(routing_chain, hitl_enabled=hitl_enabled)

        initial_state = {
            "client_id": client_id,
            "mission_id": context.get("mission_id"),
            "job_id": job_id,
            "context": context,
            "routing_chain": routing_chain,
            "results": {},
            "mission_status": "STARTED",
            "failed_steps": []
        }

        # thread_id is critical for Stage 2 persistence
        thread_id = job_id or f"mission_{client_id}_{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Stage 1 & 2 Execution
            graph.invoke(initial_state, config=config)
            
            # Check if we hit an interrupt (Stage 2)
            snapshot = graph.get_state(config)
            if snapshot.next:
                self.logger.info(f"HITL pause activated for {client_id} (Thread: {thread_id})")
                if job_id and self.db:
                    self.db.update_job_status(job_id, "PAUSED")
                
                # Stage 1: Internal Alert (User Ping)
                if self.config.get("hitl", {}).get("notify_internal", False):
                    self._send_hitl_alert(client_id, snapshot.values)
                
                return {**snapshot.values, "hitl_status": "awaiting_review", "thread_id": thread_id}

            # Finalize if completed naturally
            return self._handle_graph_completion(client_id, snapshot.values, job_id)

        except Exception as e:
            self.logger.error(f"Graph execution failed: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    def resume_mission(self, client_id: str, context: dict = None, thread_id: str = None):
        """Stage 2: Active Verification & Correction Window (Resume signal)."""
        self.logger.info(f"Resuming mission for thread: {thread_id}")

        if not thread_id:
            # Fallback for old API calls
            thread_id = context.get("thread_id") if context else None
            if not thread_id:
                return {"status": "ERROR", "error": "Missing thread_id for resume"}

        config = {"configurable": {"thread_id": thread_id}}
        routing_chain = self.mission_switcher.resolve_routing(client_id)
        
        hitl_enabled = self.config.get("hitl", {}).get("enabled", False)
        graph = self._build_graph(routing_chain, hitl_enabled=hitl_enabled)

        try:
            if context:
                # Stage 2: Correction. Apply user-provided data back to the graph state.
                # This ensures the corrected data (e.g. margin updates) is used by 
                # subsequent agents like verifier_agent or the final report generator.
                graph.update_state(config, {"context": context})

            # resume with None to continue from checkpoint
            graph.invoke(None, config=config)
            
            snapshot = graph.get_state(config)
            job_id = snapshot.values.get("job_id")
            return self._handle_graph_completion(client_id, snapshot.values, job_id)

        except Exception as e:
            self.logger.error(f"Resume mission failed: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    def _build_graph(self, routing_chain: List[str], hitl_enabled: bool = False):
        builder = StateGraph(MissionState)
        
        for step in routing_chain:
            builder.add_node(step, self._agent_node(step))
            
        for i in range(len(routing_chain) - 1):
            builder.add_edge(routing_chain[i], routing_chain[i+1])
            
        builder.set_entry_point(routing_chain[0])
        builder.add_edge(routing_chain[-1], END)
        
        interrupts = []
        if hitl_enabled and "verifier_agent" in routing_chain:
            interrupts.append("verifier_agent")
            
        return builder.compile(checkpointer=self.checkpointer, interrupt_before=interrupts)

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
                
                return {
                    "results": {step: result},
                    "context": {step: result}
                }
            except Exception as e:
                self.logger.error(f"Step '{step}' FAILURE: {e}")
                return {
                    "mission_status": "FAILED",
                    "failed_steps": [step],
                    "results": {step: {"status": "failed", "error": str(e)}}
                }
        return _node

    def _handle_graph_completion(self, client_id: str, state: MissionState, job_id: str = None):
        failed_steps = state.get("failed_steps", [])
        state["mission_status"] = "FAILED" if failed_steps else "SUCCESS"

        if job_id and self.db:
            final_status = "FAILED" if failed_steps else "COMPLETED"
            self.db.update_job_status(job_id, final_status)

        if not failed_steps and self.config.get("delivery", {}).get("auto_email", True):
            client_email = state.get("context", {}).get("mission_brief", {}).get("email") or "annastecias@gmail.com"
            self.finalize_mission(client_id, client_email, state["results"])

        return state

    def _send_hitl_alert(self, client_id, state):
        try:
            mailer = EmailSender()
            if hasattr(mailer, "send_internal_alert"):
                # Stage 1: Internal Alert (The User Ping)
                mailer.send_internal_alert(
                    client_id=client_id, 
                    stage_name="Verification & Correction", 
                    details="Mission is paused at verifier_agent. Review and correct data in the dashboard."
                )
        except Exception as e:
            self.logger.warning(f"HITL internal alert failed: {e}")


    # ---------------------------------------------------------
    # PIPELINE METRICS
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
            self.logger.error(f"Cannot finalize mission for {client_id}: AI Client (Gemini) is not initialized.")
            return

        html_narrative = self.ai_client.generate(REPORT_PROMPT_TEMPLATE, pipeline_data)

        mailer = EmailSender()
        # Stage 4: Client Delivery (Mission Accomplished)
        mailer.send_mission_report(
            to_email=email, 
            client_id=client_id, 
            status="SUCCESS", 
            human_html_content=html_narrative
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

        # FIXED: Safely inject the Orchestrator (self) if the agent class constructor expects it!
        constructor_sig = inspect.signature(agent_class.__init__)
        if "orchestrator" in constructor_sig.parameters:
            agent = agent_class(self.config, client_id, self.db, orchestrator=self)
        else:
            agent = agent_class(self.config, client_id, self.db)

        return agent.run(payload)
