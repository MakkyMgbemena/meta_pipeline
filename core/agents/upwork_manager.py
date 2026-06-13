import os
from core.unified_agent import UnifiedAgent
from utils.logger import get_logger

class UpworkManager(UnifiedAgent):
    """Handles Upwork profile optimization and project proposal logic with multi-market pricing."""

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("UpworkManager")
        self.db = db

    def run(self, payload: dict = None) -> dict:
        """
        Generates calculated strategies and dynamic client proposals.
        Fixes the variable overwrite bug and anchors rates to configuration.
        """
        payload = payload or {}
        self.logger.info(f"Upwork Strategic Agent activated for client: {self.client_id}")

        try:
            # 1. Pull base pricing dynamically from configuration
            base_price = (
                self.config.get("bizops", {})
                .get("revenue_tracking", {})
                .get("fiverr_basic_package_price", 65.0)
            )
            self.logger.info(f"Upwork baseline tier calculated from configuration: ${base_price}")

            # 2. Allow dynamic customization of focus and rates via the payload
            niche_focus = payload.get("focus", "Enterprise Data Auditing & Compliance")
            
            # Calculate dynamic hourly targets anchored to the baseline price, or use payload overrides
            min_hourly = payload.get("min_hourly_rate", int(base_price * 1.15))
            max_hourly = payload.get("max_hourly_rate", int(base_price * 2.3))
            currency = payload.get("currency", "CAD")
            
            hourly_rate_target = f"{min_hourly} - {max_hourly} {currency}"

            proposal_hook = payload.get(
                "proposal_hook",
                "Providing <1% error rate data pipelines for growth-stage agencies."
            )

            # 3. Create a single, merged strategy dictionary (BUG FIXED)
            strategy = {
                "platform": "Upwork",
                "baseline_price": base_price,
                "focus": niche_focus,
                "hourly_rate_target": hourly_rate_target,
                "proposal_hook": proposal_hook,
                "calculated_at_utc": "2026-06-13T15:43:41Z"  # Standardized audit timestamp
            }

            # 4. Save the generated strategy to the DB if active
            if self.db and self.client_id:
                try:
                    self.db.update_registry(self.client_id, f"Upwork Strategy Generated ({niche_focus})")
                    self.logger.info("Successfully recorded Upwork strategy to database.")
                except Exception as db_err:
                    self.logger.warning(f"Failed to save Upwork strategic profile: {db_err}")

            self.logger.info("Upwork market strategy generated successfully.")
            return {
                "status": "success",
                "client_id": self.client_id,
                "strategy": strategy
            }

        except Exception as e:
            self.logger.error(f"Failed to generate Upwork strategy: {e}", exc_info=True)
            return {
                "status": "failure",
                "error": str(e)
            }
