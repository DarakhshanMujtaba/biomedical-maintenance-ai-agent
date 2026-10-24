"""
Run from the project root:  venv/bin/python -m pytest -v     (Windows: venv\\Scripts\\python -m pytest -v)
"""
import smtplib
import socket
from datetime import date, timedelta

import pytest

import scheduling_tool
import sql_tool
from calendar_tool import assign_time_slots
from conftest import TODAY
from notification_tool import draft_team_notification
from prioritization_tool import calculate_priority_score
from scheduling_tool import propose_maintenance_schedule


# ─── Priority score (design rule 2) ──────────────────────────────────────────

def item(criticality, usage_hours, overdue_days=0):
    due = date.today() - timedelta(days=overdue_days)
    return {"criticality": criticality, "usage_hours": usage_hours, "next_due_date": due.isoformat()}


@pytest.mark.parametrize("overdue_days", [0, 3, 30])
@pytest.mark.parametrize("higher, lower", [("High", "Medium"), ("Medium", "Low"), ("High", "Low")])
def test_usage_can_never_flip_a_criticality_tier(higher, lower, overdue_days):
    # Lower tier with ENORMOUS usage vs higher tier with ZERO usage, same overdue days
    assert calculate_priority_score(item(higher, 0, overdue_days)) > \
           calculate_priority_score(item(lower, 10_000_000, overdue_days))


def test_score_formula_matches_documentation():
    # 11 days overdue, High, 6000 h → 110 + 60 + min(60, 15) = 185
    assert calculate_priority_score(item("High", 6000, overdue_days=11)) == 185
    # Not overdue (due in future) adds nothing
    future = {"criticality": "Low", "usage_hours": 0,
              "next_due_date": (date.today() + timedelta(days=5)).isoformat()}
    assert calculate_priority_score(future) == 20


# ─── Calendar slots (design rule 3) ──────────────────────────────────────────

def test_same_engineer_same_day_is_staggered_9_11_13_local_time():
    slots = assign_time_slots([
        {"equipment_id": 1, "engineer_id": 7, "proposed_date": "2026-10-25"},
        {"equipment_id": 2, "engineer_id": 7, "proposed_date": "2026-10-25"},
        {"equipment_id": 3, "engineer_id": 7, "proposed_date": "2026-10-25"},
        {"equipment_id": 4, "engineer_id": 8, "proposed_date": "2026-10-25"},   # other engineer
        {"equipment_id": 5, "engineer_id": 7, "proposed_date": "2026-10-26"},   # next day
    ])
    assert [s["start"].hour for s in slots] == [9, 11, 13, 9, 9]
    # 9 AM in Karachi is 04:00 UTC (so calendar apps show 9 AM, not 2 PM)
    assert slots[0]["start"].utcoffset() == timedelta(hours=5)


def test_ics_file_uses_local_time(isolated):
    propose_maintenance_schedule(top_n=2, ward="ICU", within_days=30)
    ics = (isolated / "reports" / "proposed_schedule.ics").read_text()
    assert "T040000Z" in ics            # 09:00 Asia/Karachi
    assert "T090000Z" not in ics        # the old bug: 09:00 UTC = 2 PM in Karachi


# ─── Status is always live (fix A2) ──────────────────────────────────────────

def test_compute_status_rules():
    assert sql_tool.compute_status("2026-10-23", TODAY) == "Overdue"
    assert sql_tool.compute_status("2026-10-24", TODAY) == "Due"      # due today
    assert sql_tool.compute_status("2026-11-23", TODAY) == "Due"      # exactly 30 days
    assert sql_tool.compute_status("2026-11-24", TODAY) == "OK"


def test_stored_status_is_ignored_and_status_moves_with_time(monkeypatch):
    rows = {r["name"]: r["status"] for r in sql_tool.get_all_equipment_with_status()}
    # The test DB stores "OK" for everything; live status must differ
    assert rows["Ventilator-01"] == "Overdue"
    assert rows["Infusion Pump-01"] == "Due"
    assert rows["Monitor-04"] == "OK"

    # 15 days later the infusion pump (due in 10 days) has become overdue
    monkeypatch.setattr(sql_tool, "today", lambda: TODAY + timedelta(days=15))
    later = {r["name"]: r["status"] for r in sql_tool.get_all_equipment_with_status()}
    assert later["Infusion Pump-01"] == "Overdue"


# ─── Scheduling ──────────────────────────────────────────────────────────────

def test_one_device_per_day_for_the_team():
    scheduled = propose_maintenance_schedule(top_n=5, ward=None, within_days=30)["scheduled"]
    dates = [s["proposed_date"] for s in scheduled]
    assert len(dates) == len(set(dates))
    assert dates[0] == (TODAY + timedelta(days=1)).isoformat()


def test_schedule_is_computed_once_and_reused_by_the_notification(monkeypatch):
    calls = []
    real_build = scheduling_tool.build_maintenance_schedule
    monkeypatch.setattr(scheduling_tool, "build_maintenance_schedule",
                        lambda items: calls.append(1) or real_build(items))

    first = propose_maintenance_schedule(top_n=3, ward="ICU", within_days=30)
    result = draft_team_notification(top_n=3, ward="ICU", within_days=30)

    assert len(calls) == 1                                  # .ics written once
    for s in first["scheduled"]:                            # e-mail shows the same slots
        assert s["proposed_slot"] in result["draft"]["body"]


# ─── Safety rule 1: drafting never sends ─────────────────────────────────────

def test_email_draft_has_no_send_side_effect(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Drafting tried to open a network connection / send e-mail!")
    monkeypatch.setattr(smtplib, "SMTP", forbidden)
    monkeypatch.setattr(smtplib, "SMTP_SSL", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    result = draft_team_notification(top_n=5, ward="ICU", within_days=30)
    draft = result["draft"]
    assert draft["subject"].startswith("Maintenance Schedule Update")
    assert "draft" not in draft["body"].lower()            # the approved text must not say "draft"


def test_unscheduled_overdue_count_uses_live_status():
    # top_n=1 → only the most urgent ICU device is scheduled; 1 other ICU device is overdue
    body = draft_team_notification(top_n=1, ward="ICU", within_days=30)["draft"]["body"]
    assert "1 additional overdue device(s)" in body
