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

    def resolve_routing(self, client_id: str, mission_type: str = None, runtime_chain: list = None) -> list:
        """
        Enterprise Resolver: Implements backward-compatible, layered resolution logic.
        Follows the tiered priority: Runtime > Database > Client Profile > Global Defaults.
        """
        routing_chain = []

        # 1. EXPLICIT RUNTIME OVERRIDE
        if runtime_chain:
            self.logger.info(f"Using explicit runtime routing chain provided in payload: {runtime_chain}")
            return runtime_chain

        # 2. DYNAMIC DATABASE LOOKUP (Legacy Primary)
        if self.db:
            try:
                with self.db.session_scope() as session:
                    from services.fastapi.models import ClientRegistry
                    client_record = session.query(ClientRegistry).filter_by(client_id=client_id).first()

                    if client_record and hasattr(client_record, 'routing_chain') and client_record.routing_chain:
                        routing_chain = client_record.routing_chain
                        self.logger.info(f"Loaded dynamic DB routing for client {client_id}: {routing_chain}")
                        return routing_chain
            except Exception as db_err:
                self.logger.warning(f"Database lookup failed, falling back to config: {db_err}")

        # 3. STATIC CONFIG RESOLUTION (The Nested Resolver)
        meta = self.config.get("meta_pipeline", {})
        clients = meta.get("clients", {})
        client_data = clients.get(client_id, {})

        # A. LEGACY FALLBACK: Check for flat 'routing_chain' in client root
        if "routing_chain" in client_data:
            routing_chain = client_data.get("routing_chain")
            self.logger.info(f"Loaded legacy static chain for {client_id}: {routing_chain}")
            return routing_chain

        # B. CLIENT-SPECIFIC PROFILE RESOLUTION (New Model)
        if mission_type:
            routing_profile = client_data.get("routing_profile", {})
            type_defaults = routing_profile.get("mission_type_defaults", {})
            routing_chain = type_defaults.get(mission_type)
            if routing_chain:
                # Resolve the named chain (e.g., 'social_mission') to the actual list
                routing_chain = self._get_global_default(routing_chain)
                self.logger.info(f"Resolved client-profile mission '{mission_type}' for {client_id}")
                return routing_chain

        # 4. GLOBAL POLICY RESOLUTION (routing_resolution.default_chains)
        routing_res = meta.get("routing_resolution", {})
        if mission_type:
            # Check global defaults for this specific mission type
            routing_chain = routing_res.get("default_chains", {}).get(mission_type)
            if routing_chain:
                self.logger.info(f"Resolved via global default_chains for type: {mission_type}")
                return routing_chain

        # 5. ABSOLUTE FALLBACK (Maintain stability)
        # Check new absolute default first, then legacy flat default
        fallback = routing_res.get("default_chain") or \
                   meta.get("default_routing_chain") or \
                   ["smart_cleaner", "ghost_audit", "verifier_agent"]

        # If the fallback is a string (name of a chain), resolve it
        if isinstance(fallback, str):
            fallback = self._get_global_default(fallback)

        self.logger.warning(f"No specific routing for {client_id}/{mission_type}. Using fallback: {fallback}")
        return fallback

    def _get_global_default(self, chain_name: str) -> list:
        """Helper to resolve a named chain string into its actual list of agents."""
        defaults = self.config.get("meta_pipeline", {}).get("routing_resolution", {}).get("default_chains", {})
        # If it's already a list, return it; if it's a key in defaults, return that list.
        if isinstance(chain_name, list):
            return chain_name
        return defaults.get(chain_name, ["smart_cleaner", "ghost_audit", "verifier_agent"])
