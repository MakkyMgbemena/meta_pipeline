# services/fastapi/dependencies.py
from utils.config_loader import ConfigLoader
from utils.logger import get_logger

logger = get_logger("API_Dependencies")
_orchestrator_instance = None

def get_orchestrator():
    """
    Dependency Injector: Provides the active MetaOrchestrator instance.
    Uses local imports inside the function to completely break any circular dependency loops.
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        logger.info("Initializing MetaOrchestrator for Web Engine...")
        try:
            # FIXED: Moving Orchestrator import here breaks the import loop!
            from core.orchestrator import Orchestrator

            # Load the hardened Phase 7 configuration
            config = ConfigLoader().config
            _orchestrator_instance = Orchestrator(config)
            logger.info("MetaOrchestrator successfully injected into API scope.")
        except Exception as e:
            logger.error(f"Engine Injection FAILED: {str(e)}")
            raise RuntimeError(f"Could not initialize system brain: {e}")

    return _orchestrator_instance
