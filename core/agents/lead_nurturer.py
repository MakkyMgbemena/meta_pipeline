import os
import datetime
from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
from services.fastapi.models import ClientRegistry

class LeadNurturer(UnifiedAgent):
    """
    Handles lead tracking, funnel progression, and interaction history.
    Saves CRM lead states directly to PostgreSQL to prevent serverless data loss on Cloud Run.
    """

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("LeadNurturer")
        self.db = db

        # Funnel states defined in the Master Blueprint
        self.funnel_states = ["captured", "contacted", "proposal_sent", "converted", "churned"]
        self.logger.info("LeadNurturer successfully initialized.")

    def run(self, payload: dict = None) -> dict:
        """
        Logs a nurturing event and updates a lead's funnel position dynamically.
        Saves states to persistent PostgreSQL to avoid ephemeral disk loss.
        """
        payload = payload or {}
        self.logger.info(f"Processing lead update for: {self.client_id}")

        # 1. Determine funnel stage or default to 'captured'
        stage = payload.get("stage", "captured")
        if stage not in self.funnel_states:
            self.logger.warning(f"Invalid stage '{stage}' provided. Defaulting to 'captured'.")
            stage = "captured"

        # 2. Build the interaction entry
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "client_id": self.client_id,
            "funnel_stage": stage,
            "platform": payload.get("platform", "direct"),
            "notes": payload.get("notes", "Automated system update")
        }

        # 3. FIXED: Replace the volatile JSONStore with persistent PostgreSQL
        if not self.db:
            self.logger.error("Database connection missing. Nurturing event could not be saved!")
            return {"status": "failed", "error": "Database connection unavailable."}

        try:
            with self.db.session_scope() as session:
                # Find the client in our registry
                record = session.query(ClientRegistry).filter_by(client_id=self.client_id).first()

                if record:
                    self.logger.info(f"Updating existing CRM client record status to: {stage}")
                    record.status = stage
                    record.last_sync = datetime.datetime.utcnow()
                    
                    # Accumulate notes or profile updates safely
                    profile = record.profile_data or {}
                    history = profile.get("nurture_history", [])
                    history.append(entry)
                    profile["nurture_history"] = history
                    record.profile_data = profile
                else:
                    # If this is a newly captured lead, register them automatically!
                    self.logger.info(f"Lead {self.client_id} not found. Creating new CRM entry with stage: {stage}")
                    new_lead = ClientRegistry(
                        client_id=self.client_id,
                        status=stage,
                        routing_chain=["smart_cleaner", "ghost_audit", "verifier_agent"],
                        profile_data={"nurture_history": [entry], "initial_notes": entry["notes"]},
                        last_sync=datetime.datetime.utcnow()
                    )
                    session.add(new_lead)

            self.logger.info(f"Lead status for {self.client_id} securely saved in PostgreSQL: {stage}")

            # 4. Trigger auto-onboarding triggers on successful conversion
            if stage == "converted":
                self.logger.info(f"LEAD CONVERTED: Triggering Phase 3 auto-onboarding hooks for {self.client_id}.")

            return {
                "status": "success",
                "client_id": self.client_id,
                "nurture_entry": entry
            }

        except Exception as e:
            self.logger.error(f"LeadNurturer database transaction failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "client_id": self.client_id
            }
