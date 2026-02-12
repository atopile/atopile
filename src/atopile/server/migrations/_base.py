"""Base class for migration steps."""

from __future__ import annotations

import os
import re
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Topic:
    """Migration step category shown as a group in the UI.

    Each instance defines an id (used as the wire key), a display label,
    and a Lucide icon name rendered by the frontend.
    """

    id: str
    label: str
    icon: str  # Lucide icon name, e.g. "Package", "FileCode"

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "icon": self.icon}


class Topics:
    """All known migration topics, in display order."""

    mandatory = Topic("mandatory", "Mandatory", "Package")
    ato_language = Topic("ato_language", "Language", "FileCode")
    project_config = Topic("project_config", "Config", "Settings")
    project_structure = Topic("project_structure", "Structure", "FolderTree")

    _all: list[Topic] = [mandatory, ato_language, project_config, project_structure]

    @classmethod
    def ordered(cls) -> list[Topic]:
        return list(cls._all)


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
            "topic": self.topic.id,
            "mandatory": self.mandatory,
            "order": self.order,
        }
