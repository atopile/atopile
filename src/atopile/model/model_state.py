"""Model state - workspace path, active builds, and build lock."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


class ModelState:
    """
    Shared model state for the application.

    This provides:
    - Workspace path for project discovery
    - Active builds tracking
    - Build lock for thread-safe access
    """

    def __init__(self) -> None:
        self._workspace_path: Optional[Path] = None
        self._active_builds: dict[str, dict[str, Any]] = {}
        self._build_lock = threading.RLock()  # RLock allows reentrant locking

    def set_workspace_path(self, path: Optional[Path]) -> None:
        """Set workspace path for discovery operations."""
        self._workspace_path = path

    @property
    def workspace_path(self) -> Optional[Path]:
        """Get workspace path for discovery operations."""
        return self._workspace_path

    @property
    def active_builds(self) -> dict[str, dict[str, Any]]:
        """Get the active builds dict. Use build_lock for thread-safe access."""
        return self._active_builds

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
