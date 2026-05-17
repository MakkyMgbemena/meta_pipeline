from fastapi import FastAPI, Depends, HTTPException
# FIX: Injects the secrets from .env into the running process [Source 418, 442]
from dotenv import load_dotenv 
load_dotenv() 

from .models import MissionRequest, UnifiedRequest, MissionResponse
from .dependencies import get_orchestrator
from core.orchestrator import Orchestrator

# 1. INITIALIZATION: Must come before decorators to avoid NameError [Conversation History]
app = FastAPI(title="Unified AI Meta Pipeline - Web Engine")

# 2. ROOT ROUTE: Fixes 404 Not Found error for root URL [Conversation History]
@app.get("/")
async def root():
    return {
        "status": "Online",
        "system": "Unified AI Meta Pipeline",
        "location": "Toronto Production Vault",
        "documentation": "/docs"
    }

# 3. MISSION ENDPOINTS: Orchestrates agent execution via Web Engine [7]
@app.post("/run", response_model=MissionResponse)
async def run_mission(request: MissionRequest, orchestrator: Orchestrator = Depends(get_orchestrator)):
    try:
        # Identity Injection: Forces client_id into agent payload [8]
        payload = request.payload or {}
        payload["client_id"] = request.client_id
        
        result = orchestrator.route(request.task, payload)
        return {"status": "success", "client_id": request.client_id, "results": {request.task: result}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/unified")
async def run_unified_mission(payload: dict, orchestrator = Depends(get_orchestrator)):
    # CRITICAL: We must pass the 'payload' dictionary into the run_for_client method
    client_id = payload.get("client_id", "unknown_client")
    result = orchestrator.run_for_client(client_id, context=payload)
    return result