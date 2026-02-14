"""Local mock provider for autolayout workflow development."""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutState,
    DownloadResult,
    ProviderCapabilities,
    ProviderStatus,
    SubmitRequest,
    SubmitResult,
)
from atopile.server.domains.autolayout.providers.base import AutolayoutProvider


@dataclass
class _MockJob:
    layout_path: Path
    state: AutolayoutState
    candidates: list[AutolayoutCandidate]


class MockAutolayoutProvider(AutolayoutProvider):
    """Predictable local provider that mirrors the current layout as one candidate."""

    name = "mock"
    capabilities = ProviderCapabilities(
        supports_cancel=True,
        supports_candidates=True,
        supports_download=True,
    )

    def __init__(self) -> None:
        self._jobs: dict[str, _MockJob] = {}

    def submit(self, request: SubmitRequest) -> SubmitResult:
        external_job_id = f"mock-{uuid.uuid4().hex[:12]}"
        candidate = AutolayoutCandidate(
            candidate_id="baseline",
            label="Baseline (current layout)",
            score=1.0,
        )
        self._jobs[external_job_id] = _MockJob(
            layout_path=request.layout_path,
            state=AutolayoutState.AWAITING_SELECTION,
            candidates=[candidate],
        )
        return SubmitResult(
            external_job_id=external_job_id,
            state=AutolayoutState.AWAITING_SELECTION,
            message="Mock provider generated a baseline candidate",
            candidates=[candidate],
        )

    def status(self, external_job_id: str) -> ProviderStatus:
        job = self._jobs.get(external_job_id)
        if job is None:
            return ProviderStatus(
                state=AutolayoutState.FAILED,
                message=f"Unknown mock job: {external_job_id}",
            )

        return ProviderStatus(
            state=job.state,
            message="Mock provider ready",
            progress=1.0,
            candidates=list(job.candidates),
        )

    def download_candidate(
        self,
        external_job_id: str,
        candidate_id: str,
        out_dir: Path,
        target_layout_path: Path | None = None,
    ) -> DownloadResult:
        job = self._jobs.get(external_job_id)
        if job is None:
            raise RuntimeError(f"Unknown mock job: {external_job_id}")

        if not any(c.candidate_id == candidate_id for c in job.candidates):
            raise RuntimeError(
                f"Unknown mock candidate '{candidate_id}' for job {external_job_id}"
            )

        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{candidate_id}.kicad_pcb"
        shutil.copy2(job.layout_path, output_path)

        return DownloadResult(
            candidate_id=candidate_id,
            layout_path=output_path,
            files={"kicad_pcb": str(output_path)},
        )

    def cancel(self, external_job_id: str) -> None:
        job = self._jobs.get(external_job_id)
        if job is None:
            return
        job.state = AutolayoutState.CANCELLED
