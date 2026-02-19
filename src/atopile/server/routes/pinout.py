"""Pinout artifact routes."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from atopile.server.domains import pinout as pinout_domain

log = logging.getLogger(__name__)

router = APIRouter(tags=["pinout"])


@router.get("/api/pinout")
async def get_pinout(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    """Get pinout data for a build target."""
    try:
        result = await asyncio.to_thread(
            pinout_domain.handle_get_pinout, project_root, target
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Pinout file not found. Run 'ato build' first.",
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/pinout/targets")
async def get_pinout_targets(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
):
    """Get available targets that have pinout data."""
    try:
        return await asyncio.to_thread(
            pinout_domain.handle_get_pinout_targets, project_root
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/build/{build_id}/pinout")
async def get_pinout_by_build_id(build_id: str):
    """
    Get the pinout for a specific build by build_id.

    Uses build_id -> (project, target) translation to find the artifact.
    """
    try:
        result = await asyncio.to_thread(
            pinout_domain.handle_get_pinout_by_build_id, build_id
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Pinout not found for build {build_id}",
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
