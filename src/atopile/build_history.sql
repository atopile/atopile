CREATE TABLE IF NOT EXISTS build_history (
    build_id     TEXT PRIMARY KEY,
    project_root TEXT,
    target       TEXT,
    entry        TEXT,
    status       TEXT,
    return_code  INTEGER,
    error        TEXT,
    started_at   REAL,
    duration     REAL,
    stages       TEXT,
    warnings     INTEGER,
    errors       INTEGER,
    completed_at REAL
);
