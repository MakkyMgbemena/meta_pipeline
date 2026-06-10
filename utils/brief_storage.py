import json
import os
import re
import logging
from pathlib import Path
from datetime import datetime

try:
    from google.cloud import storage
except ImportError:
    storage = None

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
BASE_DIR = Path("data/mission_briefs")
# FIX: Target the primary bucket found in your environment
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "meta-pipeline-storage")
logger = logging.getLogger("BriefStorage")

# ==============================================================================
# HELPER FUNCTIONS (SANITIZATION & VALIDATION)
# ==============================================================================
def clean_client_id(client_id: str) -> str:
    """
    Prevents path traversal attacks. Only allows letters, numbers, and underscores.
    """
    return re.sub(r'[^a-zA-Z0-9_]', '', client_id)

# ==============================================================================
# CORE OPERATIONS: SAVE & LOAD (GCS & LOCAL)
# ==============================================================================
def save_brief(client_id: str, industry: str, brief_data: dict) -> dict:
    """
    Saves a mission brief to GCS (preferred) or local disk.
    """
    safe_id = clean_client_id(client_id)
    safe_industry = clean_client_id(industry).lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"briefs/{safe_id}/brief_{timestamp}.json"

    brief_data["client_id"] = safe_id
    brief_data["industry"] = safe_industry
    brief_data["created_at"] = timestamp

    if BUCKET_NAME and storage is not None:
        try:
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(filename)
            blob.upload_from_string(json.dumps(brief_data, indent=2), content_type='application/json')
            return {"status": "gcs", "path": f"gs://{BUCKET_NAME}/{filename}"}
        except Exception as e:
            logger.error(f"GCS Upload failed, falling back to local: {e}")

    # Local Fallback
    local_path = BASE_DIR / safe_id
    local_path.mkdir(parents=True, exist_ok=True)
    full_local_file = local_path / f"brief_{timestamp}.json"
    with open(full_local_file, "w") as f:
        json.dump(brief_data, f, indent=2)
    return {"status": "local", "path": str(full_local_file)}

def load_brief(client_id: str) -> dict:
    """
    Loads the most recent mission brief for a client.
    """
    safe_id = clean_client_id(client_id)
    client_dir = BASE_DIR / safe_id

    if not client_dir.exists():
        return {}

    files = list(client_dir.glob("brief_*.json"))
    if not files:
        return {}

    latest_file = max(files, key=os.path.getmtime)

    try:
        with open(latest_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# ==============================================================================
# CROSS-REFERENCING CAPABILITIES
# ==============================================================================
def get_briefs_by_industry(target_industry: str) -> list:
    """
    Returns all briefs matching an industry vertical.
    """
    matching_briefs = []
    safe_industry = clean_client_id(target_industry).lower()

    if not BASE_DIR.exists():
        return []

    for file_path in BASE_DIR.rglob("brief_*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                if data.get("industry") == safe_industry:
                    matching_briefs.append(data)
        except (json.JSONDecodeError, FileNotFoundError):
            continue

    return matching_briefs
