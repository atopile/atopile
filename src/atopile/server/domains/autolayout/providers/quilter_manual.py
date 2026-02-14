"""Manual-export provider for Quilter when API access is unavailable."""

from __future__ import annotations

from pathlib import Path

from atopile.server.domains.autolayout.models import (
    AutolayoutState,
    DownloadResult,
    ProviderCapabilities,
    ProviderStatus,
    SubmitRequest,
    SubmitResult,
)
from atopile.server.domains.autolayout.providers.base import AutolayoutProvider


class QuilterManualProvider(AutolayoutProvider):
    """Generates a package and waits for manual candidate import."""

    name = "quilter_manual"
    capabilities = ProviderCapabilities(
        supports_cancel=True,
        supports_candidates=False,
        supports_download=False,
        requires_manual_upload=True,
    )

    def submit(self, request: SubmitRequest) -> SubmitResult:
        return SubmitResult(
            external_job_id=request.job_id,
            state=AutolayoutState.AWAITING_SELECTION,
            message=(
                "Quilter has no public API. Upload the generated input package "
                "manually and import the returned board file back into atopile."
            ),
        )

    def status(self, external_job_id: str) -> ProviderStatus:
        return ProviderStatus(
            state=AutolayoutState.AWAITING_SELECTION,
            message=(
                "Manual Quilter flow: upload package in Quilter UI, then apply "
                "an imported candidate path in atopile."
            ),
        )

    def download_candidate(
        self,
        external_job_id: str,
        candidate_id: str,
        out_dir: Path,
        target_layout_path: Path | None = None,
    ) -> DownloadResult:
        raise RuntimeError(
            "Quilter manual provider does not support candidate download."
        )
