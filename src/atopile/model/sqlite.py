from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atopile.agent.message_log import TrackedChecklistItem, TrackedMessage

from atopile.dataclasses import (
    AgentEventRow,
    Build,
    BuildStatus,
    LogRow,
    ResolvedBuildTarget,
    TestLogRow,
)
from atopile.logging import get_logger
from faebryk.libs.paths import get_log_dir

BUILD_HISTORY_DB = get_log_dir() / Path("build_history.db")
TEST_LOGS_DB = get_log_dir() / Path("test_logs.db")
BUILD_LOGS_DB = get_log_dir() / Path("build_logs.db")
AGENT_LOGS_DB = get_log_dir() / Path("agent_logs.db")

logger = get_logger(__name__)

# Thread-local storage for database connections
# Each thread gets its own connection to avoid race conditions
_thread_local = threading.local()
_init_lock = threading.Lock()


def _ensure_db_dir(db_path: Path) -> None:
    """Ensure database directory exists (called once per database)."""
    with _init_lock:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def close_thread_connections(db_paths: set[Path] | None = None) -> None:
    connections = getattr(_thread_local, "connections", None)
    if not connections:
        return

    targets = db_paths or set(connections)
    for db_path in list(targets):
        conn = connections.pop(db_path, None)
        if conn is None:
            continue
        conn.close()


@contextmanager
def _get_connection(db_path: Path, timeout: float = 30.0):
    """
    Get a thread-local database connection, creating one if needed.
    Each thread gets its own connection to avoid race conditions.
    """
    # Get or create thread-local connection dict
    if not hasattr(_thread_local, "connections"):
        _thread_local.connections = {}

    connections = _thread_local.connections

    if db_path not in connections:
        _ensure_db_dir(db_path)
        conn = sqlite3.connect(db_path, timeout=timeout)
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        connections[db_path] = conn

    conn = connections[db_path]
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# build_history.db -> build_history schema helper
class BuildHistory:
    @staticmethod
    def init_db() -> None:
        with _get_connection(BUILD_HISTORY_DB) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS build_history (
                    build_id         TEXT PRIMARY KEY,
                    name             TEXT,
                    project_name     TEXT,
                    project_root     TEXT,
                    target           TEXT,
                    status           TEXT,
                    return_code      INTEGER,
                    error            TEXT,
                    started_at       REAL,
                    elapsed_seconds  REAL,
                    stages           TEXT,
                    total_stages     INTEGER,
                    warnings         INTEGER,
                    errors           INTEGER,
                    standalone       INTEGER,
                    frozen           INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_build_history_project_name
                    ON build_history(project_root, name, started_at DESC);
            """)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Build:
        build = Build(
            build_id=row["build_id"],
            project_name=row["project_name"],
            project_root=row["project_root"],
            target=(
                ResolvedBuildTarget.model_validate_json(row["target"])
                if row["target"]
                else None
            ),
            status=BuildStatus(row["status"]),
            return_code=row["return_code"],
            error=row["error"],
            started_at=row["started_at"],
            elapsed_seconds=row["elapsed_seconds"] or 0.0,
            stages=json.loads(row["stages"]) if row["stages"] else [],
            total_stages=row["total_stages"],
            warnings=row["warnings"],
            errors=row["errors"],
            standalone=bool(row["standalone"]),
            frozen=bool(row["frozen"]),
        )
        if row["name"]:
            build.name = row["name"]
        return build

    @staticmethod
    def set(build: Build) -> None:
        """
        Persist a Build record to the history database.

        Merges with existing record - None values preserve existing data.
        This allows partial updates without losing previously set fields.
        """
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                # Get existing record to merge with
                existing_row = conn.execute(
                    "SELECT * FROM build_history WHERE build_id = ?",
                    (build.build_id,),
                ).fetchone()
                existing = (
                    BuildHistory._from_row(existing_row) if existing_row else None
                )

                # Helper to pick new value or fall back to existing
                def pick(new_val, existing_val):
                    return new_val if new_val is not None else existing_val

                conn.execute(
                    """
                    INSERT OR REPLACE INTO build_history
                        (build_id, name, project_name,
                         project_root, target, status,
                         return_code, error, started_at,
                         elapsed_seconds, stages, total_stages, warnings,
                         errors, standalone, frozen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        build.build_id,
                        pick(build.name, existing.name if existing else None),
                        pick(
                            build.project_name,
                            existing.project_name if existing else None,
                        ),
                        pick(
                            build.project_root,
                            existing.project_root if existing else None,
                        ),
                        pick(
                            build.target.model_dump_json(by_alias=True)
                            if build.target
                            else None,
                            existing.target.model_dump_json(by_alias=True)
                            if existing and existing.target
                            else None,
                        ),
                        build.status.value,  # status is always set
                        pick(
                            build.return_code,
                            existing.return_code if existing else None,
                        ),
                        pick(build.error, existing.error if existing else None),
                        pick(
                            build.started_at, existing.started_at if existing else None
                        ),
                        build.elapsed_seconds
                        if build.elapsed_seconds
                        else (existing.elapsed_seconds if existing else 0.0),
                        json.dumps(
                            [
                                stage.model_dump(mode="json", by_alias=True)
                                for stage in build.stages
                            ]
                        )
                        if build.stages
                        else (json.dumps(existing.stages) if existing else "[]"),
                        pick(
                            build.total_stages,
                            existing.total_stages if existing else None,
                        ),
                        build.warnings
                        if build.warnings
                        else (existing.warnings if existing else 0),
                        build.errors
                        if build.errors
                        else (existing.errors if existing else 0),
                        int(bool(build.standalone))
                        if build.standalone
                        else (int(bool(existing.standalone)) if existing else 0),
                        int(bool(build.frozen))
                        if build.frozen
                        else (int(bool(existing.frozen)) if existing else 0),
                    ),
                )
        except Exception:
            logger.exception(
                f"Failed to save build {build.build_id} to history. "
                "Try running 'ato dev clear_logs'."
            )
            os._exit(1)

    @staticmethod
    def get(build_id: str) -> Build | None:
        """Get a build by ID. Returns None if missing, exits on error."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
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
                f"Failed to get build {build_id} from history. "
                "Try running 'ato dev clear_logs'."
            )
            os._exit(1)

    @staticmethod
    def get_all(limit: int = 50) -> list[Build]:
        """Get recent builds. Raises on error so callers can handle gracefully."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM build_history ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [BuildHistory._from_row(r) for r in rows]
        except Exception as e:
            logger.exception(
                "Failed to load build history. Try running 'ato dev clear_logs'."
            )
            raise e

    @staticmethod
    def get_latest_finished_per_target(limit: int = 100) -> list[Build]:
        """Get the latest completed build per target root and target name."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM build_history
                    WHERE rowid IN (
                        SELECT rowid FROM (
                            SELECT rowid, ROW_NUMBER() OVER (
                                PARTITION BY
                                    json_extract(target, '$.root'),
                                    name,
                                    json_extract(target, '$.entry')
                                ORDER BY started_at DESC
                            ) AS rn
                            FROM build_history
                            WHERE status NOT IN ('queued', 'building')
                        ) WHERE rn = 1
                    )
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [BuildHistory._from_row(r) for r in rows]
        except Exception as e:
            logger.exception(
                "Failed to get latest finished builds per target. "
                "Try running 'ato dev clear_logs'."
            )
            raise e

    @staticmethod
    def get_queued(limit: int = 100) -> list[Build]:
        """Get queued builds in FIFO order."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM build_history
                    WHERE status = 'queued'
                    ORDER BY started_at ASC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [BuildHistory._from_row(r) for r in rows]
        except Exception as e:
            logger.exception(
                "Failed to get queued builds. Try running 'ato dev clear_logs'."
            )
            raise e

    @staticmethod
    def get_building(limit: int = 100) -> list[Build]:
        """Get running builds."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM build_history
                    WHERE status = 'building'
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [BuildHistory._from_row(r) for r in rows]
        except Exception as e:
            logger.exception(
                "Failed to get running builds. Try running 'ato dev clear_logs'."
            )
            raise e

    @staticmethod
    def get_finished(limit: int = 100) -> list[Build]:
        """Get builds with status other than 'queued' or 'building'."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM build_history
                    WHERE status NOT IN ('queued', 'building')
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [BuildHistory._from_row(r) for r in rows]
        except Exception as e:
            logger.exception(
                "Failed to get finished builds. Try running 'ato dev clear_logs'."
            )
            raise e

    @staticmethod
    def finalize_incomplete(
        *,
        status: BuildStatus = BuildStatus.CANCELLED,
        error: str = "Build queue restarted",
    ) -> int:
        """Finalize any queued or running builds from an earlier process."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                cursor = conn.execute(
                    """
                    UPDATE build_history
                    SET status = ?,
                    error = COALESCE(error, ?),
                    return_code = COALESCE(return_code, 1)
                    WHERE status IN ('queued', 'building')
                    """,
                    (status.value, error),
                )
                return int(cursor.rowcount or 0)
        except Exception as e:
            logger.exception(
                "Failed to finalize incomplete builds. "
                "Try running 'ato dev clear_logs'."
            )
            raise e

    @staticmethod
    def get_latest_finished_for_target(
        target: ResolvedBuildTarget,
    ) -> Build | None:
        """Get the most recent completed build for a specific project/target."""
        try:
            with _get_connection(BUILD_HISTORY_DB) as conn:
                conn.row_factory = sqlite3.Row
                params: list[str] = [
                    target.name,
                    target.root,
                ]
                query = (
                    "SELECT * FROM build_history"
                    " WHERE name = ?"
                    " AND json_extract(target, '$.root') = ?"
                    " AND status NOT IN ('queued', 'building')"
                )
                query += " ORDER BY started_at DESC LIMIT 1"
                row = conn.execute(query, params).fetchone()
                if row is None:
                    return None
                return BuildHistory._from_row(row)
        except Exception as e:
            logger.exception(
                "Failed to get latest finished build for target. "
                "Try running 'ato dev clear_logs'."
            )
            raise e


# build_logs.db -> logs table helper
class Logs:
    @staticmethod
    def init_db() -> None:
        with _get_connection(BUILD_LOGS_DB) as conn:
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
        with _get_connection(BUILD_LOGS_DB) as conn:
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

        with _get_connection(BUILD_LOGS_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logs"
                " WHERE " + " AND ".join(where) + f" ORDER BY id {order_dir} LIMIT ?",
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
        with _get_connection(TEST_LOGS_DB) as conn:
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
        with _get_connection(TEST_LOGS_DB) as conn:
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
        with _get_connection(TEST_LOGS_DB) as conn:
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

        with _get_connection(TEST_LOGS_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM test_logs"
                " WHERE " + " AND ".join(where) + f" ORDER BY id {order_dir} LIMIT ?",
                params,
            ).fetchall()
            last_id = after_id
            results = []
            for row in rows:
                last_id = row["id"]
                results.append(TestLogs._from_row(row))
            return results, last_id


# agent_logs.db -> agent_events table helper
class AgentSessions:
    @staticmethod
    def init_db() -> None:
        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id                   TEXT PRIMARY KEY,
                    project_root                 TEXT NOT NULL,
                    history_json                 TEXT NOT NULL,
                    messages_json                TEXT NOT NULL DEFAULT '[]',
                    tool_memory_json             TEXT NOT NULL,
                    recent_selected_targets_json TEXT NOT NULL,
                    activity_label               TEXT NOT NULL DEFAULT 'Ready',
                    error                        TEXT,
                    run_started_at               REAL,
                    last_response_id             TEXT,
                    conversation_id              TEXT,
                    skill_state_json             TEXT NOT NULL,
                    created_at                   REAL NOT NULL,
                    updated_at                   REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_sessions_project_updated
                    ON agent_sessions(project_root, updated_at DESC);
            """)
            conn.row_factory = sqlite3.Row
            existing_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(agent_sessions)").fetchall()
            }
            required_columns = {
                "messages_json": "TEXT NOT NULL DEFAULT '[]'",
                "activity_label": "TEXT NOT NULL DEFAULT 'Ready'",
                "error": "TEXT",
                "run_started_at": "REAL",
            }
            for column, column_type in required_columns.items():
                if column in existing_columns:
                    continue
                conn.execute(
                    f"ALTER TABLE agent_sessions ADD COLUMN {column} {column_type}"
                )

    @staticmethod
    def upsert_many(rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.executemany(
                """
                INSERT INTO agent_sessions
                    (session_id, project_root, history_json, messages_json,
                     tool_memory_json, recent_selected_targets_json,
                     activity_label, error, run_started_at, last_response_id,
                     conversation_id, skill_state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    project_root = excluded.project_root,
                    history_json = excluded.history_json,
                    messages_json = excluded.messages_json,
                    tool_memory_json = excluded.tool_memory_json,
                    recent_selected_targets_json =
                        excluded.recent_selected_targets_json,
                    activity_label = excluded.activity_label,
                    error = excluded.error,
                    run_started_at = excluded.run_started_at,
                    last_response_id = excluded.last_response_id,
                    conversation_id = excluded.conversation_id,
                    skill_state_json = excluded.skill_state_json,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        row["session_id"],
                        row["project_root"],
                        json.dumps(row.get("history", []), ensure_ascii=False),
                        json.dumps(row.get("messages", []), ensure_ascii=False),
                        json.dumps(row.get("tool_memory", {}), ensure_ascii=False),
                        json.dumps(
                            row.get("recent_selected_targets", []), ensure_ascii=False
                        ),
                        str(row.get("activity_label") or "Ready"),
                        row.get("error"),
                        (
                            float(row["run_started_at"])
                            if row.get("run_started_at") is not None
                            else None
                        ),
                        row.get("last_response_id"),
                        row.get("conversation_id"),
                        json.dumps(row.get("skill_state", {}), ensure_ascii=False),
                        float(row.get("created_at", 0.0) or 0.0),
                        float(row.get("updated_at", 0.0) or 0.0),
                    )
                    for row in rows
                ],
            )

    @staticmethod
    def load_all() -> list[dict[str, Any]]:
        if not AGENT_LOGS_DB.exists():
            return []
        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM agent_sessions ORDER BY updated_at DESC"
            ).fetchall()

        def _decode(raw: str | None, fallback: Any) -> Any:
            if not raw:
                return fallback
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return fallback

        return [
            {
                "session_id": row["session_id"],
                "project_root": row["project_root"],
                "history": _decode(row["history_json"], []),
                "messages": _decode(row["messages_json"], []),
                "tool_memory": _decode(row["tool_memory_json"], {}),
                "recent_selected_targets": _decode(
                    row["recent_selected_targets_json"], []
                ),
                "activity_label": row["activity_label"],
                "error": row["error"],
                "run_started_at": row["run_started_at"],
                "last_response_id": row["last_response_id"],
                "conversation_id": row["conversation_id"],
                "skill_state": _decode(row["skill_state_json"], {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


class AgentLogs:
    @staticmethod
    def init_db() -> None:
        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS agent_events (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id      TEXT NOT NULL,
                    run_id          TEXT,
                    timestamp       TEXT NOT NULL,
                    event           TEXT NOT NULL,
                    level           TEXT NOT NULL DEFAULT 'INFO',
                    phase           TEXT,
                    tool_name       TEXT,
                    project_root    TEXT,
                    summary         TEXT,
                    step_kind       TEXT,
                    loop            INTEGER,
                    tool_index      INTEGER,
                    tool_count      INTEGER,
                    call_id         TEXT,
                    item_id         TEXT,
                    model           TEXT,
                    response_id     TEXT,
                    previous_response_id TEXT,
                    input_tokens    INTEGER,
                    output_tokens   INTEGER,
                    total_tokens    INTEGER,
                    reasoning_tokens INTEGER,
                    cached_input_tokens INTEGER,
                    duration_ms     INTEGER,
                    payload         TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_agent_events_session
                    ON agent_events(session_id, id);
                CREATE INDEX IF NOT EXISTS idx_agent_events_run
                    ON agent_events(run_id, id);
            """)
            conn.row_factory = sqlite3.Row
            existing_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(agent_events)").fetchall()
            }
            required_columns = {
                "step_kind": "TEXT",
                "loop": "INTEGER",
                "tool_index": "INTEGER",
                "tool_count": "INTEGER",
                "call_id": "TEXT",
                "item_id": "TEXT",
                "model": "TEXT",
                "response_id": "TEXT",
                "previous_response_id": "TEXT",
                "input_tokens": "INTEGER",
                "output_tokens": "INTEGER",
                "total_tokens": "INTEGER",
                "reasoning_tokens": "INTEGER",
                "cached_input_tokens": "INTEGER",
                "duration_ms": "INTEGER",
            }
            for column, column_type in required_columns.items():
                if column in existing_columns:
                    continue
                conn.execute(
                    f"ALTER TABLE agent_events ADD COLUMN {column} {column_type}"
                )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = None
        if row["payload"]:
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                payload = row["payload"]
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "run_id": row["run_id"],
            "timestamp": row["timestamp"],
            "event": row["event"],
            "level": row["level"],
            "phase": row["phase"],
            "tool_name": row["tool_name"],
            "project_root": row["project_root"],
            "summary": row["summary"],
            "step_kind": row["step_kind"] if "step_kind" in row.keys() else None,
            "loop": row["loop"] if "loop" in row.keys() else None,
            "tool_index": row["tool_index"] if "tool_index" in row.keys() else None,
            "tool_count": row["tool_count"] if "tool_count" in row.keys() else None,
            "call_id": row["call_id"] if "call_id" in row.keys() else None,
            "item_id": row["item_id"] if "item_id" in row.keys() else None,
            "model": row["model"] if "model" in row.keys() else None,
            "response_id": row["response_id"] if "response_id" in row.keys() else None,
            "previous_response_id": (
                row["previous_response_id"]
                if "previous_response_id" in row.keys()
                else None
            ),
            "input_tokens": row["input_tokens"]
            if "input_tokens" in row.keys()
            else None,
            "output_tokens": (
                row["output_tokens"] if "output_tokens" in row.keys() else None
            ),
            "total_tokens": row["total_tokens"]
            if "total_tokens" in row.keys()
            else None,
            "reasoning_tokens": (
                row["reasoning_tokens"] if "reasoning_tokens" in row.keys() else None
            ),
            "cached_input_tokens": (
                row["cached_input_tokens"]
                if "cached_input_tokens" in row.keys()
                else None
            ),
            "duration_ms": row["duration_ms"] if "duration_ms" in row.keys() else None,
            "payload": payload,
        }

    @staticmethod
    def append_chunk(entries: list[AgentEventRow]) -> None:
        if not entries:
            return
        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.executemany(
                """
                INSERT INTO agent_events
                    (session_id, run_id, timestamp, event, level,
                     phase, tool_name, project_root, summary,
                     step_kind, loop, tool_index, tool_count, call_id, item_id,
                     model, response_id, previous_response_id,
                     input_tokens, output_tokens, total_tokens,
                     reasoning_tokens, cached_input_tokens,
                     duration_ms, payload)
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                [
                    (
                        e.session_id,
                        e.run_id,
                        e.timestamp,
                        e.event,
                        e.level,
                        e.phase,
                        e.tool_name,
                        e.project_root,
                        e.summary,
                        e.step_kind,
                        e.loop,
                        e.tool_index,
                        e.tool_count,
                        e.call_id,
                        e.item_id,
                        e.model,
                        e.response_id,
                        e.previous_response_id,
                        e.input_tokens,
                        e.output_tokens,
                        e.total_tokens,
                        e.reasoning_tokens,
                        e.cached_input_tokens,
                        e.duration_ms,
                        e.payload,
                    )
                    for e in entries
                ],
            )

    @staticmethod
    def fetch_chunk(
        session_id: str,
        *,
        run_id: str | None = None,
        events: list[str] | None = None,
        levels: list[str] | None = None,
        after_id: int = 0,
        count: int = 1000,
        order: str = "ASC",
    ) -> tuple[list[dict[str, Any]], int]:
        if not AGENT_LOGS_DB.exists():
            return [], after_id

        where = ["session_id = ?"]
        params: list[Any] = [session_id]
        if after_id:
            where.append("id > ?")
            params.append(after_id)
        if run_id:
            where.append("run_id = ?")
            params.append(run_id)
        if events:
            where.append(f"event IN ({','.join('?' * len(events))})")
            params.extend(events)
        if levels:
            where.append(f"level IN ({','.join('?' * len(levels))})")
            params.extend(levels)
        params.append(min(count, 5000))
        order_dir = "DESC" if order.upper() == "DESC" else "ASC"

        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM agent_events"
                " WHERE " + " AND ".join(where) + f" ORDER BY id {order_dir} LIMIT ?",
                params,
            ).fetchall()
            last_id = after_id
            results = []
            for row in rows:
                last_id = row["id"]
                results.append(AgentLogs._from_row(row))
            return results, last_id


# agent_logs.db -> tracked_messages + tracked_checklist_items
class MessageLog:
    @staticmethod
    def init_db() -> None:
        with _get_connection(AGENT_LOGS_DB) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tracked_messages (
                    message_id    TEXT PRIMARY KEY,
                    session_id    TEXT NOT NULL,
                    project_root  TEXT NOT NULL,
                    role          TEXT NOT NULL,
                    content       TEXT NOT NULL,
                    status        TEXT NOT NULL,
                    justification TEXT,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tracked_messages_session_status
                    ON tracked_messages(session_id, status);
                CREATE INDEX IF NOT EXISTS idx_tracked_messages_project_session
                    ON tracked_messages(project_root, session_id);
                CREATE INDEX IF NOT EXISTS idx_tracked_messages_status
                    ON tracked_messages(status);

                CREATE TABLE IF NOT EXISTS tracked_checklist_items (
                    item_id        TEXT NOT NULL,
                    session_id     TEXT NOT NULL,
                    message_id     TEXT,
                    description    TEXT NOT NULL,
                    criteria       TEXT NOT NULL,
                    status         TEXT NOT NULL,
                    requirement_id TEXT,
                    source         TEXT,
                    justification  TEXT,
                    created_at     TEXT NOT NULL,
                    updated_at     TEXT NOT NULL,
                    PRIMARY KEY (session_id, item_id)
                );
                CREATE INDEX IF NOT EXISTS idx_tracked_checklist_items_message
                    ON tracked_checklist_items(message_id);
            """)

    @staticmethod
    def register_message(msg: TrackedMessage) -> None:
        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.execute(
                    """
                    INSERT INTO tracked_messages
                        (message_id, session_id, project_root, role,
                         content, status, justification, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg.message_id,
                        msg.session_id,
                        msg.project_root,
                        msg.role,
                        msg.content,
                        msg.status,
                        msg.justification,
                        msg.created_at,
                        msg.updated_at,
                    ),
                )
        except Exception:
            logger.exception("Failed to register tracked message %s", msg.message_id)

    @staticmethod
    def update_message_status(
        message_id: str,
        status: str,
        justification: str | None = None,
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.execute(
                    """
                    UPDATE tracked_messages
                    SET status = ?, justification = COALESCE(?, justification),
                        updated_at = ?
                    WHERE message_id = ?
                    """,
                    (status, justification, now, message_id),
                )
        except Exception:
            logger.exception(
                "Failed to update tracked message %s to %s", message_id, status
            )

    @staticmethod
    def get_message(message_id: str) -> TrackedMessage | None:
        from atopile.agent.message_log import TrackedMessage

        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM tracked_messages WHERE message_id = ?",
                    (message_id,),
                ).fetchone()
                if row is None:
                    return None
                return TrackedMessage(
                    message_id=row["message_id"],
                    session_id=row["session_id"],
                    project_root=row["project_root"],
                    role=row["role"],
                    content=row["content"],
                    status=row["status"],
                    justification=row["justification"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        except Exception:
            logger.exception("Failed to get tracked message %s", message_id)
            return None

    @staticmethod
    def get_pending_messages(session_id: str) -> list[TrackedMessage]:
        from atopile.agent.message_log import MSG_PENDING, TrackedMessage

        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM tracked_messages"
                    " WHERE session_id = ? AND status = ?"
                    " ORDER BY created_at ASC",
                    (session_id, MSG_PENDING),
                ).fetchall()
                return [
                    TrackedMessage(
                        message_id=r["message_id"],
                        session_id=r["session_id"],
                        project_root=r["project_root"],
                        role=r["role"],
                        content=r["content"],
                        status=r["status"],
                        justification=r["justification"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                    for r in rows
                ]
        except Exception:
            logger.exception(
                "Failed to get pending messages for session %s", session_id
            )
            return []

    @staticmethod
    def save_checklist_item(item: TrackedChecklistItem) -> None:
        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tracked_checklist_items
                        (item_id, session_id, message_id, description,
                         criteria, status, requirement_id, source,
                         justification, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.item_id,
                        item.session_id,
                        item.message_id,
                        item.description,
                        item.criteria,
                        item.status,
                        item.requirement_id,
                        item.source,
                        item.justification,
                        item.created_at,
                        item.updated_at,
                    ),
                )
        except Exception:
            logger.exception(
                "Failed to save tracked checklist item %s/%s",
                item.session_id,
                item.item_id,
            )

    @staticmethod
    def update_checklist_item(
        session_id: str,
        item_id: str,
        status: str,
        justification: str | None = None,
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.execute(
                    """
                    UPDATE tracked_checklist_items
                    SET status = ?, justification = COALESCE(?, justification),
                        updated_at = ?
                    WHERE session_id = ? AND item_id = ?
                    """,
                    (status, justification, now, session_id, item_id),
                )
        except Exception:
            logger.exception(
                "Failed to update tracked checklist item %s/%s", session_id, item_id
            )

    @staticmethod
    def check_and_complete_messages(session_id: str) -> list[str]:
        """Auto-transition active messages when linked items are terminal."""
        from atopile.agent.message_log import (
            _TERMINAL_ITEM_STATUSES,
            MSG_ACTIVE,
            MSG_DONE,
        )

        completed_ids: list[str] = []
        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.row_factory = sqlite3.Row
                # Get all active messages for this session
                active_msgs = conn.execute(
                    "SELECT message_id FROM tracked_messages"
                    " WHERE session_id = ? AND status = ?",
                    (session_id, MSG_ACTIVE),
                ).fetchall()

                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()

                for msg_row in active_msgs:
                    mid = msg_row["message_id"]
                    # Get all linked checklist items
                    items = conn.execute(
                        "SELECT status FROM tracked_checklist_items"
                        " WHERE message_id = ?",
                        (mid,),
                    ).fetchall()
                    if not items:
                        continue
                    # Check if all items are terminal
                    if all(r["status"] in _TERMINAL_ITEM_STATUSES for r in items):
                        conn.execute(
                            """
                            UPDATE tracked_messages
                            SET status = ?, justification = ?, updated_at = ?
                            WHERE message_id = ?
                            """,
                            (
                                MSG_DONE,
                                "All linked checklist items completed",
                                now,
                                mid,
                            ),
                        )
                        completed_ids.append(mid)
        except Exception:
            logger.exception(
                "Failed to check/complete messages for session %s", session_id
            )
        return completed_ids

    @staticmethod
    def query(
        *,
        session_id: str | None = None,
        project_root: str | None = None,
        status: str | None = None,
        search: str | None = None,
        include_items: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Flexible query for tracked messages, optionally cross-thread."""
        results: dict[str, Any] = {"messages": [], "total": 0}
        try:
            with _get_connection(AGENT_LOGS_DB) as conn:
                conn.row_factory = sqlite3.Row

                where: list[str] = []
                params: list[Any] = []

                if session_id:
                    where.append("session_id = ?")
                    params.append(session_id)
                if project_root:
                    where.append("project_root = ?")
                    params.append(project_root)
                if status:
                    where.append("status = ?")
                    params.append(status)
                if search:
                    where.append("content LIKE ?")
                    params.append(f"%{search}%")

                where_clause = " WHERE " + " AND ".join(where) if where else ""
                params.append(min(limit, 200))

                rows = conn.execute(
                    f"SELECT * FROM tracked_messages{where_clause}"
                    " ORDER BY created_at DESC LIMIT ?",
                    params,
                ).fetchall()

                messages = []
                for r in rows:
                    msg_dict: dict[str, Any] = {
                        "message_id": r["message_id"],
                        "session_id": r["session_id"],
                        "project_root": r["project_root"],
                        "role": r["role"],
                        "content": r["content"][:500],
                        "status": r["status"],
                        "justification": r["justification"],
                        "created_at": r["created_at"],
                        "updated_at": r["updated_at"],
                    }
                    if include_items:
                        item_rows = conn.execute(
                            "SELECT * FROM tracked_checklist_items"
                            " WHERE message_id = ?",
                            (r["message_id"],),
                        ).fetchall()
                        msg_dict["items"] = [
                            {
                                "item_id": ir["item_id"],
                                "description": ir["description"],
                                "status": ir["status"],
                                "justification": ir["justification"],
                            }
                            for ir in item_rows
                        ]
                    messages.append(msg_dict)

                results["messages"] = messages
                results["total"] = len(messages)
        except Exception:
            logger.exception("Failed to query tracked messages")
        return results


class Tests:
    def test_paths(self) -> None:
        print(BUILD_HISTORY_DB)
        print(TEST_LOGS_DB)
        print(BUILD_LOGS_DB)

    def test_build_history(self) -> None:
        BuildHistory.init_db()
        BuildHistory.set(
            Build(
                name="target",
                build_id="123",
                project_root="project_root",
                target=ResolvedBuildTarget(
                    name="target",
                    entry="entry",
                    pcb_path="",
                    model_path="",
                    root="project_root",
                ),
                status=BuildStatus.SUCCESS,
            )
        )

    def test_logs(self) -> None:
        import uuid

        build_id = f"test-{uuid.uuid4()}"
        Logs.init_db()
        Logs.append_chunk(
            [
                LogRow(
                    build_id=build_id,
                    timestamp="2025-01-01T00:00:00",
                    stage="compile",
                    level="INFO",
                    message="hello",
                    logger_name="test",
                )
            ]
        )
        rows, last_id = Logs.fetch_chunk(build_id)
        assert len(rows) == 1
        assert rows[0]["message"] == "hello"
        assert last_id > 0

    def test_test_logs(self) -> None:
        import uuid

        test_run_id = f"test-run-{uuid.uuid4()}"
        TestLogs.init_db()
        TestLogs.register_run(test_run_id)
        TestLogs.append_chunk(
            [
                TestLogRow(
                    test_run_id=test_run_id,
                    timestamp="2025-01-01T00:00:00",
                    test_name="test_foo",
                    level="INFO",
                    message="passed",
                    logger_name="test",
                )
            ]
        )
        rows, last_id = TestLogs.fetch_chunk(test_run_id)
        assert len(rows) == 1
        assert rows[0]["message"] == "passed"
        assert last_id > 0
