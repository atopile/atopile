"""Model state - workspace path, active builds, and build lock."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from atopile.dataclasses import Build

log = logging.getLogger(__name__)


class ModelState:
    """
    Shared model state for the application.

    This provides:
    - Workspace paths for project discovery
    - Active builds tracking
    - Build lock for thread-safe access
    """

    def __init__(self) -> None:
        self._workspace_path: Optional[Path] = None
        self._workspace_paths: list[Path] = []
        self._active_builds: list[Build] = []
        self._build_lock = threading.RLock()  # RLock allows reentrant locking

    def set_workspace_paths(self, paths: list[Path]) -> None:
        """Set workspace paths for discovery operations."""
        self._workspace_paths = paths

    @property
    def workspace_paths(self) -> list[Path]:
        """Get workspace paths for discovery operations."""
        return self._workspace_paths

    # Backwards compatibility
    def set_workspace_path(self, path: Optional[Path]) -> None:
        """Set workspace path (deprecated, use set_workspace_paths)."""
        self._workspace_paths = [path] if path else []

    @property
    def workspace_path(self) -> Optional[Path]:
        """Get first workspace path (deprecated, use workspace_paths)."""
        return self._workspace_paths[0] if self._workspace_paths else None

    @property
    def active_builds(self) -> list[Build]:
        """Get the active builds list. Use build_lock for thread-safe access."""
        return self._active_builds

    def find_build(self, build_id: str) -> Build | None:
        """Find a build by ID. Must be called with build_lock held."""
        return next((b for b in self._active_builds if b.build_id == build_id), None)

    def add_build(self, build: Build) -> None:
        """Add a build. Must be called with build_lock held."""
        self._active_builds.append(build)

    def remove_build(self, build_id: str) -> bool:
        """
        Remove a build by ID. Returns True if found and removed.
        Must be called with build_lock held.
        """
        for i, build in enumerate(self._active_builds):
            if build.build_id == build_id:
                self._active_builds.pop(i)
                return True
        return False

    @property
    def build_lock(self) -> threading.RLock:
        """Get the build lock for thread-safe access to active_builds."""
        return self._build_lock

    def acquire_build_lock(
        self, timeout: float = 5.0, context: str = "unknown"
    ) -> bool:
        """
        Acquire build_lock with timeout and logging.
        Returns True if acquired, False if timed out.
        """
        log.debug(f"[LOCK] Attempting to acquire build_lock from {context}")
        acquired = self._build_lock.acquire(timeout=timeout)
        if acquired:
            log.debug(f"[LOCK] Acquired build_lock from {context}")
        else:
            log.error(
                f"[LOCK] TIMEOUT acquiring build_lock from {context} after {timeout}s"
            )
        return acquired

    def release_build_lock(self, context: str = "unknown") -> None:
        """Release build_lock with logging."""
        log.debug(f"[LOCK] Releasing build_lock from {context}")
        self._build_lock.release()


# Global singleton instance
model_state = ModelState()


def get_model_state() -> ModelState:
    """Get the global model state singleton."""
    return model_state


def reset_model_state() -> ModelState:
    """Reset the model state (used for tests)."""
    global model_state
    model_state = ModelState()
    return model_state
