"""Problems endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from atopile.server import problem_parser
from atopile.server.schemas.problem import ProblemsResponse

router = APIRouter(tags=["problems"])


@router.get("/api/problems", response_model=ProblemsResponse)
async def get_problems(
    project_root: Optional[str] = Query(
        None, description="Filter to problems from a specific project"
    ),
    build_name: Optional[str] = Query(
        None, description="Filter to problems from a specific build target"
    ),
    level: Optional[str] = Query(
        None, description="Filter by level: 'error' or 'warning'"
    ),
):
    all_problems = problem_parser._load_problems_from_db()

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
