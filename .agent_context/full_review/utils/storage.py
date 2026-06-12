import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("storage")


@dataclass
class StorageResult:
    mode: str
    path: str
    gcs_uri: Optional[str] = None


def _clean_segment(s: str) -> str:
    return "".join([c for c in (s or "anonymous") if c.isalnum() or c in ("_", "-")])[:100] or "anonymous"


def detect_storage_mode() -> str:
    # If GCS is explicitly enabled, use it; otherwise local.
    enabled = (os.getenv("GCS_ENABLED", "").strip().lower() in {"1", "true", "yes"})
    if enabled:
        return "gcs"
    # If bucket env is set, prefer gcs.
    if os.getenv("GCS_BUCKET_NAME"):
        # Only use gcs if credentials are present (either GOOGLE_APPLICATION_CREDENTIALS or GCP_SA_KEY)
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GCP_SA_KEY"):
            return "gcs"
    return "local"


def _maybe_configure_google_credentials() -> None:
    """Wire credentials from env without hardcoding JSON into source."""
    sa_key = os.getenv("GCP_SA_KEY")
    if not sa_key:
        return

    # If GOOGLE_APPLICATION_CREDENTIALS already set, respect it.
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    # Otherwise, write to a temp file inside container filesystem.
    # Cloud Run allows writing to /tmp.
    cred_path = "/tmp/gcp_sa_key.json"
    try:
        with open(cred_path, "w", encoding="utf-8") as f:
            f.write(sa_key)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        logger.info("Configured GOOGLE_APPLICATION_CREDENTIALS from GCP_SA_KEY")
    except Exception as e:
        logger.error(f"Failed to write GCP service account key: {e}")


def save_upload_bytes(*, file_bytes: bytes, filename: str, client_id: str) -> StorageResult:
    client = _clean_segment(client_id)
    ts = __import__("datetime").datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")

    storage_mode = detect_storage_mode()


    safe_name = filename or "upload"
    safe_name = safe_name.replace("\\", "_").replace("/", "_")[:200]

    if storage_mode == "gcs":
        _maybe_configure_google_credentials()
        try:
            from google.cloud import storage as gcs_storage
        except ImportError as e:
            raise RuntimeError("google-cloud-storage is required for GCS mode") from e

        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not bucket_name:
            # Keep error message explicit; caller converts this into structured API response.
            raise RuntimeError("GCS_BUCKET_NAME not configured")


        object_name = f"uploads/{client}/{ts}_{safe_name}"
        client_gcs = gcs_storage.Client()
        bucket = client_gcs.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(file_bytes, content_type="application/octet-stream")
        return StorageResult(mode="gcs", path=object_name, gcs_uri=f"gs://{bucket_name}/{object_name}")

    # Local fallback
    upload_dir = Path("data/uploads") / client
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / f"{ts}_{safe_name}"
    with open(target_path, "wb") as f:
        f.write(file_bytes)
    return StorageResult(mode="local", path=str(target_path))
