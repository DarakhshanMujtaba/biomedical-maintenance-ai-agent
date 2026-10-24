import json
from datetime import timedelta
from pathlib import Path

from sql_tool import get_equipment_needing_maintenance, get_available_engineers, today
from prioritization_tool import rank_equipment_by_priority
from calendar_tool import assign_time_slots, build_maintenance_schedule, format_slot

REPORTS_DIR = Path(__file__).parent.parent / "reports"
LATEST_SCHEDULE_PATH = REPORTS_DIR / "latest_schedule.json"

# The crew's Schedule step and Notify step both need the schedule. It is computed
# once per (top_n, ward, within_days, day) and reused, so the e-mail always matches
# the .ics file and the .ics file is written only once.
_schedule_cache = {}


def clear_schedule_cache():
    """Call at the start of each pipeline run, so data changed since the last run
    (e.g. a device marked as serviced) is picked up."""
    _schedule_cache.clear()


def propose_maintenance_schedule(top_n=5, ward=None, within_days=30):
    cache_key = (top_n, ward, within_days, today().isoformat())
    if cache_key in _schedule_cache:
        return _schedule_cache[cache_key]

    equipment = get_equipment_needing_maintenance(ward=ward, within_days=within_days)
    ranked = rank_equipment_by_priority(equipment)
    top_items = ranked[:top_n]

    scheduled = []
    unassigned = []

    # One device per day for the whole team (team decision), starting tomorrow
    for index, item in enumerate(top_items):
        available_engineers = get_available_engineers(specialty=item["type"])

        if not available_engineers:
            unassigned.append({
                "equipment_name": item["name"],
                "type": item["type"],
                "reason": "No available engineer with matching specialty",
            })
            continue

        engineer = available_engineers[0]
        proposed_date = (today() + timedelta(days=index + 1)).isoformat()

        scheduled.append({
            "equipment_id": item["id"],
            "equipment_name": item["name"],
            "ward": item["ward"],
            "engineer_id": engineer["id"],
            "engineer_name": engineer["name"],
            "proposed_date": proposed_date,
        })

    # Add the time slot (9 AM / 11 AM / 1 PM per engineer per day, local time)
    with_slots = assign_time_slots(scheduled)
    for item, slotted in zip(scheduled, with_slots):
        item["start_time"] = slotted["start"].isoformat()
        item["proposed_slot"] = format_slot(slotted["start"])

    if scheduled:
        build_maintenance_schedule(with_slots)

    result = {"scheduled": scheduled, "unassigned": unassigned}
    _schedule_cache[cache_key] = result

    # Saved for the dashboard / API ("latest draft schedule")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_SCHEDULE_PATH.write_text(json.dumps(
        {"params": {"top_n": top_n, "ward": ward, "within_days": within_days}, **result}, indent=2))
    return result


if __name__ == "__main__":
    result = propose_maintenance_schedule(top_n=5, ward="ICU", within_days=30)

    print("Scheduled:")
    for item in result["scheduled"]:
        print(f"  {item['equipment_name']} -> {item['engineer_name']} at {item['proposed_slot']}")

    print("\nUnassigned:")
    for item in result["unassigned"]:
        print(f"  {item['equipment_name']} ({item['type']}) — {item['reason']}")
