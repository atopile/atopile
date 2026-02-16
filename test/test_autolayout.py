import shutil
import uuid
from pathlib import Path

import pytest

from atopile.config import ProjectConfig
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
    DownloadResult,
    ProviderCapabilities,
    ProviderStatus,
    SubmitResult,
    utc_now_iso,
)
from atopile.server.domains.autolayout.service import AutolayoutService


class MockAutolayoutProvider:
    name = "mock"
    capabilities = ProviderCapabilities(
        supports_cancel=True,
        supports_candidates=True,
        supports_download=True,
    )

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, object]] = {}

    def submit(self, request) -> SubmitResult:
        external_job_id = f"mock-{uuid.uuid4().hex[:12]}"
        candidate = AutolayoutCandidate(
            candidate_id="baseline",
            label="Baseline (current layout)",
            score=1.0,
        )
        self._jobs[external_job_id] = {
            "layout_path": request.layout_path,
            "state": AutolayoutState.AWAITING_SELECTION,
            "candidates": [candidate],
        }
        return SubmitResult(
            external_job_id=external_job_id,
            state=AutolayoutState.AWAITING_SELECTION,
            message="Mock provider generated a baseline candidate",
            candidates=[candidate],
        )

    def status(self, external_job_id: str) -> ProviderStatus:
        job = self._jobs.get(external_job_id)
        if not isinstance(job, dict):
            return ProviderStatus(
                state=AutolayoutState.FAILED,
                message=f"Unknown mock job: {external_job_id}",
            )
        return ProviderStatus(
            state=job["state"],  # type: ignore[arg-type]
            message="Mock provider ready",
            progress=1.0,
            candidates=list(job["candidates"]),  # type: ignore[arg-type]
        )

    def download_candidate(
        self,
        external_job_id: str,
        candidate_id: str,
        out_dir: Path,
        target_layout_path: Path | None = None,
    ) -> DownloadResult:
        _ = target_layout_path
        job = self._jobs.get(external_job_id)
        if not isinstance(job, dict):
            raise RuntimeError(f"Unknown mock job: {external_job_id}")

        candidates = job.get("candidates")
        if not isinstance(candidates, list) or not any(
            isinstance(candidate, AutolayoutCandidate)
            and candidate.candidate_id == candidate_id
            for candidate in candidates
        ):
            raise RuntimeError(
                f"Unknown mock candidate '{candidate_id}' for job {external_job_id}"
            )

        layout_path = job.get("layout_path")
        if not isinstance(layout_path, Path):
            raise RuntimeError(f"Missing mock layout for job {external_job_id}")

        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{candidate_id}.kicad_pcb"
        shutil.copy2(layout_path, output_path)
        return DownloadResult(
            candidate_id=candidate_id,
            layout_path=output_path,
            files={"kicad_pcb": str(output_path)},
        )

    def cancel(self, external_job_id: str) -> None:
        job = self._jobs.get(external_job_id)
        if not isinstance(job, dict):
            return
        job["state"] = AutolayoutState.CANCELLED


def _write_test_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "project"
    layout_dir = project_root / "layout"
    layout_dir.mkdir(parents=True)

    (layout_dir / "default.kicad_pcb").write_text(
        "(kicad_pcb (version 20231010) (generator atopile-test))",
        encoding="utf-8",
    )
    (layout_dir / "default.kicad_pro").write_text("{}", encoding="utf-8")

    (project_root / "app.ato").write_text("module App:\n", encoding="utf-8")

    (project_root / "ato.yaml").write_text(
        "\n".join(
            [
                "requires-atopile: ^0.14.0",
                "paths:",
                "  src: ./",
                "  layout: ./layout",
                "builds:",
                "  default:",
                "    entry: app.ato:App",
                "    autolayout:",
                "      provider: mock",
                "      objective: balanced",
                "      candidate_count: 2",
                "      constraints:",
                "        preserve_keepouts: true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return project_root


def test_build_target_config_parses_autolayout(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    config = ProjectConfig.from_path(project_root)
    assert config is not None

    build_cfg = config.builds["default"]
    assert build_cfg.autolayout is not None
    assert build_cfg.autolayout.provider == "mock"
    assert build_cfg.autolayout.objective == "balanced"
    assert build_cfg.autolayout.candidate_count == 2
    assert build_cfg.autolayout.constraints["preserve_keepouts"] is True


def test_autolayout_service_mock_lifecycle(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    service = AutolayoutService()
    service._autolayout = MockAutolayoutProvider()

    job = service.start_job(
        project_root=str(project_root),
        build_target="default",
    )

    assert job.provider == "mock"
    assert job.state.value == "awaiting_selection"
    assert job.layout_path is not None

    candidates = service.list_candidates(job.job_id)
    assert len(candidates) == 1
    assert candidates[0].candidate_id == "baseline"

    applied = service.apply_candidate(job.job_id, candidate_id="baseline")
    assert applied.state.value == "completed"
    assert applied.applied_candidate_id == "baseline"
    assert applied.backup_layout_path is not None
    assert Path(applied.backup_layout_path).exists()
    assert Path(applied.layout_path or "").exists()


def test_autolayout_service_persists_and_restores_job_state(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    state_path = tmp_path / "autolayout_jobs_state.json"

    service = AutolayoutService(
        state_path=state_path,
    )
    service._autolayout = MockAutolayoutProvider()
    job = service.start_job(
        project_root=str(project_root),
        build_target="default",
    )
    assert state_path.exists()

    reloaded = AutolayoutService(
        state_path=state_path,
    )
    reloaded._autolayout = MockAutolayoutProvider()
    restored = reloaded.get_job(job.job_id)
    assert restored.job_id == job.job_id
    assert restored.project_root == job.project_root


def test_refresh_job_updates_completed_job_candidates(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    class CompletedRefreshProvider:
        name = "custom"
        capabilities = ProviderCapabilities(
            supports_cancel=False,
            supports_candidates=True,
            supports_download=False,
            requires_manual_upload=False,
        )

        def submit(self, request):  # pragma: no cover - unused in this test
            raise NotImplementedError

        def status(self, external_job_id: str) -> ProviderStatus:
            assert external_job_id == "board-123"
            return ProviderStatus(
                state=AutolayoutState.COMPLETED,
                message="done",
                candidates=[
                    AutolayoutCandidate(candidate_id="42"),
                    AutolayoutCandidate(candidate_id="41"),
                ],
            )

        def list_candidates(self, external_job_id: str):  # pragma: no cover - unused
            _ = external_job_id
            return []

        def download_candidate(  # pragma: no cover - unused
            self,
            external_job_id: str,
            candidate_id: str,
            out_dir: Path,
            target_layout_path: Path | None = None,
        ):
            _ = (external_job_id, candidate_id, out_dir, target_layout_path)
            raise NotImplementedError

        def cancel(self, external_job_id: str):  # pragma: no cover - unused
            _ = external_job_id
            raise NotImplementedError

    service = AutolayoutService(
        state_path=tmp_path / "autolayout_jobs_state.json",
    )
    service._autolayout = CompletedRefreshProvider()
    build_cfg = ProjectConfig.from_path(project_root).builds["default"]  # type: ignore[union-attr]
    job = AutolayoutJob(
        job_id="al-refresh123456",
        project_root=str(project_root.resolve()),
        build_target="default",
        provider="custom",
        state=AutolayoutState.COMPLETED,
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        provider_job_ref="board-123",
        layout_path=str(build_cfg.paths.layout),
        candidates=[AutolayoutCandidate(candidate_id="0")],
    )
    with service._lock:
        service._jobs[job.job_id] = job

    refreshed = service.refresh_job("al-refresh123456")
    assert refreshed.state == AutolayoutState.AWAITING_SELECTION
    assert [candidate.candidate_id for candidate in refreshed.candidates] == [
        "42",
        "41",
    ]
