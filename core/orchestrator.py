from utils.logger import get_logger
from core.mission_switcher import MissionSwitcher

# CORE AGENTS (Phase 1)
from core.agents.smart_cleaner import SmartCleaner
from core.agents.ghost_audit import GhostAudit
from core.agents.verifier_agent import VerifierAgent
from core.agents.socialmedia_agent import SocialMediaAgent

# BIZOPS AGENTS (Phase 3)
from core.agents.ledger import LedgerAgent
from core.agents.registry import RegistryAgent

class Orchestrator:
    def __init__(self, config: dict):
        self.logger = get_logger("Orchestrator")
        self.config = config
        self.registry = {}
        
        # FIX: Passes config to MissionSwitcher to resolve TypeError [8]
        self.mission_switcher = MissionSwitcher(config)
        
        self._register_agents()
        self.logger.info("Orchestrator instantiated and agents registered.")

    def _register_agents(self):
        """Maps internal agent names to their respective classes [9, 10]."""
        self.registry["smart_cleaner"] = SmartCleaner
        self.registry["ghost_audit"] = GhostAudit
        self.registry["verifier_agent"] = VerifierAgent
        self.registry["ledger_entry"] = LedgerAgent
        self.registry["client_registry"] = RegistryAgent
        self.registry["social_manage"] = SocialMediaAgent
        self.registry["socialmedia_agent"] = SocialMediaAgent

    def route(self, task_name: str, payload: dict):
        """Dispatches a single task with forced Identity Injection [9, 10]."""
        agent_class = self.registry.get(task_name)
        if not agent_class:
            raise ValueError(f"Agent '{task_name}' is not registered.")
        
        # Pass config and client_id to the agent for context-aware execution
        agent = agent_class(self.config, payload.get("client_id"))
        return agent.run(payload)

    def run_for_client(self, client_id: str, context: dict = None):
        """Executes the complete routing chain for a specific client [11]."""
        self.logger.info(f"Starting mission flow for client: {client_id}")
        
        # Use the context provided by the API, or default to a basic one
        if context is None:
            context = {"client_id": client_id}
            
        # Get the routing chain from the Mission Switcher
        routing_chain = self.mission_switcher.resolve_routing(client_id)
        self.logger.info(f"Resolved routing chain: {routing_chain}")
        
        # Execute the chain using the provided context
        return self._execute_chain(routing_chain, context)

    def _execute_chain(self, routing_chain: list, context: dict):
        """Iterates through the chain with Phase 1 Graceful Skip logic [12, 13]."""
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