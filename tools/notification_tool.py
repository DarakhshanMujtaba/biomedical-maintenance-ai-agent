import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sql_tool import get_equipment_needing_maintenance
from scheduling_tool import propose_maintenance_schedule
from email_tool import draft_maintenance_email

LATEST_DRAFT_PATH = Path(__file__).parent.parent / "reports" / "latest_email_draft.json"


def draft_team_notification(top_n=5, ward=None, within_days=30):
    # Reuses the schedule already computed in this run (no second .ics, same dates/times)
    schedule_result = propose_maintenance_schedule(top_n=top_n, ward=ward, within_days=within_days)
    scheduled = schedule_result["scheduled"]

    all_matching = get_equipment_needing_maintenance(ward=ward, within_days=within_days)
    overdue_items = [item for item in all_matching if item["status"] == "Overdue"]
    scheduled_ids = {item["equipment_id"] for item in scheduled}
    unscheduled_overdue_count = len(
        [item for item in overdue_items if item["id"] not in scheduled_ids]
    )

    email_items = [
        {
            "equipment_name": item["equipment_name"],
            "ward": item["ward"],
            "engineer_name": item["engineer_name"],
            "scheduled_date": item["proposed_slot"],
        }
        for item in scheduled
    ]

    draft = draft_maintenance_email(email_items, unscheduled_overdue_count)
    # A unique id per draft: an approval must name the exact draft it approves,
    # and the same draft can be decided (and sent) only once.
    draft["draft_id"] = uuid.uuid4().hex
    draft["created_at"] = datetime.now(timezone.utc).isoformat()

    # The exact text a human approves and n8n / the dashboard sends (not the LLM's re-wording)
    LATEST_DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_DRAFT_PATH.write_text(json.dumps(draft, indent=2, ensure_ascii=False))

    return {"draft": draft, "scheduled_count": len(scheduled), "unassigned": schedule_result["unassigned"]}


if __name__ == "__main__":
    result = draft_team_notification(top_n=5, ward="ICU", within_days=30)
    print("SUBJECT:", result["draft"]["subject"])
    print()
    print(result["draft"]["body"])
    print()
    print("Unassigned:", result["unassigned"])
