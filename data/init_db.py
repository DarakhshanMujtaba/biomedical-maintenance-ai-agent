import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "equipment.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db(db_path=DB_PATH):
    """Create missing tables. Safe to run again on an existing database:
    it also upgrades databases made before asset_code existed."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Upgrade: older databases have no equipment.asset_code column
    columns = [row[1] for row in conn.execute("PRAGMA table_info(equipment)")]
    if columns and "asset_code" not in columns:
        conn.execute("ALTER TABLE equipment ADD COLUMN asset_code TEXT")

    conn.executescript(SCHEMA_PATH.read_text())

    conn.commit()
    conn.close()
    print(f"Database ready at: {db_path}")


if __name__ == "__main__":
    init_db()
