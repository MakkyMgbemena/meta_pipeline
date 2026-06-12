from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import datetime

# --- PART 1: DATABASE MODELS (The Vault Drawers) ---
Base = declarative_base()


class FinancialLedger(Base):
    """Blueprints for the Financial Ledger table."""
    __tablename__ = "financial_ledger"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    client_id = Column(String(100), index=True)
    task = Column(String(100))
    revenue = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    margin = Column(Float, default=0.0)
    status = Column(String(50), default="pending")
    currency = Column(String(10), default="CAD")

class ClientRegistry(Base):
    """Blueprints for the Client Lifecycle Registry."""
    __tablename__ = "client_registry"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(100), unique=True, index=True)
    status = Column(String(50), default="active")
    last_sync = Column(DateTime, default=datetime.datetime.utcnow)

class MissionJob(Base):
    """Blueprints for the Mission Job tracking table."""
    __tablename__ = "mission_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, index=True)
    client_id = Column(String(100), index=True)
    status = Column(String(50), default="RECEIVED")
    file_name = Column(String(255))
    file_type = Column(String(50))
    storage_path = Column(String(512))
    payload = Column(JSON, default={})
    error_message = Column(String(1024))
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# --- PART 2: API MODELS (The Receptionists) ---
# These are the models uvicorn is currently looking for

class MissionRequest(BaseModel):
    client_id: str
    task_name: str
    payload: Optional[Dict[str, Any]] = None

class UnifiedRequest(BaseModel):
    client_id: str
    data: Optional[Dict[str, Any]] = None

class MissionResponse(BaseModel):
    status: str
    client_id: str
    results: Dict[str, Any]


# -------------------------
# Upload pipeline contracts
# -------------------------

class ValidationError(BaseModel):
    type: str
    message: str
    field: Optional[str] = None


class UploadStorageInfo(BaseModel):
    mode: str
    path: str
    gcs_uri: Optional[str] = None


class ProcessingSummary(BaseModel):
    # Flexible summary payload per file type
    data: Dict[str, Any] = {}


class ProcessingPreview(BaseModel):
    data: Dict[str, Any] = {}


class ProcessingStatus(BaseModel):
    status: str
    summary: Dict[str, Any] = {}
    preview: Dict[str, Any] = {}
    errors: List[ValidationError] = []


class JobInfo(BaseModel):
    job_id: str
    status: str


class UploadFileResponse(BaseModel):
    success: bool
    message: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    storage: Optional[UploadStorageInfo] = None
    processing: Optional[ProcessingStatus] = None
    job: Optional[JobInfo] = None


class ResumeMissionRequest(BaseModel):
    client_id: str
    context: Dict[str, Any]
