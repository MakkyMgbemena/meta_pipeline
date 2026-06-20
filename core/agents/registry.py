from core.unified_agent import UnifiedAgent
from services.fastapi.models import ClientRegistry
import datetime

class RegistryAgent(UnifiedAgent):
    """
    Phase 3 Client Lifecycle Engine.
    Tracks onboarding, profile updates, and status in the PostgreSQL headquarters.
    """

    def run(self, payload: dict = None) -> dict:
        """
        Syncs or registers the client lifecycle status and metadata in the database vault.
        Accepts client profile or routing configurations dynamically within the payload.
        """
        payload = payload or {}
        self.logger.info(f"Syncing lifecycle registry in PostgreSQL for client: {self.client_id}")

        # Default status for a successful pipeline run
        target_status = payload.get("status", "active")

        # Extract onboarding configurations or profiles if present in the payload
        profile_data = payload.get("profile") or payload.get("profile_data")
        routing_chain = payload.get("routing_chain")

        try:
            if not self.db:
                raise ValueError("Database vault connection is not available.")

            with self.db.session_scope() as session:
                # Query if the client already exists in the database
                record = session.query(ClientRegistry).filter_by(client_id=self.client_id).first()

                if record:
                    # Update existing client record
                    self.logger.info(f"Existing client record found. Updating status to: {target_status}")
                    record.status = target_status
                    record.last_sync = datetime.datetime.utcnow()

                    # Update profile and routing if new values are provided
                    if profile_data:
                        record.profile_data = profile_data
                    if routing_chain:
                        record.routing_chain = routing_chain

                    action = "updated"
                else:
                    # FIXED: Auto-create the record if this is a brand new client onboarding!
                    self.logger.info(f"Client {self.client_id} not found in database. Initializing automatic onboarding registration...")

                    new_client = ClientRegistry(
                        client_id=self.client_id,
                        status=target_status,
                        routing_chain=routing_chain or ["smart_cleaner", "ghost_audit", "verifier_agent"],
                        profile_data=profile_data or {},
                        last_sync=datetime.datetime.utcnow()
                    )
                    session.add(new_client)
                    action = "registered"

            self.logger.info(f"Registry successfully {action} in PostgreSQL for {self.client_id} with status: {target_status}")
            return {
                "registry_status": "synced",
                "action": action,
                "status": target_status,
                "client_id": self.client_id
            }

        except Exception as e:
            self.logger.error(f"PostgreSQL Registry sync failed: {e}", exc_info=True)
            return {
                "registry_status": "failed",
                "error": str(e),
                "client_id": self.client_id
            }
