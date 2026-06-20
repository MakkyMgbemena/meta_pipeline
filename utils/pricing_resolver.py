from utils.logger import get_logger

class PricingResolver:
    def __init__(self, config: dict, db=None):
        self.config = config
        self.db = db
        self.logger = get_logger("PricingResolver")

    def resolve_service_price(self, client_id: str, service_name: str, context: dict) -> dict:
        """
        Climbs the priority ladder to resolve pricing for a specific service.
        Follows config.yaml pricing_policy.service_models.[service].source_priority
        """
        policy = self.config.get("meta_pipeline", {}).get("pricing_policy", {})
        service_cfg = policy.get("service_models", {}).get(service_name, {})

        # 1. Get the Priority Ladder from Config
        priority_ladder = service_cfg.get("source_priority", [])

        # 2. Iterate through sources in order
        for source in priority_ladder:
            price = self._check_source(source, client_id, service_name, context)
            if price:
                self.logger.info(f"Resolved price for {service_name} via {source}: {price}")
                return price

        # 3. Handle Unresolved Pricing (Enterprise Safeguard)
        action = policy.get("unresolved_pricing_action", "flag_for_hitl")
        self.logger.warning(f"Pricing unresolved for {service_name}. Action: {action}")

        if action == "flag_for_hitl":
            return {"status": "UNRESOLVED", "requires_hitl": True}

        return {"status": "ERROR", "message": "No pricing found"}

    def _check_source(self, source: str, client_id: str, service_name: str, context: dict):
        """Helper to extract price data from various nested sources."""
        brief = context.get("mission_brief", {})
        payload = context.get("payload", {})

        # Source Mapping
        if source == "mission_brief.services." + service_name:
            return brief.get("services", {}).get(service_name)

        if source == "payload.services." + service_name:
            return payload.get("services", {}).get(service_name)

        if source == "client_registry.services." + service_name and self.db:
            # Check the PostgreSQL Registry
            from services.fastapi.models import ClientRegistry
            with self.db.session_scope() as session:
                record = session.query(ClientRegistry).filter_by(client_id=client_id).first()
                if record and record.services_config:
                    return record.services_config.get(service_name)

        if "pricing_policy.rules" in source:
            # Fallback to the hardcoded rules in config.yaml
            return self.config.get("meta_pipeline", {}).get("pricing_policy", {}).get("service_models", {}).get(service_name, {}).get("rules")

        return None
