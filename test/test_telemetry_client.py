from __future__ import annotations

import time
import uuid
from typing import Any

import pytest

from atopile import telemetry


@pytest.mark.timeout(2)
def test_capture_converts_distinct_id(monkeypatch):
    sent: list[tuple[str, dict[str, Any]]] = []

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

    class DummyClient:
        def __init__(self, calls: list[tuple[str, dict[str, Any]]]):
            self._calls = calls

        def post(self, url: str, json: dict[str, Any], timeout: float) -> DummyResponse:
            self._calls.append((url, json))
            return DummyResponse()

    def fake_http_client(*, headers: dict[str, str] | None = None):
        class _Context:
            def __enter__(self) -> DummyClient:
                return DummyClient(sent)

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        return _Context()

    monkeypatch.setattr(telemetry, "http_client", fake_http_client)

    client = telemetry.TelemetryClient(api_key="key", host="https://example.com")
    try:
        client.capture("event", distinct_id=uuid.uuid4(), properties={"foo": "bar"})
        time.sleep(0.2)
        client.flush(0.5)
    finally:
        client.flush(0)

    assert sent, "expected telemetry event to be sent"
    url, payload = sent[0]
    assert url.endswith("/capture/")
    assert payload["api_key"] == "key"
    assert payload["event"] == "event"
    assert payload["properties"] == {"foo": "bar"}
    assert isinstance(payload["distinct_id"], str)
