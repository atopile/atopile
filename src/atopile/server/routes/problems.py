"""
Problem-related API routes.

Endpoints:
- GET /api/problems - Get problems (errors/warnings) from builds
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from ..schemas.problem import Problem, ProblemsResponse

log = logging.getLogger(__name__)

router = APIRouter(tags=["problems"])


def _get_log_db_path():
    """Get the log database path from server state."""
    from ..server import state
    logs_base = state.get("logs_base")
    if logs_base:
        return logs_base / "central.db"
    return None


@router.get("/api/problems", response_model=ProblemsResponse)
async def get_problems(
    project_root: Optional[str] = Query(None, description="Filter by project root"),
    build_name: Optional[str] = Query(None, description="Filter by build name"),
    level: Optional[str] = Query(None, description="Filter by level (error, warning)"),
):
    """
    Get problems (errors and warnings) from builds.

    Parses log entries to extract problems with source location info.
    """
    import sqlite3
    import hashlib

    db_path = _get_log_db_path()

    if not db_path or not db_path.exists():
        return ProblemsResponse(problems=[], total=0, error_count=0, warning_count=0)

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build WHERE clause - only get warnings and errors
        conditions = ["logs.level IN ('WARNING', 'ERROR', 'ALERT')"]
        params: list = []

        if build_name:
            if ":" in build_name:
                project_part, target_part = build_name.split(":", 1)
                conditions.append("builds.target = ?")
                params.append(target_part)
                conditions.append("builds.project_path LIKE ?")
                params.append(f"%/{project_part}")
            else:
                conditions.append("builds.target = ?")
                params.append(build_name)

        if project_root:
            conditions.append("builds.project_path LIKE ?")
            params.append(f"%{project_root}%")

        if level:
            if level.lower() == "error":
                conditions.append("logs.level IN ('ERROR', 'ALERT')")
            elif level.lower() == "warning":
                conditions.append("logs.level = 'WARNING'")

        where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT logs.id, logs.timestamp, logs.stage, logs.level,
                   logs.message, logs.ato_traceback, logs.python_traceback,
                   builds.target, builds.project_path
            FROM logs
            JOIN builds ON logs.build_id = builds.build_id
            {where_clause}
            ORDER BY logs.id DESC
            LIMIT 500
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Parse problems from log entries
        problems = []
        for row in rows:
            # Generate unique ID
            problem_id = hashlib.md5(
                f"{row['id']}-{row['message'][:50]}".encode()
            ).hexdigest()[:12]

            # Parse source location from ato_traceback if available
            file_path = None
            line = None
            column = None

            if row["ato_traceback"]:
                import re
                match = re.search(
                    r'File "([^"]+)", line (\d+)(?:, column (\d+))?',
                    row["ato_traceback"]
                )
                if match:
                    file_path = match.group(1)
                    line = int(match.group(2))
                    column = int(match.group(3)) if match.group(3) else None

            # Map log level to problem level
            problem_level = "error" if row["level"] in ("ERROR", "ALERT") else "warning"

            # Extract project name from path
            project_path = row["project_path"] or ""
            project_name = project_path.split("/")[-1] if project_path else None

            problems.append(Problem(
                id=problem_id,
                level=problem_level,
                message=row["message"],
                file=file_path,
                line=line,
                column=column,
                stage=row["stage"],
                logger="atopile",
                build_name=f"{project_name}:{row['target']}" if project_name else row["target"],
                project_name=project_name,
                timestamp=row["timestamp"],
                ato_traceback=row["ato_traceback"],
                exc_info=row["python_traceback"],
            ))

        # Count by level
        error_count = sum(1 for p in problems if p.level == "error")
        warning_count = sum(1 for p in problems if p.level == "warning")

        return ProblemsResponse(
            problems=problems,
            total=len(problems),
            error_count=error_count,
            warning_count=warning_count
        )

    except Exception as e:
        log.error(f"Failed to get problems: {e}")
        return ProblemsResponse(problems=[], total=0, error_count=0, warning_count=0)
