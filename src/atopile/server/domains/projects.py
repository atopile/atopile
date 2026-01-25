"""Projects domain logic - business logic for project operations."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from atopile import config
from atopile.dataclasses import (
    AddBuildTargetRequest,
    AddBuildTargetResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteBuildTargetRequest,
    DeleteBuildTargetResponse,
    DependenciesResponse,
    DependencyInfo,
    FilesResponse,
    FileTreeNode,
    ModulesResponse,
    ProjectsResponse,
    RenameProjectRequest,
    RenameProjectResponse,
    UpdateBuildTargetRequest,
    UpdateBuildTargetResponse,
    UpdateDependencyVersionRequest,
    UpdateDependencyVersionResponse,
)
from atopile.dataclasses import AppContext
from atopile.server.core import projects as core_projects
from atopile.server.domains import packages as packages_domain
log = logging.getLogger(__name__)


def handle_get_projects(ctx: AppContext) -> ProjectsResponse:
    """Get all discovered projects in workspace path."""
    if not ctx.workspace_path:
        return ProjectsResponse(projects=[], total=0)

    projects = core_projects.discover_projects_in_paths([ctx.workspace_path])
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


def _dependency_display_parts(identifier: str) -> tuple[str, str]:
    parts = identifier.split("/")
    publisher = parts[0] if len(parts) > 1 else "unknown"
    name = parts[-1]
    return name, publisher


def _read_project_config_dependencies(
    project_path: Path,
) -> list[config.DependencySpec]:
    try:
        config_obj = config.ProjectConfig.from_path(project_path, validate_builds=False)
    except Exception:
        return []
    if not config_obj or not config_obj.dependencies:
        return []
    return [dep for dep in config_obj.dependencies if dep.identifier]


def _read_module_package_info(
    modules_root: Path, identifier: str
) -> tuple[str | None, str | None]:
    module_path = modules_root / identifier
    try:
        config_obj = config.ProjectConfig.from_path(module_path, validate_builds=False)
    except Exception:
        return None, None
    if not config_obj or not config_obj.package:
        return None, None
    return config_obj.package.version, (
        str(config_obj.package.repository) if config_obj.package.repository else None
    )


def _collect_dependency_sources(
    project_path: Path, direct_identifiers: list[str]
) -> dict[str, set[str]]:
    modules_root = project_path / ".ato" / "modules"
    if not modules_root.exists():
        return {}

    seen_pairs: set[tuple[str, str]] = set()
    sources: dict[str, set[str]] = {}
    queue: list[tuple[str, str]] = [(dep_id, dep_id) for dep_id in direct_identifiers]

    while queue:
        current_id, origin_id = queue.pop(0)
        if (current_id, origin_id) in seen_pairs:
            continue
        seen_pairs.add((current_id, origin_id))

        deps = _read_project_config_dependencies(modules_root / current_id)
        for dep in deps:
            dep_id = dep.identifier
            if not dep_id or dep_id in direct_identifiers:
                continue
            sources.setdefault(dep_id, set()).add(origin_id)
            queue.append((dep_id, origin_id))

    return sources


def _build_dependencies(project_path: Path) -> list[DependencyInfo]:
    direct_specs = _read_project_config_dependencies(project_path)
    direct_identifiers = [dep.identifier for dep in direct_specs if dep.identifier]
    direct_identifiers_set = set(direct_identifiers)

    installed = packages_domain.get_installed_packages_for_project(project_path)
    installed_versions = {pkg.identifier: pkg.version for pkg in installed}

    dependencies: list[DependencyInfo] = []

    try:
        registry_packages = packages_domain.get_all_registry_packages()
    except Exception:
        registry_packages = []
    registry_by_id = {pkg.identifier: pkg for pkg in registry_packages}

    for dep in direct_specs:
        identifier = dep.identifier
        if not identifier:
            continue

        name, publisher = _dependency_display_parts(identifier)
        version = (
            installed_versions.get(identifier)
            or getattr(dep, "release", None)
            or "unknown"
        )

        latest_version = None
        has_update = False
        repository = None

        cached_pkg = registry_by_id.get(identifier)
        if cached_pkg:
            latest_version = cached_pkg.latest_version
            has_update = packages_domain.version_is_newer(version, latest_version)
            repository = cached_pkg.repository

        dependencies.append(
            DependencyInfo(
                identifier=identifier,
                version=version,
                latest_version=latest_version,
                name=name,
                publisher=publisher,
                repository=repository,
                has_update=has_update,
                is_direct=True,
                via=None,
            )
        )

    transitive_sources = _collect_dependency_sources(project_path, direct_identifiers)
    modules_root = project_path / ".ato" / "modules"

    for identifier, sources in sorted(transitive_sources.items()):
        if identifier in direct_identifiers_set:
            continue

        name, publisher = _dependency_display_parts(identifier)
        version, repo_from_pkg = _read_module_package_info(modules_root, identifier)
        version = version or "unknown"

        latest_version = None
        has_update = False
        repository = repo_from_pkg

        cached_pkg = registry_by_id.get(identifier)
        if cached_pkg:
            latest_version = cached_pkg.latest_version
            has_update = packages_domain.version_is_newer(version, latest_version)
            repository = cached_pkg.repository or repository

        dependencies.append(
            DependencyInfo(
                identifier=identifier,
                version=version,
                latest_version=latest_version,
                name=name,
                publisher=publisher,
                repository=repository,
                has_update=has_update,
                is_direct=False,
                via=sorted(sources),
            )
        )

    return dependencies


def handle_get_dependencies(project_root: str) -> DependenciesResponse | None:
    """
    Get dependencies for a project from ato.yaml.

    Returns None if project not found.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        return None

    dependencies = _build_dependencies(project_path)
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


# --- Build Target Management ---


def handle_add_build_target(
    request: AddBuildTargetRequest,
) -> AddBuildTargetResponse:
    """Add a new build target to a project."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise ValueError(f"Project does not exist: {request.project_root}")

    try:
        target = core_projects.add_build_target(
            project_path, request.name, request.entry
        )
        return AddBuildTargetResponse(
            success=True,
            message=f"Added build target '{request.name}'",
            target={
                "name": target.name,
                "entry": target.entry,
                "root": target.root,
            },
        )
    except ValueError as exc:
        raise exc
    except Exception as exc:
        log.error(f"Failed to add build target: {exc}")
        raise ValueError(f"Failed to add build target: {exc}")


def handle_update_build_target(
    request: UpdateBuildTargetRequest,
) -> UpdateBuildTargetResponse:
    """Update a build target (rename or change entry point)."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise ValueError(f"Project does not exist: {request.project_root}")

    try:
        target = core_projects.update_build_target(
            project_path,
            request.old_name,
            request.new_name,
            request.new_entry,
        )
        return UpdateBuildTargetResponse(
            success=True,
            message=f"Updated build target '{target.name}'",
            target={
                "name": target.name,
                "entry": target.entry,
                "root": target.root,
            },
        )
    except ValueError as exc:
        raise exc
    except Exception as exc:
        log.error(f"Failed to update build target: {exc}")
        raise ValueError(f"Failed to update build target: {exc}")


def handle_delete_build_target(
    request: DeleteBuildTargetRequest,
) -> DeleteBuildTargetResponse:
    """Delete a build target from a project."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise ValueError(f"Project does not exist: {request.project_root}")

    try:
        core_projects.delete_build_target(project_path, request.name)
        return DeleteBuildTargetResponse(
            success=True,
            message=f"Deleted build target '{request.name}'",
        )
    except ValueError as exc:
        raise exc
    except Exception as exc:
        log.error(f"Failed to delete build target: {exc}")
        raise ValueError(f"Failed to delete build target: {exc}")


# --- Dependency Management ---


def handle_update_dependency_version(
    request: UpdateDependencyVersionRequest,
) -> UpdateDependencyVersionResponse:
    """Update a dependency's version in ato.yaml."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise ValueError(f"Project does not exist: {request.project_root}")

    try:
        core_projects.update_dependency_version(
            project_path, request.identifier, request.new_version
        )
        return UpdateDependencyVersionResponse(
            success=True,
            message=f"Updated '{request.identifier}' to version {request.new_version}",
        )
    except ValueError as exc:
        raise exc
    except Exception as exc:
        log.error(f"Failed to update dependency version: {exc}")
        raise ValueError(f"Failed to update dependency version: {exc}")


__all__ = [
    "CreateProjectRequest",
    "CreateProjectResponse",
    "RenameProjectRequest",
    "RenameProjectResponse",
    "AddBuildTargetRequest",
    "AddBuildTargetResponse",
    "UpdateBuildTargetRequest",
    "UpdateBuildTargetResponse",
    "DeleteBuildTargetRequest",
    "DeleteBuildTargetResponse",
    "UpdateDependencyVersionRequest",
    "UpdateDependencyVersionResponse",
    "handle_get_projects",
    "handle_get_modules",
    "handle_get_files",
    "handle_get_dependencies",
    "handle_create_project",
    "handle_rename_project",
    "handle_add_build_target",
    "handle_update_build_target",
    "handle_delete_build_target",
    "handle_update_dependency_version",
]
