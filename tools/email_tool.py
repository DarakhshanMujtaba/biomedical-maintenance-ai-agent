def draft_maintenance_email(scheduled_items, unscheduled_overdue_count):
    subject = f"Maintenance Schedule Update — {len(scheduled_items)} device(s) scheduled"

    lines = ["Hi team,", "", "The following equipment has been scheduled for maintenance:", ""]

    for item in scheduled_items:
        lines.append(
            f"- {item['equipment_name']} ({item['ward']}) "
            f"— Engineer: {item['engineer_name']} "
            f"— {item['scheduled_date']}"
        )

    lines.append("")
    if unscheduled_overdue_count > 0:
        lines.append(
            f"Note: {unscheduled_overdue_count} additional overdue device(s) "
            "were not scheduled this cycle and still require attention."
        )
    else:
        lines.append("No other overdue devices remain outstanding at this time.")

    lines.append("")
    lines.append("This is an automated draft. Please review before sending.")

    body = "\n".join(lines)

    return {"subject": subject, "body": body}


if __name__ == "__main__":
    sample_scheduled = [
        {"equipment_name": "Ventilator-01", "ward": "ICU", "engineer_name": "Ayesha Khan", "scheduled_date": "2026-09-25 09:00"},
        {"equipment_name": "Ventilator-03", "ward": "General Ward", "engineer_name": "Ayesha Khan", "scheduled_date": "2026-09-25 11:00"},
        {"equipment_name": "Infusion Pump-01", "ward": "ICU", "engineer_name": "Bilal Ahmed", "scheduled_date": "2026-09-26 09:00"},
    ]
    draft = draft_maintenance_email(sample_scheduled, unscheduled_overdue_count=2)
    print("SUBJECT:", draft["subject"])
    print()
    print(draft["body"])
