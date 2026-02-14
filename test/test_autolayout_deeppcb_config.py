import importlib
from pathlib import Path

import pytest


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


def test_deeppcb_api_key_falls_back_to_unprefixed_env(monkeypatch):
    monkeypatch.delenv("ATO_DEEPPCB_API_KEY", raising=False)
    monkeypatch.setenv("DEEPPCB_API_KEY", "plain-key")
    monkeypatch.setenv("FBRK_DEEPPCB_API_KEY", "fbrk-key")

    deeppcb_module = _reload_deeppcb_module()
    cfg = deeppcb_module.DeepPCBConfig.from_env()

    assert cfg.api_key == "plain-key"


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


def test_auth_headers_fall_back_to_api_key_as_bearer(monkeypatch):
    monkeypatch.setenv("ATO_DEEPPCB_API_KEY", "api-key")
    monkeypatch.delenv("ATO_DEEPPCB_BEARER_TOKEN", raising=False)

    deeppcb_module = _reload_deeppcb_module()
    provider = deeppcb_module.DeepPCBProvider()

    headers = provider._auth_headers()
    assert headers["x-deeppcb-api-key"] == "api-key"
    assert headers["Authorization"] == "Bearer api-key"


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
