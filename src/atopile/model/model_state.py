"""Model state - workspace path for discovery operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional




class ModelState:
    """
    Shared model state for the application.

    This provides:
    - Workspace path for project discovery
    """

    def __init__(self) -> None:
        self._workspace_paths: list[Path] = []

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
