"""
Problem parsing helpers.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sqlite3
from pathlib import Path

from atopile.dataclasses import EventType, Problem
from atopile.logging import BuildLogger
from atopile.model.sqlite import BuildHistory
from atopile.server.events import event_bus

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
        SELECT logs.id, logs.build_id, logs.timestamp, logs.stage, logs.level,
               logs.message, logs.ato_traceback, logs.python_traceback
        FROM logs
        WHERE logs.level IN ('WARNING', 'ERROR', 'ALERT')
        {audience_filter}
        ORDER BY logs.id DESC
        LIMIT ?
    """

    rows = conn.execute(query, params).fetchall()
    conn.close()

    # Look up build metadata from build history
    build_ids = {row["build_id"] for row in rows if row["build_id"]}
    build_info = {}
    for bid in build_ids:
        info = BuildHistory.get(bid)
        if info:
            build_info[bid] = info

    problems: list[Problem] = []
    for row in rows:
        info = build_info.get(row["build_id"])
        project_path = info.project_root if info else ""
        project_name = Path(project_path).name if project_path else None
        target = info.target if info else ""
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
    Uses event_bus.emit_sync for thread-safe event emission.

    Args:
        developer_mode: If True, show all audiences. If False, only show 'user' audience.
            If None, uses the current developer_mode setting from server_state.
    """
    payload = {"developer_mode": developer_mode} if developer_mode is not None else {}
    event_bus.emit_sync(EventType.PROBLEMS_CHANGED, payload)


__all__ = [
    "_load_problems_from_db",
    "sync_problems_to_state",
]
