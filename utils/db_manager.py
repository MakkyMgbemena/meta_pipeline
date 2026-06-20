import os
import datetime
from typing import Optional
from urllib.parse import quote_plus
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from utils.logger import get_logger
from services.fastapi.models import FinancialLedger, ClientRegistry, MissionJob


class DatabaseManager:
    _engine = None
    _Session = None

    def __init__(self, config: dict = None):
        self.logger = get_logger("DatabaseManager")
        self.config = config or {}

        # --- ENTERPRISE CONFIG RESOLUTION ---
        # We read the KEY name from config, then fetch the VALUE from os.environ
        db_cfg = self.config.get("database", {})

        user = self._get_env_val(db_cfg, "user_env_var", "DB_USER", "postgres")
        password = self._get_env_val(db_cfg, "password_env_var", "DB_PASS")
        db_name = self._get_env_val(db_cfg, "name_env_var", "DB_NAME", "meta_pipeline")
        db_host = self._get_env_val(db_cfg, "host_env_var", "DB_HOST", "")
        db_port = self._get_env_val(db_cfg, "port_env_var", "DB_PORT", "5432")
        instance_connection_name = self._get_env_val(db_cfg, "instance_connection_name_env_var", "INSTANCE_CONNECTION_NAME", "")

        if not password:
            self.logger.error("CRITICAL: Database password not found in environment!")
            raise ValueError("Database password is required.")

        if DatabaseManager._engine is None:
            try:
                encoded_user = quote_plus(user)
                encoded_password = quote_plus(password)
                encoded_db_name = quote_plus(db_name)

                # Prefer Cloud SQL Unix socket
                if instance_connection_name:
                    socket_dir = f"/cloudsql/{instance_connection_name}"
                    db_uri = f"postgresql+psycopg2://{encoded_user}:{encoded_password}@/{encoded_db_name}?host={socket_dir}"
                    self.logger.info(f"Connecting via Cloud SQL Socket: {socket_dir}")

                elif db_host.startswith("/cloudsql/"):
                    db_uri = f"postgresql+psycopg2://{encoded_user}:{encoded_password}@/{encoded_db_name}?host={db_host}"
                    self.logger.info(f"Connecting via Unix socket: {db_host}")

                else:
                    db_uri = f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{db_host}:{db_port}/{encoded_db_name}"
                    self.logger.info(f"Connecting via TCP/IP: {db_host}:{db_port}")

                DatabaseManager._engine = create_engine(
                    db_uri, pool_size=10, max_overflow=20, pool_pre_ping=True, future=True
                )
                DatabaseManager._Session = sessionmaker(bind=DatabaseManager._engine, future=True)

                # Initialize tables
                for model in [FinancialLedger, ClientRegistry, MissionJob]:
                    model.__table__.create(bind=DatabaseManager._engine, checkfirst=True)

            except Exception as e:
                self.logger.error(f"Database engine initialisation failed: {e}")
                raise

        self.engine = DatabaseManager._engine
        self.Session = DatabaseManager._Session

        # Now that self.engine is set, we can safely call sequence permissions
        if DatabaseManager._engine:
            self._ensure_sequence_permissions(user)

        self.session = self.Session()
        self.logger.info("DatabaseManager successfully initialised using Enterprise Config.")

    def _get_env_val(self, config_section: dict, config_key: str, default_env_name: str, fallback_val: str = None):
        """
        Helper: Resolves the environment variable name from config,
        then returns the actual value from the system environment.
        """
        env_var_name = config_section.get(config_key, default_env_name)
        return os.getenv(env_var_name, fallback_val)

    def _ensure_sequence_permissions(self, user: str):
        """USAGE/SELECT on sequences is required for auto-increment IDs."""
        if user.lower() == "postgres":
            self.logger.info("Skipping explicit sequence grants for superuser 'postgres'.")
            return

        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{user}"')
                )
                conn.execute(
                    text(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        f'GRANT USAGE, SELECT ON SEQUENCES TO "{user}"'
                    )
                )
                conn.commit()
            self.logger.info(f"Sequence permissions verified for user: {user}")
        except Exception as pe:
            self.logger.warning(
                f"Could not auto-grant sequence permissions for {user}. "
                f"Ensure the user has USAGE on sequences. Details: {pe}"
            )

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
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
        """Write a financial record."""
        try:
            with self.session_scope() as session:
                new_record = FinancialLedger(**entry)
                session.add(new_record)

            self.logger.info(
                f"PostgreSQL ledger write successful for: {entry.get('client_id')}"
            )
        except Exception as e:
            self.logger.error(f"Ledger write failed: {e}")
            raise

    def update_registry(self, client_id: str, status: str):
        """Update the client status."""
        try:
            client_found = False
            with self.session_scope() as session:
                record = (
                    session.query(ClientRegistry)
                    .filter_by(client_id=client_id)
                    .first()
                )
                if record:
                    record.status = status
                    record.last_sync = datetime.datetime.utcnow()
                    client_found = True

            if client_found:
                self.logger.info(f"PostgreSQL registry update successful for: {client_id}")
            else:
                self.logger.warning(f"Client {client_id} not found in registry.")
        except Exception as e:
            self.logger.error(f"Registry update failed: {e}")
            raise

    def get_client_email(self, client_id: str) -> Optional[str]:
        """Retrieves the email address for a registered client."""
        try:
            with self.session_scope() as session:
                record = session.query(ClientRegistry).filter_by(client_id=client_id).first()
                if record and record.profile_data:
                    return record.profile_data.get("email")
                return None
        except Exception as e:
            self.logger.error(f"Failed to fetch client email: {e}")
            return None

    def get_latest_mission(self, client_id: str):
        """Retrieve the most recent mission entry for a client."""
        try:
            with self.session_scope() as session:
                record = (
                    session.query(FinancialLedger)
                    .filter_by(client_id=client_id)
                    .order_by(FinancialLedger.timestamp.desc())
                    .first()
                )
                if record:
                    return {
                        "task": record.task,
                        "status": record.status,
                        "timestamp": record.timestamp,
                        "revenue": record.revenue,
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to fetch latest mission: {e}")
            return None

    def create_mission_job(
        self,
        job_id: str,
        client_id: str,
        file_name: str,
        file_type: str,
        storage_path: str,
    ):
        try:
            with self.session_scope() as session:
                new_job = MissionJob(
                    job_id=job_id,
                    client_id=client_id,
                    file_name=file_name,
                    file_type=file_type,
                    storage_path=storage_path,
                    status="RECEIVED",
                )
                session.add(new_job)

            self.logger.info(f"PostgreSQL MissionJob created: {job_id}")
        except Exception as e:
            self.logger.error(f"Failed to create MissionJob: {e}")
            raise

    def update_job_status(
        self,
        job_id: str,
        status: str,
        payload: dict = None,
        error: str = None,
    ):
        try:
            with self.session_scope() as session:
                job = session.query(MissionJob).filter_by(job_id=job_id).first()
                if job:
                    job.status = status
                    if payload is not None:
                        if isinstance(job.payload, dict) and isinstance(payload, dict):
                            job.payload = {**job.payload, **payload}
                        else:
                            job.payload = payload
                    if error is not None:
                        job.error_message = error
                    job.updated_at = datetime.datetime.utcnow()

            self.logger.info(f"PostgreSQL MissionJob updated: {job_id} -> {status}")
        except Exception as e:
            self.logger.error(f"Failed to update MissionJob {job_id}: {e}")
            raise

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
                        "updated_at": job.updated_at,
                    }
                return None
        except Exception as e:
            self.logger.error(f"Failed to get MissionJob {job_id}: {e}")
            return None
