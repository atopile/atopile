"""
Project discovery and file scanning logic.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from ..schemas.project import BuildTarget, BuildTargetStatus, FileTreeNode, ModuleDefinition, Project

log = logging.getLogger(__name__)


def _load_last_build_for_target(project_root: Path, target_name: str) -> Optional[BuildTargetStatus]:
    """Load the last build status for a target from its build_summary.json."""
    summary_path = project_root / "build" / "builds" / target_name / "build_summary.json"
    if not summary_path.exists():
        return None

    try:
        data = json.loads(summary_path.read_text())

        # Convert timestamp from "2026-01-21_17-33-47" to ISO format
        timestamp = data.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")
                timestamp = dt.isoformat()
            except ValueError:
                # Keep original if format doesn't match
                pass

        return BuildTargetStatus(
            status=data.get("status", "unknown"),
            timestamp=timestamp,
            elapsed_seconds=data.get("elapsed_seconds"),
            warnings=data.get("warnings", 0),
            errors=data.get("errors", 0),
            stages=data.get("stages"),  # May be None if not present
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
                    projects.append(
                        Project(
                            root=root_str,
                            name=project_root.name,
                            targets=targets,
                        )
                    )

            except Exception as e:
                log.warning(f"Failed to parse {ato_file}: {e}")
                continue

    projects.sort(key=lambda p: p.name.lower())
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
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
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


def create_project(parent_directory: Path, name: Optional[str] = None) -> tuple[Path, str]:
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
        ato_version = version.get_installed_atopile_version()
    except Exception:
        ato_version = "^0.9.0"

    ato_yaml_content = f'''requires-atopile: "{ato_version}"

paths:
  src: ./
  layout: ./layouts

builds:
  default:
    entry: main.ato:App
'''
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
