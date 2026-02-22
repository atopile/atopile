import shutil
import uuid
import os
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
    ProviderWebhookUpdate,
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
        self.submit_calls = 0

    def submit(self, request) -> SubmitResult:
        self.submit_calls += 1
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

    example_layout = Path("examples/layout_reuse/layout/sub/sub.kicad_pcb")
    (layout_dir / "default.kicad_pcb").write_text(
        example_layout.read_text(encoding="utf-8"),
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
    service.register_provider(MockAutolayoutProvider())

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


def test_autolayout_start_job_reuses_active_job_by_default(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    service = AutolayoutService()
    provider = MockAutolayoutProvider()
    service.register_provider(provider)

    job1 = service.start_job(project_root=str(project_root), build_target="default")
    job2 = service.start_job(project_root=str(project_root), build_target="default")

    assert job1.job_id == job2.job_id
    assert provider.submit_calls == 1


def test_autolayout_start_job_force_new_job_override(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    service = AutolayoutService()
    provider = MockAutolayoutProvider()
    service.register_provider(provider)

    job1 = service.start_job(project_root=str(project_root), build_target="default")
    job2 = service.start_job(
        project_root=str(project_root),
        build_target="default",
        options={"force_new_job": True},
    )

    assert job1.job_id != job2.job_id
    assert provider.submit_calls == 2


def test_autolayout_service_persists_and_restores_job_state(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    state_path = tmp_path / "autolayout_jobs_state.json"

    service = AutolayoutService(
        state_path=state_path,
    )
    service.register_provider(MockAutolayoutProvider())
    job = service.start_job(
        project_root=str(project_root),
        build_target="default",
    )
    assert state_path.exists()

    reloaded = AutolayoutService(
        state_path=state_path,
    )
    reloaded.register_provider(MockAutolayoutProvider())
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
    service.register_provider(CompletedRefreshProvider())
    service._settings.poll_provider_on_refresh = True
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


def test_autolayout_candidate_count_limit_applies_to_provider_results(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    class ManyCandidatesProvider(MockAutolayoutProvider):
        def submit(self, request) -> SubmitResult:
            self.submit_calls += 1
            external_job_id = f"mock-{uuid.uuid4().hex[:12]}"
            candidates = [
                AutolayoutCandidate(candidate_id="c1", score=0.1),
                AutolayoutCandidate(candidate_id="c2", score=0.8),
                AutolayoutCandidate(candidate_id="c3", score=0.6),
            ]
            self._jobs[external_job_id] = {
                "layout_path": request.layout_path,
                "state": AutolayoutState.AWAITING_SELECTION,
                "candidates": candidates,
            }
            return SubmitResult(
                external_job_id=external_job_id,
                state=AutolayoutState.AWAITING_SELECTION,
                message="many candidates",
                candidates=candidates,
            )

    service = AutolayoutService()
    service.register_provider(ManyCandidatesProvider())
    job = service.start_job(project_root=str(project_root), build_target="default")

    # candidate_count=2 from ato.yaml should be enforced at service boundary.
    assert [candidate.candidate_id for candidate in job.candidates] == ["c1", "c2"]


def test_autolayout_auto_apply_uses_best_score_candidate(tmp_path: Path):
    project_root = _write_test_project(tmp_path)
    ato_yaml = project_root / "ato.yaml"
    ato_yaml.write_text(
        ato_yaml.read_text(encoding="utf-8").replace(
            "      candidate_count: 2\n",
            "      candidate_count: 3\n      auto_apply: true\n",
        ),
        encoding="utf-8",
    )

    class AutoApplyProvider(MockAutolayoutProvider):
        def submit(self, request) -> SubmitResult:
            self.submit_calls += 1
            external_job_id = f"mock-{uuid.uuid4().hex[:12]}"
            candidates = [
                AutolayoutCandidate(candidate_id="low", score=0.2),
                AutolayoutCandidate(candidate_id="best", score=0.9),
            ]
            self._jobs[external_job_id] = {
                "layout_path": request.layout_path,
                "state": AutolayoutState.AWAITING_SELECTION,
                "candidates": candidates,
            }
            return SubmitResult(
                external_job_id=external_job_id,
                state=AutolayoutState.AWAITING_SELECTION,
                message="auto apply",
                candidates=candidates,
            )

    service = AutolayoutService()
    service.register_provider(AutoApplyProvider())
    job = service.start_job(project_root=str(project_root), build_target="default")

    assert job.state == AutolayoutState.COMPLETED
    assert job.applied_candidate_id == "best"


def test_autolayout_service_handles_deeppcb_webhook_updates(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    class WebhookProvider:
        name = "deeppcb"
        capabilities = ProviderCapabilities(
            supports_cancel=True,
            supports_candidates=True,
            supports_download=True,
        )

        def __init__(self) -> None:
            self.config = type("Cfg", (), {"webhook_token": None})()

        def submit(self, request):  # pragma: no cover - unused in this test
            _ = request
            raise NotImplementedError

        def status(self, external_job_id: str):  # pragma: no cover - unused
            _ = external_job_id
            raise NotImplementedError

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

        def parse_webhook(self, payload: dict):
            _ = payload
            return ProviderWebhookUpdate(
                provider_job_ref="board-123",
                request_id=None,
                token=None,
                status=ProviderStatus(
                    state=AutolayoutState.COMPLETED,
                    message="ready",
                    progress=1.0,
                    candidates=[AutolayoutCandidate(candidate_id="7")],
                ),
            )

    service = AutolayoutService(
        state_path=tmp_path / "autolayout_jobs_state.json",
    )
    service.register_provider(WebhookProvider())
    build_cfg = ProjectConfig.from_path(project_root).builds["default"]  # type: ignore[union-attr]
    job = AutolayoutJob(
        job_id="al-webhook1234",
        project_root=str(project_root.resolve()),
        build_target="default",
        provider="deeppcb",
        state=AutolayoutState.RUNNING,
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        provider_job_ref="board-123",
        layout_path=str(build_cfg.paths.layout),
        options={"webhook_token": "secret-token"},
    )
    with service._lock:
        service._jobs[job.job_id] = job

    result = service.handle_deeppcb_webhook({}, provided_token="secret-token")
    assert result["accepted"] is True
    assert result["matched"] is True
    assert result["state"] == AutolayoutState.AWAITING_SELECTION.value

    updated = service.get_job("al-webhook1234")
    assert updated.state == AutolayoutState.AWAITING_SELECTION
    assert [candidate.candidate_id for candidate in updated.candidates] == ["7"]


def test_autolayout_service_rejects_invalid_webhook_token(tmp_path: Path):
    class WebhookProvider:
        name = "deeppcb"
        capabilities = ProviderCapabilities(
            supports_cancel=True,
            supports_candidates=True,
            supports_download=True,
        )

        def __init__(self) -> None:
            self.config = type("Cfg", (), {"webhook_token": "expected-token"})()

        def submit(self, request):  # pragma: no cover - unused
            _ = request
            raise NotImplementedError

        def status(self, external_job_id: str):  # pragma: no cover - unused
            _ = external_job_id
            raise NotImplementedError

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

        def parse_webhook(self, payload: dict):
            _ = payload
            return ProviderWebhookUpdate(
                provider_job_ref="board-123",
                request_id="al-webhook1234",
                token=None,
                status=ProviderStatus(state=AutolayoutState.RUNNING),
            )

    service = AutolayoutService(
        state_path=tmp_path / "autolayout_jobs_state.json",
    )
    service.register_provider(WebhookProvider())
    with service._lock:
        service._jobs["al-webhook1234"] = AutolayoutJob(
            job_id="al-webhook1234",
            project_root=str(tmp_path),
            build_target="default",
            provider="deeppcb",
            state=AutolayoutState.RUNNING,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            provider_job_ref="board-123",
        )

    with pytest.raises(PermissionError, match="Invalid DeepPCB webhook token"):
        service.handle_deeppcb_webhook({}, provided_token="wrong-token")


def test_start_job_persists_provider_resolved_options(tmp_path: Path):
    project_root = _write_test_project(tmp_path)

    class SubmitMutatingProvider(MockAutolayoutProvider):
        def submit(self, request) -> SubmitResult:
            request.options["webhook_token"] = "generated-token"
            return super().submit(request)

    service = AutolayoutService(
        state_path=tmp_path / "autolayout_jobs_state.json",
    )
    service.register_provider(SubmitMutatingProvider())

    job = service.start_job(
        project_root=str(project_root),
        build_target="default",
    )

    assert job.options.get("webhook_token") == "generated-token"


def test_configure_deeppcb_webhook_defaults_updates_env_and_provider(
    tmp_path: Path,
    monkeypatch,
):
    class Provider:
        name = "deeppcb"
        config = type("Cfg", (), {"webhook_url": None, "webhook_token": None})()

    monkeypatch.delenv("ATO_DEEPPCB_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("ATO_DEEPPCB_WEBHOOK_TOKEN", raising=False)

    provider = Provider()
    service = AutolayoutService(
        state_path=tmp_path / "autolayout_jobs_state.json",
    )
    service.register_provider(provider)

    result = service.configure_deeppcb_webhook_defaults(
        webhook_url="https://example.com/hook",
        webhook_token="tok-configured",
    )
    assert result["webhook_url"] == "https://example.com/hook"
    assert result["webhook_token"] == "tok-configured"
    assert provider.config.webhook_url == "https://example.com/hook"
    assert provider.config.webhook_token == "tok-configured"
    os.environ.pop("ATO_DEEPPCB_WEBHOOK_URL", None)
    os.environ.pop("ATO_DEEPPCB_WEBHOOK_TOKEN", None)
