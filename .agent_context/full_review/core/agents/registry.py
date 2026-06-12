from core.unified_agent import UnifiedAgent

class RegistryAgent(UnifiedAgent):
    """
    Phase 3 Client Lifecycle Engine.
    Tracks onboarding and status in the PostgreSQL headquarters [Source 361, 493].
    """
    def run(self, payload: dict = None) -> dict:
        self.logger.info(f"Updating registry in PostgreSQL for client: {self.client_id}")

        # Standard status for a successful pipeline run
        target_status = "active"

        try:
            # FIX: Passes both client_id AND status to resolve the positional argument error
            self.db.update_registry(self.client_id, target_status)

            self.logger.info(f"Registry synced in PostgreSQL for {self.client_id} with status: {target_status}")
            return {"registry_status": "synced", "status": target_status}

        except Exception as e:
            self.logger.error(f"PostgreSQL Registry update failed: {e}")
            return {"registry_status": "failed", "error": str(e)}
