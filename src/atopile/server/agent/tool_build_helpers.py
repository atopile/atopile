"""Build/log normalization helpers for agent tools."""

from __future__ import annotations

from typing import Any

from atopile.dataclasses import BuildStatus
from atopile.logging import normalize_log_audience, normalize_log_levels
from atopile.model.build_queue import _build_queue

def _active_or_pending_build_ids() -> set[str]:
    state = _build_queue.get_queue_state()
    active = state.get("active", [])
    pending = state.get("pending", [])
    build_ids: set[str] = set()
    for values in (active, pending):
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value:
                build_ids.add(value)
    return build_ids


def _get_build_attr(build: Any, key: str, default: Any = None) -> Any:
    return getattr(build, key, default)


def _normalize_history_build(build: Any, active_ids: set[str]) -> dict[str, Any]:
    build_id = _get_build_attr(build, "build_id")
    status = _get_build_attr(build, "status")
    if isinstance(status, BuildStatus):
        status_value = status.value
    else:
        status_value = str(status or BuildStatus.FAILED.value)

    error = _get_build_attr(build, "error")
    if (
        isinstance(build_id, str)
        and status_value in {BuildStatus.QUEUED.value, BuildStatus.BUILDING.value}
        and build_id not in active_ids
    ):
        status_value = BuildStatus.FAILED.value
        error = error or "Build appears interrupted (not active in build queue)."

    return {
        "build_id": build_id,
        "project_root": _get_build_attr(build, "project_root"),
        "target": _get_build_attr(build, "target"),
        "status": status_value,
        "started_at": _get_build_attr(build, "started_at"),
        "elapsed_seconds": _get_build_attr(build, "elapsed_seconds", 0.0) or 0.0,
        "warnings": _get_build_attr(build, "warnings", 0) or 0,
        "errors": _get_build_attr(build, "errors", 0) or 0,
        "return_code": _get_build_attr(build, "return_code"),
        "error": error,
        "timestamp": _get_build_attr(build, "timestamp"),
    }


def _trim_message(text: str | None, limit: int = 2200) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


_DEFAULT_AGENT_BUILD_LOG_LEVELS = ["INFO", "WARNING", "ERROR", "ALERT"]


def _parse_build_log_levels(raw_levels: Any) -> list[str]:
    if raw_levels is None:
        return list(_DEFAULT_AGENT_BUILD_LOG_LEVELS)

    if isinstance(raw_levels, str):
        parsed = [
            part.strip().upper() for part in raw_levels.split(",") if part.strip()
        ]
        if not parsed:
            return list(_DEFAULT_AGENT_BUILD_LOG_LEVELS)
        normalized = normalize_log_levels(parsed)
        if normalized is None:
            raise ValueError(
                "log_levels must contain only: DEBUG, INFO, WARNING, ERROR, ALERT"
            )
        return normalized

    normalized = normalize_log_levels(raw_levels)
    if normalized is None:
        raise ValueError(
            "log_levels must contain only: DEBUG, INFO, WARNING, ERROR, ALERT"
        )
    if not normalized:
        return list(_DEFAULT_AGENT_BUILD_LOG_LEVELS)
    return normalized


def _parse_build_log_audience(raw_audience: Any) -> str | None:
    if raw_audience is None:
        return None
    if not isinstance(raw_audience, str):
        raise ValueError("audience must be one of: user, developer, agent")

    cleaned = raw_audience.strip().lower()
    if not cleaned or cleaned in {"all", "*"}:
        return None

    normalized = normalize_log_audience(cleaned)
    if normalized is None:
        raise ValueError("audience must be one of: user, developer, agent")
    return normalized


def _summarize_build_stages(build: Any | None) -> dict[str, Any] | None:
    if build is None:
        return None

    raw_stages = _get_build_attr(build, "stages", [])
    if not isinstance(raw_stages, list):
        raw_stages = []

    stage_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for raw_stage in raw_stages:
        if not isinstance(raw_stage, dict):
            continue

        name = (
            raw_stage.get("displayName")
            or raw_stage.get("name")
            or raw_stage.get("stageId")
            or raw_stage.get("stage_id")
            or ""
        )
        status = str(raw_stage.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
        elapsed = raw_stage.get("elapsedSeconds")
        if elapsed is None:
            elapsed = raw_stage.get("elapsed_seconds")

        stage_rows.append(
            {
                "name": str(name),
                "status": status,
                "elapsed_seconds": elapsed,
            }
        )

    return {
        "total_reported": _get_build_attr(build, "total_stages"),
        "observed": len(stage_rows),
        "counts": counts,
        "stages": stage_rows[:40],
    }


def _build_empty_log_stub(
    *,
    build_id: str,
    query: str,
    build: Any | None,
) -> dict[str, Any]:
    status = "unknown"
    return_code: int | None = None
    error_message = ""
    if build is not None:
        raw_status = _get_build_attr(build, "status")
        if isinstance(raw_status, BuildStatus):
            status = raw_status.value
        else:
            status = str(raw_status or "unknown")
        return_code = _get_build_attr(build, "return_code")
        error_message = _trim_message(_get_build_attr(build, "error"))

    if query:
        intro = f"No log lines matched query '{query}'."
    else:
        intro = "No log lines were captured for this build."

    details: list[str] = [f"status={status}"]
    if return_code is not None:
        details.append(f"return_code={return_code}")
    if error_message:
        details.append(f"error={error_message}")

    return {
        "timestamp": None,
        "stage": "agent_diagnostic",
        "level": "ERROR" if status == BuildStatus.FAILED.value else "INFO",
        "logger_name": "atopile.agent",
        "audience": "developer",
        "message": f"{intro} {'; '.join(details)}",
        "build_id": build_id,
        "synthetic": True,
    }
