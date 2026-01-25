"""Native filesystem watcher using watchdog with shared observer."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

log = logging.getLogger(__name__)


def _configure_watchdog_logging() -> None:
    for name in (
        "watchdog",
        "watchdog.events",
        "watchdog.observers",
        "watchdog.observers.fsevents",
        "watchdog.observers.inotify_buffer",
        "watchdog.observers.polling",
    ):
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        logger.disabled = True


_IGNORED_DIR_NAMES = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".ato",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    ".cursor",
    "__pycache__",
    "node_modules",
    "dist",
    "zig-out",
})

# Patterns for watchdog's built-in filtering (applied early, before events reach handlers)
_WATCH_PATTERNS = [
    "*.ato",
    "*.py",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.kicad_pcb",
    "*.kicad_pro",
    "*.kicad_sch",
    "*.kicad_mod",
    "*.kicad_sym",
]

# Ignore patterns for watchdog (applied early, skips entire directories)
_IGNORE_PATTERNS = [
    f"*/{name}/*" for name in _IGNORED_DIR_NAMES
] + [
    f"*/{name}" for name in _IGNORED_DIR_NAMES
]


@dataclass
class FileChangeResult:
    """Result of file change detection."""

    created: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    changed: list[Path] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.created or self.deleted or self.changed)


_HandlerInfo = tuple[
    str, Callable[[FileChangeResult], None], float, asyncio.AbstractEventLoop
]


class _EventDispatcher(PatternMatchingEventHandler):
    """
    Dispatches filesystem events to glob-filtered handlers with debouncing.

    Uses PatternMatchingEventHandler for early filtering - watchdog skips
    non-matching files before events even reach our handlers, reducing CPU usage.

    Single instance shared by all watchers to avoid FSEvents conflicts on macOS.
    """

    def __init__(self) -> None:
        super().__init__(
            patterns=_WATCH_PATTERNS,
            ignore_patterns=_IGNORE_PATTERNS,
            ignore_directories=True,
            case_sensitive=False,
        )
        self._lock = Lock()
        self._handlers: dict[int, _HandlerInfo] = {}
        self._pending: dict[int, FileChangeResult] = {}
        self._timers: dict[int, asyncio.TimerHandle] = {}

    def add_handler(
        self,
        handler_id: int,
        glob: str,
        callback: Callable[[FileChangeResult], None],
        debounce_s: float,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        with self._lock:
            self._handlers[handler_id] = (glob, callback, debounce_s, loop)
            self._pending[handler_id] = FileChangeResult()

    def remove_handler(self, handler_id: int) -> None:
        with self._lock:
            self._handlers.pop(handler_id, None)
            self._pending.pop(handler_id, None)
            timer = self._timers.pop(handler_id, None)
            if timer:
                timer.cancel()

    def _matches(self, glob: str, path: str) -> bool:
        return fnmatch.fnmatch(path, glob) or fnmatch.fnmatch(
            Path(path).name, glob.split("/")[-1]
        )

    def _dispatch(self, path_str: str, event_type: str) -> None:
        path = Path(path_str)
        if self._is_ignored(path):
            return
        with self._lock:
            for hid, (glob, callback, debounce_s, loop) in self._handlers.items():
                if not self._matches(glob, path_str):
                    continue

                pending = self._pending[hid]
                if event_type == "created":
                    pending.created.append(path)
                elif event_type == "deleted":
                    pending.deleted.append(path)
                elif event_type == "changed" and path not in pending.created:
                    pending.changed.append(path)

                # Schedule debounced callback
                old_timer = self._timers.get(hid)
                if old_timer:
                    old_timer.cancel()

                def fire(hid: int = hid, cb: Callable = callback) -> None:
                    with self._lock:
                        result = self._pending.get(hid)
                        if not result:
                            return
                        self._pending[hid] = FileChangeResult()
                        self._timers.pop(hid, None)
                    if result.created or result.changed or result.deleted:
                        sample = (
                            result.created[:2] + result.changed[:2] + result.deleted[:2]
                        )
                        log.info(
                            "File watcher triggered: %s created, %s changed, %s deleted",  # noqa: E501
                            len(result.created),
                            len(result.changed),
                            len(result.deleted),
                        )
                        log.info(
                            "File watcher sample: %s",
                            ", ".join(str(p) for p in sample[:3]),
                        )
                    cb(result)

                self._timers[hid] = loop.call_later(debounce_s, fire)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._dispatch(self._path_str(event.src_path), "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._dispatch(self._path_str(event.src_path), "deleted")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._dispatch(self._path_str(event.src_path), "changed")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._dispatch(self._path_str(event.src_path), "deleted")
        if hasattr(event, "dest_path"):
            self._dispatch(self._path_str(event.dest_path), "created")

    @staticmethod
    def _path_str(path: str | bytes) -> str:
        return path.decode() if isinstance(path, bytes) else path

    @staticmethod
    def _is_ignored(path: Path) -> bool:
        """Secondary filter for paths that slip through watchdog's pattern matching."""
        # Check if any path component is in ignored directories
        # This catches edge cases the glob patterns might miss
        for part in path.parts:
            if part in _IGNORED_DIR_NAMES:
                return True
        return False


# Module-level singleton state
_observer: Any = None
_dispatcher: _EventDispatcher | None = None
_path_watches: dict[Path, Any] = {}
_path_refcount: dict[Path, int] = {}
_watch_lock = Lock()


def _get_observer() -> tuple[Any, _EventDispatcher]:
    """Get or create the shared observer singleton.

    Tries native OS observer first (FSEvents/inotify/ReadDirectoryChangesW),
    falls back to polling if native fails (e.g., FSEvents stream limits).
    """
    global _observer, _dispatcher
    with _watch_lock:
        if _observer is None:
            _configure_watchdog_logging()
            try:
                obs = Observer()
                obs.start()
                log.info("Using native file observer")
            except Exception as e:
                log.warning(
                    "Native observer failed (%s), falling back to polling", e
                )
                obs = PollingObserver(timeout=2.0)
                obs.start()
                log.info("Using polling file observer")
            _observer = obs
            _dispatcher = _EventDispatcher()
        assert _dispatcher is not None
        return _observer, _dispatcher


def _watch(path: Path, handler_id: int, handler_args: _HandlerInfo) -> bool:
    """Add a watch for path. Returns True on success."""
    glob, callback, debounce_s, loop = handler_args
    observer, dispatcher = _get_observer()

    with _watch_lock:
        dispatcher.add_handler(handler_id, glob, callback, debounce_s, loop)

        if path in _path_watches:
            _path_refcount[path] += 1
            return True

        try:
            watch = observer.schedule(dispatcher, str(path), recursive=True)
            _path_watches[path] = watch
            _path_refcount[path] = 1
            log.debug("Now watching: %s", path)
            return True
        except Exception as e:
            log.warning("Failed to watch %s: %s", path, e)
            return False


def _unwatch(path: Path) -> None:
    """Remove a watch for path."""
    observer, _ = _get_observer()

    with _watch_lock:
        if path not in _path_refcount:
            return

        _path_refcount[path] -= 1
        if _path_refcount[path] <= 0:
            del _path_refcount[path]
            watch = _path_watches.pop(path, None)
            if watch:
                try:
                    observer.unschedule(watch)
                    log.debug("Stopped watching: %s", path)
                except Exception:
                    pass


def _remove_handler(handler_id: int) -> None:
    """Remove handler from dispatcher."""
    _, dispatcher = _get_observer()
    dispatcher.remove_handler(handler_id)


class FileWatcher:
    """
    Native filesystem watcher using watchdog.

    Watches directories for file changes matching a glob pattern.
    Uses OS-native notifications (FSEvents on macOS, inotify on Linux).
    """

    _id_counter = 0
    _id_lock = Lock()

    def __init__(
        self,
        name: str,
        *,
        paths: Sequence[Path] | None = None,
        paths_provider: Callable[[], Sequence[Path]] | None = None,
        on_change: Callable[[FileChangeResult], Awaitable[None] | None],
        glob: str = "**/*",
        debounce_s: float = 0.5,
    ) -> None:
        if paths is None and paths_provider is None:
            raise ValueError("paths or paths_provider must be provided")

        with FileWatcher._id_lock:
            FileWatcher._id_counter += 1
            self._id = FileWatcher._id_counter

        self._name = name
        self._paths_provider = paths_provider
        self._static_paths = list(paths or [])
        self._on_change = on_change
        self._glob = glob
        self._debounce_s = debounce_s
        self._watched_paths: set[Path] = set()
        self._stop_event = asyncio.Event()

    def _resolve_paths(self) -> set[Path]:
        paths = self._paths_provider() if self._paths_provider else self._static_paths
        return {p for p in paths if p.exists()}

    async def run(self) -> None:
        """Run the file watcher until stopped."""
        loop = asyncio.get_running_loop()

        def sync_callback(result: FileChangeResult) -> None:
            async def dispatch() -> None:
                response = self._on_change(result)
                if isinstance(response, Awaitable):
                    await response
                log.info(
                    "File watcher '%s': +%d ~%d -%d",
                    self._name,
                    len(result.created),
                    len(result.changed),
                    len(result.deleted),
                )

            loop.call_soon_threadsafe(lambda: asyncio.create_task(dispatch()))

        handler_args: _HandlerInfo = (self._glob, sync_callback, self._debounce_s, loop)
        log.info("File watcher '%s' started", self._name)

        try:
            while not self._stop_event.is_set():
                new_paths = self._resolve_paths()

                for path in self._watched_paths - new_paths:
                    _unwatch(path)

                for path in new_paths - self._watched_paths:
                    _watch(path, self._id, handler_args)

                self._watched_paths = new_paths
                await asyncio.sleep(5.0)
        finally:
            for path in self._watched_paths:
                _unwatch(path)
            _remove_handler(self._id)
            self._watched_paths.clear()
            log.info("File watcher '%s' stopped", self._name)

    def stop(self) -> None:
        self._stop_event.set()
