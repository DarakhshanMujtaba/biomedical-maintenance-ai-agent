CREATE TABLE IF NOT EXISTS equipment (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    type          TEXT NOT NULL,
    ward          TEXT NOT NULL,
    criticality   TEXT NOT NULL CHECK (criticality IN ('High', 'Medium', 'Low')),
    usage_hours   INTEGER NOT NULL DEFAULT 0,
    install_date  TEXT NOT NULL,
    asset_code    TEXT          -- link to the RFID dashboard's assets (e.g. PM-2024-001); NULL = not RFID-tagged
);

-- One asset_code per device (several NULLs are allowed)
CREATE UNIQUE INDEX IF NOT EXISTS idx_equipment_asset_code ON equipment(asset_code);

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

-- Every "Mark as serviced" click (audit trail)
CREATE TABLE IF NOT EXISTS service_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id        INTEGER NOT NULL,
    serviced_on         TEXT NOT NULL,
    serviced_by         TEXT NOT NULL,
    previous_due_date   TEXT NOT NULL,
    new_due_date        TEXT NOT NULL,
    recorded_at         TEXT NOT NULL,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
);

-- Every Approve / Decline decision on an e-mail draft. draft_id is UNIQUE,
-- so the same draft can never be decided (or sent) twice.
CREATE TABLE IF NOT EXISTS approvals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id     TEXT NOT NULL UNIQUE,
    decision     TEXT NOT NULL CHECK (decision IN ('approved', 'declined')),
    decided_by   TEXT NOT NULL,
    decided_at   TEXT NOT NULL,
    subject      TEXT NOT NULL,
    body         TEXT NOT NULL,
    recipients   TEXT,              -- who it was sent to (approved only)
    sent         INTEGER NOT NULL DEFAULT 0,
    send_error   TEXT
);
