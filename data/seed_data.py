import sqlite3
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.append(str(Path(__file__).parent.parent / "tools"))

from sql_tool import compute_status   # same Overdue/Due/OK rule used everywhere else

DB_PATH = Path(__file__).parent / "equipment.db"

MAINTENANCE_INTERVALS = {
    "Ventilator": 90,
    "Infusion Pump": 60,
    "Monitor": 180,
    "Defibrillator": 120,
}

# (name, type, ward, criticality, usage_hours, install_date, days_since_last_service)
EQUIPMENT = [
    ("Ventilator-01", "Ventilator", "ICU", "High", 4200, "2022-05-10", 95),
    ("Ventilator-02", "Ventilator", "OT", "High", 3100, "2023-01-20", 70),
    ("Ventilator-03", "Ventilator", "General Ward", "Medium", 2500, "2023-06-01", 20),
    ("Ventilator-04", "Ventilator", "ER", "Medium", 3600, "2022-04-04", 100),
    ("Infusion Pump-01", "Infusion Pump", "ICU", "Medium", 5000, "2021-11-15", 65),
    ("Infusion Pump-02", "Infusion Pump", "ER", "High", 3300, "2022-08-08", 45),
    ("Infusion Pump-03", "Infusion Pump", "OT", "Low", 1200, "2023-09-01", 10),
    ("Infusion Pump-04", "Infusion Pump", "General Ward", "Medium", 2800, "2022-12-12", 55),
    ("Monitor-01", "Monitor", "ICU", "Medium", 6000, "2020-03-01", 190),
    ("Monitor-02", "Monitor", "ER", "Low", 4200, "2021-07-19", 150),
    ("Monitor-03", "Monitor", "OT", "Medium", 3900, "2022-02-14", 60),
    ("Monitor-04", "Monitor", "General Ward", "Low", 2100, "2023-04-04", 30),
    ("Defibrillator-01", "Defibrillator", "ICU", "High", 1500, "2021-09-09", 130),
    ("Defibrillator-02", "Defibrillator", "ER", "High", 1100, "2022-10-10", 100),
    ("Defibrillator-03", "Defibrillator", "OT", "Medium", 900, "2023-03-03", 40),
    ("Defibrillator-04", "Defibrillator", "General Ward", "Low", 700, "2023-08-08", 15),
]

# (name, specialty, availability)
ENGINEERS = [
    ("Ayesha Khan", "Ventilator", "Available"),
    ("Bilal Ahmed", "Infusion Pump", "Available"),
    ("Sara Malik", "Monitor", "Available"),
    ("Omar Farooq", "Defibrillator", "Available"),
    ("Hamza Raza", "Ventilator", "Busy"),
]


def seed():
    today = date.today()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # Clear existing rows first so re-running this script during development is safe
    cur.execute("DELETE FROM maintenance_logs;")
    cur.execute("DELETE FROM equipment;")
    cur.execute("DELETE FROM engineers;")
    # Restart ids at 1 so demos and tests that use fixed ids keep working after re-seeding
    cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('equipment', 'maintenance_logs', 'engineers');")

    for name, etype, ward, criticality, usage_hours, install_date, days_since_service in EQUIPMENT:
        cur.execute(
            """
            INSERT INTO equipment (name, type, ward, criticality, usage_hours, install_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, etype, ward, criticality, usage_hours, install_date),
        )
        equipment_id = cur.lastrowid

        last_service_date = today - timedelta(days=days_since_service)
        interval = MAINTENANCE_INTERVALS[etype]
        next_due_date = last_service_date + timedelta(days=interval)
        status = compute_status(next_due_date, today)

        cur.execute(
            """
            INSERT INTO maintenance_logs (equipment_id, last_service_date, next_due_date, status)
            VALUES (?, ?, ?, ?)
            """,
            (equipment_id, last_service_date.isoformat(), next_due_date.isoformat(), status),
        )

    for name, specialty, availability in ENGINEERS:
        cur.execute(
            "INSERT INTO engineers (name, specialty, availability) VALUES (?, ?, ?)",
            (name, specialty, availability),
        )

    conn.commit()
    conn.close()
    print(f"Seeded {len(EQUIPMENT)} equipment, {len(EQUIPMENT)} maintenance logs, {len(ENGINEERS)} engineers.")


if __name__ == "__main__":
    seed()
