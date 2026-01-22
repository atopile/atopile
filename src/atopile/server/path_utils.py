"""
Path resolution helpers for projects, layouts, and workspace files.
"""

from __future__ import annotations

from pathlib import Path


def resolve_workspace_file(path_str: str, workspace_paths: list[Path]) -> Path | None:
    normalized = path_str.split("::", 1)[0].split("|", 1)[0]
    candidate = Path(normalized)
    if candidate.exists():
        return candidate

    if candidate.is_absolute():
        return None

    for root in workspace_paths:
        root_path = Path(root)
        try_path = root_path / candidate
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


def resolve_layout_path(project_root: Path, build_id: str) -> Path | None:
    candidates = [
        project_root / "layouts" / build_id / f"{build_id}.kicad_pcb",
        project_root / "layouts" / build_id,
        project_root / "layouts",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def resolve_3d_path(project_root: Path, build_id: str) -> Path | None:
    build_dir = project_root / "build" / "builds" / build_id
    if not build_dir.exists():
        return None

    candidate = build_dir / f"{build_id}.pcba.glb"
    if candidate.exists():
        return candidate

    glb_files = sorted(build_dir.glob("*.glb"))
    if glb_files:
        return glb_files[0]

    return build_dir
