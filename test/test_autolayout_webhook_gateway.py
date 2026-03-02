import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from atopile.dataclasses import AppContext
from atopile.server.agent import tools
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
    ProviderStatus,
    ProviderWebhookUpdate,
    utc_now_iso,
)
from atopile.server.domains.autolayout.service import AutolayoutService
from atopile.server.domains.autolayout.webhook_gateway import (
    AutolayoutWebhookGatewayManager,
)


def test_webhook_gateway_forwards_only_deeppcb_path() -> None:
    received: dict[str, object] = {}

    class UpstreamHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("content-length", "0") or "0")
            body = self.rfile.read(content_length) if content_length else b""
            received["path"] = self.path
            received["body"] = body
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, format: str, *args) -> None:
            _ = (format, args)
            return

    upstream_server = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    upstream_thread = threading.Thread(target=upstream_server.serve_forever, daemon=True)
    upstream_thread.start()
    upstream_port = int(upstream_server.server_address[1])

    manager = AutolayoutWebhookGatewayManager()
    try:
        status = manager.start(
            internal_base_url=f"http://127.0.0.1:{upstream_port}",
            tunnel_provider="none",
            webhook_token="tok-test",
        )
        local_url = str(status["local_webhook_url"])
        response = requests.post(
            local_url,
            json={"state": "running"},
            headers={"x-webhook-token": "tok-test"},
            timeout=5,
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert received["path"] == "/api/autolayout/webhooks/deeppcb"
        body = received["body"]
        assert isinstance(body, bytes)
        assert json.loads(body.decode("utf-8")) == {"state": "running"}

        disallowed_url = (
            f"http://{status['gateway_host']}:{status['gateway_port']}/api/autolayout/jobs"
        )
        blocked = requests.post(disallowed_url, json={"x": 1}, timeout=5)
        assert blocked.status_code == 404
    finally:
        manager.stop()
        upstream_server.shutdown()
        upstream_server.server_close()


def test_webhook_gateway_status_and_stop() -> None:
    manager = AutolayoutWebhookGatewayManager()
    try:
        started = manager.start(
            internal_base_url="http://127.0.0.1:8501",
            tunnel_provider="none",
            webhook_token="tok-test",
        )
        assert started["running"] is True
        assert started["webhook_token"] == "tok-test"
        status = manager.status()
        assert status["running"] is True
        assert status["public_exposure_scope"] == "webhook_path_only"
    finally:
        stopped = manager.stop()
        assert stopped["running"] is False


def test_gateway_webhook_updates_job_and_agent_reads_status(
    tmp_path,
    monkeypatch,
) -> None:
    job_id = "al-webhooke2e123"
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)

    class WebhookProvider:
        name = "deeppcb"

        def __init__(self) -> None:
            self.config = type("Cfg", (), {"webhook_token": None})()

        def parse_webhook(self, payload: dict):
            _ = payload
            return ProviderWebhookUpdate(
                provider_job_ref="board-123",
                request_id=job_id,
                token=None,
                status=ProviderStatus(
                    state=AutolayoutState.COMPLETED,
                    message="ready",
                    progress=1.0,
                    candidates=[AutolayoutCandidate(candidate_id="cand-1")],
                ),
            )

    service = AutolayoutService(state_path=tmp_path / "autolayout_jobs_state.json")
    service.register_provider(WebhookProvider())
    with service._lock:
        service._jobs[job_id] = AutolayoutJob(
            job_id=job_id,
            project_root=str(project_root),
            build_target="default",
            provider="deeppcb",
            state=AutolayoutState.RUNNING,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            provider_job_ref="board-123",
            options={"webhook_token": "tok-e2e"},
        )

    class UpstreamHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("content-length", "0") or "0")
            body = self.rfile.read(content_length) if content_length else b"{}"
            payload = json.loads(body.decode("utf-8"))
            token = self.headers.get("x-webhook-token")
            result = service.handle_deeppcb_webhook(payload, provided_token=token)
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))

        def log_message(self, format: str, *args) -> None:
            _ = (format, args)
            return

    upstream_server = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    upstream_thread = threading.Thread(target=upstream_server.serve_forever, daemon=True)
    upstream_thread.start()
    upstream_port = int(upstream_server.server_address[1])

    manager = AutolayoutWebhookGatewayManager()
    monkeypatch.setattr(tools, "get_autolayout_service", lambda: service)
    try:
        start_status = manager.start(
            internal_base_url=f"http://127.0.0.1:{upstream_port}",
            tunnel_provider="none",
            webhook_token="tok-e2e",
        )
        response = requests.post(
            str(start_status["local_webhook_url"]),
            json={"event": "board.updated"},
            headers={"x-webhook-token": "tok-e2e"},
            timeout=5,
        )
        assert response.status_code == 200

        result = asyncio.run(
            tools.execute_tool(
                name="autolayout_status",
                arguments={"job_id": job_id, "refresh": False},
                project_root=Path(project_root),
                ctx=AppContext(workspace_paths=[Path(project_root)]),
            )
        )
        assert result["state"] == AutolayoutState.AWAITING_SELECTION.value
        assert result["candidate_count"] == 1
        assert result["job"]["job_id"] == job_id
    finally:
        manager.stop()
        upstream_server.shutdown()
        upstream_server.server_close()
