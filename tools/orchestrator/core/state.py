"""Thread-safe state management for the orchestrator."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from ..common import get_agents_dir, get_pipelines_dir, get_sessions_dir

T = TypeVar("T", bound=BaseModel)


class StateStore(Generic[T]):
    """Thread-safe in-memory state store with optional persistence.

    Provides a simple key-value store for Pydantic models with
    thread-safe access and optional JSON file persistence.
    """

    def __init__(
        self,
        model_class: type[T],
        persist_dir: Path | None = None,
        file_suffix: str = ".json",
    ) -> None:
        """Initialize the state store.

        Args:
            model_class: The Pydantic model class for stored items
            persist_dir: Directory for persistence (None for in-memory only)
            file_suffix: File suffix for persisted files
        """
        self._model_class = model_class
        self._persist_dir = persist_dir
        self._file_suffix = file_suffix
        self._store: dict[str, T] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> T | None:
        """Get an item by key."""
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, value: T) -> None:
        """Set an item."""
        with self._lock:
            self._store[key] = value
            if self._persist_dir:
                self._persist(key, value)

    def delete(self, key: str) -> bool:
        """Delete an item. Returns True if item existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                if self._persist_dir:
                    self._delete_file(key)
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        with self._lock:
            return key in self._store

    def keys(self) -> list[str]:
        """Get all keys."""
        with self._lock:
            return list(self._store.keys())

    def values(self) -> list[T]:
        """Get all values."""
        with self._lock:
            return list(self._store.values())

    def items(self) -> list[tuple[str, T]]:
        """Get all items as (key, value) pairs."""
        with self._lock:
            return list(self._store.items())

    def count(self) -> int:
        """Get the number of items."""
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        """Clear all items."""
        with self._lock:
            self._store.clear()

    def update(self, key: str, updater: callable[[T], T]) -> T | None:
        """Atomically update an item.

        Args:
            key: The key to update
            updater: Function that takes the current value and returns the new value

        Returns:
            The updated value, or None if key doesn't exist
        """
        with self._lock:
            if key not in self._store:
                return None
            new_value = updater(self._store[key])
            self._store[key] = new_value
            if self._persist_dir:
                self._persist(key, new_value)
            return new_value

    def _persist(self, key: str, value: T) -> None:
        """Persist an item to disk."""
        if self._persist_dir is None:
            return
        file_path = self._persist_dir / f"{key}{self._file_suffix}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(value.model_dump_json(indent=2))

    def _delete_file(self, key: str) -> None:
        """Delete persisted file."""
        if self._persist_dir is None:
            return
        file_path = self._persist_dir / f"{key}{self._file_suffix}"
        if file_path.exists():
            file_path.unlink()

    def load_all(self) -> int:
        """Load all persisted items from disk.

        Returns:
            Number of items loaded
        """
        if self._persist_dir is None or not self._persist_dir.exists():
            return 0

        count = 0
        with self._lock:
            for file_path in self._persist_dir.glob(f"*{self._file_suffix}"):
                try:
                    data = json.loads(file_path.read_text())
                    key = file_path.stem
                    self._store[key] = self._model_class.model_validate(data)
                    count += 1
                except (json.JSONDecodeError, ValueError):
                    # Skip invalid files
                    pass

        return count


class AgentStateStore(StateStore):
    """State store specifically for agent states."""

    def __init__(self, persist: bool = True) -> None:
        from ..models import AgentState

        persist_dir = get_agents_dir() if persist else None
        super().__init__(AgentState, persist_dir=persist_dir)


class SessionStateStore(StateStore):
    """State store specifically for session states."""

    def __init__(self, persist: bool = True) -> None:
        from ..models import SessionState

        persist_dir = get_sessions_dir() if persist else None
        super().__init__(SessionState, persist_dir=persist_dir)


class PipelineStateStore(StateStore):
    """State store specifically for pipeline states."""

    def __init__(self, persist: bool = True) -> None:
        from ..models import PipelineState

        persist_dir = get_pipelines_dir() if persist else None
        super().__init__(PipelineState, persist_dir=persist_dir)
