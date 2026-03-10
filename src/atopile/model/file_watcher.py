"""Native filesystem watcher using watchdog with shared observer."""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from atopile.dataclasses import FileNode

log = logging.getLogger(__name__)


def _configure_watchdog_logging() -> None:
    for name in (
        "watchdog",
        "watchdog.events",
        "watchdog.observers",
        "watchdog.observers.fsevents",
        "watchdog.observers.inotify_buffer",
        "watchdog.observers.polling",
        "fsevents",
    ):
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        logger.disabled = True


_IGNORED_DIR_NAMES = frozenset(
    {
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
    }
)

_IGNORED_FILE_NAMES = frozenset(
    {
        ".DS_Store",
    }
)

_TRACK_DIR_EVENTS = frozenset(
    {
        ".ato",
        ".git",
    }
)

# Shared dispatcher must admit all files because tree watchers need to observe
# arbitrary additions/removals, including extensionless files. Per-watcher glob
# matching still narrows events before callbacks fire.
_WATCH_PATTERNS = ["*"]

# Ignore patterns for watchdog (applied early, skips contents of ignored directories)
# Note: We only ignore contents (*/{name}/*), not the directories themselves,
# so we can detect when tracked directories like .ato and .git are created/deleted
_IGNORE_PATTERNS = [
    *(f"*/{name}/*" for name in _IGNORED_DIR_NAMES),
    *(name for name in _IGNORED_FILE_NAMES),
    *(f"*/{name}" for name in _IGNORED_FILE_NAMES),
]

_WATCHER_TIMEOUT_SECONDS = 0.1


@dataclass
class FileChangeResult:
    """Watcher callback payload."""

    created: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    changed: list[Path] = field(default_factory=list)
    tree: list[dict] | None = None

    def __bool__(self) -> bool:
        return bool(self.created or self.deleted or self.changed or self.tree)


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
            ignore_directories=False,  # Allow directory events for tracked dirs
            case_sensitive=False,
        )
        self._lock = Lock()
        self._handlers: dict[int, _HandlerInfo] = {}
        self._pending: dict[int, FileChangeResult] = {}
        self._timers: dict[int, asyncio.TimerHandle] = {}
        self._file_hashes: dict[Path, str] = {}

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

    def update_hash(self, path: Path) -> None:
        """Update the stored hash for a file we just wrote ourselves,
        so the next change event for this file is correctly ignored."""
        h = self._hash_file(path)
        if h is not None:
            self._file_hashes[path] = h

    def _matches(self, glob: str, path: str) -> bool:
        return fnmatch.fnmatch(path, glob) or fnmatch.fnmatch(
            Path(path).name, glob.split("/")[-1]
        )

    def _dispatch(self, path_str: str, event_type: str) -> None:
        path = Path(path_str)
        if FileWatcher._is_ignored(path, allow_tracked_dirs=True):
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

                    # Filter by content hash — only report files
                    # whose content actually changed.
                    result = self._filter_by_hash(result)

                    if result.created or result.changed or result.deleted:
                        sample = (
                            result.created[:2] + result.changed[:2] + result.deleted[:2]
                        )
                        log.debug(
                            "File watcher triggered: %s created, %s changed, %s deleted",  # noqa: E501
                            len(result.created),
                            len(result.changed),
                            len(result.deleted),
                        )
                        log.debug(
                            "File watcher sample: %s",
                            ", ".join(str(p) for p in sample[:3]),
                        )
                        cb(result)

                self._timers[hid] = loop.call_later(debounce_s, fire)

    def _should_process_event(self, event: FileSystemEvent) -> bool:
        """Check if we should process this event.

        For files: always process (filtering done by patterns)
        For directories: process create/delete/move so tree watchers can update
        structure.
        """
        return True

    def on_created(self, event: FileSystemEvent) -> None:
        if self._should_process_event(event):
            self._dispatch(self._path_str(event.src_path), "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if self._should_process_event(event):
            self._dispatch(self._path_str(event.src_path), "deleted")

    def on_modified(self, event: FileSystemEvent) -> None:
        # Don't track directory modifications, only files
        if not event.is_directory:
            self._dispatch(self._path_str(event.src_path), "changed")

    def on_moved(self, event: FileSystemEvent) -> None:
        if not self._should_process_event(event):
            return
        self._dispatch(self._path_str(event.src_path), "deleted")
        if hasattr(event, "dest_path"):
            self._dispatch(self._path_str(event.dest_path), "created")

    @staticmethod
    def _path_str(path: str | bytes) -> str:
        return path.decode() if isinstance(path, bytes) else path

    @staticmethod
    def _hash_file(path: Path) -> str | None:
        """Return SHA-256 hex digest of a file, or None if unreadable."""
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, IOError):
            return None

    def _filter_by_hash(self, result: FileChangeResult) -> FileChangeResult:
        """Drop 'changed' entries whose content hash hasn't actually changed.

        Also updates stored hashes for created/changed files and removes
        hashes for deleted files.
        """
        truly_changed: list[Path] = []
        for p in result.changed:
            new_hash = self._hash_file(p)
            if new_hash is None:
                continue
            old_hash = self._file_hashes.get(p)
            if old_hash != new_hash:
                self._file_hashes[p] = new_hash
                truly_changed.append(p)

        for p in result.created:
            h = self._hash_file(p)
            if h is not None:
                self._file_hashes[p] = h

        for p in result.deleted:
            self._file_hashes.pop(p, None)

        return FileChangeResult(
            created=result.created,
            deleted=result.deleted,
            changed=truly_changed,
        )


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
                obs = Observer(timeout=_WATCHER_TIMEOUT_SECONDS)
                obs.start()
                log.info("Using native file observer")
            except Exception as e:
                log.warning("Native observer failed (%s), falling back to polling", e)
                obs = PollingObserver(timeout=_WATCHER_TIMEOUT_SECONDS)
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
        on_change: Callable[[FileChangeResult], Awaitable[None] | None] | None = None,
        glob: str = "**/*",
        debounce_s: float = 0.5,
        mode: Literal["changes", "tree"] = "changes",
    ) -> None:
        if paths is None and paths_provider is None:
            raise ValueError("paths or paths_provider must be provided")
        if on_change is None:
            raise ValueError("on_change must be provided")

        with FileWatcher._id_lock:
            FileWatcher._id_counter += 1
            self._id = FileWatcher._id_counter

        self._name = name
        self._paths_provider = paths_provider
        self._static_paths = list(paths or [])
        self._mode = mode
        self._on_change = on_change
        self._glob = glob
        self._debounce_s = debounce_s
        self._watched_paths: set[Path] = set()
        self._stop_event = asyncio.Event()
        self._wake_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._tree: list[FileNode] | None = None

    @staticmethod
    def _is_ignored(path: Path, *, allow_tracked_dirs: bool = False) -> bool:
        """Return whether a path should be excluded from watch/scanning logic."""
        if path.name in _IGNORED_FILE_NAMES:
            return True
        parts = path.parts
        for i, part in enumerate(parts):
            if part in _IGNORED_DIR_NAMES:
                if (
                    allow_tracked_dirs
                    and i == len(parts) - 1
                    and part in _TRACK_DIR_EVENTS
                ):
                    return False
                return True
        return False

    @staticmethod
    def _scan_tree(dir_path: Path) -> list[FileNode]:
        nodes: list[FileNode] = []
        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            log.debug("Permission denied: %s", dir_path)
            return nodes

        for entry in entries:
            if FileWatcher._is_ignored(entry):
                continue
            if entry.is_dir():
                nodes.append(
                    FileNode(name=entry.name, children=FileWatcher._scan_tree(entry))
                )
            elif entry.is_file():
                nodes.append(FileNode(name=entry.name))
        FileWatcher._sort_tree(nodes)
        return nodes

    @staticmethod
    def _serialize_tree(nodes: list[FileNode]) -> list[dict]:
        return [node.model_dump(by_alias=True) for node in nodes]

    @staticmethod
    def _sort_tree(nodes: list[FileNode]) -> None:
        nodes.sort(
            key=lambda node: (0 if node.children is not None else 1, node.name.lower())
        )

    @staticmethod
    def _find_node(
        nodes: list[FileNode], name: str
    ) -> tuple[int, FileNode] | tuple[None, None]:
        for index, node in enumerate(nodes):
            if node.name == name:
                return index, node
        return None, None

    @staticmethod
    def _snapshot_path(path: Path) -> FileNode | None:
        if FileWatcher._is_ignored(path) or not path.exists():
            return None
        if path.is_dir():
            return FileNode(name=path.name, children=FileWatcher._scan_tree(path))
        if path.is_file():
            return FileNode(name=path.name)
        return None

    @staticmethod
    def _set_tree_path(
        tree: list[FileNode], parts: tuple[str, ...], node: FileNode | None
    ) -> bool:
        if not parts:
            return False
        name = parts[0]
        index, existing = FileWatcher._find_node(tree, name)

        if len(parts) == 1:
            if node is None:
                if index is None:
                    return False
                tree.pop(index)
                return True
            if existing == node:
                return False
            if index is None:
                tree.append(node)
                FileWatcher._sort_tree(tree)
            else:
                tree[index] = node
            return True

        if existing is None or existing.children is None:
            existing = FileNode(name=name, children=[])
            if index is None:
                tree.append(existing)
                FileWatcher._sort_tree(tree)
            else:
                tree[index] = existing

        return FileWatcher._set_tree_path(existing.children, parts[1:], node)

    def _tree_parts(self, path: Path) -> tuple[str, ...] | None:
        root = self._get_tree_root()
        if root is None:
            return None
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            return None
        return tuple(part for part in relative.parts if part not in ("", "."))

    def _apply_tree_changes(self, result: FileChangeResult) -> bool:
        if self._tree is None:
            return False

        changed = False
        if result.created or result.deleted:
            log.info(
                "File watcher '%s' tree update created=%s deleted=%s",
                self._name,
                [str(path) for path in result.created[:5]],
                [str(path) for path in result.deleted[:5]],
            )
        for path in result.deleted:
            parts = self._tree_parts(path)
            if parts:
                changed = FileWatcher._set_tree_path(self._tree, parts, None) or changed

        for path in result.created:
            parts = self._tree_parts(path)
            if not parts:
                continue
            node = FileWatcher._snapshot_path(path)
            if node is not None:
                changed = FileWatcher._set_tree_path(self._tree, parts, node) or changed

        return changed

    def _resolve_paths(self) -> set[Path]:
        paths = self._paths_provider() if self._paths_provider else self._static_paths
        return {p for p in paths if p.exists()}

    def _get_tree_root(self) -> Path | None:
        paths = self._paths_provider() if self._paths_provider else self._static_paths
        return paths[0] if paths else None

    async def watch(self, paths: Sequence[Path] | None = None) -> None:
        if paths is not None:
            self._static_paths = list(paths)
            self._wake_event.set()

        if self._task is None or self._task.done():
            if self._stop_event.is_set():
                self._stop_event = asyncio.Event()
                self._wake_event = asyncio.Event()
            self._task = asyncio.create_task(self._run())

        if self._mode == "tree":
            root = self._get_tree_root()
            self._tree = await asyncio.to_thread(self._scan_tree, root) if root else []
            await self._emit_tree()

    async def _run(self) -> None:
        """Run the file watcher until stopped."""
        loop = asyncio.get_running_loop()

        def sync_callback(result: FileChangeResult) -> None:
            async def dispatch() -> None:
                if self._mode == "tree":
                    if self._apply_tree_changes(result):
                        await self._emit_tree()
                else:
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
                self._wake_event.clear()
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass
        finally:
            for path in self._watched_paths:
                _unwatch(path)
            _remove_handler(self._id)
            self._watched_paths.clear()
            log.info("File watcher '%s' stopped", self._name)

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    def notify_saved(self, path: Path) -> None:
        """Tell the watcher we just wrote this file ourselves.

        Updates the content hash so the resulting filesystem event
        is correctly recognised as unchanged and suppressed.
        """
        _, dispatcher = _get_observer()
        dispatcher.update_hash(path.resolve())

    async def _emit_tree(self) -> None:
        if self._mode != "tree":
            raise RuntimeError(
                "_emit_tree() is only supported for tree-mode FileWatcher"
            )
        log.info(
            "File watcher '%s' emitting tree root_entries=%d",
            self._name,
            len(self._tree or []),
        )
        response = self._on_change(
            FileChangeResult(tree=FileWatcher._serialize_tree(self._tree or []))
        )
        if isinstance(response, Awaitable):
            await response
