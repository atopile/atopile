"""Problem-related API routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Query

from atopile.dataclasses import ProblemsResponse
from atopile.server.domains import problems as problems_domain

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
    developer_mode: Optional[bool] = Query(
        None, description="Include developer log audiences"
    ),
):
    """Get problems (errors/warnings) from builds."""
    return await asyncio.to_thread(
        problems_domain.handle_get_problems,
        project_root=project_root,
        build_name=build_name,
        level=level,
        developer_mode=developer_mode,
    )
