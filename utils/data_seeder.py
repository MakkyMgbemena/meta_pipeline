from services.fastapi.models import FinancialLedger
import datetime

def seed_financial_ledger(db, client_id: str):
    """Seeds the financial ledger with an initial entry if it's empty for the client."""
    if not db:
        return
    with db.session_scope() as session:
        try:
            # Idempotent check
            exists = session.query(FinancialLedger).filter_by(client_id=client_id).first()
            if not exists:
                entry = {
                    "timestamp": datetime.datetime.utcnow(),
                    "client_id": client_id,
                    "task": "initial_onboarding_seed",
                    "revenue": 0.0,
                    "cost": 0.0,
                    "margin": 0.0,
                    "status": "locked",
                    "currency": "CAD"
                }
                session.add(FinancialLedger(**entry))
                session.commit()
                db.logger.info(f"Financial ledger seeded for {client_id}")
        except Exception as e:
            db.logger.error(f"Failed to seed financial ledger: {e}")
