from core.unified_agent import UnifiedAgent
import datetime

class LedgerAgent(UnifiedAgent):
    def run(self, payload: dict = None) -> dict:
        # DIAGNOSTIC: Print what the agent actually received
        self.logger.info(f"DEBUG: Ledger received payload keys: {list(payload.keys()) if payload else 'NONE'}")
        
        data_block = payload.get("data", {}) if payload else {}
        
        # Check both the 'data' block and the top-level payload
        revenue = float(data_block.get("revenue", payload.get("revenue", 0.0)))
        cost = float(data_block.get("cost", payload.get("cost", 0.0)))
        margin = revenue - cost

        entry = {
            "client_id": self.client_id,
            "task": data_block.get("task", payload.get("task", "automated_cleanup_v1")),
            "revenue": revenue,
            "cost": cost,
            "margin": margin,
            "status": "locked", # Required for the VerifierAgent to PASS
            "currency": "CAD"
        }

        try:
            self.db.write_ledger(entry)
            self.logger.info(f"Financial record locked: Net ${margin:.2f}")
            return {"ledger_status": "recorded", "entry": entry}
        except Exception as e:
            self.logger.error(f"PostgreSQL Ledger write failed: {e}")
            return {"ledger_status": "failed", "error": str(e)}