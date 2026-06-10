from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
from utils.file_utils import normalize_text, clean_whitespace


class SmartCleaner(UnifiedAgent):
    """
    Cleans, normalizes, and prepares client data.
    This is the first agent in the routing chain for most clients.
    """

    def __init__(self, config: dict, client_id: str, db=None):
        super().__init__(config, client_id, db)
        self.logger = get_logger("SmartCleaner")

    # ---------------------------------------------------------
    # MAIN EXECUTION
    # ---------------------------------------------------------
    def run(self, payload: dict = None):
        """
        Executes the cleaning pipeline.
        Payload can be raw text, dicts, or tabular-like structures.
        """

        self.logger.info(f"SmartCleaner started for client '{self.client_id}'.")

        if payload is None:
            self.logger.warning("No payload provided. Nothing to clean.")
            return None

        cleaned = self._clean_payload(payload)

        self.logger.info("SmartCleaner completed successfully.")
        return cleaned

    # ---------------------------------------------------------
    # CLEANING LOGIC
    # ---------------------------------------------------------
    def _clean_payload(self, payload):
        """
        Core cleaning logic.
        Handles strings, dicts, lists, and nested structures.
        """

        if isinstance(payload, str):
            return self._clean_string(payload)

        if isinstance(payload, dict):
            return {k: self._clean_payload(v) for k, v in payload.items()}

        if isinstance(payload, list):
            return [self._clean_payload(item) for item in payload]

        return payload  # passthrough for unsupported types

    def _clean_string(self, text: str) -> str:
        """
        Normalizes text, trims whitespace, and standardizes formatting.
        """

        text = clean_whitespace(text)
        text = normalize_text(text)

        return text
