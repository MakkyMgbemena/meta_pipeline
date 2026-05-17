from utils.logger import get_logger
from utils.db_manager import DatabaseManager
import os

class UnifiedAgent:
    """
    Base class providing Database and Logger access to all agents.
    Anchors the system in Phase 7 (Enterprise Scale) persistence [Source 481].
    """
    def __init__(self, config: dict, client_id: str = None):
        # Dynamically names the logger after the specific child agent (e.g., 'LedgerAgent')
        self.logger = get_logger(self.__class__.__name__)
        self.config = config or {}
        self.client_id = client_id
        
        # Initialize Database Manager for permanent Phase 7 relational persistence
        db_config = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASS"),
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": os.getenv("DB_PORT", "5432")
        }
        self.db = DatabaseManager(db_config)
        self.logger.info(f"{self.__class__.__name__} armed for {self.client_id}.")

    def _load_client_profile(self, client_id: str) -> dict:
        """
        Retrieves the client's profile (name, industry, location) from config.yaml [Source 338].
        """
        clients = self.config.get("meta_pipeline", {}).get("clients", {})
        client_data = clients.get(client_id, {})
        return client_data.get("profile", {})

    def run(self, payload: dict) -> dict:
        """
        Standard execution interface enforced across all agents [Source 338, 541].
        """
        raise NotImplementedError("Every agent must implement the .run() method.")