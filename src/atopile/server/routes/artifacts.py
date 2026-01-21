"""Build artifact routes (BOM, variables, stdlib, resolve-location)."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from atopile.server.app_context import AppContext
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import resolve as resolve_domain
from atopile.server.domains import stdlib as stdlib_domain
from atopile.server.domains.deps import get_ctx

log = logging.getLogger(__name__)

router = APIRouter(tags=["artifacts"])


@router.get("/api/bom")
async def get_bom(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    """Get the bill of materials for a build target."""
    try:
        result = await asyncio.to_thread(
            artifacts_domain.handle_get_bom, project_root, target
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"BOM file not found. Run 'ato build' first.",
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/bom/targets")
async def get_bom_targets(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
):
    """Get available targets that have BOM data."""
    try:
        return await asyncio.to_thread(
            artifacts_domain.handle_get_bom_targets, project_root
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/variables")
async def get_variables(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    """Get design variables for a build target."""
    try:
        result = await asyncio.to_thread(
            artifacts_domain.handle_get_variables, project_root, target
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Variables file not found. Run build first.",
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/variables/targets")
async def get_variables_targets(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
):
    """Get available targets that have variables data."""
    try:
        return await asyncio.to_thread(
            artifacts_domain.handle_get_variables_targets, project_root
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/resolve-location")
async def resolve_location(
    address: str = Query(
        ..., description="Atopile address to resolve (e.g., 'file.ato::Module.field')"
    ),
    project_root: Optional[str] = Query(
        None, description="Path to project root (optional for resolution)"
    ),
    ctx: AppContext = Depends(get_ctx),
):
    """Resolve an atopile address to a source file location."""
    try:
        return await asyncio.to_thread(
            resolve_domain.handle_resolve_location, address, project_root, ctx
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/stdlib")
async def get_stdlib(
    type_filter: str | None = Query(
        None,
        description="Filter by item type: interface, module, trait, component",
    ),
    search: str | None = Query(
        None, description="Search query to filter items by name or description"
    ),
    refresh: bool = Query(False, description="Force refresh the library cache"),
    max_depth: int | None = Query(
        None,
        description="Maximum depth for nested children. 0=none, 1=one level, 2=default.",
        ge=0,
        le=5,
    ),
):
    """Get the atopile standard library."""
    return await asyncio.to_thread(
        stdlib_domain.handle_get_stdlib, type_filter, search, refresh, max_depth
    )


@router.get("/api/stdlib/{item_id}")
async def get_stdlib_item(item_id: str):
    """Get details for a specific stdlib item."""
    result = await asyncio.to_thread(stdlib_domain.handle_get_stdlib_item, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
    return result
