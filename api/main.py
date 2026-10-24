import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "agents"))
sys.path.append(str(Path(__file__).parent.parent / "tools"))

from fastapi import FastAPI
from pydantic import BaseModel

from crew import crew
from scheduling_tool import clear_schedule_cache, LATEST_SCHEDULE_PATH
from notification_tool import LATEST_DRAFT_PATH

app = FastAPI(title="Biomedical Ops Agent API")

TASK_KEYS = ["monitor", "prioritize", "schedule", "notify", "report"]


class AskRequest(BaseModel):
    request: str


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


@app.post("/ask")
def ask(payload: AskRequest):
    # Start every run clean: fresh schedule, and no leftover draft from an earlier run
    clear_schedule_cache()
    LATEST_DRAFT_PATH.unlink(missing_ok=True)

    result = crew.kickoff(inputs={"request": payload.request})
    tasks = {key: output.raw for key, output in zip(TASK_KEYS, result.tasks_output)}
    return {
        "result": result.raw,
        "tasks": tasks,                                  # each agent's own (LLM-written) answer
        "email_draft": read_json(LATEST_DRAFT_PATH),     # exact tool-built text to approve and send
        "schedule": read_json(LATEST_SCHEDULE_PATH),     # structured schedule with time slots
    }
