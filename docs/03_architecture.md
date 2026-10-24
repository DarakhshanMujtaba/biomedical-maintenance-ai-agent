# System Architecture

## 1. High-Level Diagram

```mermaid
flowchart TD
    U[User / n8n Cron Trigger] --> A[AI Agent Layer - CrewAI]

    subgraph A[AI Agent Layer - CrewAI]
        direction TB
        A1[Understand request]
        A2[Plan steps]
        A3[Decide which tool + params]
        A1 --> A2 --> A3
    end

    A3 --> T1[SQL Tool]
    A3 --> T2[Calendar Tool]
    A3 --> T3[Email Draft Tool]
    A3 --> T4[PDF Report Tool]

    T1 --> DB[(SQLite: equipment, maintenance_logs, engineers)]
    T2 --> ICS[.ics calendar file]
    T3 --> DRAFT[Draft email content]
    T4 --> PDF[Monthly report PDF]

    DRAFT --> H{Human Approval Gate - n8n}
    ICS --> H
    H -- approved --> X1[n8n sends email via Gmail node]
    H -- declined --> LOG[No Operation: nothing is sent]

```

## 2. Component Breakdown

### Agent Layer (CrewAI) — `agents/`
| Agent | Role | Tools It Uses |
|---|---|---|
| **Equipment Monitor Agent** | Finds equipment due/overdue for maintenance, filters by ward/criticality | SQL Tool |
| **Prioritization Agent** | Scores and ranks equipment by risk: `max(0, overdue_days)*10 + criticality_weight*20 + min(usage_hours/100, 15)` (High=3, Medium=2, Low=1; usage is capped so it can never flip a criticality tier) | SQL Tool |
| **Scheduling Agent** | Proposes maintenance slots and engineer assignments | Calendar Tool, SQL Tool |
| **Reporting Agent** | Builds the monthly/weekly maintenance report | SQL Tool, PDF Tool |
| **Notification Agent** | Drafts the email to the biomedical team (does NOT send it) | Email Draft Tool |

These are wired together as a **CrewAI Crew** with sequential/hierarchical tasks — the orchestration script decides which agents run based on the user's request.

### Tool Layer — `tools/`
- `sql_tool.py` — parametrized read/write queries against SQLite (equipment, maintenance_logs, engineers tables).
- `calendar_tool.py` — generates `.ics` files for proposed maintenance slots.
- `email_tool.py` — formats email subject/body (returns a draft object, never sends).
- `pdf_tool.py` — builds the maintenance report PDF using fpdf2.

**Key design rule:** tools that cause a real-world side effect (send email, create calendar event) are *not allowed to execute directly from the agent*. They only produce a **draft/proposal object**. Only n8n, after human approval, performs the actual send/create. This is what makes the human-approval gate real instead of decorative.

### Data Layer — SQLite (`data/equipment.db`)
- `equipment` (id, name, type, ward, criticality, usage_hours, install_date)
- `maintenance_logs` (id, equipment_id, last_service_date, next_due_date, status)
- `engineers` (id, name, specialty, availability)

### Automation Layer — n8n workflows (`n8n/`)
1. **Trigger workflow** — Cron (e.g. every Monday 8AM) OR manual webhook — calls the FastAPI `/ask` endpoint.
2. **Human approval workflow** — receives the agent's draft (email/schedule), e-mails the exact tool-built draft (`email_draft` from `/ask`) to the approver with Approve/Decline buttons (n8n "Send and Wait for Response"), and pauses until they respond. Approve → the same text is sent to the team. Decline → No Operation, nothing is sent. The .ics file and PDF stay in `reports/` (not sent yet).
3. **Execution workflow** — on approval, sends the real email (Gmail node) and/or saves the `.ics` file; on rejection, logs it and stops.

### API Layer — FastAPI (`api/main.py`)
- `POST /ask` — takes a natural-language request, runs the CrewAI crew, returns the result/draft as JSON. This is the single integration point both a CLI demo and n8n use.

## 3. End-to-End Example Flow

> "Show me all ICU equipment that needs maintenance within the next 30 days, prioritize it, schedule the top 5, notify the team, and generate this month's report."

1. FastAPI receives the request → CrewAI Crew kicks off.
2. **Equipment Monitor Agent** → SQL Tool → filters ICU + due-within-30-days.
3. **Prioritization Agent** → ranks by risk score.
4. **Scheduling Agent** → picks top 5 → one device per day for the team, 9 AM local time (Asia/Karachi; same engineer + same day would get 11 AM, 1 PM) → draft `.ics` + engineer assignments. The schedule is computed once per run and reused by step 5.
5. **Notification Agent** → Email Tool → drafts a summary email from that same schedule (not sent).
6. **Reporting Agent** → PDF Tool → builds the monthly report (status always computed from `next_due_date`).
7. FastAPI returns: `{ result, tasks: {monitor, prioritize, schedule, notify, report}, email_draft: {subject, body}, schedule }`.
8. n8n e-mails `email_draft` to the approver with **Approve / Decline**.
9. Approve → n8n sends exactly that subject/body to the team. Decline → nothing is sent.
10. Not yet: sending the `.ics`/PDF as attachments, and an approvals log (planned with the dashboard integration). n8n's execution history currently shows which branch ran.

## 4. Why This Is "Agentic" (not just a chatbot)

At each step the LLM is making a **decision**, not just generating text:
- *Which tool do I need?* (SQL vs Calendar vs Email vs PDF)
- *What parameters does it need?* (ward="ICU", days=30)
- *What do I do with the result?* (pass ranked list to Scheduling Agent)
- *Does this need human approval before it happens in the real world?* (yes, always, for send/schedule actions)
