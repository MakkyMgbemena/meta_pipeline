from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
from utils.json_store import JSONStore
from pathlib import Path
import datetime

class LeadNurturer(UnifiedAgent):
    """
    Handles lead tracking, funnel progression, and interaction history.
    Aligns with Phase 3 CRM goals: capture, contact, and conversion tracking.
    """

    # Path aligned with Phase 3 Internal Operations vault
    NURTURE_LOG_PATH = "data/internal/lead_nurture_log.json"

    def __init__(self, config: dict, client_id: str = None, db=None):
        super().__init__(config, client_id, db)
        self.logger = get_logger("LeadNurturer")

        # Ensure the internal data directory exists safely
        Path("data/internal").mkdir(parents=True, exist_ok=True)
        self.store = JSONStore(self.NURTURE_LOG_PATH)

        # Funnel states defined in the Master Blueprint [3]
        self.funnel_states = ["captured", "contacted", "proposal_sent", "converted", "churned"]
        self.logger.info("LeadNurturer initialized.")

    def run(self, payload: dict = None):
        """
        Logs a nurturing event or updates a lead's funnel position.
        Tracks preferred communication platforms (X, Instagram, LinkedIn).
        """
        self.logger.info(f"Processing lead update for: {self.client_id}")

        # Determine funnel stage or default to 'captured'
        stage = payload.get("stage", "captured") if payload else "captured"
        if stage not in self.funnel_states:
            self.logger.warning(f"Invalid stage '{stage}' provided. Defaulting to 'captured'.")
            stage = "captured"

        # Build the interaction entry
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "client_id": self.client_id,
            "funnel_stage": stage,
            "platform": payload.get("platform", "direct") if payload else "direct",
            "notes": payload.get("notes", "Automated system update") if payload else "Initial capture"
        }

        # Use the durable append-safe storage engine
        self.store.append(entry)
        self.logger.info(f"Lead status for {self.client_id} updated to: {stage}")

        # Trigger onboarding hook if converted [3]
        if stage == "converted":
            self.logger.info(f"LEAD CONVERTED: Triggering Phase 3 auto-onboarding hooks for {self.client_id}.")

        return {"status": "success", "nurture_entry": entry}
