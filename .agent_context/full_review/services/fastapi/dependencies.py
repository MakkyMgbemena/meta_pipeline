from core.orchestrator import Orchestrator
from utils.config_loader import ConfigLoader
from utils.logger import get_logger

# Initialize a single global instance for the entire FastAPI lifecycle
# This ensures we don't reconnect to PostgreSQL on every single API call [Source 483].
logger = get_logger("API_Dependencies")
_orchestrator_instance = None

def get_orchestrator() -> Orchestrator:
    """
    Dependency Injector: Provides the active MetaOrchestrator instance.
    Guarantees the engine is armed with the latest config.yaml and .env secrets [Source 436].
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        logger.info("Initializing MetaOrchestrator for Web Engine...")
        try:
            # Load the hardened Phase 7 configuration
            config = ConfigLoader().config
            _orchestrator_instance = Orchestrator(config)
            logger.info("MetaOrchestrator successfully injected into API scope.")
        except Exception as e:
            logger.error(f"Engine Injection FAILED: {str(e)}")
            raise RuntimeError(f"Could not initialize system brain: {e}")

    return _orchestrator_instance
