import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class JobRecord:
    job_id: str
    status: str = "queued"  # queued|running|completed|failed
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    storage: Dict[str, Any] = field(default_factory=dict)
    processing: Dict[str, Any] = field(default_factory=dict)
    errors: list = field(default_factory=list)


_jobs: Dict[str, JobRecord] = {}
_lock = threading.Lock()


def create_job(*, file_name: str, file_type: Optional[str], storage: Dict[str, Any]) -> JobRecord:
    job_id = str(uuid.uuid4())
    rec = JobRecord(job_id=job_id, file_name=file_name, file_type=file_type, storage=storage)
    with _lock:
        _jobs[job_id] = rec
    return rec


def get_job(job_id: str) -> Optional[JobRecord]:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> None:
    with _lock:
        rec = _jobs.get(job_id)
        if not rec:
            return
        for k, v in kwargs.items():
            if hasattr(rec, k):
                setattr(rec, k, v)
            else:
                # allow nested updates for storage/processing/errors
                if k in ("storage", "processing") and isinstance(v, dict):
                    getattr(rec, k).update(v)


def serialize_job(rec: JobRecord) -> Dict[str, Any]:
    return {
        "job_id": rec.job_id,
        "status": rec.status,
        "file_name": rec.file_name,
        "file_type": rec.file_type,
        "storage": rec.storage,
        "processing": rec.processing,
        "errors": rec.errors,
    }
