"""
Build artifact routes (BOM, variables, etc.).

Endpoints:
- GET /api/bom - Get bill of materials
- GET /api/bom/targets - Get available BOM targets
- GET /api/variables - Get design variables
- GET /api/variables/targets - Get available variable targets
- GET /api/resolve-location - Resolve atopile address to source location
- GET /api/stdlib - Get standard library
- GET /api/stdlib/{item_id} - Get stdlib item details
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)

router = APIRouter(tags=["artifacts"])


def _get_workspace_paths():
    """Get workspace paths from server state."""
    from ..server import state

    return state.get("workspace_paths", [])


@router.get("/api/bom")
async def get_bom(
    project_root: str = Query(..., description="Project root directory"),
    target: str = Query("default", description="Build target name"),
):
    """
    Get the bill of materials for a build target.
    """
    from ..server import get_bom_data

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    bom = get_bom_data(project_path, target)
    if not bom:
        raise HTTPException(
            status_code=404, detail="BOM not found. Run 'ato build' first."
        )

    return bom


@router.get("/api/bom/targets")
async def get_bom_targets(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    Get available targets that have BOM data.
    """
    from ..server import get_bom_targets

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    targets = get_bom_targets(project_path)
    return {"targets": targets}


@router.get("/api/variables")
async def get_variables(
    project_root: str = Query(..., description="Project root directory"),
    target: str = Query("default", description="Build target name"),
):
    """
    Get design variables for a build target.
    """
    from ..server import get_variables_data

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    variables = get_variables_data(project_path, target)
    if not variables:
        raise HTTPException(
            status_code=404, detail="Variables not found. Run 'ato build' first."
        )

    return variables


@router.get("/api/variables/targets")
async def get_variables_targets(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    Get available targets that have variables data.
    """
    from ..server import get_variables_targets

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    targets = get_variables_targets(project_path)
    return {"targets": targets}


@router.get("/api/resolve-location")
async def resolve_location(
    address: str = Query(
        ..., description="Atopile address (e.g., 'App.power_supply::r_top')"
    ),
    project_root: Optional[str] = Query(None, description="Project root for context"),
):
    """
    Resolve an atopile address to a source file location.

    Used for "go to definition" functionality.
    """
    from ..server import resolve_atopile_address

    workspace_paths = _get_workspace_paths()
    project_path = (
        Path(project_root)
        if project_root
        else (workspace_paths[0] if workspace_paths else None)
    )

    if not project_path:
        raise HTTPException(
            status_code=400,
            detail="No project root provided and no workspace paths configured",
        )

    result = resolve_atopile_address(address, project_path)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"Could not resolve address: {address}"
        )

    return result


@router.get("/api/stdlib")
async def get_stdlib(
    refresh: bool = Query(False, description="Force refresh of stdlib cache"),
):
    """
    Get the atopile standard library.

    Returns interfaces, modules, and components from the stdlib.
    """
    from ..stdlib import get_standard_library, StdLibResponse

    items = get_standard_library(force_refresh=refresh)
    return StdLibResponse(items=items, total=len(items))


@router.get("/api/stdlib/{item_id}")
async def get_stdlib_item(item_id: str):
    """
    Get details for a specific stdlib item.
    """
    from ..stdlib import get_standard_library

    items = get_standard_library()
    for item in items:
        if item.id == item_id:
            return item

    raise HTTPException(status_code=404, detail=f"Stdlib item not found: {item_id}")
