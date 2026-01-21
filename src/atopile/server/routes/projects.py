"""Project-related API routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from atopile.dataclasses import (
    DependenciesResponse,
    FilesResponse,
    ModulesResponse,
    ProjectsResponse,
)
from atopile.server.app_context import AppContext
from atopile.server.domains import projects as projects_domain
from atopile.server.domains.deps import get_ctx

log = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


@router.get("/api/projects", response_model=ProjectsResponse)
async def get_projects(ctx: AppContext = Depends(get_ctx)):
    """List all discovered projects in workspace paths."""
    return await asyncio.to_thread(projects_domain.handle_get_projects, ctx)


@router.get("/api/modules", response_model=ModulesResponse)
async def get_modules(
    project_root: str = Query(
        ..., description="Path to the project root to scan for modules"
    ),
    type_filter: Optional[str] = Query(
        None,
        description="Filter by type: 'module', 'interface', or 'component'",
    ),
):
    """List all module/interface/component definitions in a project."""
    result = await asyncio.to_thread(
        projects_domain.handle_get_modules, project_root, type_filter
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {project_root}",
        )
    return result


@router.get("/api/files", response_model=FilesResponse)
async def get_files(
    project_root: str = Query(
        ..., description="Path to the project root to scan for files"
    ),
):
    """List all .ato and .py files in a project."""
    result = await asyncio.to_thread(projects_domain.handle_get_files, project_root)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {project_root}",
        )
    return result


@router.get("/api/dependencies", response_model=DependenciesResponse)
async def get_dependencies(
    project_root: str = Query(
        ..., description="Path to the project root to get dependencies for"
    ),
):
    """List dependencies for a project from ato.yaml."""
    result = await asyncio.to_thread(
        projects_domain.handle_get_dependencies, project_root
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {project_root}",
        )
    return result


@router.post(
    "/api/project/create",
    response_model=projects_domain.CreateProjectResponse,
)
async def create_project(request: projects_domain.CreateProjectRequest):
    """Create a new project."""
    try:
        return await asyncio.to_thread(projects_domain.handle_create_project, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(f"Failed to create project: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {exc}",
        )


@router.post(
    "/api/project/rename",
    response_model=projects_domain.RenameProjectResponse,
)
async def rename_project(request: projects_domain.RenameProjectRequest):
    """Rename a project."""
    try:
        return await asyncio.to_thread(projects_domain.handle_rename_project, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(f"Failed to rename project: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rename project: {exc}",
        )


# --- Build Target Management ---


@router.post(
    "/api/build-target/add",
    response_model=projects_domain.AddBuildTargetResponse,
)
async def add_build_target(request: projects_domain.AddBuildTargetRequest):
    """Add a new build target to a project."""
    try:
        return await asyncio.to_thread(projects_domain.handle_add_build_target, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(f"Failed to add build target: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add build target: {exc}",
        )


@router.post(
    "/api/build-target/update",
    response_model=projects_domain.UpdateBuildTargetResponse,
)
async def update_build_target(request: projects_domain.UpdateBuildTargetRequest):
    """Update a build target (rename or change entry point)."""
    try:
        return await asyncio.to_thread(
            projects_domain.handle_update_build_target, request
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(f"Failed to update build target: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update build target: {exc}",
        )


@router.post(
    "/api/build-target/delete",
    response_model=projects_domain.DeleteBuildTargetResponse,
)
async def delete_build_target(request: projects_domain.DeleteBuildTargetRequest):
    """Delete a build target from a project."""
    try:
        return await asyncio.to_thread(
            projects_domain.handle_delete_build_target, request
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(f"Failed to delete build target: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete build target: {exc}",
        )


# --- Dependency Management ---


@router.post(
    "/api/dependency/update",
    response_model=projects_domain.UpdateDependencyVersionResponse,
)
async def update_dependency_version(
    request: projects_domain.UpdateDependencyVersionRequest,
):
    """Update a dependency's version in ato.yaml."""
    try:
        return await asyncio.to_thread(
            projects_domain.handle_update_dependency_version, request
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error(f"Failed to update dependency version: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update dependency version: {exc}",
        )
