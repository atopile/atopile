"""Filesystem mutation helpers for UI-facing file explorer actions."""

from __future__ import annotations

import shutil
from pathlib import Path


def next_duplicate_path(source: Path) -> Path:
    suffix = "".join(source.suffixes) if source.is_file() else ""
    base_name = source.name[: -len(suffix)] if suffix else source.name
    for index in range(1, 10_000):
        candidate_name = (
            f"{base_name} copy{suffix}"
            if index == 1
            else f"{base_name} copy {index}{suffix}"
        )
        candidate = source.with_name(candidate_name)
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find duplicate name for {source}")


def create_file(path_str: str) -> str:
    path = Path(path_str)
    if path.exists():
        raise FileExistsError(f"Path already exists: {path}")
    path.parent.mkdir(parents=False, exist_ok=True)
    path.touch(exist_ok=False)
    return str(path)


def create_folder(path_str: str) -> str:
    path = Path(path_str)
    path.mkdir(parents=False, exist_ok=False)
    return str(path)


def rename_path(path_str: str, new_path_str: str) -> str:
    path = Path(path_str)
    new_path = Path(new_path_str)
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    if new_path.exists():
        raise FileExistsError(f"Path already exists: {new_path}")
    path.rename(new_path)
    return str(new_path)


def delete_path(path_str: str) -> None:
    path = Path(path_str)
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def duplicate_path(path_str: str) -> str:
    source = Path(path_str)
    if not source.exists():
        raise FileNotFoundError(f"Path not found: {source}")
    destination = next_duplicate_path(source)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
    return str(destination)
