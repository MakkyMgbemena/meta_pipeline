import os
from utils.logger import get_logger

class ProxyManager:
    """
    Step 3: The Stealth Layer (Hardened for Bright Data Solo).
    Provides a high-trust ISP-zone gateway for 'Hacker Era' automation [Source 677].
    Enforces Mission-Level Persistence to prevent IP-hopping flags [Source 679].
    """
    def __init__(self):
        self.logger = get_logger("ProxyManager")
        # Load the single Bright Data backconnect gateway from .env
        self.gateway = os.getenv("BRIGHTDATA_PROXY")

    def get_proxy_argument(self) -> str:
        """
        Returns the formatted proxy argument for the Selenium Chrome driver [Source 678].
        Locked to the Bright Data monthly subscription gateway.
        """
        if not self.gateway:
            self.logger.warning("Stealth Warning: BRIGHTDATA_PROXY not found in .env. Running on local IP.")
            return None
            
        self.logger.info("Stealth Mode: Injected Bright Data ISP Gateway for this mission.")
        return f"--proxy-server={self.gateway}"