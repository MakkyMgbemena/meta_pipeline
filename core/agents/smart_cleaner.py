from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
from utils.file_utils import normalize_text, clean_whitespace

class SmartCleaner(UnifiedAgent):
    """
    Cleans, normalizes, and prepares client data.
    Acts as the robust entry-gate agent in the routing chain.
    """

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("SmartCleaner")
        self.db = db

        # FIXED: Fields that MUST NEVER be altered or normalized to prevent authorization or URL breakage
        self.protected_keys = {
            "client_id", "job_id", "api_key", "token", "url",
            "email", "password", "db_pass", "secret"
        }

    def run(self, payload: dict = None) -> dict:
        """
        Executes the cleaning pipeline.
        Payload can be raw text, dicts, or tabular-like structures.
        """
        self.logger.info(f"SmartCleaner started for client '{self.client_id}'.")

        if payload is None:
            self.logger.warning("No payload provided. Nothing to clean.")
            return {"status": "skipped", "reason": "empty_payload"}

        try:
            # FIXED: Keep track of visited object IDs to prevent circular reference stack overflows
            visited_ids = set()
            cleaned_data = self._clean_payload(payload, visited_ids)

            # Log successful cleaning metadata to PostgreSQL DB
            if self.db and self.client_id:
                try:
                    self.db.update_registry(self.client_id, "Data Sanitization Completed")
                except Exception as db_err:
                    self.logger.warning(f"Failed to update database registry: {db_err}")

            self.logger.info("SmartCleaner completed successfully.")
            return {
                "status": "success",
                "client_id": self.client_id,
                "data": cleaned_data
            }

        except Exception as e:
            self.logger.error(f"SmartCleaner failed during processing: {e}", exc_info=True)
            return {
                "status": "failure",
                "error": str(e)
            }

    def _clean_payload(self, payload, visited_ids: set):
        """
        Core cleaning logic.
        Handles strings, dicts, lists, and nested structures with recursion-guarding.
        """
        # Recursion safety guard: Check if object is already being processed
        payload_id = id(payload)
        if payload_id in visited_ids:
            self.logger.warning("Circular reference detected in payload. Halting recursion branch safely.")
            return "[Circular Reference]"

        if isinstance(payload, str):
            return self._clean_string(payload)

        if isinstance(payload, dict):
            visited_ids.add(payload_id)
            cleaned_dict = {}
            for k, v in payload.items():
                # FIXED: Skip normalization for system-critical or protected keys
                if k.lower() in self.protected_keys:
                    cleaned_dict[k] = v
                else:
                    cleaned_dict[k] = self._clean_payload(v, visited_ids)
            visited_ids.remove(payload_id)
            return cleaned_dict

        if isinstance(payload, list):
            visited_ids.add(payload_id)
            cleaned_list = [self._clean_payload(item, visited_ids) for item in payload]
            visited_ids.remove(payload_id)
            return cleaned_list

        return payload  # Passthrough for integers, floats, booleans, etc.

    def _clean_string(self, text: str) -> str:
        """
        Normalizes text, trims whitespace, and standardizes formatting.
        """
        if not text:
            return ""
        text = clean_whitespace(text)
        text = normalize_text(text)
        return text
