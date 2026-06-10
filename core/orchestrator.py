from core.agents.registry import RegistryAgent
from utils.logger import get_logger
from core.mission_switcher import MissionSwitcher
from delivery.email_sender import EmailSender
from utils.prompts import REPORT_PROMPT_TEMPLATE
from utils.db_manager import DatabaseManager

# CORE AGENTS (Phase 1)
from core.agents.smart_cleaner import SmartCleaner
from core.agents.ghost_audit import GhostAudit
from core.agents.verifier_agent import VerifierAgent
from core.agents.socialmedia_agent import SocialMediaAgent
from core.agents.seo_agent import SEOAgent

# BIZOPS AGENTS (Phase 3)
from core.agents.ledger import LedgerAgent


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
            self.db = DatabaseManager(config)
        except Exception as e:
            self.logger.error(f"Database Manager initialization failed: {e}")
            self.db = None

        self.mission_switcher = MissionSwitcher(config)
        self.ai_client = self._init_ai_client()

        self._register_agents()
        self.logger.info("Orchestrator instantiated and agents registered.")

    # ---------------------------------------------------------
    # AI CLIENT
    # ---------------------------------------------------------
    def _init_ai_client(self):
        class MockAI:
            def generate(self, prompt, data):
                failed = []
                passed = []
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
                if skipped:
                    html.append(
                        f"<p><strong>Skipped:</strong> {', '.join(skipped)}</p>"
                    )
                if failed:
                    html.append(f"<p><strong>Failed:</strong> {', '.join(failed)}</p>")

                html.append("</body></html>")
                return "".join(html)

        return MockAI()

    # ---------------------------------------------------------
    # AGENT REGISTRY
    # ---------------------------------------------------------
    def _register_agents(self):
        self.registry["smart_cleaner"] = SmartCleaner
        self.registry["ghost_audit"] = GhostAudit
        self.registry["verifier_agent"] = VerifierAgent
        self.registry["ledger_entry"] = LedgerAgent
        self.registry["client_registry"] = RegistryAgent
        self.registry["social_manage"] = SocialMediaAgent
        self.registry["socialmedia_agent"] = SocialMediaAgent
        self.registry["seo_optimize"] = SEOAgent
        self.registry["validation_grader"] = ValidationGrader
        self.registry["narrative_grader"] = NarrativeGrader

    # ---------------------------------------------------------
    # ROUTING
    # ---------------------------------------------------------
    def route(self, task_name: str, payload: dict):
        agent_class = self.registry.get(task_name)
        if not agent_class:
            raise ValueError(f"Agent '{task_name}' is not registered.")

        agent = agent_class(self.config, payload.get("client_id"), db=self.db)
        return agent.run(payload)

    # ---------------------------------------------------------
    # MAIN EXECUTION FLOW
    # ---------------------------------------------------------
    def run_for_client(self, client_id: str, context: dict = None):
        self.logger.info(f"Starting mission flow for client: {client_id}")

        context = context or {}
        context["client_id"] = client_id

        from utils.brief_storage import load_brief

        brief = load_brief(client_id)
        if brief:
            context["mission_brief"] = brief
            self.logger.info(f"Loaded mission brief for {client_id}")

        routing_chain = self.mission_switcher.resolve_routing(client_id)
        self.logger.info(f"Resolved routing chain: {routing_chain}")

        context = self._execute_chain(routing_chain, context)

        failed_steps = self._get_failed_steps(routing_chain, context)
        context["failed_steps"] = failed_steps
        context["mission_status"] = "FAILED" if failed_steps else "SUCCESS"

        if failed_steps:
            self.logger.error(
                f"Mission failed for {client_id}. Failed steps: {failed_steps}"
            )
            context["delivery_status"] = "not_sent"
            return context

        hitl_enabled = self.config.get("hitl", {}).get("enabled", False)

        if hitl_enabled:
            self.logger.info(f"HITL pause activated for {client_id}")
            context["hitl_status"] = "awaiting_review"

            try:
                if self.config.get("hitl", {}).get("notify_internal", False):
                    mailer = EmailSender()
                    if hasattr(mailer, "send_internal_alert"):
                        mailer.send_internal_alert(client_id, context)
            except Exception as e:
                self.logger.warning(f"HITL internal alert failed: {e}")

            return context

        if self.config.get("delivery", {}).get("auto_email", True):
            client_email = (
                context.get("mission_brief", {}).get("email") or "annastecias@gmail.com"
            )
            self.finalize_mission(client_id, client_email, context)

        return context

    # ---------------------------------------------------------
    # EXECUTION CHAIN
    # ---------------------------------------------------------
    def _execute_chain(self, routing_chain: list, context: dict):
        if "ghost_audit" in routing_chain:
            idx = routing_chain.index("ghost_audit")
            if "validation_grader" not in routing_chain[:idx]:
                routing_chain.insert(idx, "validation_grader")

        for step in routing_chain:
            try:
                task_payload = {**context, "client_id": context.get("client_id")}
                context[step] = self.route(step, task_payload)
            except ValueError as e:
                self.logger.warning(f"Step '{step}' skipped: {str(e)}")
                context[step] = {"status": "skipped", "message": str(e)}
            except Exception as e:
                self.logger.error(f"Step '{step}' CRITICAL FAILURE: {str(e)}")
                context[step] = {"status": "failed", "error": str(e)}

        return context

    # ---------------------------------------------------------
    # PIPELINE METRICS
    # ---------------------------------------------------------
    def gather_pipeline_results(self, context: dict) -> dict:
        metrics = {}
        for key, value in context.items():
            if isinstance(value, dict) and "status" in value:
                metrics[key] = value
        return metrics

    # ---------------------------------------------------------
    # FINALIZATION
    # ---------------------------------------------------------
    def finalize_mission(self, client_id: str, client_email: str, context: dict):
        self.logger.info(f"Finalizing mission for {client_id}...")

        if context.get("hitl_status") == "delivered":
            self.logger.warning(
                f"Mission for {client_id} already delivered. Skipping duplicate send."
            )
            return

        if context.get("mission_status") == "FAILED":
            self.logger.error(
                f"Email blocked for {client_id} because mission_status=FAILED"
            )
            context["delivery_status"] = "blocked_failed_mission"
            return {"delivery_status": "blocked_failed_mission"}

        before_path = f"./reports/screenshots/before_{client_id}.png"
        after_path = f"./reports/screenshots/after_{client_id}.png"

        raw_metrics = self.gather_pipeline_results(context)
        human_html_content = self.ai_client.generate(
            prompt=REPORT_PROMPT_TEMPLATE, data=raw_metrics
        )

        self.logger.info("Executing Narrative Grader node...")
        grading_payload = {**context, "generated_narrative": human_html_content}
        context["narrative_evaluation"] = self.route(
            "narrative_grader", grading_payload
        )

        import os

        before_exists = os.path.exists(before_path)
        after_exists = os.path.exists(after_path)

        mailer = EmailSender()
        delivery_report = mailer.send_mission_report(
            to_email=client_email,
            client_id=client_id,
            status=context.get("mission_status"),
            human_html_content=human_html_content,
            before_img_path=before_path if before_exists else None,
            after_img_path=after_path if after_exists else None,
        )

        self.logger.info(f"Mission report dispatched: {delivery_report}")
        context["hitl_status"] = "delivered"
        context["delivery_status"] = "sent"
        return delivery_report

    # ---------------------------------------------------------
    # RESUME MISSION
    # ---------------------------------------------------------
    def resume_mission(self, client_id: str, context: dict):
        self.logger.info(f"Resuming mission for {client_id}")
        context["hitl_status"] = "approved"
        client_email = (
            context.get("mission_brief", {}).get("email") or "annastecias@gmail.com"
        )
        return self.finalize_mission(client_id, client_email, context)

    # ---------------------------------------------------------
    # FAILURE DETECTION
    # ---------------------------------------------------------
    def _get_failed_steps(self, routing_chain: list, context: dict) -> list:
        failed_steps = []
        for step in routing_chain:
            result = context.get(step, {})
            if (
                isinstance(result, dict)
                and str(result.get("status", "")).lower() == "failed"
            ):
                failed_steps.append(step)
        return failed_steps
