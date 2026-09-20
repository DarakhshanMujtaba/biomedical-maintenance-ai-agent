from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta

from ics import Calendar, Event

from sql_tool import get_equipment_by_ids, get_engineers_by_ids

OUTPUT_DIR = Path(__file__).parent.parent / "reports"
START_HOUR = 9
DURATION_HOURS = 1
SLOT_SPACING_HOURS = 2


def build_maintenance_schedule(schedule_items):
    equipment_ids = [item["equipment_id"] for item in schedule_items]
    engineer_ids = [item["engineer_id"] for item in schedule_items]

    equipment_by_id = {row["id"]: row for row in get_equipment_by_ids(equipment_ids)}
    engineers_by_id = {row["id"]: row for row in get_engineers_by_ids(engineer_ids)}

    calendar = Calendar()
    slot_counters = defaultdict(int)

    for item in schedule_items:
        equipment = equipment_by_id[item["equipment_id"]]
        engineer = engineers_by_id[item["engineer_id"]]

        day_key = (item["engineer_id"], item["proposed_date"])
        slot_index = slot_counters[day_key]
        slot_counters[day_key] += 1

        start = datetime.fromisoformat(item["proposed_date"]).replace(hour=START_HOUR, minute=0)
        start += timedelta(hours=slot_index * SLOT_SPACING_HOURS)

        event = Event()
        event.name = f"Maintenance: {equipment['name']}"
        event.begin = start
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
        f.writelines(calendar)

    print(f"Schedule draft saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    sample_schedule = [
        {"equipment_id": 1, "engineer_id": 1, "proposed_date": "2026-09-25"},
        {"equipment_id": 5, "engineer_id": 2, "proposed_date": "2026-09-26"},
        {"equipment_id": 3, "engineer_id": 1, "proposed_date": "2026-09-25"},  # same engineer + day as item 1
    ]
    build_maintenance_schedule(sample_schedule)
