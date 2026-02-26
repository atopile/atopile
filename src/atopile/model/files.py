"""File tree scanning and watching for the project file explorer."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from atopile.dataclasses import FileNode

try:
    import watchfiles
except ImportError:
    watchfiles = None

log = logging.getLogger(__name__)


class FileWatcher:
    """Scan and watch a project directory for the file explorer."""

    DEBOUNCE_SECONDS = 0.3
    _active: FileWatcher | None = None

    def __init__(
        self,
        project_root: str,
        broadcast: Callable[[str, Any], Coroutine[Any, Any, None]],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.project_root = project_root
        self._broadcast = broadcast
        self._loop = loop
        self._stop_event = threading.Event()
        threading.Thread(target=self._watch, daemon=True).start()
        log.info("File watcher started for %s", self.project_root)

    @staticmethod
    def scan(dir_path: Path) -> list[FileNode]:
        """Recursively scan a directory and return a sorted FileNode tree."""
        nodes: list[FileNode] = []

        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            log.debug("Permission denied: %s", dir_path)
            return nodes

        dirs: list[Path] = []
        files: list[Path] = []
        for entry in entries:
            if entry.is_dir():
                dirs.append(entry)
            elif entry.is_file():
                files.append(entry)

        dirs.sort(key=lambda p: p.name.lower())
        files.sort(key=lambda p: p.name.lower())

        for d in dirs:
            nodes.append(FileNode(name=d.name, children=FileWatcher.scan(d)))

        for f in files:
            nodes.append(FileNode(name=f.name))

        return nodes

    @staticmethod
    def scan_and_serialize(project_root: str) -> dict:
        root = Path(project_root)
        nodes = FileWatcher.scan(root) if root.is_dir() else []
        return {"projectFiles": [n.model_dump(by_alias=True) for n in nodes]}

    @classmethod
    def start(
        cls,
        project_root: str,
        broadcast: Callable[[str, Any], Coroutine[Any, Any, None]],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Start a watcher for the given project root, replacing any existing one."""
        if cls._active and cls._active.project_root == project_root:
            return
        if cls._active:
            cls._active._stop_event.set()
        cls._active = cls(project_root, broadcast, loop)

    def _broadcast_scan(self) -> None:
        try:
            result = FileWatcher.scan_and_serialize(self.project_root)
        except Exception:
            log.exception("File watcher: error re-scanning %s", self.project_root)
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast("projectFiles", result),
            self._loop,
        )

    def _watch(self) -> None:
        if watchfiles is not None:
            for _changes in watchfiles.watch(
                self.project_root,
                stop_event=self._stop_event,
                debounce=int(self.DEBOUNCE_SECONDS * 1000),
                step=100,
            ):
                if self._stop_event.is_set():
                    break
                self._broadcast_scan()
        else:
            log.debug("watchfiles not available, using polling fallback")
            self._watch_polling()

    def _watch_polling(self) -> None:
        last_json = ""
        while not self._stop_event.wait(timeout=1.0):
            result = FileWatcher.scan_and_serialize(self.project_root)
            current_json = json.dumps(result, sort_keys=True)
            if current_json != last_json:
                last_json = current_json
                asyncio.run_coroutine_threadsafe(
                    self._broadcast("projectFiles", result),
                    self._loop,
                )
