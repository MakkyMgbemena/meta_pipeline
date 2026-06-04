from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
import datetime

class DualWriteGate(UnifiedAgent):
    """
    Routes a payload to two downstream agents safely.
    Ensures financial data (ledger) is written before registry data.
    """

    def __init__(self, config: dict, client_id: str = None, db=None):
        # Pass context to parent class for standardized logging and config access
        super().__init__(config, client_id, db)
        self.logger = get_logger("DualWriteGate")

    def run(self, payload: dict = None):
        """
        Accepts a payload specifying two target agents and the data to write.
        Example: {"agent_a": "ledger_entry", "agent_b": "client_registry", "data": {...}}
        """
        self.logger.info(f"DualWriteGate starting parallel write for: {self.client_id}")

        if payload is None:
            self.logger.warning("No payload provided. Nothing to route.")
            return {"status": "skipped", "reason": "empty_payload"}

        agent_a = payload.get("agent_a")
        agent_b = payload.get("agent_b")
        data = payload.get("data", {})

        if not agent_a or not agent_b:
            self.logger.error("DualWriteGate requires both agent_a and agent_b targets.")
            return {"status": "error", "message": "Missing routing targets"}

        results = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "client_id": self.client_id,
            "agent_a": agent_a,
            "agent_b": agent_b,
            "result_a": None,
            "result_b": None,
        }

        # Use the orchestrator to execute the first write (e.g., Ledger)
        self.logger.info(f"Executing Primary Write: {agent_a}")
        results["result_a"] = self.orchestrator.route(agent_a, data)

        # Use the orchestrator to execute the second write (e.g., Registry)
        self.logger.info(f"Executing Secondary Write: {agent_b}")
        results["result_b"] = self.orchestrator.route(agent_b, data)

        self.logger.info("DualWriteGate transaction completed successfully.")
        
        return {"status": "success", "transaction_results": results}