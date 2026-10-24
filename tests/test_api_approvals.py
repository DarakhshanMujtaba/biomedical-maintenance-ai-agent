"""
Dashboard endpoints and the human-approval gate (api/approvals.py).
No LLM is called and no real e-mail is ever sent: SMTP is replaced by a fake.
"""
import smtplib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import sql_tool
from api import approvals
from api.main import app
from conftest import TODAY

client = TestClient(app)   # no "with": the startup hook (real init_db) does not run


class FakeSMTP:
    """Stands in for smtplib.SMTP and remembers every message 'sent'."""
    sent = []

    def __init__(self, host, port, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


@pytest.fixture
def email_configured(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("TEAM_EMAILS", "team1@example.com, team2@example.com")


def new_draft():
    r = client.post("/drafts", json={"top_n": 3, "ward": "ICU", "within_days": 30})
    assert r.status_code == 200
    return r.json()["email_draft"]


def decide(draft_id, decision, who="Dr. Test"):
    return client.post(f"/drafts/{draft_id}/decision", json={"decision": decision, "decided_by": who})


# ─── Fast dashboard endpoints ─────────────────────────────────────────────────

def test_equipment_list_has_asset_code_live_status_and_priority():
    devices = client.get("/equipment").json()
    assert devices[0]["priority_score"] >= devices[-1]["priority_score"]   # most urgent first
    assert {"asset_code", "status", "priority_score"} <= set(devices[0])


def test_mark_serviced_by_asset_code_moves_due_date_and_logs_it():
    conn = sql_tool.get_connection()
    conn.execute("UPDATE equipment SET asset_code = 'PM-TEST-1' WHERE name = 'Monitor-01'")
    conn.commit()
    conn.close()

    r = client.post("/equipment/by-asset/PM-TEST-1/serviced", json={"serviced_by": "Sara Malik"})
    assert r.status_code == 200
    device = r.json()
    assert device["status"] == "OK"
    assert device["next_due_date"] == (TODAY + timedelta(days=180)).isoformat()   # Monitor interval

    conn = sql_tool.get_connection()
    event = conn.execute("SELECT * FROM service_events").fetchone()
    conn.close()
    assert event["serviced_by"] == "Sara Malik"

    assert client.post("/equipment/by-asset/NOPE/serviced", json={"serviced_by": "x"}).status_code == 404


def test_making_a_draft_sends_nothing(fake_smtp, email_configured):
    draft = new_draft()
    assert draft["draft_id"]
    assert fake_smtp.sent == []


# ─── The approval gate ───────────────────────────────────────────────────────

def test_decline_is_recorded_and_never_sends(fake_smtp, email_configured):
    draft = new_draft()
    r = decide(draft["draft_id"], "declined")
    assert r.status_code == 200
    assert r.json()["decision"] == "declined" and r.json()["sent"] == 0
    assert fake_smtp.sent == []


def test_approve_sends_exact_stored_text_once(fake_smtp, email_configured):
    draft = new_draft()
    r = decide(draft["draft_id"], "approved", who="Head of Biomedical")
    assert r.status_code == 200
    assert r.json()["sent"] == 1
    assert r.json()["decided_by"] == "Head of Biomedical"

    assert len(fake_smtp.sent) == 1
    msg = fake_smtp.sent[0]
    assert msg["Subject"] == draft["subject"]
    assert msg["To"] == "team1@example.com, team2@example.com"
    assert draft["body"] in msg.get_body(preferencelist=("plain",)).get_content()
    attached = [part.get_filename() for part in msg.iter_attachments()]
    assert "proposed_schedule.ics" in attached and any(n.endswith(".pdf") for n in attached)

    # Clicking Approve again must not send a second time
    assert decide(draft["draft_id"], "approved").status_code == 409
    assert len(fake_smtp.sent) == 1


def test_outdated_draft_cannot_be_approved(fake_smtp, email_configured):
    old = new_draft()
    new_draft()                                   # a newer draft replaces it
    assert decide(old["draft_id"], "approved").status_code == 409
    assert fake_smtp.sent == []


def test_approve_refused_when_email_not_configured(fake_smtp):
    draft = new_draft()
    r = decide(draft["draft_id"], "approved")
    assert r.status_code == 503
    assert fake_smtp.sent == []
    assert approvals.get_decision(draft["draft_id"]) is None   # nothing recorded, can retry later


def test_failed_send_is_not_recorded_and_can_be_retried(monkeypatch, email_configured):
    class BrokenSMTP(FakeSMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"bad password")
    monkeypatch.setattr(smtplib, "SMTP", BrokenSMTP)

    draft = new_draft()
    assert decide(draft["draft_id"], "approved").status_code == 502
    assert approvals.get_decision(draft["draft_id"]) is None


def test_decision_needs_a_name_and_a_valid_choice(email_configured, fake_smtp):
    draft = new_draft()
    assert decide(draft["draft_id"], "maybe").status_code == 400
    assert decide(draft["draft_id"], "approved", who="  ").status_code == 400
    assert fake_smtp.sent == []
