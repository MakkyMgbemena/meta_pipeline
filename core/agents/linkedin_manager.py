import os
from core.unified_agent import UnifiedAgent
from utils.logger import get_logger

class LinkedInManager(UnifiedAgent):
    """Generates targeted outbound engagement and algorithmic hashtag clusters for LinkedIn."""

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        # Inherit from UnifiedAgent to get shared logging and config access
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("LinkedInManager")
        # Store the database manager (such as the one we just configured!)
        self.db = db 

    def run(self, payload: dict = None) -> dict:
        """
        Executes the LinkedIn agent to generate high-performing outbound strategies.
        Accepts dynamic variables inside the payload to override defaults.
        """
        payload = payload or {}
        self.logger.info(f"LinkedIn Manager Agent activated for client: {self.client_id}")

        try:
            # 1. Dynamically read inputs from payload or fall back to configuration/defaults
            market_region = payload.get("region", "Greater Toronto Area")
            target_roles = payload.get("roles", ["COO", "VP Operations"])
            target_scale = payload.get("scale", ["SMB", "Agency"])
            
            # Construct boolean search query dynamically
            roles_query = " OR ".join(f'"{role}"' for role in target_roles)
            scale_query = " OR ".join(f'"{scale}"' for scale in target_scale)
            boolean_search = f"({roles_query}) AND ({scale_query})"

            # 2. Extract context-aware hooks
            outbound_hook = payload.get(
                "custom_hook", 
                "Building a bridge between business goals and affordable AI systems."
            )

            # Algorithmic hashtag clusters matching the specific target domain
            target_clusters = payload.get(
                "hashtags", 
                ["#OperationsManagement", "#Scalability", "#FractionalCOO", "#BusinessOperations"]
            )

            # 3. Create the blueprint payload
            engagement_plan = {
                "platform": "LinkedIn",
                "market_region": market_region,
                "target_clusters": target_clusters,
                "boolean_search": boolean_search,
                "outbound_hook": outbound_hook,
            }

            # 4. Use the DB to record the generation if database manager is active
            if self.db and self.client_id:
                try:
                    # Log the generation in the client registry or dedicated ledger
                    self.db.update_registry(self.client_id, f"LinkedIn Blueprint Generated for {market_region}")
                    self.logger.info("Successfully recorded blueprint generation to database.")
                except Exception as db_err:
                    self.logger.warning(f"Failed to record execution to database: {db_err}")

            self.logger.info("LinkedIn engagement blueprint generated successfully.")
            return {
                "status": "success", 
                "client_id": self.client_id,
                "engagement_plan": engagement_plan
            }

        except Exception as e:
            self.logger.error(f"Failed to run LinkedInManager execution: {e}", exc_info=True)
            return {
                "status": "failure",
                "error": str(e)
            }
