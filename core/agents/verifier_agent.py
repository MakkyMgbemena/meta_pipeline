from core.unified_agent import UnifiedAgent
from utils.logger import get_logger
from services.fastapi.models import FinancialLedger, ClientRegistry

class VerifierAgent(UnifiedAgent):
    """
    Phase 3 Final Integrity Layer.
    Reconciles agent outputs against the PostgreSQL vault.
    """

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        # Explicitly initialize constructor to guarantee logger and database bindings
        super().__init__(config or {}, client_id, db)
        self.logger = get_logger("VerifierAgent")
        self.db = db

    def run(self, payload: dict = None) -> dict:
        """
        Runs the final integrity reconciliation suite.
        Protects against empty payloads and verifies structural database health.
        """
        self.logger.info(f"VerifierAgent starting final validation for client: {self.client_id}")
        
        # FIXED: Protect against NoneType payload crash
        payload = payload or {}
        errors = []

        try:
            # 1. Runtime Integrity: Fail if any upstream step encountered a CRITICAL FAILURE
            for step, result in payload.items():
                if isinstance(result, dict):
                    # Check for standardized failure formats
                    if result.get("status") in ["failed", "FAILED", "failure", "error"]:
                        errors.append(
                            f"RUNTIME: Step '{step}' failed during execution: {result.get('error', 'Unknown Error')}"
                        )

            # Ensure we have a database manager to reconcile with
            if not self.db:
                self.logger.error("Verification halted: Database manager is not connected.")
                return {
                    "status": "FAILED", 
                    "errors": ["INTEGRITY: Database vault connection is unavailable."]
                }

            # 2. Reconcile with the Database using self.db.session_scope()
            with self.db.session_scope() as session:
                
                # Fetch target states from configuration or fall back to standard defaults
                ledger_target_status = self.config.get("verifier", {}).get("ledger_status", "locked")
                registry_target_status = self.config.get("verifier", {}).get("registry_status", "active")

                # Reconcile Financial Ledger
                ledger_record = (
                    session.query(FinancialLedger)
                    .filter_by(client_id=self.client_id, status=ledger_target_status)
                    .order_by(FinancialLedger.timestamp.desc())
                    .first()
                )

                if not ledger_record:
                    errors.append(f"INTEGRITY: Financial record not found with status '{ledger_target_status}'.")
                elif ledger_record.revenue == 0:
                    errors.append("INTEGRITY: Financial record exists but holds a zero-value revenue ledger.")

                # Reconcile Client Registry
                registry_record = (
                    session.query(ClientRegistry)
                    .filter_by(client_id=self.client_id, status=registry_target_status)
                    .first()
                )

                if not registry_record:
                    errors.append(f"INTEGRITY: Client lineage sync failed. Status '{registry_target_status}' not found in PostgreSQL vault.")

            # 3. Process verification results
            if errors:
                self.logger.error(f"Verification FAILED: {errors}")
                
                # Log verification failure to DB for frontend tracking
                try:
                    self.db.update_registry(self.client_id, "INTEGRITY AUDIT FAILED")
                except Exception as log_err:
                    self.logger.warning(f"Failed to record audit failure in registry: {log_err}")
                
                return {"status": "FAILED", "errors": errors}

            # Success: All checks cleared!
            self.logger.info("Verification passed: Output is clean. Mission Accomplished.")
            
            # Log verification success to DB
            try:
                self.db.update_registry(self.client_id, "INTEGRITY AUDIT PASSED")
            except Exception as log_err:
                self.logger.warning(f"Failed to record audit success in registry: {log_err}")

            return {"status": "PASS", "message": "All integrity checks cleared."}

        except Exception as e:
            self.logger.error(f"Verifier critical system error: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}
