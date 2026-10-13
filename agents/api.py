"""
FastAPI REST API Server for Homa Ir Calculator.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from homa import assess_row
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Homa Ir Calculator API",
    description="HOMA1 calculations and optional demonstration audit workflows",
    version="3.0.0-ENTERPRISE",
)


app.mount("/web", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "web")), name="web")

class ChatRequest(BaseModel):
    query: str




class HomaRequest(BaseModel):
    glucose_mmol: Optional[float] = None
    glucose_mgdl: Optional[float] = None
    insulin_mu_u_ml: Optional[float] = None


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/web/index.html")


@app.post("/api/homa")
def api_homa(payload: HomaRequest):
    """Compute validated HOMA1 values; no diagnostic category is assigned."""
    data = payload.model_dump(exclude_none=True)
    result = assess_row(data)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    # Do not expose the legacy illustrative diagnostic flag in the API.
    result.pop("insulin_resistance", None)
    result.pop("interpretation_note", None)
    return result


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "homa-ir-calculator", "domain": "Clinical & Biomedical AI", "standard": "Demonstration rules only", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
