"""Project-related API routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from atopile.server.app_context import AppContext
from atopile.server.core import projects as core_projects
from atopile.server.domains import packages as packages_domain
from atopile.server.domains.deps import get_ctx
from atopile.server.state import server_state
from atopile.server.schemas.project import (
    ProjectsResponse,
    ModulesResponse,
    FilesResponse,
    FileTreeNode,
    DependenciesResponse,
    DependencyInfo,
)
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


@router.get("/api/projects", response_model=ProjectsResponse)
async def get_projects(ctx: AppContext = Depends(get_ctx)):
    if not ctx.workspace_paths:
        return ProjectsResponse(projects=[], total=0)

    projects = core_projects.discover_projects_in_paths(ctx.workspace_paths)
    return ProjectsResponse(projects=projects, total=len(projects))


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
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {project_root}",
        )

    modules = core_projects.discover_modules_in_project(project_path)
    if type_filter:
        modules = [m for m in modules if m.type == type_filter]

    modules.sort(key=lambda m: (m.file, m.name))
    return ModulesResponse(modules=modules, total=len(modules))


@router.get("/api/files", response_model=FilesResponse)
async def get_files(
    project_root: str = Query(
        ..., description="Path to the project root to scan for files"
    )
):
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {project_root}",
        )

    file_tree = core_projects.build_file_tree(project_path, project_path)

    def count_files(nodes: list[FileTreeNode]) -> int:
        count = 0
        for node in nodes:
            if node.type == "file":
                count += 1
            elif node.children:
                count += count_files(node.children)
        return count

    total = count_files(file_tree)
    return FilesResponse(files=file_tree, total=total)


@router.get("/api/dependencies", response_model=DependenciesResponse)
async def get_dependencies(
    project_root: str = Query(
        ..., description="Path to the project root to get dependencies for"
    )
):
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {project_root}",
        )

    installed = packages_domain.get_installed_packages_for_project(project_path)

    dependencies: list[DependencyInfo] = []
    for pkg in installed:
        parts = pkg.identifier.split("/")
        publisher = parts[0] if len(parts) > 1 else "unknown"
        name = parts[-1]

        latest_version = None
        has_update = False
        repository = None

        cached_pkg = server_state.packages_by_id.get(pkg.identifier)
        if cached_pkg:
            latest_version = cached_pkg.latest_version
            has_update = packages_domain.version_is_newer(pkg.version, latest_version)
            repository = cached_pkg.repository

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


class CreateProjectRequest(BaseModel):
    parent_directory: str
    name: str | None = None


class CreateProjectResponse(BaseModel):
    success: bool
    message: str
    project_root: str | None = None
    project_name: str | None = None


@router.post("/api/project/create", response_model=CreateProjectResponse)
async def create_project(request: CreateProjectRequest):
    parent_dir = Path(request.parent_directory)
    project_dir: Path | None = None
    try:
        project_dir, project_name = core_projects.create_project(
            parent_dir, request.name
        )
        return CreateProjectResponse(
            success=True,
            message=f"Created project '{project_name}'",
            project_root=str(project_dir),
            project_name=project_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        if project_dir and project_dir.exists():
            import shutil

            shutil.rmtree(project_dir, ignore_errors=True)
        log.error(f"Failed to create project: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {exc}",
        )


class RenameProjectRequest(BaseModel):
    project_root: str
    new_name: str


class RenameProjectResponse(BaseModel):
    success: bool
    message: str
    old_root: str
    new_root: str | None = None


@router.post("/api/project/rename", response_model=RenameProjectResponse)
async def rename_project(request: RenameProjectRequest):
    import shutil

    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project does not exist: {request.project_root}",
        )

    if not request.new_name or "/" in request.new_name or "\\" in request.new_name:
        raise HTTPException(status_code=400, detail="Invalid project name")

    new_path = project_path.parent / request.new_name
    if new_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Directory already exists: {new_path}",
        )

    try:
        shutil.move(str(project_path), str(new_path))

        main_ato = new_path / "main.ato"
        if main_ato.exists():
            content = main_ato.read_text()
            old_name = project_path.name
            if f'"""{old_name}' in content:
                content = content.replace(f'"""{old_name}', f'"""{request.new_name}')
                main_ato.write_text(content)

        return RenameProjectResponse(
            success=True,
            message=f"Renamed to '{request.new_name}'",
            old_root=str(project_path),
            new_root=str(new_path),
        )
    except Exception as exc:
        log.error(f"Failed to rename project: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rename project: {exc}",
        )
