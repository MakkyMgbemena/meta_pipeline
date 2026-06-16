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
        Enterprise Verification Layer:
        Enforces config-driven safeguards (Pricing, Currency, Market) and DB integrity.
        """
        self.logger.info(f"VerifierAgent enforcing Enterprise safeguards for: {self.client_id}")
        
        payload = payload or {}
        errors = []
        
        # 1. ENFORCE CONFIG SAFEGUARDS (From meta_pipeline.pricing_policy.safeguards)
        safeguards = self.config.get("meta_pipeline", {}).get("pricing_policy", {}).get("safeguards", {})
        
        # A. Currency Resolution Check
        if safeguards.get("require_currency_resolution_before_quote", True):
            # Check if commercial_resolution has been satisfied in the payload/context
            resolved_currency = payload.get("commercial_profile", {}).get("currency")
            if not resolved_currency:
                errors.append("SAFEGUARD: Currency resolution failed. External delivery blocked per pricing_policy.")

        # B. Pricing Resolution Verification
        # Check if the mission results contain a valid price/ledger status
        if not payload.get("ledger_entry") or payload.get("ledger_entry", {}).get("status") == "UNRESOLVED":
            if safeguards.get("require_hitl_for_unresolved_market_rules", True):
                errors.append("SAFEGUARD: Unresolved pricing/market rules detected. HITL review required.")

        # 2. RUNTIME INTEGRITY (Existing Logic)
        for step, result in payload.items():
            if isinstance(result, dict) and result.get("status") in ["failed", "FAILED", "error"]:
                errors.append(f"RUNTIME: Step '{step}' failure: {result.get('error', 'Unknown Error')}")

        # 3. DATABASE RECONCILIATION (Vault Check)
        if not self.db:
            return {"status": "FAILED", "errors": ["INTEGRITY: PostgreSQL vault connection unavailable."]}

        try:
            with self.db.session_scope() as session:
                ledger_target = self.config.get("verifier", {}).get("ledger_status", "locked")
                registry_target = self.config.get("verifier", {}).get("registry_status", "active")

                # Verify Ledger exists for this specific job/mission
                ledger = session.query(FinancialLedger).filter_by(
                    client_id=self.client_id, 
                    status=ledger_target
                ).order_by(FinancialLedger.timestamp.desc()).first()

                if not ledger:
                    errors.append(f"INTEGRITY: Financial ledger missing or not in '{ledger_target}' state.")
                elif ledger.revenue <= 0 and not self.config.get("meta_pipeline", {}).get("pricing_policy", {}).get("minimum_viable_quote_required", False):
                    # Only error on zero revenue if config doesn't explicitly allow free/unresolved quotes
                    errors.append("INTEGRITY: Zero-value revenue detected in production ledger.")

                # Verify Registry sync
                registry = session.query(ClientRegistry).filter_by(client_id=self.client_id).first()
                if not registry:
                    errors.append("INTEGRITY: Client Registry record missing for this client.")

            # 4. FINAL VERDICT
            if errors:
                self.logger.error(f"Verification FAILED: {errors}")
                self.db.update_registry(self.client_id, "INTEGRITY AUDIT FAILED")
                return {"status": "FAILED", "errors": errors}

            self.logger.info("Verification PASSED: All Enterprise safeguards and integrity checks cleared.")
            self.db.update_registry(self.client_id, "INTEGRITY AUDIT PASSED")
            return {"status": "PASS", "message": "All integrity checks cleared."}

        except Exception as e:
            self.logger.error(f"Verifier System Error: {e}")
            return {"status": "ERROR", "error": str(e)}
