from datetime import date, timedelta

from sql_tool import get_equipment_needing_maintenance, get_available_engineers
from prioritization_tool import rank_equipment_by_priority
from calendar_tool import build_maintenance_schedule


def propose_maintenance_schedule(top_n=5, ward=None, within_days=30):
    equipment = get_equipment_needing_maintenance(ward=ward, within_days=within_days)
    ranked = rank_equipment_by_priority(equipment)
    top_items = ranked[:top_n]

    scheduled = []
    unassigned = []

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
        proposed_date = (date.today() + timedelta(days=index + 1)).isoformat()

        scheduled.append({
            "equipment_id": item["id"],
            "equipment_name": item["name"],
            "ward": item["ward"],
            "engineer_id": engineer["id"],
            "engineer_name": engineer["name"],
            "proposed_date": proposed_date,
        })


    if scheduled:
        ics_input = [
            {"equipment_id": s["equipment_id"], "engineer_id": s["engineer_id"], "proposed_date": s["proposed_date"]}
            for s in scheduled
        ]
        build_maintenance_schedule(ics_input)

    return {"scheduled": scheduled, "unassigned": unassigned}


if __name__ == "__main__":
    result = propose_maintenance_schedule(top_n=5, ward="ICU", within_days=30)

    print("Scheduled:")
    for item in result["scheduled"]:
        print(f"  {item['equipment_name']} -> {item['engineer_name']} on {item['proposed_date']}")

    print("\nUnassigned:")
    for item in result["unassigned"]:
        print(f"  {item['equipment_name']} ({item['type']}) — {item['reason']}")
