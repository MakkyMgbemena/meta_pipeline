from utils.logger import get_logger

class MissionSwitcher:
    """
    Determines which mission or operational mode the pipeline should run [Source 315].
    Acts as the 'Investigator' that resolves task chains from client context [Source 484].
    """
    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger("MissionSwitcher")
        self.logger.info("Mission Switcher initialized.")

    def resolve_routing(self, client_id: str) -> list:
        """
        Returns the routing chain for a given client from config [Source 316].
        Mirrors the behavior: Context -> ordered task chain [Source 304].
        """
        # Navigate the config dictionary to find the client [Source 311]
        clients = self.config.get("meta_pipeline", {}).get("clients", {})
        client_data = clients.get(client_id)

        if not client_data:
            self.logger.warning(f"Client {client_id} not found in config. Using fallback chain.")
            return ["smart_cleaner", "ghost_audit", "verifier_agent"]

        routing_chain = client_data.get("routing_chain", [])

        # Log the trigger based on mission context [Source 294, 301]
        if "lead_nurture" in routing_chain:
            self.logger.info(f"PHASE 3 TRIGGER: Planning onboarding chain for {client_id}")
        elif "linkedin_manage" in routing_chain or "upwork_manage" in routing_chain:
            self.logger.info(f"MARKETING TRIGGER: Resolving outreach strategy for {client_id}")

        return routing_chain
