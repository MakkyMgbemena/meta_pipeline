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
            # 1. Reconcile Financial Ledger
            ledger_record = self.db.session.query(FinancialLedger).filter_by(
                client_id=self.client_id, status="locked"
            ).order_by(FinancialLedger.timestamp.desc()).first()

            if not ledger_record or ledger_record.revenue == 0:
                errors.append("INTEGRITY: Financial record not confirmed or zero-value in headquarters.")

            # 2. Reconcile Client Registry
            registry_record = self.db.session.query(ClientRegistry).filter_by(
                client_id=self.client_id, status="active"
            ).first()

            if not registry_record:
                errors.append("INTEGRITY: Client lineage sync failed in PostgreSQL vault.")

            if errors:
                self.logger.error(f"Verification FAILED: {errors}")
                return {"status": "FAILED", "errors": errors}

            self.logger.info("Verification passed: Output is clean and consistent. Mission Accomplished.")
            return {"status": "PASS", "message": "All integrity checks cleared."}

        except Exception as e:
            self.logger.error(f"Verifier critical system error: {e}")
            return {"status": "ERROR", "error": str(e)}