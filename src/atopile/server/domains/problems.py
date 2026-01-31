"""Problems domain logic - business logic for problem reporting."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from atopile.dataclasses import ProblemsResponse
from atopile.server import problem_parser

log = logging.getLogger(__name__)


def handle_get_problems(
    project_root: Optional[str] = None,
    build_name: Optional[str] = None,
    level: Optional[str] = None,
    developer_mode: Optional[bool] = None,
) -> ProblemsResponse:
    """
    Get problems (errors and warnings) from builds.

    Args:
        project_root: Filter to problems from a specific project
        build_name: Filter to problems from a specific build target
        level: Filter by level ('error' or 'warning')

    Returns:
        ProblemsResponse with problems and counts
    """
    all_problems = problem_parser._load_problems_from_db(
        developer_mode=bool(developer_mode)
    )

    if project_root:
        project_name = Path(project_root).name
        all_problems = [p for p in all_problems if p.project_name == project_name]

    if build_name:
        if ":" in build_name:
            all_problems = [p for p in all_problems if p.build_name == build_name]
        else:
            all_problems = [
                p
                for p in all_problems
                if p.build_name == build_name
                or (p.build_name and p.build_name.endswith(f":{build_name}"))
            ]

    if level:
        all_problems = [p for p in all_problems if p.level == level]

    error_count = sum(1 for p in all_problems if p.level == "error")
    warning_count = sum(1 for p in all_problems if p.level == "warning")

    return ProblemsResponse(
        problems=all_problems,
        total=len(all_problems),
        error_count=error_count,
        warning_count=warning_count,
    )


__all__ = [
    "handle_get_problems",
]
