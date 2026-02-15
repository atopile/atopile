"""Typed models for autolayout jobs and DeepPCB contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AutolayoutState(str, Enum):
    """Lifecycle state of an autolayout job."""

    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_SELECTION = "awaiting_selection"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_AUTO_LAYOUT_STATES = {
    AutolayoutState.COMPLETED,
    AutolayoutState.FAILED,
    AutolayoutState.CANCELLED,
}


class _AutolayoutModel(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


class ProviderCapabilities(_AutolayoutModel):
    """Feature flags for a provider adapter."""

    supports_cancel: bool = True
    supports_candidates: bool = True
    supports_download: bool = True
    requires_manual_upload: bool = False


class AutolayoutCandidate(_AutolayoutModel):
    """A selectable layout candidate produced by a provider."""

    candidate_id: str
    label: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    files: dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SubmitRequest(_AutolayoutModel):
    """Input contract passed from service to provider adapter."""

    job_id: str
    project_root: Path
    build_target: str
    layout_path: Path
    input_zip_path: Path
    work_dir: Path
    constraints: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    kicad_project_path: Path | None = None
    schematic_path: Path | None = None


class SubmitResult(_AutolayoutModel):
    """Provider response after initial submission."""

    external_job_id: str
    state: AutolayoutState = AutolayoutState.RUNNING
    message: str | None = None
    candidates: list[AutolayoutCandidate] = Field(default_factory=list)


class ProviderStatus(_AutolayoutModel):
    """Provider status payload mapped to internal state."""

    state: AutolayoutState
    message: str | None = None
    progress: float | None = None
    candidates: list[AutolayoutCandidate] = Field(default_factory=list)


class DownloadResult(_AutolayoutModel):
    """Provider download result for a specific candidate."""

    candidate_id: str
    layout_path: Path
    files: dict[str, str] = Field(default_factory=dict)


class AutolayoutJob(_AutolayoutModel):
    """Persistent in-memory representation of an autolayout job."""

    job_id: str
    project_root: str
    build_target: str
    provider: str
    state: AutolayoutState
    created_at: str
    updated_at: str
    provider_job_ref: str | None = None
    progress: float | None = None
    message: str | None = None
    error: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    input_zip_path: str | None = None
    work_dir: str | None = None
    layout_path: str | None = None
    selected_candidate_id: str | None = None
    applied_candidate_id: str | None = None
    applied_layout_path: str | None = None
    backup_layout_path: str | None = None
    candidates: list[AutolayoutCandidate] = Field(default_factory=list)

    def mark_updated(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ResolvedAutolayoutTargetFiles(_AutolayoutModel):
    """Typed result of resolving project/build target inputs for autolayout."""

    project_root: Path
    build_target: str
    layout_path: Path
    kicad_project_path: Path | None = None
    schematic_path: Path | None = None
    work_root: Path
    default_constraints: dict[str, Any] = Field(default_factory=dict)
    default_options: dict[str, Any] = Field(default_factory=dict)


def utc_now_iso() -> str:
    """Return a compact UTC timestamp string."""

    return datetime.now(tz=UTC).isoformat(timespec="seconds")
