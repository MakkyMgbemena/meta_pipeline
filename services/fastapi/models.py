from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Dict, Any, Optional
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