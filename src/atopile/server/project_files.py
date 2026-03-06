"""Backend-owned file tree state for the sidebar file explorer."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from threading import Lock
from typing import Any

from atopile.server.file_watcher import FileWatcher

log = logging.getLogger(__name__)

BroadcastFn = Callable[[str, dict[str, Any]], Awaitable[None]]

_IGNORED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    ".venv",
    "venv",
    ".git",
}


def _is_ignored(path: Path, project_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(project_root.resolve())
    except (OSError, ValueError):
        return True

    return any(
        part in _IGNORED_DIRS or part.endswith(".egg-info") for part in relative.parts
    )


def scan_project_tree(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    if not root.is_dir():
        return []

    def scan_dir(dir_path: Path) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        try:
            entries = list(dir_path.iterdir())
        except (PermissionError, FileNotFoundError, NotADirectoryError):
            return nodes

        dirs: list[Path] = []
        files: list[Path] = []
        for entry in entries:
            if _is_ignored(entry, root):
                continue
            if entry.is_dir():
                dirs.append(entry)
            elif entry.is_file():
                files.append(entry)

        dirs.sort(key=lambda p: p.name.lower())
        files.sort(key=lambda p: p.name.lower())

        for directory in dirs:
            rel_path = directory.relative_to(root).as_posix()
            nodes.append(
                {
                    "name": directory.name,
                    "path": rel_path,
                    "type": "folder",
                    "children": scan_dir(directory),
                }
            )

        for file_path in files:
            rel_path = file_path.relative_to(root).as_posix()
            nodes.append(
                {
                    "name": file_path.name,
                    "path": rel_path,
                    "type": "file",
                }
            )

        return nodes

    return scan_dir(root)


class ProjectFilesWatcher:
    """Owns the currently watched project file tree and broadcasts full state."""

    _active: "ProjectFilesWatcher | None" = None
    _lock = Lock()

    def __init__(
        self,
        project_root: str,
        *,
        broadcast: BroadcastFn,
    ) -> None:
        self.project_root = Path(project_root)
        self._broadcast = broadcast
        self._watcher = FileWatcher(
            "project-files",
            paths=[self.project_root],
            on_change=lambda _result: self._emit_if_changed(),
            glob="**/*",
            debounce_s=0.3,
        )
        self._task: asyncio.Task[None] | None = None
        self._last_json = ""

    @classmethod
    async def watch(
        cls,
        project_root: str,
        *,
        broadcast: BroadcastFn,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        del loop
        root = Path(project_root)

        with cls._lock:
            if cls._active and cls._active.project_root == root:
                active = cls._active
            else:
                if cls._active:
                    cls._active.stop()
                active = cls(project_root, broadcast=broadcast)
                cls._active = active
                active.start()

        await active._emit_if_changed()

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            if cls._active:
                cls._active.stop()
                cls._active = None

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._watcher.run())
        log.info("Project files watcher started for %s", self.project_root)

    def stop(self) -> None:
        self._watcher.stop()
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        log.info("Project files watcher stopped for %s", self.project_root)

    async def _emit_if_changed(self) -> None:
        try:
            files = scan_project_tree(self.project_root)
            current_json = json.dumps(files, sort_keys=True)
            if current_json == self._last_json:
                return
            self._last_json = current_json
        except Exception:
            log.exception("Failed to scan project tree for %s", self.project_root)
            return

        await self._broadcast(
            "project_files_changed",
            {
                "project_root": str(self.project_root),
                "files": files,
            },
        )
