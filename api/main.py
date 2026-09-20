import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "agents"))

from fastapi import FastAPI
from pydantic import BaseModel

from crew import crew

app = FastAPI(title="Biomedical Ops Agent API")

TASK_KEYS = ["monitor", "prioritize", "schedule", "notify", "report"]


class AskRequest(BaseModel):
    request: str


@app.post("/ask")
def ask(payload: AskRequest):
    result = crew.kickoff(inputs={"request": payload.request})
    tasks = {key: output.raw for key, output in zip(TASK_KEYS, result.tasks_output)}
    return {"result": result.raw, "tasks": tasks}
