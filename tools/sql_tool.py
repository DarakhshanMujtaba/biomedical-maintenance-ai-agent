import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "equipment.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def get_equipment_needing_maintenance(ward=None, within_days=30):
    cutoff_date = (date.today() + timedelta(days=within_days)).isoformat()
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT equipment.id, equipment.name, equipment.type, equipment.ward,
               equipment.criticality, equipment.usage_hours,
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
    return [dict(row) for row in rows]


def get_equipment_by_ids(equipment_ids):
    if not equipment_ids:
        return []

    conn = get_connection()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in equipment_ids)
    query = f"""
        SELECT equipment.id, equipment.name, equipment.type, equipment.ward,
               equipment.criticality, equipment.usage_hours,
               maintenance_logs.last_service_date, maintenance_logs.next_due_date,
               maintenance_logs.status
        FROM equipment
        JOIN maintenance_logs ON maintenance_logs.equipment_id = equipment.id
        WHERE equipment.id IN ({placeholders})
    """
    cur.execute(query, equipment_ids)
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
    return [dict(row) for row in rows]

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
    return [dict(row) for row in rows]


def get_all_equipment_with_status():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT equipment.id, equipment.name, equipment.type, equipment.ward,
               equipment.criticality, equipment.usage_hours, equipment.install_date,
               maintenance_logs.last_service_date, maintenance_logs.next_due_date,
               maintenance_logs.status
        FROM equipment
        JOIN maintenance_logs ON maintenance_logs.equipment_id = equipment.id
        ORDER BY equipment.ward, equipment.type
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
