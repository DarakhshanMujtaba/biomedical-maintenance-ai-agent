# AI-Powered Biomedical Equipment Operations Agent
## Project Scope Document

**Project Type:** Agentic AI Assistant + Automated Reporting/Email System (combined)
**Owner:** Darakhshan Mujtaba
**Date:** September 2026

---

## 1. Problem Statement

Hospitals and clinics manage large volumes of biomedical equipment (ventilators, infusion pumps, monitors, defibrillators, etc.). Maintenance is typically tracked manually in spreadsheets or paper logs, which causes:

- Missed or delayed preventive maintenance → equipment failure risk in critical care areas (ICU, OT).
- No prioritization logic — engineers don't know which equipment is highest-risk this week.
- Manual, slow communication between the biomedical engineering department and equipment users/wards.
- No automated audit trail (reports) for compliance/accreditation reviews.

## 2. Objective

Build an **agentic AI system** that doesn't just answer questions — it **understands a request, decides which tools/data it needs, takes multi-step action, and asks for human approval before anything irreversible happens** (scheduling, sending emails). This directly satisfies both parts of the assignment:

1. **Personal AI Assistant with Tools** → the agent understands natural-language ops requests and executes them using real tools (DB queries, calendar, email, PDF).
2. **Automated Email + Reporting Agent System** → a scheduled n8n workflow that collects equipment/maintenance data, generates a report, and emails it automatically — with a human-approval checkpoint before anything is sent/scheduled.

## 3. Primary User

A Biomedical Engineering Department Head / Ops Coordinator managing a mid-size hospital's equipment fleet.

## 4. In-Scope Capabilities

The agent must be able to handle requests like:

| # | Example Request | What the Agent Does |
|---|---|---|
| 1 | "Show all ICU equipment needing maintenance in the next 30 days" | Queries equipment DB, filters by location + due date |
| 2 | "Which ones are highest priority?" | Applies a risk score (usage hours, criticality, overdue days) |
| 3 | "Schedule the top 5" | Proposes calendar slots + assigns engineers → **waits for human approval** |
| 4 | "Notify the biomedical team" | Drafts email → **waits for human approval** → sends via n8n |
| 5 | "Generate this month's maintenance report" | Pulls DB data → builds PDF → emails/saves it |
| 6 (automated) | Every Monday 8 AM | n8n triggers the same pipeline automatically, no manual prompt needed, still gated by human approval before send |

## 5. Out of Scope

- No direct control of physical medical devices (software-only, administrative layer).
- No clinical/diagnostic decisions about patients.
- No real hospital data — uses realistic **mock/seed data** (clearly labeled), since real hospital records aren't accessible.
- No mobile app — CLI + simple FastAPI endpoint + n8n workflows is sufficient for the assignment.

## 6. Success Criteria (mapped to assignment rubric)

- ✅ Agentic behavior: LLM decides *which tool to call* and *what parameters*, not just chats.
- ✅ Real tool/API integration: SQL DB tool, PDF generation tool, Calendar tool, Email tool.
- ✅ Automation: n8n handles scheduling (cron trigger) + email delivery end-to-end.
- ✅ Human-in-the-loop: no email is sent / no calendar event is created without an explicit approval step.
- ✅ Practical, demoable: can run a live demo showing a request → decision → approval → execution → report email.

## 7. Constraints (from dev environment)

- Windows laptop, i3-1215U, 8GB RAM, no GPU → **no local LLM**, use Groq API (fast, free-tier, cloud-hosted).
- Docker unavailable → n8n runs via `npx n8n`, not containerized.
- SQLite instead of Postgres → zero setup, file-based, enough for this scale.
- Project will live on `C:\...\Desktop\biomedical-ops-agent` (separate from the earlier D-drive attempt).
