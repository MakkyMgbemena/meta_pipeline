import os
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from utils.logger import get_logger
from contextlib import contextmanager

# Import your models so the manager knows which 'drawers' to open
from services.fastapi.models import FinancialLedger, ClientRegistry, MissionJob


class DatabaseManager:
    def __init__(self, config: dict = None):
        self.logger = get_logger("DatabaseManager")
        self.config = config

        # 1. Environment-aware Authentication [Source 453, 468]
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASS")
        host = os.getenv("DB_HOST", "34.130.156.62")
        port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "meta_pipeline")

        if not password:
            self.logger.error("CRITICAL: DB_PASS not found!")
            raise ValueError("Database password is required.")

        try:
            # 2. Establish the Physical Bridge via native container socket
            db_uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
            self.engine = create_engine(db_uri)

            # Auto-initialize missing database tables natively
            FinancialLedger.__table__.create(bind=self.engine, checkfirst=True)
            ClientRegistry.__table__.create(bind=self.engine, checkfirst=True)
            MissionJob.__table__.create(bind=self.engine, checkfirst=True)

            # 3. Create the Session Factory (The "Clerk" that handles the vault)
            self.Session = sessionmaker(bind=self.engine)

            # 4. FIX: Restore .session attribute for backward compatibility
            self.session = self.Session()

            # 5. FIX: Auto-grant sequence permissions to fix InsufficientPrivilege for ID generation [2]
            self._ensure_sequence_permissions(user)

            self.logger.info(
                "DatabaseManager successfully initialized and authenticated."
            )
        except Exception as e:
            self.logger.error(f"Database Engine Failed: {str(e)}")
            raise e

    def _ensure_sequence_permissions(self, user: str):
        """USAGE/SELECT on sequences is required for auto-increment IDs."""
        try:
            with self.engine.connect() as conn:
                # Grant permissions for existing and future sequences
                conn.execute(text(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{user}"'))
                conn.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{user}"'))
                conn.commit()
            self.logger.info(f"Sequence permissions verified for user: {user}")
        except Exception as pe:
            # We treat this as a warning because the user might already have permissions via a role
            self.logger.warning(f"Sequence permission check skipped: {pe}")

    @contextmanager
    def session_scope(self):
        """Provides a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def write_ledger(self, entry: dict):
        """Writes a financial record and SEALS it in the vault."""
        try:
            with self.session_scope() as session:
                new_record = FinancialLedger(**entry)
                session.add(new_record)
                session.commit() # Mandatory persistence fix [2]
            self.logger.info(
                f"PostgreSQL Ledger write successful for: {entry.get('client_id')}"
            )
        except Exception as e:
            self.logger.error(f"Ledger write failed: {e}")
            raise e

    def update_registry(self, client_id: str, status: str):
        """Updates the client status and SEALS it in the vault."""
        try:
            client_found = False
            with self.session_scope() as session:
                record = session.query(ClientRegistry).filter_by(client_id=client_id).first()
                if record:
                    record.status = status
                    record.last_sync = datetime.datetime.utcnow()
                    session.commit() # Mandatory persistence fix [2]
                    client_found = True

            if client_found:
                self.logger.info(f"PostgreSQL Registry update successful for: {client_id}")
            else:
                self.logger.warning(f"Client {client_id} not found in registry.")
        except Exception as e:
            self.logger.error(f"Registry update failed: {e}")
            raise e

    def get_latest_mission(self, client_id: str):
        """Retrieves the most recent mission entry for a client."""
        try:
            with self.session_scope() as session:
                record = session.query(FinancialLedger).filter_by(client_id=client_id).order_by(FinancialLedger.timestamp.desc()).first()
                if record:
                    return {
                        "task": record.task,
                        "status": record.status,
                        "timestamp": record.timestamp,
                        "revenue": record.revenue
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to fetch latest mission: {e}")
            return None

    def create_mission_job(self, job_id: str, client_id: str, file_name: str, file_type: str, storage_path: str):
        try:
            with self.session_scope() as session:
                new_job = MissionJob(
                    job_id=job_id,
                    client_id=client_id,
                    file_name=file_name,
                    file_type=file_type,
                    storage_path=storage_path,
                    status="RECEIVED"
                )
                session.add(new_job)
                session.commit()
            self.logger.info(f"PostgreSQL MissionJob created: {job_id}")
        except Exception as e:
            self.logger.error(f"Failed to create MissionJob: {e}")
            raise e

    def update_job_status(self, job_id: str, status: str, payload: dict = None, error: str = None):
        try:
            with self.session_scope() as session:
                job = session.query(MissionJob).filter_by(job_id=job_id).first()
                if job:
                    job.status = status
                    if payload is not None:
                        # Merge payload if it's a dict
                        if isinstance(job.payload, dict) and isinstance(payload, dict):
                            merged = {**job.payload, **payload}
                            job.payload = merged
                        else:
                            job.payload = payload
                    if error is not None:
                        job.error_message = error
                    job.updated_at = datetime.datetime.utcnow()
                    session.commit()
            self.logger.info(f"PostgreSQL MissionJob updated: {job_id} -> {status}")
        except Exception as e:
            self.logger.error(f"Failed to update MissionJob {job_id}: {e}")
            raise e

    def get_mission_job(self, job_id: str):
        try:
            with self.session_scope() as session:
                job = session.query(MissionJob).filter_by(job_id=job_id).first()
                if job:
                    return {
                        "job_id": job.job_id,
                        "client_id": job.client_id,
                        "status": job.status,
                        "file_name": job.file_name,
                        "file_type": job.file_type,
                        "storage_path": job.storage_path,
                        "payload": job.payload,
                        "error_message": job.error_message,
                        "updated_at": job.updated_at
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to get MissionJob {job_id}: {e}")
            return None
