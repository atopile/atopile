"""
Problem parsing helpers.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sqlite3
from pathlib import Path

from atopile.dataclasses import Problem
from atopile.logging import BuildLogger
from atopile.server.connections import server_state

log = logging.getLogger(__name__)

PROBLEM_QUERY_LIMIT = 500


def _parse_traceback_location(
    traceback: str | None,
) -> tuple[str | None, int | None, int | None]:
    import re

    if not traceback:
        return None, None, None

    match = re.search(r'File "([^"]+)", line (\d+)(?:, column (\d+))?', traceback)
    if not match:
        return None, None, None

    file_path = match.group(1)
    line_num = int(match.group(2))
    column = int(match.group(3)) if match.group(3) else None
    return file_path, line_num, column


def _load_problems_from_db(
    limit: int = PROBLEM_QUERY_LIMIT,
    developer_mode: bool = False,
) -> list[Problem]:
    """
    Load problems from the central log database.

    Args:
        limit: Maximum number of problems to load
        developer_mode: If True, show all audiences. If False (default), only show 'user' audience.
    """
    db_path = BuildLogger.get_log_db()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Filter by audience: only show 'user' messages unless developer mode is enabled
    if developer_mode:
        audience_filter = ""
        params: tuple = (limit,)
    else:
        audience_filter = "AND logs.audience = ?"
        params = ("user", limit)

    query = f"""
        SELECT logs.id, logs.timestamp, logs.stage, logs.level,
               logs.message, logs.ato_traceback, logs.python_traceback,
               builds.target, builds.project_path
        FROM logs
        JOIN builds ON logs.build_id = builds.build_id
        WHERE logs.level IN ('WARNING', 'ERROR', 'ALERT')
        {audience_filter}
        ORDER BY logs.id DESC
        LIMIT ?
    """

    rows = conn.execute(query, params).fetchall()
    conn.close()

    problems: list[Problem] = []
    for row in rows:
        project_path = row["project_path"] or ""
        project_name = Path(project_path).name if project_path else None
        target = row["target"] or ""
        build_name = f"{project_name}:{target}" if project_name and target else target

        file_path, line_num, column = _parse_traceback_location(row["ato_traceback"])

        problem_id = hashlib.md5(
            f"{row['id']}-{row['message'][:50]}".encode()
        ).hexdigest()[:12]

        problems.append(
            Problem(
                id=problem_id,
                level="warning" if row["level"] == "WARNING" else "error",
                message=row["message"],
                file=file_path,
                line=line_num,
                column=column,
                stage=row["stage"],
                logger=None,
                build_name=build_name,
                project_name=project_name,
                timestamp=row["timestamp"],
                ato_traceback=row["ato_traceback"],
                exc_info=row["python_traceback"],
            )
        )

    return problems


def sync_problems_to_state(developer_mode: bool | None = None) -> None:
    """
    Emit a problems-changed event for WebSocket clients.

    Called after build completes to update problems from log files.
    Uses asyncio.run_coroutine_threadsafe to schedule on main event loop.

    Args:
        developer_mode: If True, show all audiences. If False, only show 'user' audience.
            If None, uses the current developer_mode setting from server_state.
    """
    loop = server_state._event_loop
    if loop is not None and loop.is_running():
        payload = {"developer_mode": developer_mode} if developer_mode is not None else {}
        asyncio.run_coroutine_threadsafe(
            server_state.emit_event("problems_changed", payload), loop
        )
    else:
        log.warning("Cannot emit problems event: event loop not available")


__all__ = [
    "_load_problems_from_db",
    "sync_problems_to_state",
]
