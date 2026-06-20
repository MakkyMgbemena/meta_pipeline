import os
import datetime
from utils.logger import get_logger

class UnifiedAgent:
    """
    Base class providing Database, Cloud Storage, and Logger access to all agents.
    Anchors the system in Phase 7 (Enterprise Scale) persistence.
    """
    # Shared class-level database engine to prevent pool exhaustion across separate agent instances
    _shared_db = None

    def __init__(self, config: dict = None, client_id: str = None, db=None):
        # Dynamically names the logger after the specific child agent (e.g., 'LinkedInManager')
        self.logger = get_logger(self.__class__.__name__)
        self.config = config or {}
        self.client_id = client_id

        # FIXED: Enforce strict single-pool fallback to prevent database connection exhaustion
        if db:
            self.db = db
        else:
            if UnifiedAgent._shared_db is None:
                self.logger.warning(
                    f"No DB injected into {self.__class__.__name__}. Initializing a single shared DatabaseManager instance."
                )
                from utils.db_manager import DatabaseManager
                # Initialize once globally across all agent classes
                UnifiedAgent._shared_db = DatabaseManager()
            self.db = UnifiedAgent._shared_db

        self.logger.info(f"{self.__class__.__name__} armed for client: {self.client_id}.")

    def _capture_state(self, driver, filename: str) -> str:
        """
        Ensures the screenshots directory exists, captures driver state,
        and automatically uploads to GCS for permanent Cloud Run persistence.
        """
        local_path = f"./reports/screenshots/{filename}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            # 1. Capture local image state
            driver.save_screenshot(local_path)
            self.logger.info(f"Visual state captured locally: {local_path}")

            # 2. Check for GCS configuration to upload
            bucket_name = os.getenv("GCS_BUCKET_NAME")
            if not bucket_name:
                self.logger.warning("GCS_BUCKET_NAME not configured; screenshot will be ephemeral.")
                return local_path

            # Upload to GCS
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)

            blob_name = f"screenshots/{self.client_id}/{filename}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)

            # Generate a secure 7-day signed URL for frontend rendering
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(days=7),
                method="GET"
            )

            # Clean up local file since it's now securely in GCS
            if os.path.exists(local_path):
                os.remove(local_path)

            self.logger.info(f"Screenshot successfully persisted in GCS: {signed_url}")
            return signed_url

        except Exception as e:
            self.logger.error(f"Unified _capture_state failed: {e}", exc_info=True)
            return local_path

    def _load_client_profile(self, client_id: str) -> dict:
        """
        Retrieves the client's profile from the PostgreSQL database first.
        Falls back to config.yaml if client is not in the registry.
        """
        client_id = client_id or self.client_id

        # 1. DYNAMIC STEP: Try loading profile from PostgreSQL first!
        if self.db and client_id:
            try:
                with self.db.session_scope() as session:
                    from services.fastapi.models import ClientRegistry
                    record = session.query(ClientRegistry).filter_by(client_id=client_id).first()
                    if record and hasattr(record, 'profile_data') and record.profile_data:
                        self.logger.info(f"Loaded dynamic database profile for client: {client_id}")
                        return record.profile_data
            except Exception as db_err:
                self.logger.warning(f"Database profile lookup failed, using static config: {db_err}")

        # 2. STATIC STEP: Fall back to reading the static config file
        clients = self.config.get("meta_pipeline", {}).get("clients", {})
        client_data = clients.get(client_id, {})
        return client_data.get("profile", {})

    def run(self, payload: dict) -> dict:
        """
        Standard execution interface enforced across all agents.
        """
        raise NotImplementedError("Every agent must implement the .run() method.")
