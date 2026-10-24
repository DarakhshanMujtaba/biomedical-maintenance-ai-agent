"""
Test setup: every test gets its own temporary database (built from data/schema.sql)
and its own temporary reports folder, so data/equipment.db and reports/ are never touched.
No LLM is called by any test.
"""
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for folder in (ROOT, ROOT / "tools", ROOT / "agents", ROOT / "data"):
    sys.path.insert(0, str(folder))

import calendar_tool
import notification_tool
import pdf_tool
import scheduling_tool
import sql_tool
from api import approvals

TODAY = date(2026, 10, 24)   # fixed "today" so results never depend on the real date


def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript((ROOT / "data" / "schema.sql").read_text())
    equipment = [
        # name, type, ward, criticality, usage_hours, days until due (negative = overdue)
        ("Ventilator-01", "Ventilator", "ICU", "High", 4200, -6),
        ("Monitor-01", "Monitor", "ICU", "Medium", 6000, -11),
        ("Infusion Pump-01", "Infusion Pump", "ICU", "Medium", 5000, 10),
        ("Defibrillator-02", "Defibrillator", "ER", "High", 1100, 20),
        ("Monitor-04", "Monitor", "General Ward", "Low", 2100, 150),
    ]
    for name, etype, ward, crit, hours, due_in in equipment:
        cur = conn.execute(
            "INSERT INTO equipment (name, type, ward, criticality, usage_hours, install_date) VALUES (?,?,?,?,?,?)",
            (name, etype, ward, crit, hours, "2022-01-01"))
        due = TODAY + timedelta(days=due_in)
        # Stored status is deliberately WRONG ("OK") to prove it is never used
        conn.execute(
            "INSERT INTO maintenance_logs (equipment_id, last_service_date, next_due_date, status) VALUES (?,?,?,?)",
            (cur.lastrowid, "2026-01-01", due.isoformat(), "OK"))
    for name, specialty, availability in [
        ("Ayesha Khan", "Ventilator", "Available"),
        ("Bilal Ahmed", "Infusion Pump", "Available"),
        ("Sara Malik", "Monitor", "Available"),
        ("Omar Farooq", "Defibrillator", "Available"),
        ("Hamza Raza", "Ventilator", "Busy"),
    ]:
        conn.execute("INSERT INTO engineers (name, specialty, availability) VALUES (?,?,?)",
                     (name, specialty, availability))
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    make_db(db_path)
    reports = tmp_path / "reports"

    monkeypatch.setattr(sql_tool, "DB_PATH", db_path)
    monkeypatch.setattr(sql_tool, "today", lambda: TODAY)
    monkeypatch.setattr(scheduling_tool, "today", lambda: TODAY)
    monkeypatch.setattr(calendar_tool, "OUTPUT_DIR", reports)
    monkeypatch.setattr(scheduling_tool, "REPORTS_DIR", reports)
    monkeypatch.setattr(scheduling_tool, "LATEST_SCHEDULE_PATH", reports / "latest_schedule.json")
    monkeypatch.setattr(notification_tool, "LATEST_DRAFT_PATH", reports / "latest_email_draft.json")
    monkeypatch.setattr(pdf_tool, "REPORTS_DIR", reports)
    monkeypatch.setattr(approvals, "REPORTS_DIR", reports)
    # Never use real e-mail settings from .env in tests
    for var in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM", "TEAM_EMAILS"):
        monkeypatch.delenv(var, raising=False)
    scheduling_tool.clear_schedule_cache()
    return tmp_path
