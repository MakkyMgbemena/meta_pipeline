from utils.config_loader import ConfigLoader
from core.orchestrator import Orchestrator
from utils.logger import get_logger
# THIS LINE IS THE PHASE 5 "BRIDGE" TO YOUR SAAS DASHBOARD [Source 481]
from services.fastapi.api import app 

logger = get_logger("MAIN")

def main():
    """CLI Entrypoint for local testing and manual missions [Source 472, 671]."""
    logger.info("Universal Headquarters: STARTING PRODUCTION RUN (CLI)...")
    config = ConfigLoader().config
    orchestrator = Orchestrator(config)
    
    # Triggering the default mission for high-trust verification
    result = orchestrator.run_for_client("client_enterprise_777", {"task": "cleanup"})
    logger.info(f"CLI mission result: {result.get('status')}")

if __name__ == "__main__":
    main()