import importlib
from pathlib import Path

import pytest

from faebryk.libs.kicad.fileformats import Property, kicad


def _reload_deeppcb_module():
    import atopile.server.domains.autolayout.providers.deeppcb as deeppcb_module

    return importlib.reload(deeppcb_module)


def test_deeppcb_api_key_prefers_ato_prefix(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "ato-key")
    monkeypatch.setenv("DEEPPCB_API_KEY", "plain-key")
    monkeypatch.setenv("FBRK_DEEPPCB_API_KEY", "fbrk-key")

    deeppcb_module = _reload_deeppcb_module()
    cfg = deeppcb_module.DeepPCBConfig.from_env()

    assert cfg.api_key == "ato-key"


def test_deeppcb_api_key_ignores_legacy_env_vars(monkeypatch):
    monkeypatch.delenv("ATO_DEEPPCB_API_KEY", raising=False)
    monkeypatch.setenv("DEEPPCB_API_KEY", "plain-key")
    monkeypatch.setenv("FBRK_DEEPPCB_API_KEY", "fbrk-key")

    deeppcb_module = _reload_deeppcb_module()
    cfg = deeppcb_module.DeepPCBConfig.from_env()

    assert cfg.api_key == ""


def test_deeppcb_defaults_match_public_api_paths(monkeypatch):
    monkeypatch.delenv("ATO_DEEPPCB_API_KEY", raising=False)
    monkeypatch.delenv("DEEPPCB_API_KEY", raising=False)
    monkeypatch.delenv("FBRK_DEEPPCB_API_KEY", raising=False)

    deeppcb_module = _reload_deeppcb_module()
    cfg = deeppcb_module.DeepPCBConfig.from_env()

    assert cfg.upload_path == "/api/v1/files/uploads/board-file"
    assert cfg.layout_path == "/api/v1/boards"
    assert cfg.confirm_path_template == "/api/v1/boards/{task_id}/confirm"
    assert cfg.alt_confirm_path_template == "/api/v1/user/boards/{task_id}/confirm"
    assert cfg.resume_path_template == "/api/v1/boards/{task_id}/resume"
    assert cfg.alt_resume_path_template == "/api/v1/user/boards/{task_id}/resume"
    assert cfg.request_lookup_path_template == "/api/v1/boards/requests/{request_id}"
    assert cfg.status_path_template == "/api/v1/boards/{task_id}"
    assert cfg.alt_status_path_template == "/api/v1/user/boards/{task_id}"
    assert cfg.download_path_template == "/api/v1/boards/{task_id}/revision-artifact"
    assert (
        cfg.alt_download_path_template == "/api/v1/boards/{task_id}/download-artifact"
    )
    assert cfg.cancel_path_template == "/api/v1/boards/{task_id}/stop"
    assert cfg.alt_cancel_path_template == "/api/v1/boards/{task_id}/workflow/stop"
    assert cfg.confirm_retries == 8
    assert cfg.confirm_retry_delay_s == 1.5
    assert cfg.board_ready_timeout_s == 90.0
    assert cfg.board_ready_poll_s == 2.0
    assert cfg.api_key == ""
    assert cfg.bearer_token is None
    assert cfg.webhook_url == "https://example.com/deeppcb-autolayout"
    assert cfg.webhook_token is None


def test_deeppcb_optional_bearer_token(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_BEARER_TOKEN", "bearer-token")

    deeppcb_module = _reload_deeppcb_module()
    cfg = deeppcb_module.DeepPCBConfig.from_env()

    assert cfg.bearer_token == "bearer-token"


def test_deeppcb_optional_webhook_overrides(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_WEBHOOK_URL", "https://example.com/deeppcb")
    monkeypatch.setenv("ATO_DEEPPCB_WEBHOOK_TOKEN", "token-value")

    deeppcb_module = _reload_deeppcb_module()
    cfg = deeppcb_module.DeepPCBConfig.from_env()

    assert cfg.webhook_url == "https://example.com/deeppcb"
    assert cfg.webhook_token == "token-value"


def test_extract_board_candidates_prefers_explicit_board_keys():
    import atopile.server.domains.autolayout.providers.deeppcb as deeppcb_module

    payload = {
        "id": "generic-id",
        "result": {
            "boardId": "board-uuid",
            "requestId": "req-1",
        },
    }
    assert deeppcb_module._extract_board_candidates(payload)[0] == "board-uuid"


def test_extract_board_candidates_falls_back_to_top_level_id():
    import atopile.server.domains.autolayout.providers.deeppcb as deeppcb_module

    payload = {"id": "generic-id"}
    assert deeppcb_module._extract_board_candidates(payload)[0] == "generic-id"


def test_auth_headers_do_not_use_api_key_as_bearer(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    monkeypatch.delenv("ATO_DEEPPCB_BEARER_TOKEN", raising=False)

    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    headers = provider._auth_headers()
    assert headers["x-deeppcb-api-key"] == "api-key"
    assert "Authorization" not in headers


def test_auth_headers_include_explicit_bearer(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    monkeypatch.setenv("ATO_DEEPPCB_BEARER_TOKEN", "bearer-token")

    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    headers = provider._auth_headers()
    assert headers["x-deeppcb-api-key"] == "api-key"
    assert headers["Authorization"] == "Bearer bearer-token"


def test_redact_sensitive_values():
    deeppcb_module = _reload_deeppcb_module()

    text = "error token=abc123 and key=shhh-secret"
    redacted = deeppcb_module._redact_sensitive_values(
        text,
        ("abc123", "shhh-secret", None, ""),
    )
    assert "abc123" not in redacted
    assert "shhh-secret" not in redacted
    assert "***REDACTED***" in redacted


def test_create_board_kicad_uses_kicad_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()

    board = tmp_path / "demo.kicad_pcb"
    board.write_text("pcb", encoding="utf-8")
    project = tmp_path / "demo.kicad_pro"
    project.write_text("{}", encoding="utf-8")

    request = deeppcb_module.SubmitRequest(
        job_id="al-test",
        project_root=tmp_path,
        build_target="default",
        layout_path=board,
        input_zip_path=tmp_path / "input_bundle.zip",
        work_dir=tmp_path,
        constraints={},
        options={},
        kicad_project_path=project,
        schematic_path=None,
    )

    provider = deeppcb_module.DeepPCBProvider()
    captured: dict[str, object] = {}

    def fake_request_payload(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["kwargs"] = kwargs
        return "board-uuid"

    monkeypatch.setattr(provider, "_request_payload", fake_request_payload)
    board_id = provider._create_board(request)

    assert board_id == "board-uuid"
    assert captured["method"] == "POST"
    assert captured["path"] == provider.config.layout_path
    files = captured["kwargs"]["files"]
    assert "boardInputType" in files
    assert files["boardInputType"] == (None, "Kicad")
    assert "kicadBoardFile" in files
    assert "kicadProjectFile" in files


def test_create_board_kicad_requires_project_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()

    board = tmp_path / "demo.kicad_pcb"
    board.write_text("pcb", encoding="utf-8")

    request = deeppcb_module.SubmitRequest(
        job_id="al-test",
        project_root=tmp_path,
        build_target="default",
        layout_path=board,
        input_zip_path=tmp_path / "input_bundle.zip",
        work_dir=tmp_path,
        constraints={},
        options={},
        kicad_project_path=None,
        schematic_path=None,
    )

    provider = deeppcb_module.DeepPCBProvider()
    with pytest.raises(RuntimeError, match="requires a .kicad_pro file"):
        provider._create_board(request)


def test_resume_option_parsing(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    request = deeppcb_module.SubmitRequest(
        job_id="al-test",
        project_root=Path("."),
        build_target="default",
        layout_path=Path("layout.kicad_pcb"),
        input_zip_path=Path("input_bundle.zip"),
        work_dir=Path("."),
        options={"resumeBoardId": "board-123", "resumeStopFirst": "false"},
    )

    assert provider._resume_board_id(request) == "board-123"
    assert provider._resume_stop_first(request) is False


def test_extract_workflow_statuses_and_running_detection():
    import atopile.server.domains.autolayout.providers.deeppcb as deeppcb_module

    payload = {
        "workflows": [
            {"status": "Stopped"},
            {"status": "Started"},
        ]
    }
    statuses = deeppcb_module._extract_workflow_statuses(payload)
    assert "Stopped" in statuses
    assert "Started" in statuses
    assert deeppcb_module._is_running_workflow_status("Started") is True
    assert deeppcb_module._is_running_workflow_status("Stopped") is False


def test_inject_constraints_file_url_for_placement(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    request = deeppcb_module.SubmitRequest(
        job_id="al-test",
        project_root=tmp_path,
        build_target="default",
        layout_path=tmp_path / "layout.kicad_pcb",
        input_zip_path=tmp_path / "input_bundle.zip",
        work_dir=tmp_path,
        constraints={
            "decoupling_constraints": {
                "U1-1": [{"type": "decoupled_by", "targets": ["C1-1"]}]
            }
        },
        options={"jobType": "Placement"},
    )

    monkeypatch.setattr(
        provider, "_upload_board_file", lambda _: "https://tmp/url.json"
    )
    monkeypatch.setattr(
        provider,
        "_request_payload",
        lambda *args, **kwargs: {"is_valid": True, "error": ""},
    )

    provider._inject_constraints_file_url(request)

    assert request.options["constraintsFileUrl"] == "https://tmp/url.json"
    constraints_file = tmp_path / "deeppcb_constraints.json"
    assert constraints_file.exists()
    payload = constraints_file.read_text(encoding="utf-8")
    assert "decoupling_constraints" in payload
    assert "U1-1" in payload


def test_inject_constraints_skips_non_placement(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    request = deeppcb_module.SubmitRequest(
        job_id="al-test",
        project_root=tmp_path,
        build_target="default",
        layout_path=tmp_path / "layout.kicad_pcb",
        input_zip_path=tmp_path / "input_bundle.zip",
        work_dir=tmp_path,
        constraints={"decoupling_constraints": {"U1-1": []}},
        options={"jobType": "Routing"},
    )

    provider._inject_constraints_file_url(request)
    assert "constraintsFileUrl" not in request.options


def test_inject_constraints_validation_failure_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    request = deeppcb_module.SubmitRequest(
        job_id="al-test",
        project_root=tmp_path,
        build_target="default",
        layout_path=tmp_path / "layout.kicad_pcb",
        input_zip_path=tmp_path / "input_bundle.zip",
        work_dir=tmp_path,
        constraints={
            "decoupling_constraints": {
                "U1-1": [{"type": "decoupled_by", "targets": ["BADPIN"]}]
            }
        },
        options={"jobType": "Placement"},
    )

    monkeypatch.setattr(
        provider,
        "_request_payload",
        lambda *args, **kwargs: {
            "is_valid": False,
            "error": "Target 'BADPIN' does not follow format",
        },
    )

    with pytest.raises(RuntimeError, match="constraints validation failed"):
        provider._inject_constraints_file_url(request)


def test_json_artifact_transform_applies_placement_and_routing(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    source_layout = Path(
        "test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb"
    )
    target_layout = tmp_path / "target.kicad_pcb"
    target_layout.write_text(
        source_layout.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    json_payload = {
        "components": [
            {
                "id": "D1",
                "position": {"x": 70.0, "y": 80.0},
                "rotation": 90.0,
                "side": "Bottom",
            }
        ],
        "wires": [
            {
                "net": "TEST_NET",
                "layer": "Top",
                "width": 0.25,
                "points": [{"x": 10.0, "y": 10.0}, {"x": 20.0, "y": 20.0}],
            }
        ],
        "vias": [
            {
                "net": "TEST_NET",
                "position": {"x": 20.0, "y": 20.0},
                "diameter": 0.7,
                "drill": 0.35,
            }
        ],
    }

    output_path = provider._persist_downloaded_layout(
        content=deeppcb_module.json.dumps(json_payload).encode("utf-8"),
        content_type="application/json",
        out_dir=tmp_path / "downloads",
        candidate_id="rev-1",
        target_layout_path=target_layout,
    )

    pcb_file = kicad.loads(kicad.pcb.PcbFile, output_path)
    pcb = pcb_file.kicad_pcb

    footprint = next(
        fp
        for fp in pcb.footprints
        if Property.try_get_property(fp.propertys, "Reference") == "D1"
    )
    assert footprint.layer == "B.Cu"
    assert footprint.at.x == pytest.approx(70.0)
    assert footprint.at.y == pytest.approx(80.0)
    assert footprint.at.r == pytest.approx(90.0)

    assert any(net.name == "TEST_NET" for net in pcb.nets)
    assert len(pcb.segments) >= 1
    assert len(pcb.vias) >= 1


def test_json_artifact_requires_target_layout_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    with pytest.raises(RuntimeError, match="target layout path"):
        provider._persist_downloaded_layout(
            content=b'{"components":[]}',
            content_type="application/json",
            out_dir=tmp_path / "downloads",
            candidate_id="rev-1",
            target_layout_path=None,
        )


def test_json_extractors_scale_resolution_units():
    deeppcb_module = _reload_deeppcb_module()

    payload = {
        "resolution": {"unit": "mm", "value": 1000},
        "components": [
            {
                "id": "U1",
                "position": [1000, -2500],
                "rotation": 90,
                "side": "FRONT",
            }
        ],
        "wires": [
            {
                "net": "N1",
                "layer": "F.Cu",
                "width": 200,
                "points": [[1000, -2500], [3000, -2500]],
            }
        ],
        "vias": [
            {
                "net": "N1",
                "position": [3000, -2500],
                "diameter": 600,
                "drill": 300,
            }
        ],
    }

    placements = deeppcb_module._extract_component_updates(payload)
    wires = deeppcb_module._extract_wire_updates(payload)
    vias = deeppcb_module._extract_via_updates(payload)

    assert placements[0]["x"] == pytest.approx(1.0)
    assert placements[0]["y"] == pytest.approx(-2.5)
    assert wires[0]["width"] == pytest.approx(0.2)
    assert wires[0]["points"][1][0] == pytest.approx(3.0)
    assert vias[0]["diameter"] == pytest.approx(0.6)
    assert vias[0]["drill"] == pytest.approx(0.3)


def test_infer_transform_uses_boundary_and_edge_cuts():
    deeppcb_module = _reload_deeppcb_module()
    pcb = kicad.loads(
        kicad.pcb.PcbFile,
        Path("examples/esp32_minimal/layouts/esp32_minimal/esp32_minimal.kicad_pcb"),
    ).kicad_pcb

    target_bbox = deeppcb_module._extract_edge_cuts_bbox(pcb)
    assert target_bbox is not None
    tx_min, ty_min, tx_max, ty_max = target_bbox

    # Build a synthetic DeepPCB boundary:
    # x shifted by +10mm, y mirrored and shifted by +5mm.
    sx_min = tx_min + 10.0
    sx_max = tx_max + 10.0
    sy_min = -ty_max + 5.0
    sy_max = -ty_min + 5.0
    payload = {
        "resolution": {"unit": "mm", "value": 1},
        "boundary": {
            "shape": {
                "type": "polyline",
                "points": [
                    [sx_min, sy_min],
                    [sx_max, sy_min],
                    [sx_max, sy_max],
                    [sx_min, sy_max],
                    [sx_min, sy_min],
                ],
            }
        },
    }

    transform = deeppcb_module._infer_json_to_kicad_transform(payload, pcb)
    ax, bx, ay, by = transform
    assert ax == pytest.approx(1.0)
    assert bx == pytest.approx(-10.0)
    assert ay == pytest.approx(-1.0)
    assert by == pytest.approx(5.0)
