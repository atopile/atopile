"""Base class for migration steps."""

from __future__ import annotations

import os
import re
import tempfile
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path


class Topic(StrEnum):
    """Migration step categories shown as groups in the UI.

    Order here determines display order in the frontend.
    """

    mandatory = "mandatory"
    ato_language = "ato_language"
    project_config = "project_config"
    project_structure = "project_structure"


# WebSocket event names — keep in sync with frontend constants
EVENT_MIGRATION_STEP_RESULT = "migration_step_result"
EVENT_MIGRATION_RESULT = "migration_result"


class MigrationStep(ABC):
    """
    Base class for all migration steps.

    To add a new step, create a .py file in the migrations/ folder and
    subclass MigrationStep. The registry in __init__.py discovers it
    automatically — no other files need editing.

    The ``id`` is auto-generated from ``label`` (lowercased, spaces → underscores,
    non-alphanumeric stripped).  Override ``id`` explicitly if needed.
    """

    label: str
    """Short human-readable name shown in the UI."""

    description: str
    """1-2 line explanation shown below the label in the UI."""

    topic: Topic
    """Category group for the UI."""

    mandatory: bool = False
    """If True the checkbox is always selected and cannot be unchecked."""

    order: int = 100
    """Sort key within its topic group (lower = first)."""

    @classmethod
    def get_id(cls) -> str:
        """Derive a stable snake_case id from the label."""
        raw = cls.label.lower().strip()
        raw = re.sub(r"[^a-z0-9]+", "_", raw)
        return raw.strip("_")

    @abstractmethod
    async def run(self, project_path: Path) -> None:
        """
        Execute the migration step.

        Raise any exception to signal failure — the runner will catch it and
        report the error to the UI.
        """

    @staticmethod
    def atomic_write(file_path: Path, content: str) -> None:
        """Write content to file atomically via tempfile + os.replace."""
        fd, tmp_path = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as tmp:
                tmp.write(content)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, file_path)
        except BaseException:
            # Clean up the temp file on any failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # Convenience: make instances serialisable for the frontend
    def to_dict(self) -> dict:
        return {
            "id": self.get_id(),
            "label": self.label,
            "description": self.description,
            "topic": str(self.topic),
            "mandatory": self.mandatory,
            "order": self.order,
        }
