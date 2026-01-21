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

from ..core import packages as core_packages
from ..core import projects as core_projects
from ..models import registry as registry_model
from ..schemas.project import (
    Project,
    ProjectsResponse,
    ModulesResponse,
    FilesResponse,
    DependenciesResponse,
    DependencyInfo,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


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
    workspace_paths = _get_workspace_paths()

    if not workspace_paths:
        return ProjectsResponse(projects=[], total=0)

    projects = core_projects.discover_projects_in_paths(workspace_paths)
    return ProjectsResponse(projects=projects, total=len(projects))


@router.get("/api/modules", response_model=ModulesResponse)
async def list_modules(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    List all module/interface/component definitions in a project.

    Parses .ato files in the project to find all block definitions.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    modules = core_projects.discover_modules_in_project(project_path)
    return ModulesResponse(modules=modules, total=len(modules))


@router.get("/api/files", response_model=FilesResponse)
async def list_files(
    project_root: str = Query(..., description="Project root directory"),
):
    """
    List all .ato and .py files in a project.

    Returns a tree structure for file explorer display.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    files = core_projects.build_file_tree(project_path, project_path)

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
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    # Build registry lookup for latest versions
    registry_packages = registry_model.get_all_registry_packages()
    registry_map = {pkg.identifier: pkg for pkg in registry_packages}

    dependencies = []
    installed = core_packages.get_installed_packages_for_project(project_path)
    for pkg in installed:
        parts = pkg.identifier.split("/")
        publisher = parts[0] if len(parts) > 1 else "unknown"
        name = parts[-1]

        latest_version = None
        has_update = False
        repository = None
        if pkg.identifier in registry_map:
            reg = registry_map[pkg.identifier]
            latest_version = reg.latest_version
            repository = reg.repository
            has_update = registry_model.version_is_newer(pkg.version, latest_version)

        dependencies.append(
            DependencyInfo(
                identifier=pkg.identifier,
                version=pkg.version,
                latest_version=latest_version,
                name=name,
                publisher=publisher,
                repository=repository,
                has_update=has_update,
            )
        )
    return DependenciesResponse(dependencies=dependencies, total=len(dependencies))


# Project creation/renaming endpoints would go here
# Currently implemented in server.py, will be migrated later
