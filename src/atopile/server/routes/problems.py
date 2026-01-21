"""Problem-related API routes."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from atopile.server.domains import problems as problems_domain
from atopile.server.schemas.problem import ProblemsResponse

log = logging.getLogger(__name__)

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
    """Get problems (errors/warnings) from builds."""
    return problems_domain.handle_get_problems(
        project_root=project_root,
        build_name=build_name,
        level=level,
    )
