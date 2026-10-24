import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "equipment.db"

DUE_SOON_WINDOW_DAYS = 30

# Days between preventive maintenance visits, per equipment type
MAINTENANCE_INTERVALS = {
    "Ventilator": 90,
    "Infusion Pump": 60,
    "Monitor": 180,
    "Defibrillator": 120,
}


def today():
    """Single place that decides "today" (tests replace it to simulate later dates)."""
    return date.today()


def compute_status(next_due_date, on_date=None):
    """Overdue / Due / OK, always calculated from next_due_date.
    The stored maintenance_logs.status is only a snapshot from seeding time and goes
    stale as days pass, so every read uses this instead."""
    on_date = on_date or today()
    if isinstance(next_due_date, str):
        next_due_date = date.fromisoformat(next_due_date)
    if next_due_date < on_date:
        return "Overdue"
    if next_due_date <= on_date + timedelta(days=DUE_SOON_WINDOW_DAYS):
        return "Due"
    return "OK"


def with_live_status(rows):
    """Turn sqlite rows into dicts and replace the stored status with the live one."""
    result = []
    for row in rows:
        item = dict(row)
        if "next_due_date" in item:
            item["status"] = compute_status(item["next_due_date"])
        result.append(item)
    return result


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def get_equipment_needing_maintenance(ward=None, within_days=30):
    cutoff_date = (today() + timedelta(days=within_days)).isoformat()
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT equipment.id, equipment.name, equipment.type, equipment.ward,
               equipment.criticality, equipment.usage_hours, equipment.asset_code,
               maintenance_logs.last_service_date, maintenance_logs.next_due_date,
               maintenance_logs.status
        FROM equipment
        JOIN maintenance_logs ON maintenance_logs.equipment_id = equipment.id
        WHERE maintenance_logs.next_due_date <= ?
    """
    params = [cutoff_date]

    if ward is not None:
        query += " AND equipment.ward = ?"
        params.append(ward)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return with_live_status(rows)


def get_equipment_by_ids(equipment_ids):
    if not equipment_ids:
        return []

    conn = get_connection()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in equipment_ids)
    query = f"""
        SELECT equipment.id, equipment.name, equipment.type, equipment.ward,
               equipment.criticality, equipment.usage_hours, equipment.asset_code,
               maintenance_logs.last_service_date, maintenance_logs.next_due_date,
               maintenance_logs.status
        FROM equipment
        JOIN maintenance_logs ON maintenance_logs.equipment_id = equipment.id
        WHERE equipment.id IN ({placeholders})
    """
    cur.execute(query, equipment_ids)
    rows = cur.fetchall()
    conn.close()
    return with_live_status(rows)


def get_available_engineers(specialty=None):
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT id, name, specialty, availability FROM engineers WHERE availability = 'Available'"
    params = []

    if specialty is not None:
        query += " AND specialty = ?"
        params.append(specialty)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return with_live_status(rows)

def get_engineers_by_ids(engineer_ids):
    if not engineer_ids:
        return []

    conn = get_connection()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in engineer_ids)
    query = f"SELECT id, name, specialty, availability FROM engineers WHERE id IN ({placeholders})"
    cur.execute(query, engineer_ids)
    rows = cur.fetchall()
    conn.close()
    return with_live_status(rows)


def get_all_equipment_with_status():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT equipment.id, equipment.name, equipment.type, equipment.ward,
               equipment.criticality, equipment.usage_hours, equipment.install_date, equipment.asset_code,
               maintenance_logs.last_service_date, maintenance_logs.next_due_date,
               maintenance_logs.status
        FROM equipment
        JOIN maintenance_logs ON maintenance_logs.equipment_id = equipment.id
        ORDER BY equipment.ward, equipment.type
    """)
    rows = cur.fetchall()
    conn.close()
    return with_live_status(rows)


def mark_serviced(equipment_id, serviced_by, serviced_on=None):
    """Record that a device was serviced: last service = serviced_on (default today),
    next due = serviced_on + the type's interval. Logged in service_events.
    Returns the updated device, or None if the id does not exist."""
    serviced_on = serviced_on or today()
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT equipment.id, equipment.type, maintenance_logs.next_due_date
            FROM equipment JOIN maintenance_logs ON maintenance_logs.equipment_id = equipment.id
            WHERE equipment.id = ?""", (equipment_id,)).fetchone()
        if row is None:
            return None

        new_due = serviced_on + timedelta(days=MAINTENANCE_INTERVALS[row["type"]])
        conn.execute(
            "UPDATE maintenance_logs SET last_service_date = ?, next_due_date = ?, status = ? WHERE equipment_id = ?",
            (serviced_on.isoformat(), new_due.isoformat(), compute_status(new_due, serviced_on), equipment_id))
        conn.execute(
            """INSERT INTO service_events (equipment_id, serviced_on, serviced_by, previous_due_date, new_due_date, recorded_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (equipment_id, serviced_on.isoformat(), serviced_by, row["next_due_date"], new_due.isoformat()))
        conn.commit()
    finally:
        conn.close()
    return get_equipment_by_ids([equipment_id])[0]


def get_equipment_by_asset_code(asset_code):
    conn = get_connection()
    row = conn.execute("SELECT id FROM equipment WHERE asset_code = ?", (asset_code,)).fetchone()
    conn.close()
    return get_equipment_by_ids([row["id"]])[0] if row else None


if __name__ == "__main__":
    print("Equipment needing maintenance (ICU, next 30 days):")
    for row in get_equipment_needing_maintenance(ward="ICU", within_days=30):
        print(row)

    print("\nEquipment by IDs [1, 2]:")
    for row in get_equipment_by_ids([1, 2]):
        print(row)

    print("\nAvailable Ventilator engineers:")
    for row in get_available_engineers(specialty="Ventilator"):
        print(row)

    print("\nAll equipment with status:")
    for row in get_all_equipment_with_status():
        print(row)
