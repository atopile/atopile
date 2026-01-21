"""Projects domain logic - business logic for project operations."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from atopile.server.app_context import AppContext
from atopile.server.core import projects as core_projects
from atopile.server.domains import packages as packages_domain
from atopile.server.state import server_state
from atopile.server.schemas.project import (
    ProjectsResponse,
    ModulesResponse,
    FilesResponse,
    FileTreeNode,
    DependenciesResponse,
    DependencyInfo,
)

log = logging.getLogger(__name__)


class CreateProjectRequest(BaseModel):
    parent_directory: str
    name: str | None = None


class CreateProjectResponse(BaseModel):
    success: bool
    message: str
    project_root: str | None = None
    project_name: str | None = None


class RenameProjectRequest(BaseModel):
    project_root: str
    new_name: str


class RenameProjectResponse(BaseModel):
    success: bool
    message: str
    old_root: str
    new_root: str | None = None


def handle_get_projects(ctx: AppContext) -> ProjectsResponse:
    """Get all discovered projects in workspace paths."""
    if not ctx.workspace_paths:
        return ProjectsResponse(projects=[], total=0)

    projects = core_projects.discover_projects_in_paths(ctx.workspace_paths)
    return ProjectsResponse(projects=projects, total=len(projects))


def handle_get_modules(
    project_root: str,
    type_filter: Optional[str] = None,
) -> ModulesResponse | None:
    """
    Get all module/interface/component definitions in a project.

    Returns None if project not found.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        return None

    modules = core_projects.discover_modules_in_project(project_path)
    if type_filter:
        modules = [m for m in modules if m.type == type_filter]

    modules.sort(key=lambda m: (m.file, m.name))
    return ModulesResponse(modules=modules, total=len(modules))


def handle_get_files(project_root: str) -> FilesResponse | None:
    """
    Get file tree for a project.

    Returns None if project not found.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        return None

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


def handle_get_dependencies(project_root: str) -> DependenciesResponse | None:
    """
    Get dependencies for a project from ato.yaml.

    Returns None if project not found.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        return None

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


def handle_create_project(
    request: CreateProjectRequest,
) -> CreateProjectResponse:
    """
    Create a new project.

    Raises ValueError for invalid inputs.
    """
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
        raise exc
    except Exception as exc:
        if project_dir and project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        log.error(f"Failed to create project: {exc}")
        raise ValueError(f"Failed to create project: {exc}")


def handle_rename_project(
    request: RenameProjectRequest,
) -> RenameProjectResponse:
    """
    Rename a project.

    Raises ValueError for invalid inputs.
    """
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise ValueError(f"Project does not exist: {request.project_root}")

    if not request.new_name or "/" in request.new_name or "\\" in request.new_name:
        raise ValueError("Invalid project name")

    new_path = project_path.parent / request.new_name
    if new_path.exists():
        raise ValueError(f"Directory already exists: {new_path}")

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
        raise ValueError(f"Failed to rename project: {exc}")


__all__ = [
    "CreateProjectRequest",
    "CreateProjectResponse",
    "RenameProjectRequest",
    "RenameProjectResponse",
    "handle_get_projects",
    "handle_get_modules",
    "handle_get_files",
    "handle_get_dependencies",
    "handle_create_project",
    "handle_rename_project",
]
