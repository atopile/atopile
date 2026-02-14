"""Base provider interface for autolayout backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    DownloadResult,
    ProviderCapabilities,
    ProviderStatus,
    SubmitRequest,
    SubmitResult,
)


class AutolayoutProvider(ABC):
    """Abstract provider contract for autolayout service."""

    name: str
    capabilities: ProviderCapabilities

    @abstractmethod
    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Submit a new provider-side autolayout job."""

    @abstractmethod
    def status(self, external_job_id: str) -> ProviderStatus:
        """Fetch current provider-side status for a job."""

    def list_candidates(self, external_job_id: str) -> list[AutolayoutCandidate]:
        """List layout candidates if provider supports candidate listing."""

        return self.status(external_job_id).candidates

    @abstractmethod
    def download_candidate(
        self,
        external_job_id: str,
        candidate_id: str,
        out_dir: Path,
        target_layout_path: Path | None = None,
    ) -> DownloadResult:
        """Download a selected candidate and return local output paths."""

    def cancel(self, external_job_id: str) -> None:
        """Cancel a provider-side job when supported."""

        if not self.capabilities.supports_cancel:
            raise RuntimeError(f"Provider '{self.name}' does not support cancellation")
