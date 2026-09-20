# Implementation Plan (Phased, with Checkpoints)

After each phase, there is a **checkpoint** — we pause to confirm everything is working correctly before moving to the next phase.

| Phase | Goal | Deliverable |
|---|---|---|
| **0** | Project skeleton | Folder structure, venv, git init, requirements.txt, `.env` |
| **1** | Data layer | SQLite schema + seed script with realistic mock equipment data |
| **2** | Tools | `sql_tool.py`, `pdf_tool.py`, `calendar_tool.py`, `email_tool.py` — each tested standalone |
| **3** | Agents | CrewAI agents (Monitor, Prioritization, Scheduling, Reporting, Notification) + Crew wiring |
| **4** | CLI test | Run the crew from terminal with a hardcoded request, verify output end-to-end |
| **5** | API layer | FastAPI `/ask` endpoint wrapping the crew |
| **6** | n8n: trigger + execution | Cron trigger workflow calling `/ask`, plus Gmail-send workflow |
| **7** | n8n: human approval gate | Wait-for-webhook approval step wired between draft and execution |
| **8** | Polish + demo | README, sample run screenshots/recording, edge case handling |

## Phase 0 — Project Skeleton (we'll do this first)

**Folder structure:**
```
biomedical-ops-agent/
├── agents/
├── tools/
├── data/
├── n8n/
├── api/
├── docs/          <- these 4 md files go here
├── tests/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

**What you'll run (Windows, Desktop, C: drive):**
```bat
cd Desktop
mkdir biomedical-ops-agent
cd biomedical-ops-agent
mkdir agents tools data n8n api docs tests
python -m venv venv
venv\Scripts\activate
```

**requirements.txt (first draft):**
```
crewai
crewai-tools
groq
fastapi
uvicorn
python-dotenv
fpdf2
ics
```

```bat
pip install -r requirements.txt
```

**Checkpoint 0:** The venv should be active (you should see `(venv)` in your prompt), and `pip install` should complete without errors. Once this is confirmed, we'll move on to Phase 1 (database schema + seed data).

## Phases 1–8 — Detail Comes Step by Step

The actual code for each phase will be given in this conversation only once the previous phase is confirmed working — so you understand one piece at a time, instead of copy-pasting everything at once.
