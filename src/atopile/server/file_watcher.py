from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from faebryk.libs.util import FileChangedWatcher

log = logging.getLogger(__name__)

WatchCallback = Callable[[FileChangedWatcher.Result], Awaitable[None] | None]


class PollingFileWatcher:
    """Platform-independent file watcher using polling."""

    def __init__(
        self,
        name: str,
        *,
        paths: Sequence[Path] | None = None,
        paths_provider: Callable[[], Sequence[Path]] | None = None,
        on_change: WatchCallback,
        glob: str | None = None,
        interval_s: float = 1.0,
        method: FileChangedWatcher.CheckMethod = FileChangedWatcher.CheckMethod.FS,
    ) -> None:
        if paths is None and paths_provider is None:
            raise ValueError("paths or paths_provider must be provided")

        self._name = name
        self._paths_provider = paths_provider
        self._static_paths = list(paths or [])
        self._on_change = on_change
        self._glob = glob
        self._interval_s = interval_s
        self._method = method
        self._stop_event = asyncio.Event()
        self._paths: list[Path] = []
        self._watcher = self._build_watcher(self._resolve_paths())

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        log.info("File watcher '%s' started", self._name)
        while not self._stop_event.is_set():
            try:
                self._refresh_paths()
                result = self._watcher.has_changed(reset=True)
                if result:
                    await self._dispatch(result)
            except Exception as exc:
                log.warning("File watcher '%s' error: %s", self._name, exc)
            await asyncio.sleep(self._interval_s)
        log.info("File watcher '%s' stopped", self._name)

    def _resolve_paths(self) -> list[Path]:
        paths = (
            list(self._paths_provider())
            if self._paths_provider is not None
            else list(self._static_paths)
        )
        return [path for path in paths if path.exists()]

    def _refresh_paths(self) -> None:
        new_paths = self._resolve_paths()
        if self._paths == new_paths:
            return
        self._paths = new_paths
        self._watcher = self._build_watcher(new_paths)
        log.debug("File watcher '%s' updated paths: %s", self._name, new_paths)

    def _build_watcher(self, paths: Sequence[Path]) -> FileChangedWatcher:
        if not paths:
            return FileChangedWatcher(method=self._method)
        return FileChangedWatcher(*paths, method=self._method, glob=self._glob)

    async def _dispatch(self, result: FileChangedWatcher.Result) -> None:
        response = self._on_change(result)
        if isinstance(response, Awaitable):
            await response
        log.info(
            "File watcher '%s' changes: +%d ~%d -%d",
            self._name,
            len(result.created),
            len(result.changed),
            len(result.deleted),
        )
