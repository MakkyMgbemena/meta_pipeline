import os
from pathlib import Path
from dotenv import load_dotenv


class EnvLoader:
    """
    Loads environment variables from:
    - system environment
    - .env file (if present)
    Provides safe access to secrets and API keys.
    """

    def __init__(self, env_path: str = ".env"):
        self.env_path = Path(env_path)
        self._load_env_file()

    # ---------------------------------------------------------
    # LOAD .env FILE
    # ---------------------------------------------------------
    def _load_env_file(self):
        """
        Loads environment variables from a .env file if it exists.
        """
        if self.env_path.exists():
            load_dotenv(self.env_path)

    # ---------------------------------------------------------
    # GETTER
    # ---------------------------------------------------------
    def get(self, key: str, default=None):
        """
        Safe getter for environment variables.
        Example:
            env.get("OPENAI_API_KEY")
        """
        return os.getenv(key, default)
