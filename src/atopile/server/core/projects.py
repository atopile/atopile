"""
Project discovery and file scanning logic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from atopile.dataclasses import (
    Build,
    BuildStatus,
    BuildTarget,
    BuildTargetStatus,
    FileTreeNode,
    ModuleDefinition,
    Project,
)
from atopile.model import build_history

log = logging.getLogger(__name__)


def _load_last_build_for_target(
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
            elapsed_seconds=build.duration,
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


def discover_projects_in_path(path: Path) -> list[Project]:
    """Discover all ato projects in the given path."""
    return discover_projects_in_paths([path])


def discover_projects_in_paths(paths: list[Path]) -> list[Project]:
    """
    Discover all ato projects in the given paths.
    """
    projects: list[Project] = []
    seen_roots: set[str] = set()

    for root_path in paths:
        if not root_path.exists():
            log.warning(f"Path does not exist: {root_path}")
            continue

        if (root_path / "ato.yaml").exists():
            ato_files = [root_path / "ato.yaml"]
        else:
            ato_files = list(root_path.rglob("ato.yaml"))

        for ato_file in ato_files:
            if ".ato" in ato_file.parts:
                continue

            # Skip cookiecutter template directories
            if "{{cookiecutter" in str(ato_file):
                continue

            project_root = ato_file.parent
            root_str = str(project_root)

            if root_str in seen_roots:
                continue
            seen_roots.add(root_str)

            try:
                with open(ato_file, "r") as f:
                    data = yaml.safe_load(f)

                if not data or "builds" not in data:
                    continue

                targets: list[BuildTarget] = []
                for name, config in data.get("builds", {}).items():
                    if isinstance(config, dict):
                        last_build = _load_last_build_for_target(project_root, name)
                        targets.append(
                            BuildTarget(
                                name=name,
                                entry=config.get("entry", ""),
                                root=root_str,
                                last_build=last_build,
                            )
                        )

                if targets:
                    # Build display path: workspace_folder/relative_path
                    # e.g., "packages/adi-adau145x" or "packages_alt/packages/st-lps22"
                    try:
                        rel_path = project_root.relative_to(root_path)
                        if rel_path == Path("."):
                            # Project is at workspace root
                            display_path = root_path.name
                        else:
                            display_path = f"{root_path.name}/{rel_path}"
                    except ValueError:
                        # Fallback if relative_to fails
                        display_path = project_root.name

                    projects.append(
                        Project(
                            root=root_str,
                            name=project_root.name,
                            display_path=display_path,
                            targets=targets,
                        )
                    )

            except Exception as e:
                log.warning(f"Failed to parse {ato_file}: {e}")
                continue

    # Sort by path (root) to group projects in the same directory together
    projects.sort(key=lambda p: p.root.lower())
    return projects


def build_file_tree(directory: Path, base_path: Path) -> list[FileTreeNode]:
    """
    Build a file tree of .ato and .py files for UI display.
    """
    nodes: list[FileTreeNode] = []

    excluded_dirs = {
        "build",
        ".ato",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "egg-info",
    }

    try:
        items = sorted(
            directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
        )
    except PermissionError:
        return nodes

    for item in items:
        if item.name.startswith(".") and item.name not in {".ato"}:
            continue
        if item.name in excluded_dirs:
            continue
        if item.name.endswith(".egg-info"):
            continue

        rel_path = str(item.relative_to(base_path))

        if item.is_dir():
            children = build_file_tree(item, base_path)
            if children:
                nodes.append(
                    FileTreeNode(
                        name=item.name,
                        path=rel_path,
                        type="folder",
                        children=children,
                    )
                )
        elif item.is_file():
            if item.suffix == ".ato":
                nodes.append(
                    FileTreeNode(
                        name=item.name,
                        path=rel_path,
                        type="file",
                        extension="ato",
                    )
                )
            elif item.suffix == ".py":
                nodes.append(
                    FileTreeNode(
                        name=item.name,
                        path=rel_path,
                        type="file",
                        extension="py",
                    )
                )

    return nodes


def create_project(
    parent_directory: Path, name: Optional[str] = None
) -> tuple[Path, str]:
    """
    Create a new atopile project using the standard cookiecutter template.

    This ensures consistency with CLI-created projects and provides:
    - Proper version handling with clean_version()
    - Comprehensive .gitignore
    - GitHub CI/CD workflows
    - LICENSE file
    """
    import sys

    from cookiecutter.main import cookiecutter

    from atopile import version

    if not parent_directory.exists():
        raise ValueError(f"Parent directory does not exist: {parent_directory}")
    if not parent_directory.is_dir():
        raise ValueError(f"Path is not a directory: {parent_directory}")

    # Generate unique project name if not provided
    if name:
        project_name = name
    else:
        base_name = "new_project"
        project_name = base_name
        counter = 2
        while (parent_directory / project_name).exists():
            project_name = f"{base_name}_{counter}"
            counter += 1

    # Check if directory would already exist
    project_slug = project_name.lower().replace(" ", "_").replace("-", "_")
    if (parent_directory / project_slug).exists():
        raise ValueError(f"Directory already exists: {parent_directory / project_slug}")

    # Get clean version
    try:
        ato_version = str(
            version.clean_version(version.get_installed_atopile_version())
        )
    except Exception:
        ato_version = "0.9.0"

    # Use the standard project template
    template_dir = Path(__file__).parent.parent.parent / "templates/project-template"

    project_path = Path(
        cookiecutter(
            str(template_dir),
            output_dir=str(parent_directory),
            no_input=True,
            extra_context={
                "project_name": project_name,
                "author_name": "Author",
                "author_email": "author@example.com",
                "license": "MIT license",
                "description": "A new atopile project",
                "__ato_version": ato_version,
                "__python_path": sys.executable,
            },
        )
    )

    return project_path, project_path.name


def _load_ato_yaml(project_root: Path) -> tuple[dict, Path]:
    """Load and return ato.yaml data and path."""
    ato_file = project_root / "ato.yaml"
    if not ato_file.exists():
        raise ValueError(f"ato.yaml not found in {project_root}")

    with open(ato_file, "r") as f:
        data = yaml.safe_load(f) or {}

    return data, ato_file


def _save_ato_yaml(ato_file: Path, data: dict) -> None:
    """Save ato.yaml preserving structure as much as possible."""
    with open(ato_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def add_build_target(project_root: Path, name: str, entry: str) -> BuildTarget:
    """
    Add a new build target to ato.yaml.

    Raises ValueError if target already exists.
    """
    data, ato_file = _load_ato_yaml(project_root)

    if "builds" not in data:
        data["builds"] = {}

    if name in data["builds"]:
        raise ValueError(f"Build target '{name}' already exists")

    data["builds"][name] = {"entry": entry}
    _save_ato_yaml(ato_file, data)

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
    data, ato_file = _load_ato_yaml(project_root)

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
    _save_ato_yaml(ato_file, data)

    # Load last build status for the target
    last_build = _load_last_build_for_target(project_root, final_name)

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
    data, ato_file = _load_ato_yaml(project_root)

    if "builds" not in data or name not in data["builds"]:
        raise ValueError(f"Build target '{name}' not found")

    del data["builds"][name]
    _save_ato_yaml(ato_file, data)

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
    data, ato_file = _load_ato_yaml(project_root)

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

    _save_ato_yaml(ato_file, data)
    return True
