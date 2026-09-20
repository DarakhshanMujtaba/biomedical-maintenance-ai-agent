CREATE TABLE IF NOT EXISTS equipment (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    type          TEXT NOT NULL,
    ward          TEXT NOT NULL,
    criticality   TEXT NOT NULL CHECK (criticality IN ('High', 'Medium', 'Low')),
    usage_hours   INTEGER NOT NULL DEFAULT 0,
    install_date  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engineers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    specialty     TEXT NOT NULL,
    availability  TEXT NOT NULL CHECK (availability IN ('Available', 'Busy'))
);

CREATE TABLE IF NOT EXISTS maintenance_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id        INTEGER NOT NULL,
    last_service_date   TEXT NOT NULL,
    next_due_date       TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('OK', 'Due', 'Overdue')),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
);
