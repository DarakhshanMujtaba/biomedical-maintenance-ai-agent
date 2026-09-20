# Tech Stack

| Layer | Technology | Why This Choice |
|---|---|---|
| LLM Inference | **Groq API** (`llama-3.3-70b-versatile` for reasoning, `llama-3.1-8b-instant` for cheap/fast calls) | No GPU on your machine — Groq is cloud-hosted and very fast (already your default). |
| Agent Framework | **CrewAI** | Gives us Agents + Tasks + Tools abstraction out of the box; easy to define "Equipment Monitor Agent", "Scheduler Agent", "Reporter Agent" with clear roles. |
| Automation / Orchestration | **n8n** (self-hosted via `npx n8n`) | Handles cron scheduling, the human-approval wait step, and email/calendar sending — the "automated" half of the assignment, no Docker needed. |
| Database | **SQLite** (`equipment.db`) | Zero setup, file-based, plenty for equipment/maintenance/engineer records at this scale. |
| Backend / API | **FastAPI** | Exposes the CrewAI agent as a `/ask` endpoint so both a CLI *and* n8n (via HTTP Request node) can call it the same way. |
| PDF Reports | **fpdf2** | Lightweight, pure-Python, no system dependencies (important — no Docker, limited RAM). |
| Calendar | **.ics file generation** (`ics` Python package) first; Google Calendar API as optional stretch goal | Avoids needing Google Cloud OAuth setup just to pass the assignment; `.ics` files open in any calendar app and are enough to prove the "scheduling" tool works. |
| Email | **Gmail via n8n's Gmail/SMTP node** | n8n already handles auth + sending; agent only *drafts* the email, n8n *sends* it after approval. |
| Human Approval | **n8n "Wait for Webhook" node + email/Telegram approval link** | Real human-in-the-loop gate — nothing gets sent/scheduled without a click. |
| Env/Secrets | `.env` + `python-dotenv` | Keeps the Groq API key and email creds out of source code. |
| Dependency Mgmt | `venv` + `requirements.txt` | Standard, no extra tooling needed. |
| Version Control | Git + GitHub | Same as your other projects — needed for your portfolio anyway. |

## Why not X?

- **Not Ollama / local LLM** → 8GB RAM + no GPU would make this unusably slow.
- **Not Postgres/Docker** → Docker is broken on your machine; SQLite avoids the whole problem.
- **Not LangChain agents** → CrewAI is more readable for a portfolio reviewer skimming your code (clear role/goal/backstory per agent), and matches what you already used in the earlier healthcare-ops-assistant plan.
- **Not a real Google Calendar integration first** → OAuth setup is a time sink; `.ics` generation proves the same "agent uses a scheduling tool" capability with far less setup risk. We can add real Google Calendar later as a stretch goal once the core pipeline works.
