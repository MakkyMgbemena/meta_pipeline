import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url 
from sqlalchemy.orm import sessionmaker
from utils.logger import get_logger

# Import your models so the manager knows which 'drawers' to open
from services.fastapi.models import FinancialLedger, ClientRegistry

class DatabaseManager:
    def __init__(self, config: dict = None):
        self.logger = get_logger("DatabaseManager")
        self.config = config
        
        # 1. Environment-aware Authentication [Source 453, 468]
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASS") 
        host = os.getenv("DB_HOST", "127.0.0.1")
        port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "meta_pipeline_prod")

        if not password:
            self.logger.error("CRITICAL: DB_PASS not found!")
            raise ValueError("Database password is required.")

        db_uri = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        
        try:
            # 2. Establish the Physical Bridge
            url_object = make_url(db_uri)
            self.engine = create_engine(url_object)
            
            # 3. Create the Session Factory (The "Clerk" that handles the vault)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            self.logger.info("DatabaseManager successfully initialized and authenticated.")
        except Exception as e:
            self.logger.error(f"Database Engine Failed: {str(e)}")
            raise e

    def write_ledger(self, entry: dict):
        """Writes a financial record and SEALS it in the vault."""
        try:
            # Create a new record using the dictionary payload
            new_record = FinancialLedger(**entry) 
            
            # Add to the session and COMMIT to solve the 'Visibility Gap'
            self.session.add(new_record) 
            self.session.commit() 
            
            self.logger.info(f"PostgreSQL Ledger write successful for: {entry['client_id']}")
        except Exception as e:
            self.session.rollback() # Undo if the write fails
            self.logger.error(f"Ledger write failed: {e}")
            raise e

    def update_registry(self, client_id: str, status: str):
        """Updates the client status and SEALS it in the vault."""
        try:
            # Locate the existing client in the Digital Registry
            record = self.session.query(ClientRegistry).filter_by(client_id=client_id).first()
            if record:
                record.status = status
                record.last_sync = datetime.datetime.utcnow()
                
                # Commit the changes so the VerifierAgent can see them [1]
                self.session.commit() 
                self.logger.info(f"PostgreSQL Registry update successful for: {client_id}")
            else:
                self.logger.warning(f"Client {client_id} not found in registry.")
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Registry update failed: {e}")
            raise e