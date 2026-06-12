import yaml
from pathlib import Path


class ConfigLoader:
    """
    Loads the main YAML configuration file.
    Provides a clean dictionary for the orchestrator and all agents.
    """

    def __init__(self, path: str = "config.yaml"):
        self.path = Path(path)
        self.config = self._load()

    # ---------------------------------------------------------
    # LOAD CONFIG
    # ---------------------------------------------------------
    def _load(self) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(
                f"Config file not found at {self.path}. "
                "Ensure config.yaml exists in the project root."
            )

        with open(self.path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ---------------------------------------------------------
    # ACCESSOR
    # ---------------------------------------------------------
    def get(self, key: str, default=None):
        """
        Safe getter for config values.
        Example:
            config.get("database.host")
        """
        parts = key.split(".")
        value = self.config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value
