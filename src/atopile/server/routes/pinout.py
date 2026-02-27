"""Pinout artifact routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

from atopile.server.domains import pinout as pinout_domain

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
