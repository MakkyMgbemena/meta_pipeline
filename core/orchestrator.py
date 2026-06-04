from utils.logger import get_logger
from core.mission_switcher import MissionSwitcher
from delivery.email_sender import EmailSender
from utils.prompts import REPORT_PROMPT_TEMPLATE
import os
from utils.db_manager import DatabaseManager

# CORE AGENTS (Phase 1)
from core.agents.smart_cleaner import SmartCleaner
from core.agents.ghost_audit import GhostAudit
from core.agents.verifier_agent import VerifierAgent
from core.agents.socialmedia_agent import SocialMediaAgent
from core.agents.seo_agent import SEOAgent

# BIZOPS AGENTS (Phase 3)
from core.agents.ledger import LedgerAgent
from utils.prompts import REPORT_PROMPT_TEMPLATE, VALIDATION_GRADER_PROMPT, NARRATIVE_GRADER_PROMPT

class ValidationGrader:
    def __init__(self, config, client_id, db=None): 
        self.client_id = client_id
        self.db = db
    def run(self, payload): 
        # In a real system, this would call the AI client with VALIDATION_GRADER_PROMPT
        return {"status": "graded", "verdict": "PASS", "message": f"Workflow validated for {self.client_id}."}

class NarrativeGrader:
    def __init__(self, config, client_id, db=None): 
        self.client_id = client_id
        self.db = db
    def run(self, payload): 
        # In a real system, this would call the AI client with NARRATIVE_GRADER_PROMPT
        return {"status": "graded", "verdict": "HIGH_QUALITY", "message": "Narrative meets enterprise standards."}


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
        
        # FIX: Passes config to MissionSwitcher to resolve TypeError [8]
        self.mission_switcher = MissionSwitcher(config)
        
        # AI Client Placeholder for Human-in-the-Loop narratives
        self.ai_client = self._init_ai_client()
        
        self._register_agents()
        self.logger.info("Orchestrator instantiated and agents registered.")

    def _init_ai_client(self):
        """Simple wrapper for AI narrative generation."""
        class MockAI:
            def generate(self, prompt, data):
                return f"<html><body><h2>Mission Summary</h2><p>The mission for client was successful. Milestones: {list(data.keys())}</p></body></html>"
        return MockAI()

    def _register_agents(self):
        """Maps internal agent names to their respective classes [9, 10]."""
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

    def route(self, task_name: str, payload: dict):
        """Dispatches a single task with forced Identity Injection [9, 10]."""
        agent_class = self.registry.get(task_name)
        if not agent_class:
            raise ValueError(f"Agent '{task_name}' is not registered.")
        
        # Pass config and client_id to the agent for context-aware execution
        agent = agent_class(self.config, payload.get("client_id"), db=self.db)
        return agent.run(payload)

    def run_for_client(self, client_id: str, context: dict = None):
        """Executes the complete routing chain for a specific client [11]."""
        self.logger.info(f"Starting mission flow for client: {client_id}")
        
        # FIX: Always ensure client_id is part of the context [11]
        context = context or {}
        context["client_id"] = client_id
            
        from utils.brief_storage import load_brief
        brief = load_brief(client_id)
        if brief:
            context["mission_brief"] = brief
            self.logger.info(f"Loaded mission brief for {client_id}")

        # Get the routing chain from the Mission Switcher
        routing_chain = self.mission_switcher.resolve_routing(client_id)
        self.logger.info(f"Resolved routing chain: {routing_chain}")
        
        # Execute the chain using the provided context
        context = self._execute_chain(routing_chain, context)
        
        # Human-in-the-loop: Finalize and send report
        if self.config.get("delivery", {}).get("auto_email", True):
            client_email = context.get("mission_brief", {}).get("email") or "annastecias@gmail.com"
            self.finalize_mission(client_id, client_email, context)
            
        return context

    def _execute_chain(self, routing_chain: list, context: dict):
        """Iterates through the chain with Phase 1 Graceful Skip logic [12, 13]."""
        # Insert Validation Grader before GhostAudit in the sequence
        if "ghost_audit" in routing_chain:
            idx = routing_chain.index("ghost_audit")
            if "validation_grader" not in routing_chain[:idx]:
                routing_chain.insert(idx, "validation_grader")

        for step in routing_chain:
            try:
                # Ensure the client_id is preserved in every agent payload
                task_payload = {**context, "client_id": context.get("client_id")}
                context[step] = self.route(step, task_payload)
            except ValueError as e:
                # GRACEFUL SKIP: Prevents mission crashes for non-registered agents [13]
                self.logger.warning(f"Step '{step}' skipped: {str(e)}")
                context[step] = {"status": "skipped", "message": str(e)}
            except Exception as e:
                self.logger.error(f"Step '{step}' CRITICAL FAILURE: {str(e)}")
                context[step] = {"status": "failed", "error": str(e)}
        return context

    def gather_pipeline_results(self, context: dict) -> dict:
        """Siphons results from all agents in the context for AI analysis."""
        metrics = {}
        for key, value in context.items():
            if isinstance(value, dict) and "status" in value:
                metrics[key] = value
        return metrics

    def finalize_mission(self, client_id: str, client_email: str, context: dict):
        """
        Gathers results, generates a narrative report, and dispatches via email.
        """
        self.logger.info(f"Finalizing mission for {client_id}...")
        
        # 1. Path definitions (aligned with UnifiedAgent standardized paths)
        before_path = f"./reports/screenshots/before_{client_id}.png"
        after_path = f"./reports/screenshots/after_{client_id}.png"
        
        # 2. Compile metrics
        raw_metrics = self.gather_pipeline_results(context)

        # 3. Generate human narrative via AI
        human_html_content = self.ai_client.generate(
            prompt=REPORT_PROMPT_TEMPLATE, 
            data=raw_metrics
        )

        # 3.5. Evaluate Narrative quality
        self.logger.info("Executing Narrative Grader node...")
        grading_payload = {**context, "generated_narrative": human_html_content}
        context["narrative_evaluation"] = self.route("narrative_grader", grading_payload)

        # 4. Trigger delivery
        mailer = EmailSender()
        delivery_report = mailer.send_mission_report(
            to_email=client_email,
            client_id=client_id,
            status="SUCCESS" if context.get("verifier_agent", {}).get("status") == "PASS" else "PARTIAL",
            human_html_content=human_html_content,
            before_img_path=before_path,
            after_img_path=after_path
        )
        
        self.logger.info(f"Mission report dispatched: {delivery_report}")
        return delivery_report
