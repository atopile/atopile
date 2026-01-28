import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from atopile.dataclasses import Build, BuildStatus, LogRow, TestLogRow
from atopile.logging import get_logger
from faebryk.libs.paths import get_log_dir

BUILD_HISTORY_DB = get_log_dir() / Path("build_history.db")
TEST_LOGS_DB = get_log_dir() / Path("test_logs.db")
BUILD_LOGS_DB = get_log_dir() / Path("build_logs.db")

logger = get_logger(__name__)

# build_history.db -> build_history schema helper
class BuildHistory:
    @staticmethod
    def init_db() -> None:
        BUILD_HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(BUILD_HISTORY_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS build_history (
                    build_id         TEXT PRIMARY KEY,
                    name             TEXT,
                    display_name     TEXT,
                    project_name     TEXT,
                    project_root     TEXT,
                    target           TEXT,
                    entry            TEXT,
                    status           TEXT,
                    return_code      INTEGER,
                    error            TEXT,
                    started_at       REAL,
                    elapsed_seconds  REAL,
                    stages           TEXT,
                    warnings         INTEGER,
                    errors           INTEGER,
                    timestamp        TEXT,
                    standalone       INTEGER,
                    frozen           INTEGER
                )
            """)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Build:
        return Build(
            build_id=row["build_id"],
            name=row["name"] or "default",
            display_name=row["display_name"] or "default",
            project_name=row["project_name"],
            project_root=row["project_root"],
            target=row["target"],
            entry=row["entry"],
            status=BuildStatus(row["status"]),
            return_code=row["return_code"],
            error=row["error"],
            started_at=row["started_at"],
            elapsed_seconds=row["elapsed_seconds"] or 0.0,
            stages=json.loads(row["stages"]) if row["stages"] else [],
            warnings=row["warnings"],
            errors=row["errors"],
            timestamp=row["timestamp"],
            standalone=bool(row["standalone"]),
            frozen=bool(row["frozen"]),
        )

    @staticmethod
    def set(build: Build) -> None:
        """Persist a Build record to the history database. Exits on error."""
        try:
            with sqlite3.connect(BUILD_HISTORY_DB) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO build_history
                        (build_id, name, display_name, project_name,
                         project_root, target, entry, status,
                         return_code, error, started_at,
                         elapsed_seconds, stages, warnings,
                         errors, timestamp, standalone, frozen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        build.build_id,
                        build.name,
                        build.display_name,
                        build.project_name,
                        build.project_root,
                        build.target,
                        build.entry,
                        build.status.value,
                        build.return_code,
                        build.error,
                        build.started_at,
                        build.elapsed_seconds,
                        json.dumps(build.stages),
                        build.warnings,
                        build.errors,
                        build.timestamp,
                        int(bool(build.standalone)),
                        int(bool(build.frozen)),
                    ),
                )
        except Exception:
            logger.exception(
                f"Failed to save build {build.build_id} to history. Try running 'ato dev clear_logs'."
            )
            os._exit(1)

    @staticmethod
    def get(build_id: str) -> Build | None:
        """Get a build by ID. Returns None if missing, exits on error."""
        try:
            with sqlite3.connect(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM build_history WHERE build_id = ?",
                    (build_id,),
                ).fetchone()
            if row is None:
                return None
            return BuildHistory._from_row(row)
        except Exception:
            logger.exception(
                f"Failed to get build {build_id} from history. Try running 'ato dev clear_logs'."
            )
            os._exit(1)

    @staticmethod
    def get_all(limit: int = 50) -> list[Build]:
        """Get recent builds. Exits on error."""
        try:
            with sqlite3.connect(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM build_history ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [BuildHistory._from_row(r) for r in rows]
        except Exception:
            logger.exception(
                "Failed to load build history. Try running 'ato dev clear_logs'."
            )
            os._exit(1)


# build_logs.db -> logs table helper
class Logs:
    @staticmethod
    def init_db() -> None:
        BUILD_LOGS_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(BUILD_LOGS_DB) as conn:
            conn.executescript("""
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
            """)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> dict[str, Any]:
        obj = None
        if row["objects"]:
            try:
                obj = json.loads(row["objects"])
            except json.JSONDecodeError:
                pass
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "stage": row["stage"],
            "level": row["level"],
            "audience": row["audience"],
            "logger_name": row["logger_name"],
            "message": row["message"],
            "source_file": row["source_file"],
            "source_line": row["source_line"],
            "ato_traceback": row["ato_traceback"],
            "python_traceback": row["python_traceback"],
            "objects": obj,
        }

    @staticmethod
    def append_chunk(entries: list[LogRow]) -> None:
        if not entries:
            return
        with sqlite3.connect(BUILD_LOGS_DB, timeout=30.0) as conn:
            conn.executemany(
                """
                INSERT INTO logs
                    (build_id, timestamp, stage, level, message,
                     logger_name, audience, source_file, source_line,
                     ato_traceback, python_traceback, objects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.build_id,
                        e.timestamp,
                        e.stage,
                        e.level,
                        e.message,
                        e.logger_name,
                        e.audience,
                        e.source_file,
                        e.source_line,
                        e.ato_traceback,
                        e.python_traceback,
                        e.objects,
                    )
                    for e in entries
                ],
            )

    @staticmethod
    def fetch_chunk(
        build_id: str,
        *,
        stage: str | None = None,
        levels: list[str] | None = None,
        audience: str | None = None,
        after_id: int = 0,
        count: int = 1000,
        order: str = "ASC",
    ) -> tuple[list[dict[str, Any]], int]:
        if not BUILD_LOGS_DB.exists():
            return [], after_id

        where = ["build_id = ?"]
        params: list[Any] = [build_id]
        if after_id:
            where.append("id > ?")
            params.append(after_id)
        if stage:
            where.append("stage = ?")
            params.append(stage)
        if levels:
            where.append(f"level IN ({','.join('?' * len(levels))})")
            params.extend(levels)
        if audience:
            where.append("audience = ?")
            params.append(audience)
        params.append(min(count, 5000))
        order_dir = "DESC" if order.upper() == "DESC" else "ASC"

        with sqlite3.connect(BUILD_LOGS_DB, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logs"
                " WHERE " + " AND ".join(where) +
                f" ORDER BY id {order_dir} LIMIT ?",
                params,
            ).fetchall()

        last_id = after_id
        results = []
        for row in rows:
            last_id = row["id"]
            results.append(Logs._from_row(row))
        return results, last_id


# test_logs.db -> test_logs table helper
class TestLogs:
    @staticmethod
    def init_db() -> None:
        TEST_LOGS_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(TEST_LOGS_DB) as conn:
            conn.executescript("""
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
                CREATE INDEX IF NOT EXISTS idx_test_logs_test_run_id
                    ON test_logs(test_run_id);
            """)

    @staticmethod
    def register_run(test_run_id: str) -> None:
        with sqlite3.connect(TEST_LOGS_DB, timeout=30.0) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO test_runs (test_run_id) VALUES (?)",
                (test_run_id,),
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> dict[str, Any]:
        obj = None
        if row["objects"]:
            try:
                obj = json.loads(row["objects"])
            except json.JSONDecodeError:
                pass
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "test_name": row["test_name"],
            "level": row["level"],
            "audience": row["audience"],
            "logger_name": row["logger_name"],
            "message": row["message"],
            "source_file": row["source_file"],
            "source_line": row["source_line"],
            "ato_traceback": row["ato_traceback"],
            "python_traceback": row["python_traceback"],
            "objects": obj,
        }

    @staticmethod
    def append_chunk(entries: list[TestLogRow]) -> None:
        if not entries:
            return
        with sqlite3.connect(TEST_LOGS_DB, timeout=30.0) as conn:
            conn.executemany(
                """
                INSERT INTO test_logs
                    (test_run_id, timestamp, test_name, level, message,
                     logger_name, audience, source_file, source_line,
                     ato_traceback, python_traceback, objects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.test_run_id,
                        e.timestamp,
                        e.test_name,
                        e.level,
                        e.message,
                        e.logger_name,
                        e.audience,
                        e.source_file,
                        e.source_line,
                        e.ato_traceback,
                        e.python_traceback,
                        e.objects,
                    )
                    for e in entries
                ],
            )

    @staticmethod
    def fetch_chunk(
        test_run_id: str,
        *,
        test_name: str | None = None,
        levels: list[str] | None = None,
        audience: str | None = None,
        after_id: int = 0,
        count: int = 1000,
        order: str = "ASC",
    ) -> tuple[list[dict[str, Any]], int]:
        if not TEST_LOGS_DB.exists():
            return [], after_id

        where = ["test_run_id = ?"]
        params: list[Any] = [test_run_id]
        if after_id:
            where.append("id > ?")
            params.append(after_id)
        if test_name:
            where.append("test_name LIKE ?")
            params.append(f"%{test_name}%")
        if levels:
            where.append(f"level IN ({','.join('?' * len(levels))})")
            params.extend(levels)
        if audience:
            where.append("audience = ?")
            params.append(audience)
        params.append(min(count, 5000))
        order_dir = "DESC" if order.upper() == "DESC" else "ASC"

        with sqlite3.connect(TEST_LOGS_DB, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM test_logs"
                " WHERE " + " AND ".join(where) +
                f" ORDER BY id {order_dir} LIMIT ?",
                params,
            ).fetchall()

        last_id = after_id
        results = []
        for row in rows:
            last_id = row["id"]
            results.append(TestLogs._from_row(row))
        return results, last_id


class Tests:
    def test_paths(self) -> None:
        print(BUILD_HISTORY_DB)
        print(TEST_LOGS_DB)
        print(BUILD_LOGS_DB)

    def test_build_history(self) -> None:
        BuildHistory.init_db()
        BuildHistory.set(Build(
            name="target",
            display_name="project_root:target",
            build_id="123",
            project_root="project_root",
            target="target",
            entry="entry",
            status=BuildStatus.SUCCESS,
        ))

    def test_logs(self) -> None:
        Logs.init_db()
        Logs.append_chunk([LogRow(
            build_id="123",
            timestamp="2025-01-01T00:00:00",
            stage="compile",
            level="INFO",
            message="hello",
            logger_name="test",
        )])
        rows, last_id = Logs.fetch_chunk("123")
        assert len(rows) == 1
        assert rows[0]["message"] == "hello"
        assert last_id > 0

    def test_test_logs(self) -> None:
        TestLogs.init_db()
        TestLogs.register_run("run-1")
        TestLogs.append_chunk([TestLogRow(
            test_run_id="run-1",
            timestamp="2025-01-01T00:00:00",
            test_name="test_foo",
            level="INFO",
            message="passed",
            logger_name="test",
        )])
        rows, last_id = TestLogs.fetch_chunk("run-1")
        assert len(rows) == 1
        assert rows[0]["message"] == "passed"
        assert last_id > 0
