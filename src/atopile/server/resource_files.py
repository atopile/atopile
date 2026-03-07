"""Server-owned resource file watchers for extension previews."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from threading import Lock
from typing import Any

from atopile.server.file_watcher import FileWatcher

log = logging.getLogger(__name__)

BroadcastFn = Callable[[str, dict[str, Any]], Awaitable[None]]


def _existing_watch_root(path: Path, project_root: Path | None) -> Path | None:
    if project_root and project_root.exists():
        return project_root

    current = path.parent
    while True:
        if current.exists():
            return current
        if current == current.parent:
            return None
        current = current.parent


class ResourceFileWatcher:
    """Tracks one preview resource path per resource type."""

    _active: dict[str, "ResourceFileWatcher"] = {}
    _lock = Lock()

    def __init__(
        self,
        resource_type: str,
        *,
        path: str,
        project_root: str | None,
        broadcast: BroadcastFn,
    ) -> None:
        self.resource_type = resource_type
        self.path = Path(path)
        self.project_root = Path(project_root) if project_root else None
        self._broadcast = broadcast
        self._watch_root = _existing_watch_root(self.path, self.project_root)
        self._watcher: FileWatcher | None = None
        self._task: asyncio.Task[None] | None = None
        self._last_exists: bool | None = None

        if self._watch_root:
            self._watcher = FileWatcher(
                f"resource-{resource_type}",
                paths=[self._watch_root],
                on_change=lambda _result: self._emit_current(),
                glob=self._glob_pattern(),
                debounce_s=0.2,
            )

    @classmethod
    async def watch(
        cls,
        resource_type: str,
        *,
        path: str | None,
        project_root: str | None,
        broadcast: BroadcastFn,
    ) -> dict[str, Any]:
        with cls._lock:
            existing = cls._active.get(resource_type)
            if existing:
                existing.stop()
                cls._active.pop(resource_type, None)

            if not path:
                return {"resourceType": resource_type, "path": None, "exists": False}

            watcher = cls(
                resource_type,
                path=path,
                project_root=project_root,
                broadcast=broadcast,
            )
            cls._active[resource_type] = watcher
            watcher.start()

        await watcher._emit_current(force=True)
        return {
            "resourceType": resource_type,
            "path": str(watcher.path),
            "exists": watcher.path.exists(),
        }

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            for watcher in cls._active.values():
                watcher.stop()
            cls._active.clear()

    def start(self) -> None:
        if not self._watcher:
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._watcher.run())
        log.info(
            "Resource watcher started for %s (%s via %s)",
            self.resource_type,
            self.path,
            self._watch_root,
        )

    def stop(self) -> None:
        if self._watcher:
            self._watcher.stop()
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        log.info("Resource watcher stopped for %s (%s)", self.resource_type, self.path)

    def _glob_pattern(self) -> str:
        if self._watch_root is None:
            return self.path.name

        try:
            relative = self.path.relative_to(self._watch_root).as_posix()
            return f"**/{relative}"
        except ValueError:
            return self.path.name

    async def _emit_current(self, *, force: bool = False) -> None:
        exists = self.path.exists()
        if not force and self._last_exists == exists:
            return
        self._last_exists = exists
        await self._broadcast(
            "resource_file_changed",
            {
                "resourceType": self.resource_type,
                "path": str(self.path),
                "exists": exists,
            },
        )
