from fastapi import FastAPI, Depends, HTTPException, APIRouter
from dotenv import load_dotenv
load_dotenv()

from services.fastapi.models import MissionRequest, MissionResponse
from services.fastapi.dependencies import get_orchestrator
from utils.brief_storage import save_brief
import os
import resend

app = FastAPI(title="Unified AI Meta Pipeline - Web Engine")
router = APIRouter()

resend.api_key = os.getenv("RESEND_API_KEY", "")

@router.get("/")
async def root():
    return {
        "status": "Online",
        "system": "Unified AI Meta Pipeline",
        "location": "Toronto Production Vault",
        "documentation": "/docs"
    }

@router.get("/health")
async def health():
    return {"status": "online", "service": "unified-meta-pipeline", "version": "2.0.0"}

@router.post("/run", response_model=MissionResponse)
async def run_mission(request: MissionRequest, orchestrator = Depends(get_orchestrator)):
    try:
        payload = request.payload or {}
        payload["client_id"] = request.client_id
        result = orchestrator.route(request.task, payload)
        return {"status": "success", "client_id": request.client_id, "results": {request.task: result}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unified")
async def run_unified_mission(payload: dict, orchestrator = Depends(get_orchestrator)):
    client_id = payload.get("client_id", "unknown_client")
    result = orchestrator.run_for_client(client_id, context=payload)
    return result

@router.post("/brief")
async def create_brief(request: dict):
    required = ["client_id", "industry", "mission_type", "platform", "destructive_allowed", "success_criteria"]
    for field in required:
        if field not in request:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    brief_data = {
        "mission_type": request["mission_type"],
        "platform": request["platform"],
        "destructive_allowed": request["destructive_allowed"],
        "success_criteria": request["success_criteria"]
    }

    result = save_brief(
        client_id=request["client_id"],
        industry=request["industry"],
        brief_data=brief_data
    )

    return {"status": "success", "message": f"Brief saved for {request['client_id']}", "path": result["path"]}

@router.post("/deliver")
async def deliver_mission(request: dict, orchestrator = Depends(get_orchestrator)):
    if "client_id" not in request:
        raise HTTPException(status_code=400, detail="Missing client_id")

    client_id = request["client_id"]

    latest_mission = None
    try:
        latest_mission = orchestrator.db.get_latest_mission(client_id)
    except Exception:
        pass

    if not latest_mission:
        screenshots = {}
        verdict = {"status": "UNKNOWN"}
    else:
        screenshots = latest_mission.get("screenshots", {})
        verdict = latest_mission.get("verification", {})

    html_content = f"""
    <h1>Mission Delivery Report</h1>
    <p><strong>Client:</strong> {client_id}</p>
    <p><strong>Status:</strong> {verdict.get('status', 'UNKNOWN')}</p>
    <h2>Evidence</h2>
    <p>Before: <a href="{screenshots.get('before', '#')}">View Screenshot</a></p>
    <p>After: <a href="{screenshots.get('after', '#')}">View Screenshot</a></p>
    """

    if resend.api_key:
        try:
            resend.Emails.send({
                "from": "delivery@meta-pipeline.com",
                "to": f"{client_id}@example.com",
                "subject": f"Mission Delivery: {client_id}",
                "html": html_content
            })
        except Exception:
            pass

    return {"status": "delivered", "client_id": client_id}
app.include_router(router)