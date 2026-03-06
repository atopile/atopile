"""Backend-owned file tree state for the sidebar file explorer."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from threading import Lock, Timer
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

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


class _ProjectFilesEventHandler(FileSystemEventHandler):
    def __init__(self, owner: "ProjectFilesWatcher") -> None:
        self._owner = owner

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._owner.on_fs_event(event)


class ProjectFilesWatcher:
    """Owns the currently watched project file tree and broadcasts full state."""

    _active: "ProjectFilesWatcher | None" = None
    _lock = Lock()
    DEBOUNCE_SECONDS = 0.3

    def __init__(
        self,
        project_root: str,
        *,
        broadcast: BroadcastFn,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.project_root = Path(project_root)
        self._broadcast = broadcast
        self._loop = loop
        self._observer: Observer | PollingObserver | None = None
        self._timer: Timer | None = None
        self._state_lock = Lock()
        self._last_json = ""

    @classmethod
    async def watch(
        cls,
        project_root: str,
        *,
        broadcast: BroadcastFn,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        root = Path(project_root)

        with cls._lock:
            if cls._active and cls._active.project_root == root:
                active = cls._active
            else:
                if cls._active:
                    cls._active.stop()
                active = cls(project_root, broadcast=broadcast, loop=loop)
                cls._active = active
                active.start()

        active.schedule_emit(immediate=True)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            if cls._active:
                cls._active.stop()
                cls._active = None

    def start(self) -> None:
        handler = _ProjectFilesEventHandler(self)
        try:
            observer: Observer | PollingObserver = Observer()
            observer.schedule(handler, str(self.project_root), recursive=True)
            observer.start()
            self._observer = observer
            log.info("Project files watcher started for %s", self.project_root)
        except Exception as exc:
            log.warning(
                "Project files native watcher failed for %s (%s), using polling",
                self.project_root,
                exc,
            )
            observer = PollingObserver(timeout=1.0)
            observer.schedule(handler, str(self.project_root), recursive=True)
            observer.start()
            self._observer = observer

    def stop(self) -> None:
        with self._state_lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None

        observer = self._observer
        self._observer = None
        if observer is not None:
            observer.stop()
            observer.join(timeout=2.0)
        log.info("Project files watcher stopped for %s", self.project_root)

    def on_fs_event(self, event: FileSystemEvent) -> None:
        paths = [Path(event.src_path)]
        dest_path = getattr(event, "dest_path", None)
        if dest_path:
            paths.append(Path(dest_path))

        if any(not _is_ignored(path, self.project_root) for path in paths):
            self.schedule_emit()

    def schedule_emit(self, *, immediate: bool = False) -> None:
        with self._state_lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None

            delay = 0.0 if immediate else self.DEBOUNCE_SECONDS
            self._timer = Timer(delay, self._emit_if_changed)
            self._timer.daemon = True
            self._timer.start()

    def _emit_if_changed(self) -> None:
        with self._state_lock:
            self._timer = None

        try:
            files = scan_project_tree(self.project_root)
            current_json = json.dumps(files, sort_keys=True)
            if current_json == self._last_json:
                return
            self._last_json = current_json
        except Exception:
            log.exception("Failed to scan project tree for %s", self.project_root)
            return

        future = asyncio.run_coroutine_threadsafe(
            self._broadcast(
                "project_files_changed",
                {
                    "project_root": str(self.project_root),
                    "files": files,
                },
            ),
            self._loop,
        )
        future.add_done_callback(self._log_emit_error)

    @staticmethod
    def _log_emit_error(future: asyncio.Future) -> None:
        try:
            future.result()
        except Exception:
            log.exception("Failed to broadcast project file tree update")
