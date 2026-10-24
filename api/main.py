import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT / "agents"))
sys.path.append(str(ROOT / "tools"))
sys.path.append(str(ROOT / "data"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from crew import crew
from init_db import init_db
import sql_tool
from prioritization_tool import rank_equipment_by_priority
import scheduling_tool
import notification_tool
from pdf_tool import build_maintenance_report
from api import approvals


@asynccontextmanager
async def lifespan(app):
    init_db(sql_tool.DB_PATH)   # creates/upgrades tables at server start (safe to repeat)
    yield


# Only the RFID dashboard's server calls this API. Run it on 127.0.0.1 (the default),
# so it is never reachable from the network or through the tunnel directly.
app = FastAPI(title="Biomedical Ops Agent API", lifespan=lifespan)

TASK_KEYS = ["monitor", "prioritize", "schedule", "notify", "report"]


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


# ─── Slow: the full 5-agent AI pipeline (about 20–40 s) ──────────────────────

class AskRequest(BaseModel):
    request: str


@app.post("/ask")
def ask(payload: AskRequest):
    # Start every run clean: fresh schedule, and no leftover draft from an earlier run
    scheduling_tool.clear_schedule_cache()
    notification_tool.LATEST_DRAFT_PATH.unlink(missing_ok=True)

    result = crew.kickoff(inputs={"request": payload.request})
    tasks = {key: output.raw for key, output in zip(TASK_KEYS, result.tasks_output)}
    return {
        "result": result.raw,
        "tasks": tasks,                                  # each agent's own (LLM-written) answer
        "email_draft": read_json(notification_tool.LATEST_DRAFT_PATH),     # exact tool-built text to approve and send
        "schedule": read_json(scheduling_tool.LATEST_SCHEDULE_PATH),     # structured schedule with time slots
    }


# ─── Fast: plain database/tool calls, no LLM (for the dashboard) ─────────────

@app.get("/health")
def health():
    return {"status": "ok", "email_configured": approvals.email_is_configured()}


@app.get("/equipment")
def equipment():
    """Every device with live status and priority score, most urgent first."""
    return rank_equipment_by_priority(sql_tool.get_all_equipment_with_status())


@app.get("/priorities")
def priorities(ward: Optional[str] = None, within_days: int = 30):
    """Devices needing maintenance within `within_days`, ranked."""
    return rank_equipment_by_priority(
        sql_tool.get_equipment_needing_maintenance(ward=ward, within_days=within_days))


class DraftRequest(BaseModel):
    top_n: int = 5
    ward: Optional[str] = None
    within_days: int = 30


@app.post("/drafts")
def make_draft(payload: DraftRequest):
    """Same tools the agents use, called directly: schedule + e-mail draft + PDF.
    Nothing is sent."""
    scheduling_tool.clear_schedule_cache()
    note = notification_tool.draft_team_notification(top_n=payload.top_n, ward=payload.ward, within_days=payload.within_days)
    build_maintenance_report()
    return {"email_draft": read_json(notification_tool.LATEST_DRAFT_PATH), "schedule": read_json(scheduling_tool.LATEST_SCHEDULE_PATH),
            "unassigned": note["unassigned"]}


@app.get("/drafts/latest")
def latest_draft():
    draft = approvals.latest_draft()
    return {
        "email_draft": draft,
        "schedule": read_json(scheduling_tool.LATEST_SCHEDULE_PATH),
        "decision": approvals.get_decision(draft["draft_id"]) if draft and draft.get("draft_id") else None,
        "email_configured": approvals.email_is_configured(),
    }


class DecisionRequest(BaseModel):
    decision: str          # "approved" or "declined"
    decided_by: str


@app.post("/drafts/{draft_id}/decision")
def decide(draft_id: str, payload: DecisionRequest):
    try:
        return approvals.decide(draft_id, payload.decision, payload.decided_by)
    except approvals.ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@app.get("/approvals")
def approval_log(limit: int = 50):
    return approvals.list_decisions(limit)


class ServicedRequest(BaseModel):
    serviced_by: str


@app.post("/equipment/{equipment_id}/serviced")
def serviced(equipment_id: int, payload: ServicedRequest):
    device = sql_tool.mark_serviced(equipment_id, payload.serviced_by)
    if device is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return device


@app.post("/equipment/by-asset/{asset_code}/serviced")
def serviced_by_asset(asset_code: str, payload: ServicedRequest):
    device = sql_tool.get_equipment_by_asset_code(asset_code)
    if device is None:
        raise HTTPException(status_code=404, detail=f"No equipment with asset code {asset_code}")
    return sql_tool.mark_serviced(device["id"], payload.serviced_by)


@app.get("/report")
def report():
    """Builds this month's PDF report and returns it as a download."""
    result = build_maintenance_report()
    path = Path(result["output_path"])
    return FileResponse(path, media_type="application/pdf", filename=path.name)
