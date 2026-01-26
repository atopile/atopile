CREATE TABLE IF NOT EXISTS builds (
    build_id     TEXT PRIMARY KEY,
    project_path TEXT,
    target       TEXT,
    timestamp    TEXT,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id          TEXT,
    timestamp         TEXT,
    stage             TEXT,
    level             TEXT,
    message           TEXT,
    logger_name       TEXT,
    audience          TEXT DEFAULT 'developer',
    source_file       TEXT,
    source_line       INTEGER,
    ato_traceback     TEXT,
    python_traceback  TEXT,
    objects           TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_build_id ON logs(build_id);
