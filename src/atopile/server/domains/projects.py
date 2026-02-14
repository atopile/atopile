"""Projects domain logic - business logic for project operations."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from atopile import config
from atopile.dataclasses import (
    AddBuildTargetRequest,
    AddBuildTargetResponse,
    AppContext,
    Build,
    BuildStatus,
    BuildTarget,
    BuildTargetStatus,
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteBuildTargetRequest,
    DeleteBuildTargetResponse,
    DependenciesResponse,
    DependencyInfo,
    ModuleDefinition,
    ModulesResponse,
    Project,
    ProjectsResponse,
    RenameProjectRequest,
    RenameProjectResponse,
    UpdateBuildTargetRequest,
    UpdateBuildTargetResponse,
    UpdateDependencyVersionRequest,
    UpdateDependencyVersionResponse,
)
from atopile.model import build_history
from atopile.server.domains import packages as packages_domain
from atopile.version import needs_migration
from faebryk.libs.package.meta import get_package_state

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level helpers (previously in core/projects.py)
# ---------------------------------------------------------------------------


def load_last_build_for_target(
    project_root: Path, target_name: str
) -> Optional[BuildTargetStatus]:
    """Load the last build status for a target from build history database."""
    try:
        build: Optional[Build] = build_history.get_latest_build_for_target(
            str(project_root), target_name
        )

        if not build:
            return None

        # Convert started_at timestamp to ISO format
        if build.started_at:
            timestamp = datetime.fromtimestamp(build.started_at).isoformat()
        else:
            timestamp = ""

        status = build.status

        # If status is "building" or "queued", the build was interrupted
        # (server crashed/restarted while build was in progress)
        # Treat as "failed" so UI doesn't show stale "building" status
        if status in (BuildStatus.BUILDING, BuildStatus.QUEUED):
            status = BuildStatus.FAILED

        return BuildTargetStatus(
            status=status,
            timestamp=timestamp,
            elapsed_seconds=build.elapsed_seconds,
            warnings=build.warnings,
            errors=build.errors,
            stages=build.stages,
            build_id=build.build_id,
        )
    except Exception as e:
        log.debug(f"Failed to load build summary for {target_name}: {e}")
        return None


def extract_modules_from_file(
    ato_file: Path, project_root: Path
) -> list[ModuleDefinition]:
    """
    Extract all module/interface/component definitions from an .ato file.
    """
    from atopile.compiler.parse import parse_file
    from atopile.compiler.parser.AtoParser import AtoParser

    modules: list[ModuleDefinition] = []

    try:
        tree = parse_file(ato_file)
    except Exception as e:
        log.warning(f"Failed to parse {ato_file}: {e}")
        return modules

    try:
        rel_path = ato_file.relative_to(project_root)
    except ValueError:
        rel_path = ato_file.name

    def extract_blockdefs(ctx) -> None:
        if ctx is None:
            return

        if isinstance(ctx, AtoParser.BlockdefContext):
            try:
                blocktype_ctx = ctx.blocktype()
                if blocktype_ctx:
                    if blocktype_ctx.MODULE():
                        block_type = "module"
                    elif blocktype_ctx.INTERFACE():
                        block_type = "interface"
                    elif blocktype_ctx.COMPONENT():
                        block_type = "component"
                    else:
                        block_type = "unknown"
                else:
                    block_type = "unknown"

                type_ref_ctx = ctx.type_reference()
                if type_ref_ctx:
                    name_ctx = type_ref_ctx.name()
                    if name_ctx:
                        name = name_ctx.getText()
                    else:
                        name = type_ref_ctx.getText()
                else:
                    name = "Unknown"

                super_type = None
                super_ctx = ctx.blockdef_super()
                if super_ctx:
                    super_type_ref = super_ctx.type_reference()
                    if super_type_ref:
                        super_type = super_type_ref.getText()

                line = ctx.start.line if ctx.start else None
                entry = f"{rel_path}:{name}"

                modules.append(
                    ModuleDefinition(
                        name=name,
                        type=block_type,
                        file=str(rel_path),
                        entry=entry,
                        line=line,
                        super_type=super_type,
                    )
                )
            except Exception as e:
                log.debug(f"Failed to extract blockdef: {e}")

        if hasattr(ctx, "children") and ctx.children:
            for child in ctx.children:
                extract_blockdefs(child)

    extract_blockdefs(tree)
    return modules


def discover_modules_in_project(project_root: Path) -> list[ModuleDefinition]:
    """
    Discover all module definitions in a project by scanning .ato files.
    """
    all_modules: list[ModuleDefinition] = []

    for ato_file in project_root.rglob("*.ato"):
        if "build" in ato_file.parts:
            continue
        if ".ato" in ato_file.parts:
            continue

        modules = extract_modules_from_file(ato_file, project_root)
        all_modules.extend(modules)

    return all_modules


def discover_projects_in_paths(paths: list[Path]) -> list[Project]:
    """
    Discover all ato projects in the given paths.
    """
    projects: list[Project] = []
    seen_roots: set[str] = set()

    # Directories that never contain projects — skip to avoid
    # walking potentially huge trees (e.g. .ato/modules dependencies).
    _SKIP_DIRS = {
        ".ato",
        ".git",
        "build",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
    }

    for root_path in paths:
        if not root_path.exists():
            log.warning(f"Path does not exist: {root_path}")
            continue

        if (root_path / "ato.yaml").exists():
            ato_files = [root_path / "ato.yaml"]
        else:
            ato_files: list[Path] = []
            for dirpath, dirnames, filenames in os.walk(root_path):
                # Prune in-place so os.walk doesn't descend
                dirnames[:] = [
                    d
                    for d in dirnames
                    if d not in _SKIP_DIRS and not d.startswith("{{")
                ]
                if "ato.yaml" in filenames:
                    ato_files.append(Path(dirpath) / "ato.yaml")
                    # Don't descend into project subdirs — no nested projects
                    dirnames.clear()

        for ato_file in ato_files:
            project_root = ato_file.parent
            root_str = str(project_root)

            if root_str in seen_roots:
                continue
            seen_roots.add(root_str)

            try:
                raw = ato_file.read_bytes()

                # Fast pre-check: skip full YAML parse if no builds section
                if b"builds:" not in raw and b"builds :" not in raw:
                    continue

                data = yaml.safe_load(raw)

                if not data or "builds" not in data:
                    continue

                targets: list[BuildTarget] = []
                for name, cfg in data.get("builds", {}).items():
                    if isinstance(cfg, dict):
                        targets.append(
                            BuildTarget(
                                name=name,
                                entry=cfg.get("entry", ""),
                                root=root_str,
                            )
                        )

                if targets:
                    try:
                        rel_path = project_root.relative_to(root_path)
                        if rel_path == Path("."):
                            display_path = root_path.name
                        else:
                            display_path = f"{root_path.name}/{rel_path}"
                    except ValueError:
                        display_path = project_root.name

                    projects.append(
                        Project(
                            root=root_str,
                            name=project_root.name,
                            display_path=display_path,
                            targets=targets,
                            needs_migration=needs_migration(
                                data.get("requires-atopile")
                            ),
                        )
                    )

            except Exception as e:
                log.warning(f"Failed to parse {ato_file}: {e}")
                continue

    projects.sort(key=lambda p: p.root.lower())
    return projects


def create_project(
    parent_directory: Path, name: Optional[str] = None
) -> tuple[Path, str]:
    """
    Create a new minimal atopile project.
    """
    from atopile import version

    if not parent_directory.exists():
        raise ValueError(f"Parent directory does not exist: {parent_directory}")
    if not parent_directory.is_dir():
        raise ValueError(f"Path is not a directory: {parent_directory}")

    if name:
        project_name = name
    else:
        base_name = "new-project"
        project_name = base_name
        counter = 2
        while (parent_directory / project_name).exists():
            project_name = f"{base_name}-{counter}"
            counter += 1

    project_dir = parent_directory / project_name
    if project_dir.exists():
        raise ValueError(f"Directory already exists: {project_dir}")

    project_dir.mkdir(parents=True)
    (project_dir / "layouts").mkdir()

    try:
        ato_version = version.clean_version(version.get_installed_atopile_version())
    except Exception:
        ato_version = "0.9.0"

    ato_yaml_content = f"""requires-atopile: "^{ato_version}"

paths:
  src: ./
  layout: ./layouts

builds:
  default:
    entry: main.ato:App
"""
    (project_dir / "ato.yaml").write_text(ato_yaml_content)

    main_ato_content = f'''"""{project_name} - A new atopile project"""

module App:
    pass
'''
    (project_dir / "main.ato").write_text(main_ato_content)

    gitignore_content = """# Build outputs
build/

# Dependencies
.ato/

# IDE
.vscode/
.idea/

# OS
.DS_Store
"""
    (project_dir / ".gitignore").write_text(gitignore_content)

    return project_dir, project_name


def load_ato_yaml(project_root: Path) -> tuple[dict, Path]:
    """Load and return ato.yaml data and path."""
    ato_file = project_root / "ato.yaml"
    if not ato_file.exists():
        raise ValueError(f"ato.yaml not found in {project_root}")

    with open(ato_file, "r") as f:
        data = yaml.safe_load(f) or {}

    return data, ato_file


def save_ato_yaml(ato_file: Path, data: dict) -> None:
    """Save ato.yaml preserving structure as much as possible."""
    with open(ato_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def add_build_target(project_root: Path, name: str, entry: str) -> BuildTarget:
    """
    Add a new build target to ato.yaml.

    Raises ValueError if target already exists.
    """
    data, ato_file = load_ato_yaml(project_root)

    if "builds" not in data:
        data["builds"] = {}

    if name in data["builds"]:
        raise ValueError(f"Build target '{name}' already exists")

    data["builds"][name] = {"entry": entry}
    save_ato_yaml(ato_file, data)

    return BuildTarget(name=name, entry=entry, root=str(project_root))


def update_build_target(
    project_root: Path,
    old_name: str,
    new_name: Optional[str] = None,
    new_entry: Optional[str] = None,
) -> BuildTarget:
    """
    Update a build target in ato.yaml.

    Can rename the target and/or change its entry point.
    Raises ValueError if target not found or new name already exists.
    """
    data, ato_file = load_ato_yaml(project_root)

    if "builds" not in data or old_name not in data["builds"]:
        raise ValueError(f"Build target '{old_name}' not found")

    target_data = data["builds"][old_name]
    if not isinstance(target_data, dict):
        target_data = {"entry": target_data}

    # Update entry if provided
    if new_entry is not None:
        target_data["entry"] = new_entry

    # Handle rename
    final_name = old_name
    if new_name is not None and new_name != old_name:
        if new_name in data["builds"]:
            raise ValueError(f"Build target '{new_name}' already exists")

        # Remove old key and add new one
        del data["builds"][old_name]
        final_name = new_name

    data["builds"][final_name] = target_data
    save_ato_yaml(ato_file, data)

    # Load last build status for the target
    last_build = load_last_build_for_target(project_root, final_name)

    return BuildTarget(
        name=final_name,
        entry=target_data.get("entry", ""),
        root=str(project_root),
        last_build=last_build,
    )


def delete_build_target(project_root: Path, name: str) -> bool:
    """
    Delete a build target from ato.yaml.

    Raises ValueError if target not found.
    Returns True on success.
    """
    data, ato_file = load_ato_yaml(project_root)

    if "builds" not in data or name not in data["builds"]:
        raise ValueError(f"Build target '{name}' not found")

    del data["builds"][name]
    save_ato_yaml(ato_file, data)

    return True


def update_dependency_version(
    project_root: Path, identifier: str, new_version: str
) -> bool:
    """
    Update a dependency's version in ato.yaml.

    The dependencies section in ato.yaml looks like:
    dependencies:
      - atopile/resistors@^1.0.0
      - atopile/capacitors@^1.0.0

    Or can be:
    dependencies:
      atopile/resistors: ^1.0.0
      atopile/capacitors: ^1.0.0

    Raises ValueError if dependency not found.
    Returns True on success.
    """
    data, ato_file = load_ato_yaml(project_root)

    if "dependencies" not in data:
        raise ValueError(f"No dependencies section in {project_root}")

    deps = data["dependencies"]

    # Handle list format: ["atopile/resistors@^1.0.0", ...] or
    # [{type: registry, identifier: ..., release: ...}, ...]
    if isinstance(deps, list):
        found = False
        new_deps = []
        for dep in deps:
            if isinstance(dep, str):
                # Parse "identifier@version" format
                if "@" in dep:
                    dep_id, _old_version = dep.rsplit("@", 1)
                else:
                    dep_id = dep

                if dep_id == identifier:
                    new_deps.append(f"{identifier}@{new_version}")
                    found = True
                else:
                    new_deps.append(dep)
            elif isinstance(dep, dict):
                # Handle registry format:
                # {type: registry, identifier: ..., release: ...}
                dep_id = dep.get("identifier")
                if dep_id == identifier:
                    dep["release"] = new_version
                    found = True
                new_deps.append(dep)
            else:
                new_deps.append(dep)

        if not found:
            raise ValueError(f"Dependency '{identifier}' not found")

        data["dependencies"] = new_deps

    # Handle dict format: {"atopile/resistors": "^1.0.0", ...}
    elif isinstance(deps, dict):
        if identifier not in deps:
            raise ValueError(f"Dependency '{identifier}' not found")
        deps[identifier] = new_version

    else:
        raise ValueError(f"Unknown dependencies format in {project_root}")

    save_ato_yaml(ato_file, data)
    return True


# ---------------------------------------------------------------------------
# Domain-level handlers
# ---------------------------------------------------------------------------


def handle_get_projects(ctx: AppContext) -> ProjectsResponse:
    """Get all discovered projects in workspace paths."""
    if not ctx.workspace_paths:
        return ProjectsResponse(projects=[], total=0)

    projects = discover_projects_in_paths(ctx.workspace_paths)
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

    modules = discover_modules_in_project(project_path)
    if type_filter:
        modules = [m for m in modules if m.type == type_filter]

    modules.sort(key=lambda m: (m.file, m.name))
    return ModulesResponse(modules=modules, total=len(modules))


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


def _get_dependency_status(
    modules_root: Path, identifier: str, expected_version: str | None
) -> str:
    """Get the integrity status of an installed dependency."""
    package_path = modules_root / identifier
    try:
        state, _, _ = get_package_state(
            package_path,
            expected_version=expected_version,
            check_integrity=True,
        )
        return state.value
    except Exception as e:
        log.debug(f"Error checking package state for {identifier}: {e}")
        return "unknown"


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

    modules_root = project_path / ".ato" / "modules"
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

        # Get package integrity status
        expected_version = getattr(dep, "release", None)
        status = _get_dependency_status(modules_root, identifier, expected_version)

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
                status=status,
            )
        )

    transitive_sources = _collect_dependency_sources(project_path, direct_identifiers)

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

        # Get package integrity status (no expected version for transitive deps)
        status = _get_dependency_status(modules_root, identifier, version)

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
                status=status,
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
        project_dir, project_name = create_project(parent_dir, request.name)
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
        target = add_build_target(project_path, request.name, request.entry)
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
        target = update_build_target(
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
        delete_build_target(project_path, request.name)
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
        update_dependency_version(project_path, request.identifier, request.new_version)
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
    "handle_get_dependencies",
    "handle_create_project",
    "handle_rename_project",
    "handle_add_build_target",
    "handle_update_build_target",
    "handle_delete_build_target",
    "handle_update_dependency_version",
]
