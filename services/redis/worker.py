import time
import json
from redis import Redis # Ensure you ran 'python -m pip install redis'
from utils.logger import get_logger
from core.orchestrator import Orchestrator
from utils.config_loader import ConfigLoader

class RedisWorker:
    """
    Phase 5 Background Task Engine.
    Stays online 24/7 to catch missions triggered via the FastAPI web gateway [Source 479, 671].
    """
    def __init__(self):
        self.logger = get_logger("Redis_Worker")
        self.redis = Redis(host='localhost', port=6379, db=0, decode_responses=True)

        # Injects the system brain into the worker
        config = ConfigLoader().config
        self.orchestrator = Orchestrator(config)

    def start(self):
        """Starts the infinite mission-listening loop [Source 671]."""
        self.logger.info("--- REDIS WORKER ONLINE: LISTENING FOR MISSIONS ---")

        while True:
            try:
                # Listen for the 'mission_queue' to receive new payloads
                mission = self.redis.blpop("mission_queue", timeout=30)

                if mission:
                    _, data = mission
                    payload = json.loads(data)
                    client_id = payload.get("client_id")

                    self.logger.info(f"MISSION RECEIVED: {client_id}")
                    # Physically execute the agent chain via the Orchestrator
                    self.orchestrator.run_for_client(client_id, context=payload.get("payload"))

            except Exception as e:
                self.logger.error(f"Worker Loop Error: {str(e)}")
                time.sleep(5) # Prevents CPU-burn on connection failure

if __name__ == "__main__":
    # THIS BLOCK IS THE TRIGGER: It keeps the terminal open
    worker = RedisWorker()
    worker.start()
