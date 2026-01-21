"""
Problem parsing helpers.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sqlite3
from pathlib import Path

from atopile.logging import get_central_log_db
from atopile.server.schemas.problem import Problem
from atopile.server.state import server_state

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


def _load_problems_from_db(limit: int = PROBLEM_QUERY_LIMIT) -> list[Problem]:
    db_path = get_central_log_db()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT logs.id, logs.timestamp, logs.stage, logs.level,
               logs.message, logs.ato_traceback, logs.python_traceback,
               builds.target, builds.project_path
        FROM logs
        JOIN builds ON logs.build_id = builds.build_id
        WHERE logs.level IN ('WARNING', 'ERROR', 'ALERT')
        ORDER BY logs.id DESC
        LIMIT ?
    """

    rows = conn.execute(query, (limit,)).fetchall()
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


def sync_problems_to_state() -> None:
    """
    Sync problems to server_state for WebSocket broadcast.

    Called after build completes to update problems from log files.
    Uses asyncio.run_coroutine_threadsafe to schedule on main event loop.
    """
    loop = server_state._event_loop
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(sync_problems_to_state_async(), loop)
    else:
        log.warning("Cannot sync problems to state: event loop not available")


async def sync_problems_to_state_async() -> None:
    """
    Async function to refresh problems from build logs.

    Reads problems from the central SQLite log DB and updates server_state.
    """
    from atopile.server.state import Problem as StateProblem

    try:
        all_problems: list[StateProblem] = []

        for problem in _load_problems_from_db():
            all_problems.append(
                StateProblem(
                    id=problem.id,
                    level=problem.level,
                    message=problem.message,
                    file=problem.file,
                    line=problem.line,
                    column=problem.column,
                    stage=problem.stage,
                    logger=problem.logger,
                    build_name=problem.build_name,
                    project_name=problem.project_name,
                    timestamp=problem.timestamp,
                    ato_traceback=problem.ato_traceback,
                    exc_info=problem.exc_info,
                )
            )

        await server_state.set_problems(all_problems)
        log.info(f"Refreshed problems after build: {len(all_problems)} problems found")
    except Exception as exc:
        log.error(f"Failed to refresh problems: {exc}")


__all__ = [
    "_load_problems_from_db",
    "sync_problems_to_state",
    "sync_problems_to_state_async",
]
