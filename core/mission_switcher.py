from utils.logger import get_logger

class MissionSwitcher:
    """
    Determines which mission or operational mode the pipeline should run.
    Acts as the 'Investigator' that resolves task chains from live client context.
    """
    def __init__(self, config: dict, db=None):
        self.config = config
        self.logger = get_logger("MissionSwitcher")
        self.db = db  # FIXED: Inject the DatabaseManager we verified!
        self.logger.info("Mission Switcher successfully initialized.")

    def resolve_routing(self, client_id: str) -> list:
        """
        Returns the routing chain for a given client.
        Prioritizes dynamic database configurations over static config files.
        """
        routing_chain = []

        # 1. DYNAMIC STEP: Attempt to load routing dynamically from PostgreSQL
        if self.db:
            try:
                with self.db.session_scope() as session:
                    # Query the client_registry table that we verified exists in SQL Studio!
                    # Supposing client_registry has client_id and a routing_chain (JSON or string array) field
                    from services.fastapi.models import ClientRegistry
                    client_record = session.query(ClientRegistry).filter_by(client_id=client_id).first()
                    
                    if client_record and hasattr(client_record, 'routing_chain') and client_record.routing_chain:
                        routing_chain = client_record.routing_chain
                        self.logger.info(f"Loaded dynamic database routing chain for client {client_id}: {routing_chain}")
            except Exception as db_err:
                self.logger.warning(f"Database routing lookup failed, falling back to static config. Details: {db_err}")

        # 2. STATIC FALLBACK: If no database override found, search the static config dictionary
        if not routing_chain:
            clients = self.config.get("meta_pipeline", {}).get("clients", {})
            client_data = clients.get(client_id)

            if client_data:
                routing_chain = client_data.get("routing_chain", [])
                self.logger.info(f"Loaded static config routing chain for client {client_id}: {routing_chain}")

        # 3. ABSOLUTE FALLBACK: Fallback to configurable default chain
        if not routing_chain:
            default_chain = self.config.get("meta_pipeline", {}).get(
                "default_routing_chain", 
                ["smart_cleaner", "ghost_audit", "verifier_agent"]  # Safe default fallback
            )
            self.logger.warning(f"Client {client_id} not found in DB or config. Using default fallback chain: {default_chain}")
            return default_chain

        # 4. Phase/Marketing Trigger Warnings (Unchanged but cleaned)
        if "lead_nurture" in routing_chain:
            self.logger.info(f"PHASE 3 TRIGGER: Planning onboarding chain for {client_id}")
        elif any(agent in routing_chain for agent in ["linkedin_manage", "upwork_manage"]):
            self.logger.info(f"MARKETING TRIGGER: Resolving outreach strategy for {client_id}")

        return routing_chain
