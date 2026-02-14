import zipfile
from pathlib import Path

from atopile.config import ProjectConfig
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
    ProviderCapabilities,
    ProviderStatus,
    utc_now_iso,
)
from atopile.server.domains.autolayout.providers.base import AutolayoutProvider
from atopile.server.domains.autolayout.providers import MockAutolayoutProvider
from atopile.server.domains.autolayout.service import AutolayoutService


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

    service = AutolayoutService(providers={"mock": MockAutolayoutProvider()})

    job = service.start_job(
        project_root=str(project_root),
        build_target="default",
        provider_name="mock",
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


def test_export_quilter_package_contains_constraints(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    service = AutolayoutService(providers={"mock": MockAutolayoutProvider()})
    package_path = Path(service.export_quilter_package(str(project_root), "default"))

    assert package_path.exists()
    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())

    assert "default.kicad_pcb" in names
    assert "autolayout_constraints.json" in names


def test_autolayout_service_persists_jobs_to_state_file(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    state_path = tmp_path / "autolayout_jobs_state.json"

    service = AutolayoutService(
        providers={"mock": MockAutolayoutProvider()},
        state_path=state_path,
    )
    job = service.start_job(
        project_root=str(project_root),
        build_target="default",
        provider_name="mock",
    )
    assert state_path.exists()

    reloaded = AutolayoutService(
        providers={"mock": MockAutolayoutProvider()},
        state_path=state_path,
    )
    restored = reloaded.get_job(job.job_id)
    assert restored.job_id == job.job_id
    assert restored.project_root == str(project_root.resolve())
    assert restored.provider == "mock"


def test_autolayout_service_recover_job_from_local_download(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    build_cfg = ProjectConfig.from_path(project_root).builds["default"]  # type: ignore[union-attr]

    job_id = "al-recover123456"
    work_dir = build_cfg.paths.output_base.parent / "autolayout" / job_id
    downloads_dir = work_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    (downloads_dir / "cand-local.kicad_pcb").write_text("new-layout", encoding="utf-8")

    service = AutolayoutService(
        providers={"mock": MockAutolayoutProvider()},
        state_path=tmp_path / "autolayout_jobs_state.json",
    )

    recovered = service.recover_job(str(project_root), job_id)
    assert recovered is not None
    assert recovered.job_id == job_id
    assert recovered.state == AutolayoutState.AWAITING_SELECTION
    assert recovered.candidates
    assert recovered.candidates[0].candidate_id == "cand-local"

    applied = service.apply_candidate(job_id, candidate_id="cand-local")
    assert applied.applied_candidate_id == "cand-local"
    assert Path(applied.layout_path or "").read_text(encoding="utf-8") == "new-layout"


def test_refresh_job_updates_completed_job_candidates(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    class CompletedRefreshProvider(AutolayoutProvider):
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

        def _resolve_board_ids_single(self, request_id: str):
            _ = request_id
            return ["board-123"]

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
        providers={"custom": CompletedRefreshProvider()},
        state_path=tmp_path / "autolayout_jobs_state.json",
    )
    build_cfg = ProjectConfig.from_path(project_root).builds["default"]  # type: ignore[union-attr]
    job = AutolayoutJob(
        job_id="al-refresh123456",
        project_root=str(project_root.resolve()),
        build_target="default",
        provider="custom",
        state=AutolayoutState.COMPLETED,
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        provider_job_ref=None,
        layout_path=str(build_cfg.paths.layout),
        candidates=[AutolayoutCandidate(candidate_id="0")],
    )
    with service._lock:
        service._jobs[job.job_id] = job

    refreshed = service.refresh_job("al-refresh123456")
    assert refreshed.provider_job_ref == "board-123"
    assert refreshed.state == AutolayoutState.AWAITING_SELECTION
    assert [candidate.candidate_id for candidate in refreshed.candidates] == ["42", "41"]
