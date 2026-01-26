import json
import sqlite3
from pathlib import Path

from atopile.dataclasses import BuildStatus, HistoricalBuild
from faebryk.libs.paths import get_log_dir

BUILD_HISTORY_DB = get_log_dir() / Path("build_history.db")
TEST_LOGS_DB = get_log_dir() / Path("test_logs.db")
BUILD_LOGS_DB = get_log_dir() / Path("build_logs.db")



# build_history.db -> build_history schema helper
class BuildHistory:
    @staticmethod
    def init_db() -> None:
        BUILD_HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(BUILD_HISTORY_DB) as conn:
            conn.execute("""
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
                )
            """)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> HistoricalBuild:
        return HistoricalBuild(
            build_id=row["build_id"],
            project_root=row["project_root"],
            target=row["target"],
            entry=row["entry"],
            status=BuildStatus(row["status"]),
            return_code=row["return_code"],
            error=row["error"],
            started_at=row["started_at"],
            duration=row["duration"],
            stages=json.loads(row["stages"]) if row["stages"] else [],
            warnings=row["warnings"],
            errors=row["errors"],
            completed_at=row["completed_at"],
        )

    @staticmethod
    def set(build: HistoricalBuild) -> None:
        with sqlite3.connect(BUILD_HISTORY_DB) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO build_history
                    (build_id, project_root, target, entry, status,
                     return_code, error, started_at, duration,
                     stages, warnings, errors, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    build.build_id,
                    build.project_root,
                    build.target,
                    build.entry,
                    build.status.value,
                    build.return_code,
                    build.error,
                    build.started_at,
                    build.duration,
                    json.dumps(build.stages),
                    build.warnings,
                    build.errors,
                    build.completed_at,
                ),
            )

    @staticmethod
    def get(build_id: str) -> HistoricalBuild | None:
        with sqlite3.connect(BUILD_HISTORY_DB) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM build_history WHERE build_id = ?",
                (build_id,),
            ).fetchone()
        if row is None:
            return None
        return BuildHistory._from_row(row)

    @staticmethod
    def get_all(limit: int = 50) -> list[HistoricalBuild]:
        with sqlite3.connect(BUILD_HISTORY_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM build_history ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [BuildHistory._from_row(r) for r in rows]


# build_logs.db -> logs schema helper
class Logs:
    @staticmethod
    def init_db() -> None:
        BUILD_LOGS_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(BUILD_LOGS_DB) as conn:
            conn.execute("""
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
                )
            """)



# test_logs.db -> test_runs schema helper
class TestRuns:
    pass


# test_logs.db -> test_logs schema helper
class TestLogs:
    pass


class Tests:
    def test_paths(self) -> None:
        print(BUILD_HISTORY_DB)
        print(TEST_LOGS_DB)
        print(BUILD_LOGS_DB)

    def test_build_history(self) -> None:
        BuildHistory.init_db()
        BuildHistory.set(HistoricalBuild(
            build_id="123",
            project_root="project_root",
            target="target",
            entry="entry",
            status=BuildStatus.SUCCESS,
        ))


