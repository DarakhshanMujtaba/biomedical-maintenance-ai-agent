import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "equipment.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    schema_sql = SCHEMA_PATH.read_text()
    conn.executescript(schema_sql)

    conn.commit()
    conn.close()
    print(f"Database created at: {DB_PATH}")

if __name__ == "__main__":
    init_db()
