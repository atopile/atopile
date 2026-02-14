"""Typed models for autolayout jobs and provider contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


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


@dataclass
class ProviderCapabilities:
    """Feature flags for a provider adapter."""

    supports_cancel: bool = True
    supports_candidates: bool = True
    supports_download: bool = True
    requires_manual_upload: bool = False


@dataclass
class AutolayoutCandidate:
    """A selectable layout candidate produced by a provider."""

    candidate_id: str
    label: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SubmitRequest:
    """Input contract passed from service to provider adapter."""

    job_id: str
    project_root: Path
    build_target: str
    layout_path: Path
    input_zip_path: Path
    work_dir: Path
    constraints: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    kicad_project_path: Path | None = None
    schematic_path: Path | None = None


@dataclass
class SubmitResult:
    """Provider response after initial submission."""

    external_job_id: str
    state: AutolayoutState = AutolayoutState.RUNNING
    message: str | None = None
    candidates: list[AutolayoutCandidate] = field(default_factory=list)


@dataclass
class ProviderStatus:
    """Provider status payload mapped to internal state."""

    state: AutolayoutState
    message: str | None = None
    progress: float | None = None
    candidates: list[AutolayoutCandidate] = field(default_factory=list)


@dataclass
class DownloadResult:
    """Provider download result for a specific candidate."""

    candidate_id: str
    layout_path: Path
    files: dict[str, str] = field(default_factory=dict)


@dataclass
class AutolayoutJob:
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
    constraints: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    input_zip_path: str | None = None
    work_dir: str | None = None
    layout_path: str | None = None
    selected_candidate_id: str | None = None
    applied_candidate_id: str | None = None
    applied_layout_path: str | None = None
    backup_layout_path: str | None = None
    candidates: list[AutolayoutCandidate] = field(default_factory=list)

    def mark_updated(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["candidates"] = [candidate.to_dict() for candidate in self.candidates]
        return payload


def utc_now_iso() -> str:
    """Return a compact UTC timestamp string."""

    return datetime.now(tz=UTC).isoformat(timespec="seconds")
