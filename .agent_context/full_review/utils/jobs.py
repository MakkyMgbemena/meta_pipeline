import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from utils.db_manager import DatabaseManager
from utils.config_loader import ConfigLoader

@dataclass
class JobRecord:
    job_id: str
    status: str = "RECEIVED"
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    storage: Dict[str, Any] = field(default_factory=dict)
    processing: Dict[str, Any] = field(default_factory=dict)
    errors: list = field(default_factory=list)


def create_job(*, file_name: str, file_type: Optional[str], storage: Dict[str, Any], client_id: str = "anonymous") -> JobRecord:
    job_id = str(uuid.uuid4())
    rec = JobRecord(job_id=job_id, file_name=file_name, file_type=file_type, storage=storage)

    config = ConfigLoader().config
    db = DatabaseManager(config)
    db.create_mission_job(
        job_id=job_id,
        client_id=client_id,
        file_name=file_name,
        file_type=file_type,
        storage_path=storage.get("path") or storage.get("gcs_uri") or ""
    )
    return rec


def get_job(job_id: str) -> Optional[JobRecord]:
    config = ConfigLoader().config
    db = DatabaseManager(config)
    job_data = db.get_mission_job(job_id)
    if not job_data:
        return None

    return JobRecord(
        job_id=job_data["job_id"],
        status=job_data["status"],
        file_name=job_data["file_name"],
        file_type=job_data["file_type"],
        storage={"path": job_data["storage_path"]},
        processing=job_data["payload"] or {},
        errors=[{"type": "error", "message": job_data["error_message"]}] if job_data["error_message"] else []
    )


def update_job(job_id: str, **kwargs) -> None:
    config = ConfigLoader().config
    db = DatabaseManager(config)

    status = kwargs.get("status")
    payload = kwargs.get("processing")
    errors = kwargs.get("errors")
    error_msg = str(errors[0]["message"]) if errors and len(errors) > 0 else None

    db.update_job_status(job_id, status=status, payload=payload, error=error_msg)
