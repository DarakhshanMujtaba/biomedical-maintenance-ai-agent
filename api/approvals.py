"""
Human approval of e-mail drafts — the ONLY place in this project that sends e-mail.

It lives in api/ (not tools/) on purpose: the AI agents only get the functions in
tools/, so no agent can ever call this. It runs only when a person clicks
Approve or Decline on the dashboard.

Rules:
  - The decision must name the exact draft_id of the latest draft (an outdated
    draft cannot be approved).
  - A draft can be decided only once (approvals.draft_id is UNIQUE), so it can
    never be sent twice, even if Approve is clicked twice.
  - Decline records the decision and sends nothing.
  - Approve sends exactly the stored subject/body (the browser cannot change it).

E-mail settings come from .env (never committed):
  SMTP_HOST (default smtp.gmail.com), SMTP_PORT (default 587), SMTP_USER,
  SMTP_PASSWORD (a Gmail App Password), MAIL_FROM (default SMTP_USER),
  TEAM_EMAILS (comma-separated recipients)
"""
import json
import os
import smtplib
import sqlite3
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import notification_tool
import sql_tool

REPORTS_DIR = Path(__file__).parent.parent / "reports"


class ApprovalError(Exception):
    """A decision that must be refused. status_code is the HTTP status to return."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def latest_draft():
    path = notification_tool.LATEST_DRAFT_PATH
    if not path.exists():
        return None
    return json.loads(path.read_text())


def get_decision(draft_id):
    conn = sql_tool.get_connection()
    row = conn.execute("SELECT * FROM approvals WHERE draft_id = ?", (draft_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_decisions(limit=50):
    conn = sql_tool.get_connection()
    rows = conn.execute("SELECT * FROM approvals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def email_settings():
    recipients = [e.strip() for e in os.getenv("TEAM_EMAILS", "").split(",") if e.strip()]
    user = os.getenv("SMTP_USER", "").strip()
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": user,
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "sender": os.getenv("MAIL_FROM", user).strip(),
        "recipients": recipients,
    }


def email_is_configured():
    s = email_settings()
    return bool(s["user"] and s["password"] and s["sender"] and s["recipients"])


def attachments():
    """The draft schedule (.ics) and this month's report (PDF), if they exist."""
    files = []
    ics = REPORTS_DIR / "proposed_schedule.ics"
    if ics.exists():
        files.append((ics, "text", "calendar"))
    pdfs = sorted(REPORTS_DIR.glob("maintenance_report_*.pdf"))
    if pdfs:
        files.append((pdfs[-1], "application", "pdf"))
    return files


def send_email(subject, body):
    s = email_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s["sender"]
    msg["To"] = ", ".join(s["recipients"])
    msg.set_content(body)
    for path, maintype, subtype in attachments():
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)

    with smtplib.SMTP(s["host"], s["port"], timeout=30) as smtp:
        smtp.starttls()
        smtp.login(s["user"], s["password"])
        smtp.send_message(msg)
    return s["recipients"]


def decide(draft_id, decision, decided_by):
    if decision not in ("approved", "declined"):
        raise ApprovalError("decision must be 'approved' or 'declined'")
    if not decided_by or not decided_by.strip():
        raise ApprovalError("decided_by is required (who made the decision)")

    draft = latest_draft()
    if draft is None:
        raise ApprovalError("There is no draft to decide on.", 404)
    if draft.get("draft_id") != draft_id:
        raise ApprovalError("This draft is outdated. Reload to see the latest draft.", 409)
    if get_decision(draft_id):
        raise ApprovalError("This draft was already decided.", 409)
    if decision == "approved" and not email_is_configured():
        raise ApprovalError("E-mail is not set up yet (SMTP_USER, SMTP_PASSWORD, TEAM_EMAILS in .env). "
                            "Nothing was sent.", 503)

    now = datetime.now(timezone.utc).isoformat()
    conn = sql_tool.get_connection()
    try:
        # 1. Claim the draft first. UNIQUE(draft_id) makes a second click fail here,
        #    before anything is sent.
        conn.execute(
            "INSERT INTO approvals (draft_id, decision, decided_by, decided_at, subject, body) VALUES (?,?,?,?,?,?)",
            (draft_id, decision, decided_by.strip(), now, draft["subject"], draft["body"]))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ApprovalError("This draft was already decided.", 409)

    try:
        if decision == "declined":
            return get_decision(draft_id)            # Decline: recorded, nothing sent

        # 2. Approve: send exactly the stored text
        try:
            recipients = send_email(draft["subject"], draft["body"])
        except Exception as exc:
            # Sending failed: release the claim so it can be approved again later
            conn.execute("DELETE FROM approvals WHERE draft_id = ?", (draft_id,))
            conn.commit()
            raise ApprovalError(f"Sending failed, nothing was sent: {exc}", 502)

        # 3. Confirm it was sent
        conn.execute("UPDATE approvals SET sent = 1, recipients = ? WHERE draft_id = ?",
                     (", ".join(recipients), draft_id))
        conn.commit()
        return get_decision(draft_id)
    finally:
        conn.close()
