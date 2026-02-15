from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .logging import get_logger


def _normalize_field(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return [_normalize_field(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_field(item) for key, item in value.items()}
    return repr(value)


def log_event(
    *,
    service: str,
    event: str,
    level: int = logging.INFO,
    logger_name: str | None = None,
    **fields: Any,
) -> None:
    logger = get_logger(logger_name or f"backend.components.{service}")
    payload: dict[str, Any] = {"service": service, "event": event}
    payload.update({key: _normalize_field(value) for key, value in fields.items()})
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
    )


def test_log_event_emits_json_payload(caplog) -> None:
    caplog.set_level(logging.INFO)
    log_event(service="components-serve", event="test", foo=123)
    message = caplog.records[-1].getMessage()
    payload = json.loads(message)
    assert payload["service"] == "components-serve"
    assert payload["event"] == "test"
    assert payload["foo"] == 123
