"""Dev webhook gateway for exposing only the DeepPCB callback endpoint."""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

_CLOUDFLARED_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _normalize_webhook_path(path: str) -> str:
    cleaned = str(path or "").strip()
    if not cleaned:
        raise ValueError("webhook_path is required")
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned


def _normalize_base_url(base_url: str) -> str:
    cleaned = str(base_url or "").strip().rstrip("/")
    if not cleaned:
        raise ValueError("internal_base_url is required")
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        raise ValueError(
            "internal_base_url must include scheme, e.g. http://127.0.0.1:8501"
        )
    return cleaned


def _normalized_token(token: str | None) -> str | None:
    if not isinstance(token, str):
        return None
    cleaned = token.strip()
    return cleaned or None


@dataclass
class _GatewayRuntime:
    internal_base_url: str
    webhook_path: str
    gateway_host: str
    gateway_port: int
    local_webhook_url: str
    webhook_url: str
    webhook_token: str | None
    tunnel_provider: str
    cloudflared_binary: str
    started_at: str
    tunnel_public_base_url: str | None = None
    tunnel_pid: int | None = None
    tunnel_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": True,
            "internal_base_url": self.internal_base_url,
            "gateway_host": self.gateway_host,
            "gateway_port": self.gateway_port,
            "webhook_path": self.webhook_path,
            "local_webhook_url": self.local_webhook_url,
            "webhook_url": self.webhook_url,
            "webhook_token": self.webhook_token,
            "tunnel_provider": self.tunnel_provider,
            "tunnel_public_base_url": self.tunnel_public_base_url,
            "tunnel_pid": self.tunnel_pid,
            "tunnel_error": self.tunnel_error,
            "started_at": self.started_at,
            "public_exposure_scope": "webhook_path_only",
        }


class AutolayoutWebhookGatewayManager:
    """Runs a local webhook-only gateway and optional cloudflared tunnel."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runtime: _GatewayRuntime | None = None
        self._http_server: ThreadingHTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._tunnel_process: subprocess.Popen[str] | None = None
        self._tunnel_thread: threading.Thread | None = None
        self._tunnel_lines: deque[str] = deque(maxlen=80)
        self._tunnel_url_ready = threading.Event()
        self._tunnel_public_base_url: str | None = None

    def start(
        self,
        *,
        internal_base_url: str,
        webhook_path: str = "/api/autolayout/webhooks/deeppcb",
        gateway_host: str = "127.0.0.1",
        gateway_port: int = 0,
        tunnel_provider: str = "cloudflared",
        webhook_token: str | None = None,
        cloudflared_binary: str = "cloudflared",
        cloudflared_timeout_s: float = 20.0,
        forward_timeout_s: float = 20.0,
    ) -> dict[str, Any]:
        """Start gateway and return webhook configuration for DeepPCB."""
        self.stop()

        base = _normalize_base_url(internal_base_url)
        path = _normalize_webhook_path(webhook_path)
        token = _normalized_token(webhook_token)
        provider = str(tunnel_provider or "cloudflared").strip().lower()
        if provider not in {"cloudflared", "none"}:
            raise ValueError("tunnel_provider must be 'cloudflared' or 'none'")
        if not token:
            token = secrets.token_urlsafe(32)

        with self._lock:
            self._tunnel_url_ready.clear()
            self._tunnel_public_base_url = None
            self._tunnel_lines.clear()

            handler_class = self._build_handler(
                internal_base_url=base,
                webhook_path=path,
                forward_timeout_s=max(2.0, float(forward_timeout_s)),
            )
            self._http_server = ThreadingHTTPServer(
                (gateway_host, int(gateway_port)),
                handler_class,
            )
            actual_host = gateway_host
            actual_port = int(self._http_server.server_address[1])
            self._http_thread = threading.Thread(
                target=self._http_server.serve_forever,
                name="autolayout-webhook-gateway",
                daemon=True,
            )
            self._http_thread.start()

            local_webhook_url = f"http://{actual_host}:{actual_port}{path}"
            runtime = _GatewayRuntime(
                internal_base_url=base,
                webhook_path=path,
                gateway_host=actual_host,
                gateway_port=actual_port,
                local_webhook_url=local_webhook_url,
                webhook_url=local_webhook_url,
                webhook_token=token,
                tunnel_provider=provider,
                cloudflared_binary=cloudflared_binary,
                started_at=_utc_now_iso(),
            )
            self._runtime = runtime

        if provider == "cloudflared":
            public_base_url = self._start_cloudflared_locked(
                gateway_host=actual_host,
                gateway_port=actual_port,
                binary=cloudflared_binary,
                timeout_s=max(5.0, float(cloudflared_timeout_s)),
            )
            with self._lock:
                if self._runtime is None:
                    raise RuntimeError("Webhook gateway was stopped during startup.")
                self._runtime.tunnel_public_base_url = public_base_url
                self._runtime.webhook_url = f"{public_base_url}{path}"
                if self._tunnel_process is not None:
                    self._runtime.tunnel_pid = self._tunnel_process.pid

        return self.status()

    def stop(self) -> dict[str, Any]:
        """Stop any running gateway/tunnel processes."""
        with self._lock:
            runtime = self._runtime
            http_server = self._http_server
            tunnel_process = self._tunnel_process

            self._runtime = None
            self._http_server = None
            self._http_thread = None
            self._tunnel_process = None
            self._tunnel_thread = None
            self._tunnel_lines.clear()
            self._tunnel_public_base_url = None
            self._tunnel_url_ready.clear()

        if http_server is not None:
            try:
                http_server.shutdown()
            except Exception:
                log.exception("Failed shutting down webhook gateway HTTP server")
            try:
                http_server.server_close()
            except Exception:
                log.exception("Failed closing webhook gateway HTTP server")

        if tunnel_process is not None:
            self._stop_process(tunnel_process)

        return {
            "running": False,
            "stopped": runtime is not None,
        }

    def status(self) -> dict[str, Any]:
        """Return current gateway status."""
        with self._lock:
            runtime = self._runtime
            process = self._tunnel_process
            lines = list(self._tunnel_lines)

        if runtime is None:
            return {"running": False}

        payload = runtime.to_dict()
        payload["tunnel_log_tail"] = lines[-20:]
        if process is not None:
            payload["tunnel_pid"] = process.pid
            return_code = process.poll()
            payload["tunnel_return_code"] = return_code
            if return_code is not None and runtime.tunnel_error is None:
                payload["tunnel_error"] = (
                    f"cloudflared exited unexpectedly with code {return_code}"
                )
        return payload

    def _build_handler(
        self,
        *,
        internal_base_url: str,
        webhook_path: str,
        forward_timeout_s: float,
    ) -> type[BaseHTTPRequestHandler]:
        manager = self

        class _WebhookGatewayHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                request_path = urlsplit(self.path).path
                if request_path != webhook_path:
                    self.send_response(404)
                    self.send_header("content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps({"detail": "Not found"}).encode("utf-8")
                    )
                    return

                max_body_bytes = 1_048_576  # 1 MB
                content_length_raw = self.headers.get("content-length", "0")
                try:
                    content_length = max(0, int(content_length_raw))
                except ValueError:
                    content_length = 0
                if content_length > max_body_bytes:
                    self.send_response(413)
                    self.send_header("content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps({"detail": "Request body too large"}).encode("utf-8")
                    )
                    return
                body = self.rfile.read(content_length) if content_length else b""

                upstream_url = f"{internal_base_url}{webhook_path}"
                forward_headers: dict[str, str] = {}
                for key, value in self.headers.items():
                    lowered = key.lower()
                    if lowered in {
                        "host",
                        "content-length",
                        "connection",
                        "accept-encoding",
                    }:
                        continue
                    forward_headers[key] = value

                try:
                    response = requests.post(
                        upstream_url,
                        data=body,
                        headers=forward_headers,
                        timeout=forward_timeout_s,
                    )
                except Exception as exc:
                    log.warning("Webhook gateway forward failed: %s", exc)
                    self.send_response(502)
                    self.send_header("content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps({"detail": "Failed to forward webhook"}).encode(
                            "utf-8"
                        )
                    )
                    return

                response_content = response.content or b""
                response_content_type = (
                    response.headers.get("content-type") or "application/json"
                )
                self.send_response(response.status_code)
                self.send_header("content-type", response_content_type)
                self.send_header("content-length", str(len(response_content)))
                self.end_headers()
                if response_content:
                    self.wfile.write(response_content)

            def do_GET(self) -> None:  # noqa: N802
                self.send_response(404)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Not found"}).encode("utf-8"))

            def log_message(self, format: str, *args: Any) -> None:
                _ = (manager, format, args)
                return

        return _WebhookGatewayHandler

    def _start_cloudflared_locked(
        self,
        *,
        gateway_host: str,
        gateway_port: int,
        binary: str,
        timeout_s: float,
    ) -> str:
        resolved_binary = shutil.which(binary)
        if not resolved_binary:
            self.stop()
            raise RuntimeError(
                "cloudflared binary not found. Install cloudflared and ensure it is "
                "on PATH, or use tunnel_provider='none'."
            )

        command = [
            resolved_binary,
            "tunnel",
            "--url",
            f"http://{gateway_host}:{gateway_port}",
            "--no-autoupdate",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        with self._lock:
            self._tunnel_process = process

        def _drain_output() -> None:
            stream = process.stdout
            if stream is None:
                return
            for line in iter(stream.readline, ""):
                stripped = line.strip()
                if stripped:
                    with self._lock:
                        self._tunnel_lines.append(stripped)
                    match = _CLOUDFLARED_URL_RE.search(stripped)
                    if match:
                        with self._lock:
                            self._tunnel_public_base_url = match.group(0)
                            self._tunnel_url_ready.set()
            with self._lock:
                self._tunnel_url_ready.set()

        reader = threading.Thread(
            target=_drain_output,
            name="autolayout-cloudflared-reader",
            daemon=True,
        )
        with self._lock:
            self._tunnel_thread = reader
        reader.start()

        ready = self._tunnel_url_ready.wait(timeout=timeout_s)
        with self._lock:
            public_base = self._tunnel_public_base_url

        if ready and public_base:
            return public_base.rstrip("/")

        process_return_code = process.poll()
        error_logs = self._tail_logs_for_error()
        self.stop()
        raise RuntimeError(
            "Failed to establish cloudflared tunnel. "
            f"return_code={process_return_code}, logs={error_logs}"
        )

    def _tail_logs_for_error(self) -> str:
        with self._lock:
            lines = list(self._tunnel_lines)
        if not lines:
            return "no output from cloudflared"
        return " | ".join(lines[-5:])

    def _stop_process(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=3)
            return
        except Exception:
            pass
        try:
            process.kill()
            process.wait(timeout=2)
        except Exception:
            pass


_AUTOLAYOUT_WEBHOOK_GATEWAY_MANAGER = AutolayoutWebhookGatewayManager()


def get_autolayout_webhook_gateway_manager() -> AutolayoutWebhookGatewayManager:
    """Return singleton dev webhook gateway manager."""

    return _AUTOLAYOUT_WEBHOOK_GATEWAY_MANAGER


def default_internal_api_base_url() -> str:
    """Best-effort local backend base URL for webhook forwarding."""

    explicit = (
        os.getenv("ATOPILE_SERVER_BASE_URL")
        or os.getenv("ATO_SERVER_BASE_URL")
        or os.getenv("FBRK_SERVER_BASE_URL")
    )
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip().rstrip("/")

    port = os.getenv("ATOPILE_SERVER_PORT")
    if isinstance(port, str) and port.strip().isdigit():
        return f"http://127.0.0.1:{int(port.strip())}"

    return "http://127.0.0.1:8501"
