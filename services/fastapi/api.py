from fastapi import FastAPI, Depends, HTTPException, APIRouter, UploadFile, File, Form
from dotenv import load_dotenv
load_dotenv()

from typing import Any, Dict, Optional
from pydantic import BaseModel

from services.fastapi.models import (

    MissionRequest,
    MissionResponse,
    UploadFileResponse,
    ProcessingStatus,
    ValidationError,
    UploadStorageInfo,
    JobInfo,
)


from services.fastapi.dependencies import get_orchestrator
from utils.auth import ensure_client_registered
from utils.data_seeder import seed_financial_ledger
from utils.brief_storage import save_brief, clean_client_id

from utils.logger import get_logger
import os
import resend
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Unified AI Meta Pipeline - Web Engine")
router = APIRouter()
logger = get_logger("FastAPI")

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
    return {"status": "ok", "timestamp": os.getpid()}

@router.post("/run", response_model=MissionResponse)
async def run_mission(request: MissionRequest, orchestrator = Depends(get_orchestrator)):
    logger.info(f"API CALL /run: client_id={request.client_id} task_name={request.task_name}")
    try:
        payload = request.payload or {}
        payload["client_id"] = request.client_id
        result = orchestrator.route(request.task_name, payload)
        response = {"status": "success", "client_id": request.client_id, "results": {request.task_name: result}}
        logger.info(f"API RESPONSE /run: client_id={request.client_id} task_name={request.task_name} status=success")
        return response
    except Exception as e:
        logger.error(f"API ERROR /run: client_id={request.client_id} task_name={request.task_name} error={e}")
        raise HTTPException(status_code=500, detail=str(e))


class MissionTriggerRequest(BaseModel):
    mission_id: str
    client_id: str
    task_name: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


@router.post("/run-mission")
async def run_mission_trigger(request: MissionTriggerRequest, orchestrator = Depends(get_orchestrator)):
    logger.info(
        f"MISSION_TRIGGER_REQUEST: mission_id={request.mission_id} client_id={request.client_id} task_name={request.task_name or '<full>'}"
    )
    try:
        context = {"client_id": request.client_id, "mission_id": request.mission_id}
        if request.payload:
            context.update(request.payload)

        if request.task_name:
            result = orchestrator.route(request.task_name, context)
            response = {
                "status": "success",
                "action": "run_task",
                "mission_id": request.mission_id,
                "client_id": request.client_id,
                "task_name": request.task_name,
                "result": result,
            }
        else:
            result = orchestrator.run_for_client(request.client_id, context=context)
            response = {
                "status": "success",
                "action": "run_full_mission",
                "mission_id": request.mission_id,
                "client_id": request.client_id,
                "results": result,
            }

        logger.info(
            f"MISSION_TRIGGER_RESULT: mission_id={request.mission_id} client_id={request.client_id} action={response['action']} status=success"
        )
        return response
    except Exception as e:
        logger.error(
            f"MISSION_TRIGGER_FAILED: mission_id={request.mission_id} client_id={request.client_id} error={e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unified")
async def run_unified_mission(payload: dict, orchestrator = Depends(get_orchestrator)):
    client_id = payload.get("client_id", "unknown_client")
    
    # Auto-Onboarding Workflow (Client lookup -> Insert -> Seed trigger)
    if not ensure_client_registered(client_id, orchestrator):
        seed_financial_ledger(orchestrator.db, client_id)

    result = orchestrator.run_for_client(client_id, context=payload)
    return result

@router.get("/health/browser")
async def health_browser():
    """Minimal browser-friendly health status."""
    return {"browser_service": "online", "ready": True}

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
                # Configurable via environment variable set in cloudbuild.yaml
                "from": os.getenv("RESEND_FROM_EMAIL", "Universal Headquarters <reports@yourdomain.com>"),
                "to": f"{client_id}@example.com",
                "subject": f"Mission Delivery: {client_id}",
                "html": html_content
            })
        except Exception:
            pass

    return {"status": "delivered", "client_id": client_id}


@router.post("/upload-file", response_model=UploadFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    client_id: Optional[str] = Form(None),
):
    """Upload a file and start background processing (CSV/Excel/PDF).

    Returns a consistent UploadFileResponse schema family.
    """




    # ---- validation ----
    if not file:
        return UploadFileResponse(success=False, message="Missing file")

    raw_filename = file.filename or ""
    # Accept common spreadsheet/text/pdf types
    allowed_ext = {".csv", ".xlsx", ".xls", ".pdf"}
    lower = raw_filename.lower()
    ext_ok = any(lower.endswith(e) for e in allowed_ext)
    if not ext_ok:
        return UploadFileResponse(
            success=False,
            message="Unsupported file type. Allowed: csv, xlsx, xls, pdf.",
            file_name=raw_filename,
            file_type=None,
            processing=ProcessingStatus(
                status="failed",
                errors=[ValidationError(type="unsupported_type", message="Unsupported extension")],
            ),
        )

    # ---- size limit ----
    max_mb = float(os.getenv("MAX_UPLOAD_MB", "25"))
    max_bytes = int(max_mb * 1024 * 1024)
    data = await file.read()
    if len(data) == 0:
        return UploadFileResponse(
            success=False,
            message="Empty file.",
            file_name=raw_filename,
        )
    if len(data) > max_bytes:
        return UploadFileResponse(
            success=False,
            message=f"File too large. Max {max_mb} MB.",
            file_name=raw_filename,
        )

    # ---- detect ----
    from utils.upload_processing import detect_file_type, process_by_type, ProcessResult

    from utils.storage import save_upload_bytes
    from utils.jobs import create_job, get_job, update_job, serialize_job

    ext, file_type = detect_file_type(raw_filename)
    safe_client = clean_client_id(client_id or "anonymous")

    # ---- storage save first ----
    try:
        storage_res = save_upload_bytes(file_bytes=data, filename=raw_filename, client_id=safe_client)
    except Exception as e:
        # Return structured failure (no uncaught 500 for storage misconfig).
        return UploadFileResponse(
            success=False,
            message="Storage failed",
            file_name=raw_filename,
            file_type=file_type,
            storage=None,
            processing=ProcessingStatus(
                status="failed",
                errors=[ValidationError(type="storage_error", message=str(e))],
            ),
            job=None,
        )


    # ---- create job + background processing thread ----
    job = create_job(file_name=raw_filename, file_type=file_type, storage={"mode": storage_res.mode, "path": storage_res.path, "gcs_uri": storage_res.gcs_uri})

    import threading

    def _work():
        update_job(job.job_id, status="running")
        try:
            result: ProcessResult = process_by_type(file_type, data)
            payload = {
                "status": "completed" if result.status == "success" else "failed",
                "summary": result.summary,
                "preview": result.preview,
                "errors": result.errors,
            }
            update_job(
                job.job_id,
                processing=payload,
                status="completed" if result.status == "success" else "failed",
                errors=result.errors,
            )
        except Exception as e:
            update_job(job.job_id, status="failed", errors=[{"type": "processing_exception", "message": str(e)}])

    threading.Thread(target=_work, daemon=True).start()

    return UploadFileResponse(
        success=True,
        message="Upload received; processing started.",
        file_name=raw_filename,
        file_type=file_type,
        storage=UploadStorageInfo(mode=storage_res.mode, path=storage_res.path, gcs_uri=storage_res.gcs_uri),
        processing=ProcessingStatus(status="queued"),
        job=JobInfo(job_id=job.job_id, status=job.status),
    )


@router.get("/upload-status/{job_id}", response_model=UploadFileResponse)
async def upload_status(job_id: str):
    from utils.jobs import get_job, serialize_job

    rec = get_job(job_id)
    if not rec:
        return UploadFileResponse(success=False, message="job not found", job=JobInfo(job_id=job_id, status="unknown"))

    # normalize processing.errors to ValidationError shape
    processing_data = rec.processing or {}
    errors = rec.errors or []

    return UploadFileResponse(
        success=(rec.status == "completed"),
        message=f"job {rec.status}",
        file_name=rec.file_name,
        file_type=rec.file_type,
        storage=UploadStorageInfo(**rec.storage) if rec.storage else None,
        processing=ProcessingStatus(
            status=rec.processing.get("status", rec.status) if rec.processing else rec.status,
            summary=processing_data.get("summary", {}) if processing_data else {},
            preview=processing_data.get("preview", {}) if processing_data else {},
            errors=[ValidationError(**e) if isinstance(e, dict) else ValidationError(type="unknown", message=str(e)) for e in errors],
        ),
        job=JobInfo(job_id=rec.job_id, status=rec.status),
    )


app.include_router(router)

