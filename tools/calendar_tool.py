import os
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ics import Calendar, Event

from sql_tool import get_equipment_by_ids, get_engineers_by_ids

OUTPUT_DIR = Path(__file__).parent.parent / "reports"
START_HOUR = 9
DURATION_HOURS = 1
SLOT_SPACING_HOURS = 2

# Slot times are local hospital time. Without a time zone the .ics file says
# 09:00 UTC, which a calendar in Karachi shows as 2 PM.
TIMEZONE = ZoneInfo(os.getenv("SCHEDULE_TIMEZONE", "Asia/Karachi"))


def assign_time_slots(schedule_items):
    """Give each item a start time. Per engineer per day the slots are
    9 AM, 11 AM, 1 PM, ... (2-hour spacing). Returns new dicts with a "start" datetime."""
    slot_counters = defaultdict(int)
    result = []
    for item in schedule_items:
        day_key = (item["engineer_id"], item["proposed_date"])
        slot_index = slot_counters[day_key]
        slot_counters[day_key] += 1

        day = datetime.fromisoformat(item["proposed_date"])
        start = day.replace(hour=START_HOUR, minute=0, tzinfo=TIMEZONE)
        start += timedelta(hours=slot_index * SLOT_SPACING_HOURS)
        result.append({**item, "start": start})
    return result


def format_slot(start):
    """2026-10-25 09:00 PKT — used in the email draft."""
    return start.strftime("%Y-%m-%d %H:%M ") + (start.tzname() or "")


def build_maintenance_schedule(schedule_items):
    if schedule_items and "start" not in schedule_items[0]:
        schedule_items = assign_time_slots(schedule_items)

    equipment_ids = [item["equipment_id"] for item in schedule_items]
    engineer_ids = [item["engineer_id"] for item in schedule_items]

    equipment_by_id = {row["id"]: row for row in get_equipment_by_ids(equipment_ids)}
    engineers_by_id = {row["id"]: row for row in get_engineers_by_ids(engineer_ids)}

    calendar = Calendar()

    for item in schedule_items:
        equipment = equipment_by_id[item["equipment_id"]]
        engineer = engineers_by_id[item["engineer_id"]]

        event = Event()
        event.name = f"Maintenance: {equipment['name']}"
        event.begin = item["start"]
        event.duration = timedelta(hours=DURATION_HOURS)
        event.description = (
            f"Engineer: {engineer['name']}\n"
            f"Ward: {equipment['ward']}\n"
            f"Type: {equipment['type']}"
        )
        calendar.events.add(event)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "proposed_schedule.ics"
    with open(output_path, "w") as f:
        f.writelines(calendar.serialize_iter())

    print(f"Schedule draft saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    sample_schedule = [
        {"equipment_id": 1, "engineer_id": 1, "proposed_date": "2026-09-25"},
        {"equipment_id": 5, "engineer_id": 2, "proposed_date": "2026-09-26"},
        {"equipment_id": 3, "engineer_id": 1, "proposed_date": "2026-09-25"},  # same engineer + day as item 1
    ]
    for slot in assign_time_slots(sample_schedule):
        print(slot["equipment_id"], "->", format_slot(slot["start"]))
    build_maintenance_schedule(sample_schedule)
