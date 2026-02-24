"""Build artifact routes (BOM, variables, stdlib, resolve-location)."""

from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import Response

from pydantic import BaseModel

from atopile.dataclasses import AppContext
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import requirements as requirements_domain
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
                detail="BOM file not found. Run 'ato build' first.",
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


def _sanitize_floats(obj: object) -> object:
    """Replace non-JSON-compliant floats (inf, -inf, nan) with None."""
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    return obj


@router.get("/api/requirements")
async def get_requirements(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    """Get simulation requirements results for a build target."""
    try:
        result = await asyncio.to_thread(
            artifacts_domain.handle_get_requirements, project_root, target
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Requirements file not found. Run build with simulation first.",
            )
        safe_result = _sanitize_floats(result)
        return Response(
            content=json.dumps(safe_result, separators=(",", ":")),
            media_type="application/json",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class UpdateRequirementRequest(BaseModel):
    source_file: str
    var_name: str
    updates: dict[str, str]


@router.post("/api/requirements/update")
async def update_requirement(request: UpdateRequirementRequest):
    """Update requirement fields in the .ato source file."""
    try:
        applied = await asyncio.to_thread(
            requirements_domain.handle_update_requirement,
            request.source_file,
            request.var_name,
            request.updates,
        )
        return {"success": True, "applied": applied}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.exception("Failed to update requirement")
        raise HTTPException(status_code=500, detail=str(exc))


class CreatePlotRequest(BaseModel):
    source_file: str
    req_var_name: str
    plot_var_name: str
    fields: dict[str, str]


@router.post("/api/plots/create")
async def create_plot(request: CreatePlotRequest):
    """Create a new LineChart plot linked to a requirement."""
    try:
        result = await asyncio.to_thread(
            requirements_domain.handle_create_plot,
            request.source_file,
            request.req_var_name,
            request.plot_var_name,
            request.fields,
        )
        return {"success": True, **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.exception("Failed to create plot")
        raise HTTPException(status_code=500, detail=str(exc))


class RerunSimulationRequest(BaseModel):
    project_root: str
    target: str = "default"


@router.post("/api/requirements/rerun")
async def rerun_simulation(request: RerunSimulationRequest):
    """Trigger a build to rerun simulations for the given target."""
    try:
        result = await asyncio.to_thread(
            requirements_domain.handle_rerun_simulation,
            request.project_root,
            request.target,
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Failed to trigger simulation rerun")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/resolve-location")
async def resolve_location(
    address: str = Query(
        ..., description="atopile address to resolve (e.g., 'file.ato::Module.field')"
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
        description="Maximum depth for nested children. 0=none, 1=one level, 2=default.",  # noqa: E501
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


# Build-ID based artifact endpoints


@router.get("/api/build/{build_id}/bom")
async def get_bom_by_build_id(build_id: str):
    """
    Get the BOM for a specific build by build_id.

    Uses build_id -> (project, target) translation to find the artifact.
    """
    try:
        result = await asyncio.to_thread(
            artifacts_domain.handle_get_bom_by_build_id, build_id
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"BOM not found for build {build_id}",
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/build/{build_id}/variables")
async def get_variables_by_build_id(build_id: str):
    """
    Get the variables for a specific build by build_id.

    Uses build_id -> (project, target) translation to find the artifact.
    """
    try:
        result = await asyncio.to_thread(
            artifacts_domain.handle_get_variables_by_build_id, build_id
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Variables not found for build {build_id}",
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
