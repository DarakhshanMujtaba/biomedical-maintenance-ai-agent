from datetime import date

CRITICALITY_WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}
USAGE_COMPONENT_CAP = 15


def calculate_priority_score(equipment):
    next_due_date = date.fromisoformat(equipment["next_due_date"])
    overdue_days = (date.today() - next_due_date).days

    overdue_component = max(0, overdue_days) * 10
    criticality_component = CRITICALITY_WEIGHTS[equipment["criticality"]] * 20
    usage_component = min(equipment["usage_hours"] / 100, USAGE_COMPONENT_CAP)

    return overdue_component + criticality_component + usage_component


def rank_equipment_by_priority(equipment_list):
    scored = []
    for item in equipment_list:
        scored_item = dict(item)
        scored_item["priority_score"] = calculate_priority_score(item)
        scored.append(scored_item)

    scored.sort(key=lambda row: row["priority_score"], reverse=True)
    return scored


if __name__ == "__main__":
    sample_equipment = [
        {"name": "High-crit, barely used, due today", "criticality": "High", "usage_hours": 100, "next_due_date": date.today().isoformat()},
        {"name": "Medium-crit, absurdly heavily used", "criticality": "Medium", "usage_hours": 999999, "next_due_date": date.today().isoformat()},
        {"name": "Low-crit, absurdly heavily used", "criticality": "Low", "usage_hours": 999999, "next_due_date": date.today().isoformat()},
        {"name": "High-crit, 18 days overdue", "criticality": "High", "usage_hours": 1500, "next_due_date": "2026-09-01"},
    ]

    ranked = rank_equipment_by_priority(sample_equipment)
    for item in ranked:
        print(f"{item['priority_score']:.1f} — {item['name']}")
