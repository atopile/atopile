import zipfile
from pathlib import Path

from atopile.config import ProjectConfig
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
