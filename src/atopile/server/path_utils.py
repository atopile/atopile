"""
Path resolution helpers for projects, layouts, and workspace files.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml


def resolve_workspace_file(path_str: str, workspace_path: Path | None) -> Path | None:
    normalized = path_str.split("::", 1)[0].split("|", 1)[0]
    candidate = Path(normalized)
    if candidate.exists():
        return candidate

    if candidate.is_absolute():
        return None

    if workspace_path:
        try_path = workspace_path / candidate
        if try_path.exists():
            return try_path

    return None


def resolve_entry_path(project_root: Path, entry: str | None) -> Path | None:
    if not entry:
        return None

    entry_file = entry.split(":")[0] if ":" in entry else entry
    entry_path = Path(entry_file)
    if not entry_path.is_absolute():
        entry_path = project_root / entry_file
    return entry_path


def _get_layout_root(project_root: Path) -> Path:
    ato_yaml = project_root / "ato.yaml"
    if ato_yaml.exists():
        try:
            data = yaml.safe_load(ato_yaml.read_text()) or {}
            layout_path = data.get("paths", {}).get("layout")
            if layout_path:
                layout_root = Path(layout_path)
                if not layout_root.is_absolute():
                    layout_root = project_root / layout_root
                return layout_root
        except Exception:
            pass
    legacy_root = project_root / "layouts"
    if legacy_root.exists():
        return legacy_root
    return project_root / "elec" / "layout"


def _match_user_layout(path: Path) -> bool:
    autosave_patterns = [
        "_autosave-*",
        "*-save.kicad_pcb",
    ]
    for pattern in autosave_patterns:
        if fnmatch.fnmatch(path.name, pattern):
            return False
    return True


def _find_layout_in_dir(layout_dir: Path) -> Path | None:
    if not layout_dir.is_dir():
        return None
    candidates = [p for p in layout_dir.glob("*.kicad_pcb") if _match_user_layout(p)]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        return None
    return None


def resolve_layout_path(project_root: Path, target_name: str) -> Path | None:
    layout_root = _get_layout_root(project_root)
    layout_base = layout_root / target_name

    file_candidate = layout_base.with_suffix(".kicad_pcb")
    if file_candidate.exists():
        return file_candidate

    dir_candidate = _find_layout_in_dir(layout_base)
    if dir_candidate is not None:
        return dir_candidate

    if layout_base.exists():
        return layout_base

    if layout_root.exists():
        return layout_root

    return None


def resolve_3d_path(project_root: Path, target_name: str) -> Path | None:
    build_dir = project_root / "build" / "builds" / target_name
    if not build_dir.exists():
        return None

    candidate = build_dir / f"{target_name}.pcba.glb"
    if candidate.exists():
        return candidate

    glb_files = sorted(build_dir.glob("*.glb"))
    if glb_files:
        return glb_files[0]

    return build_dir
