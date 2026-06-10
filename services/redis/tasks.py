from core.orchestrator import Orchestrator
from utils.config_loader import ConfigLoader
import logging

logger = logging.getLogger("Redis_Tasks")

def execute_mission_task(client_id: str, payload: dict):
    """
    Background task wrapper for the MetaOrchestrator.
    Enables parallel processing for 50+ concurrent clients [Source 481, 608].
    """
    try:
        # Re-initialize the brain within the worker context
        config = ConfigLoader().config
        orchestrator = Orchestrator(config)

        logger.info(f"Worker starting background mission for: {client_id}")
        result = orchestrator.run_for_client(client_id, payload)

        return {"status": "success", "client_id": client_id, "result": result}
    except Exception as e:
        logger.error(f"Background Mission Failed for {client_id}: {str(e)}")
        return {"status": "failed", "error": str(e)}
