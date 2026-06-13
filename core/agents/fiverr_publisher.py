import os
from core.unified_agent import UnifiedAgent
from utils.logger import get_logger

class FiverrPublisher(UnifiedAgent):
    """
    Generates optimized Fiverr Gig content based on the Master Blueprint.
    Tiers are dynamically calculated and grounded in system configuration.
    """

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("FiverrPublisher")
        self.db = db

    def run(self, payload: dict = None) -> dict:
        """
        Generates calculated tiers and descriptions dynamically.
        Accepts dynamic variables from the payload to customize the gig focus.
        """
        payload = payload or {}
        self.logger.info(f"Fiverr Gig Profile Agent activated for client: {self.client_id}")

        try:
            # 1. Pull base pricing dynamically from config with fallbacks
            gig_config = self.config.get("meta_pipeline", {}).get("pricing", {}).get("fiverr_smart_cleaner_gig", {})
            base_price = gig_config.get("amount", 65.0)
            currency = gig_config.get("currency", "CAD")

            # Move multipliers to config or fallback to defaults
            standard_multiplier = gig_config.get("standard_multiplier", 2.3)
            premium_multiplier = gig_config.get("premium_multiplier", 5.4)

            # 2. Allow dynamic customization of the gig focus via the payload
            niche = payload.get("data_niche", "datasets")  # e.g., "financial ledgers", "real estate leads"
            custom_title = payload.get("title")
            custom_desc = payload.get("description")

            # Construct dynamic title and description if not explicitly provided
            title = custom_title or f"I will perform a high-accuracy multi-agent AI {niche} cleaning and audit"
            description = custom_desc or (
                f"Stop manual spreadsheet scrubbing. I use a production-grade multi-agent "
                f"AI pipeline to clean, normalize, and audit your {niche} with <1% error rates."
            )

            # 3. Build the calculated gig profile
            gig_profile = {
                "title": title,
                "description": description,
                "tiers": {
                    "Basic": {
                        "price": f"{base_price:.2f} {currency}",
                        "depth": "SmartCleaner (4-Pass Deduplication & Normalization)",
                        "delivery": payload.get("basic_delivery", "2 Days")
                    },
                    "Standard": {
                        "price": f"{(base_price * standard_multiplier):.0f} {currency}",
                        "depth": "SmartCleaner + GhostAudit + Risk Report",
                        "delivery": payload.get("standard_delivery", "3 Days")
                    },
                    "Premium": {
                        "price": f"{(base_price * premium_multiplier):.0f} {currency}",
                        "depth": "Full UnifiedAgent Chain + Internal Ledger Integration",
                        "delivery": payload.get("premium_delivery", "5 Days")
                    }
                },
                "technical_hook": "Powered by a decoupled MetaOrchestrator architecture for 100% data integrity."
            }

            # 4. Save the generated profile to the DB if active
            if self.db and self.client_id:
                try:
                    self.db.update_registry(self.client_id, f"Fiverr Gig Profile Created ({niche})")
                    self.logger.info("Successfully recorded gig generation to database.")
                except Exception as db_err:
                    self.logger.warning(f"Failed to save gig profile metadata: {db_err}")

            self.logger.info(f"Gig profile generated successfully for {currency} market baseline.")
            return {
                "status": "success",
                "client_id": self.client_id,
                "gig_profile": gig_profile
            }

        except Exception as e:
            self.logger.error(f"Failed to generate Fiverr gig profile: {e}", exc_info=True)
            return {
                "status": "failure",
                "error": str(e)
            }
