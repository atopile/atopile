CREATE TABLE IF NOT EXISTS test_runs (
    test_run_id TEXT PRIMARY KEY,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS test_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id       TEXT,
    timestamp         TEXT,
    test_name         TEXT,
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

CREATE INDEX IF NOT EXISTS idx_test_logs_test_run_id ON test_logs(test_run_id);
