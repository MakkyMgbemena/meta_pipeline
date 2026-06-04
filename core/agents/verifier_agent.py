from core.unified_agent import UnifiedAgent
from services.fastapi.models import FinancialLedger, ClientRegistry
from utils.logger import get_logger

class VerifierAgent(UnifiedAgent):
    """
    Phase 3 Final Integrity Layer.
    Reconciles agent outputs against the PostgreSQL vault [Source 678, 690].
    """
    def run(self, payload: dict = None) -> dict:
        self.logger.info(f"VerifierAgent starting final validation for client: {self.client_id}")
        errors = []

        try:
            # 0. Runtime Integrity: Fail if any upstream step encountered a CRITICAL FAILURE
            for step, result in payload.items():
                if isinstance(result, dict) and result.get("status") == "failed":
                    errors.append(f"RUNTIME: Step '{step}' failed during execution: {result.get('error')}")

            # Use the new session_scope context manager to handle the connection [4]
            with self.db.session_scope() as session:
                # 1. Reconcile Financial Ledger (using the 'session' from the context manager)
                ledger_record = session.query(FinancialLedger).filter_by(
                    client_id=self.client_id, status="locked"
                ).order_by(FinancialLedger.timestamp.desc()).first()

                if not ledger_record or ledger_record.revenue == 0:
                    errors.append("INTEGRITY: Financial record not confirmed or zero-value.")

                # 2. Reconcile Client Registry
                registry_record = session.query(ClientRegistry).filter_by(
                    client_id=self.client_id, status="active"
                ).first()

                if not registry_record:
                    errors.append("INTEGRITY: Client lineage sync failed in PostgreSQL vault.")

            if errors:
                self.logger.error(f"Verification FAILED: {errors}")
                return {"status": "FAILED", "errors": errors}

            self.logger.info("Verification passed: Output is clean. Mission Accomplished.")
            return {"status": "PASS", "message": "All integrity checks cleared."}

        except Exception as e:
            self.logger.error(f"Verifier critical system error: {e}")
            return {"status": "ERROR", "error": str(e)}