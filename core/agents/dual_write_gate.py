from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
import datetime

class DualWriteGate(UnifiedAgent):
    """
    Routes a payload to two downstream agents safely.
    Enforces transaction integrity by ensuring primary writes succeed before executing secondary writes.
    """

    def __init__(self, config: dict = None, client_id: str = None, db=None, orchestrator=None):
        # Pass context to parent class for standardized logging and config access
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("DualWriteGate")
        
        # FIXED: Inject and bind the master orchestrator to prevent AttributeError crashes!
        self.orchestrator = orchestrator

    def run(self, payload: dict = None) -> dict:
        """
        Accepts a payload specifying two target agents and the data to write.
        Example: {"agent_a": "ledger_entry", "agent_b": "client_registry", "data": {...}}
        """
        self.logger.info(f"DualWriteGate starting parallel write for: {self.client_id}")

        if payload is None:
            self.logger.warning("No payload provided. Nothing to route.")
            return {"status": "skipped", "reason": "empty_payload"}

        # Validate that the orchestrator is connected before attempting routing
        if not self.orchestrator:
            self.logger.error("DualWriteGate execution aborted: Orchestrator instance not injected.")
            return {
                "status": "error",
                "message": "DualWriteGate requires an injected orchestrator reference."
            }

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

        try:
            # 1. Primary Write (e.g. Ledger Entry)
            self.logger.info(f"Executing Primary Write: {agent_a}")
            results["result_a"] = self.orchestrator.route(agent_a, data)

            # Check if Primary Write failed
            result_a_status = results["result_a"].get("status") if isinstance(results["result_a"], dict) else None
            
            if result_a_status in ["failed", "FAILED", "error"]:
                self.logger.error(f"Primary Write ({agent_a}) FAILED. Aborting secondary write to preserve transaction integrity.")
                return {
                    "status": "failed",
                    "reason": "primary_write_failed",
                    "transaction_results": results
                }

            # 2. Secondary Write (e.g. Registry Update) - Only executed if primary was successful!
            self.logger.info(f"Executing Secondary Write: {agent_b}")
            results["result_b"] = self.orchestrator.route(agent_b, data)

            # Check if Secondary Write failed
            result_b_status = results["result_b"].get("status") if isinstance(results["result_b"], dict) else None

            if result_b_status in ["failed", "FAILED", "error"]:
                self.logger.error(f"Secondary Write ({agent_b}) FAILED. Warning: Data state may be inconsistent!")
                return {
                    "status": "partial_success",
                    "reason": "secondary_write_failed",
                    "transaction_results": results
                }

            self.logger.info("DualWriteGate transaction completed successfully.")
            return {"status": "success", "transaction_results": results}

        except Exception as e:
            self.logger.error(f"DualWriteGate critical execution failure: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "transaction_results": results
            }
