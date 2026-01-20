"""
Project-related API routes.

Endpoints:
- GET /api/projects - List discovered projects
- GET /api/modules - List modules in a project
- GET /api/files - List files in a project
- GET /api/dependencies - List project dependencies
- POST /api/project/create - Create a new project
- POST /api/project/rename - Rename a project
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.project import (
    Project,
    ProjectsResponse,
    ModulesResponse,
    FilesResponse,
    DependenciesResponse,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


# These functions will be moved to core layer and injected via dependencies
# For now, import from server.py to maintain compatibility
def _get_discover_projects():
    """Get the project discovery function from server module."""
    from ..server import discover_projects_in_paths

    return discover_projects_in_paths


def _get_discover_modules():
    """Get the module discovery function from server module."""
    from ..server import discover_modules_in_project

    return discover_modules_in_project


def _get_workspace_paths():
    """Get workspace paths from server state."""
    from ..server import state

    return state.get("workspace_paths", [])


@router.get("/api/projects", response_model=ProjectsResponse)
async def list_projects():
    """
    List all discovered projects in workspace paths.

    Scans ato.yaml files in configured workspace paths and returns
    project information including build targets.
    """
    discover_projects = _get_discover_projects()
    workspace_paths = _get_workspace_paths()

    if not workspace_paths:
        return ProjectsResponse(projects=[], total=0)

    projects = discover_projects(workspace_paths)
    return ProjectsResponse(projects=projects, total=len(projects))


@router.get("/api/modules", response_model=ModulesResponse)
async def list_modules(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    List all module/interface/component definitions in a project.

    Parses .ato files in the project to find all block definitions.
    """
    discover_modules = _get_discover_modules()

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    modules = discover_modules(project_path)
    return ModulesResponse(modules=modules, total=len(modules))


@router.get("/api/files", response_model=FilesResponse)
async def list_files(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    List all .ato and .py files in a project.

    Returns a tree structure for file explorer display.
    """
    from ..server import build_file_tree  # Import from server for now

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    files = build_file_tree(project_path)

    # Count total files (not folders)
    def count_files(nodes):
        total = 0
        for node in nodes:
            if node.type == "file":
                total += 1
            elif node.children:
                total += count_files(node.children)
        return total

    return FilesResponse(files=files, total=count_files(files))


@router.get("/api/dependencies", response_model=DependenciesResponse)
async def list_dependencies(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    List dependencies for a project from ato.yaml.
    """
    from ..server import get_project_dependencies  # Import from server for now

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    dependencies = get_project_dependencies(project_path)
    return DependenciesResponse(dependencies=dependencies, total=len(dependencies))


# Project creation/renaming endpoints would go here
# Currently implemented in server.py, will be migrated later
