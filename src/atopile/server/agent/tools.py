"""Typed agent tools for atopile operations."""

from __future__ import annotations

import asyncio
import difflib
import json
import math
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from atopile.config import ProjectConfig
from atopile.dataclasses import (
    AddBuildTargetRequest,
    AppContext,
    BuildRequest,
    BuildStatus,
    UpdateBuildTargetRequest,
)
from atopile.logging import (
    load_build_logs,
    normalize_log_audience,
    normalize_log_levels,
)
from atopile.model import builds as builds_domain
from atopile.model.build_queue import _build_queue
from atopile.model.sqlite import BuildHistory
from atopile.server import module_introspection
from atopile.server.agent import policy
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import manufacturing as manufacturing_domain
from atopile.server.domains import packages as packages_domain
from atopile.server.domains import parts_search as parts_domain
from atopile.server.domains import problems as problems_domain
from atopile.server.domains import projects as projects_domain
from atopile.server.domains import stdlib as stdlib_domain
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
)
from atopile.server.domains.autolayout.service import get_autolayout_service
from atopile.server.path_utils import resolve_layout_path

_openai_file_client: AsyncOpenAI | None = None
_OPENAI_FILE_CACHE_MAX_ENTRIES = max(
    256,
    min(
        int(os.getenv("ATOPILE_AGENT_OPENAI_FILE_CACHE_MAX_ENTRIES", "4096")),
        200_000,
    ),
)
_DATASHEET_READ_CACHE_MAX_ENTRIES = max(
    256,
    min(
        int(os.getenv("ATOPILE_AGENT_DATASHEET_READ_CACHE_MAX_ENTRIES", "4096")),
        200_000,
    ),
)
_openai_file_cache: OrderedDict[str, str] = OrderedDict()
_datasheet_read_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
_EXPECTED_MANUFACTURING_OUTPUT_KEYS: tuple[str, ...] = (
    "gerbers",
    "bom_json",
    "bom_csv",
    "pick_and_place",
    "step",
    "glb",
    "kicad_pcb",
    "kicad_sch",
    "pcb_summary",
)
_AUTOLAYOUT_MAX_TIMEOUT_MINUTES = 2
_PACKAGE_REFERENCE_MAX_FILES_SCANNED = int(
    os.getenv("ATOPILE_AGENT_PACKAGE_REFERENCE_MAX_FILES_SCANNED", "5000")
)
_PACKAGE_REFERENCE_MAX_FILES_SCANNED = max(
    200,
    min(_PACKAGE_REFERENCE_MAX_FILES_SCANNED, 200_000),
)


def _datasheet_cache_key(*, project_root: Path, source_type: str, source: str) -> str:
    root = str(project_root.resolve())
    return f"{root}|{source_type}:{source.strip()}"


def _cache_get_lru[T](cache: OrderedDict[str, T], key: str) -> T | None:
    value = cache.get(key)
    if value is None:
        return None
    cache.move_to_end(key)
    return value


def _cache_set_lru[T](
    cache: OrderedDict[str, T],
    key: str,
    value: T,
    *,
    max_entries: int,
) -> None:
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > max_entries:
        cache.popitem(last=False)


def _datasheet_cache_keys(
    *,
    project_root: Path,
    lcsc_id: str | None = None,
    url: str | None = None,
    path: str | None = None,
    source_kind: str | None = None,
    source: str | None = None,
) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()

    def add(source_type: str, value: str | None) -> None:
        if not value:
            return
        key = _datasheet_cache_key(
            project_root=project_root,
            source_type=source_type,
            source=value,
        )
        if key in seen:
            return
        seen.add(key)
        keys.append(key)

    if lcsc_id:
        add("lcsc_id", lcsc_id.upper())
    if url:
        add("url", url)
    if path:
        add("path", path)
    if source_kind and source:
        add(source_kind, source)

    return keys


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


def _get_openai_file_client() -> AsyncOpenAI:
    global _openai_file_client
    if _openai_file_client is not None:
        return _openai_file_client

    api_key = os.getenv("ATOPILE_AGENT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set ATOPILE_AGENT_OPENAI_API_KEY or OPENAI_API_KEY."
        )

    base_url = os.getenv("ATOPILE_AGENT_BASE_URL", "https://api.openai.com/v1")
    timeout_s = float(os.getenv("ATOPILE_AGENT_TIMEOUT_S", "120"))
    _openai_file_client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_s,
    )
    return _openai_file_client


def _extract_openai_api_error(exc: APIStatusError) -> str:
    response = getattr(exc, "response", None)
    response_text = getattr(response, "text", None)
    if isinstance(response_text, str) and response_text:
        return response_text
    body = getattr(exc, "body", None)
    if body is None:
        return str(exc)
    try:
        return json.dumps(body)
    except TypeError:
        return str(body)


async def _upload_openai_user_file(
    *,
    filename: str,
    content: bytes,
    cache_key: str,
) -> tuple[str, bool]:
    cached = _cache_get_lru(_openai_file_cache, cache_key)
    if cached:
        return cached, True

    client = _get_openai_file_client()
    try:
        uploaded = await client.files.create(
            file=(filename, content, "application/pdf"),
            purpose="user_data",
            expires_after={
                "anchor": "created_at",
                "seconds": 7 * 24 * 60 * 60,
            },
        )
    except APIStatusError as exc:
        snippet = _extract_openai_api_error(exc)[:500]
        status_code = getattr(exc, "status_code", "unknown")
        raise RuntimeError(
            f"OpenAI files.create failed ({status_code}): {snippet}"
        ) from exc
    except (APIConnectionError, APITimeoutError) as exc:
        raise RuntimeError(f"OpenAI files.create failed: {exc}") from exc

    file_id = str(getattr(uploaded, "id", "") or "")
    if not file_id:
        raise RuntimeError("OpenAI files.create returned no file id")

    _cache_set_lru(
        _openai_file_cache,
        cache_key,
        file_id,
        max_entries=_OPENAI_FILE_CACHE_MAX_ENTRIES,
    )
    return file_id, False


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


def _count_modules_by_type(modules: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for module in modules:
        module_type = module.get("type")
        if not isinstance(module_type, str):
            continue
        counts[module_type] = counts.get(module_type, 0) + 1
    return counts


def _count_module_children(children: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    stack = list(children)
    while stack:
        child = stack.pop()
        item_type = getattr(child, "item_type", None)
        if isinstance(item_type, str):
            counts[item_type] = counts.get(item_type, 0) + 1
        nested = getattr(child, "children", None)
        if isinstance(nested, list):
            stack.extend(nested)
    return counts


def _build_artifact_summary(
    data: Any,
    *,
    preferred_list_keys: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"shape": type(data).__name__}

    top_level_keys = [str(key) for key in data.keys()][:30]
    list_lengths: dict[str, int] = {}
    for key, value in data.items():
        if isinstance(value, list):
            list_lengths[str(key)] = len(value)

    records_key: str | None = None
    records_count: int | None = None
    sample_fields: list[str] = []

    for key in preferred_list_keys:
        value = data.get(key)
        if isinstance(value, list):
            records_key = key
            records_count = len(value)
            if value and isinstance(value[0], dict):
                sample_fields = [str(field) for field in value[0].keys()][:20]
            break

    if records_key is None and list_lengths:
        records_key = next(iter(list_lengths))
        records_count = list_lengths[records_key]
        maybe_rows = data.get(records_key)
        if (
            isinstance(maybe_rows, list)
            and maybe_rows
            and isinstance(maybe_rows[0], dict)
        ):
            sample_fields = [str(field) for field in maybe_rows[0].keys()][:20]

    return {
        "shape": "dict",
        "top_level_keys": top_level_keys,
        "records_key": records_key,
        "records_count": records_count,
        "list_lengths": list_lengths,
        "sample_fields": sample_fields,
    }


def _manufacturing_outputs_dict(outputs: Any) -> dict[str, Any]:
    return {
        "gerbers": getattr(outputs, "gerbers", None),
        "bom_json": getattr(outputs, "bom_json", None),
        "bom_csv": getattr(outputs, "bom_csv", None),
        "pick_and_place": getattr(outputs, "pick_and_place", None),
        "step": getattr(outputs, "step", None),
        "glb": getattr(outputs, "glb", None),
        "kicad_pcb": getattr(outputs, "kicad_pcb", None),
        "kicad_sch": getattr(outputs, "kicad_sch", None),
        "pcb_summary": getattr(outputs, "pcb_summary", None),
    }


def _present_output_keys(outputs: dict[str, Any]) -> list[str]:
    return [
        key
        for key in _EXPECTED_MANUFACTURING_OUTPUT_KEYS
        if isinstance(outputs.get(key), str) and str(outputs.get(key)).strip()
    ]


def _resolve_build_target(project_root: Path, build_target: str) -> Any:
    project_cfg = ProjectConfig.from_path(project_root)
    if project_cfg is None:
        raise ValueError(f"No ato.yaml found in: {project_root}")
    build_cfg = project_cfg.builds.get(build_target)
    if build_cfg is None:
        known = ", ".join(sorted(project_cfg.builds.keys()))
        raise ValueError(f"Unknown build target '{build_target}'. Available: {known}")
    return build_cfg


def _extract_candidate_id(candidate: Any) -> str | None:
    if isinstance(candidate, AutolayoutCandidate):
        return candidate.candidate_id
    if isinstance(candidate, dict):
        raw = candidate.get("candidate_id") or candidate.get("candidateId")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None
    raw = getattr(candidate, "candidate_id", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _extract_candidate_score(candidate: Any) -> float | None:
    if isinstance(candidate, AutolayoutCandidate):
        return candidate.score
    if isinstance(candidate, dict):
        raw = candidate.get("score")
        if isinstance(raw, (int, float)):
            return float(raw)
        return None
    raw = getattr(candidate, "score", None)
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _autolayout_state_value(raw: Any) -> str:
    if isinstance(raw, AutolayoutState):
        return raw.value
    if isinstance(raw, str):
        return raw
    return str(raw or "")


def _recommended_autolayout_check_back_seconds(
    *,
    state: str,
    candidate_count: int,
) -> int:
    state_clean = state.strip().lower()
    if state_clean == AutolayoutState.QUEUED.value:
        return 20
    if state_clean == AutolayoutState.RUNNING.value and candidate_count <= 0:
        return 15
    if state_clean == AutolayoutState.RUNNING.value and candidate_count > 0:
        return 10
    return 10


def _autolayout_recommended_action(
    *,
    state_value: str,
    candidate_count: int,
    provider_job_ref: str | None,
) -> str:
    if state_value in {AutolayoutState.QUEUED.value, AutolayoutState.RUNNING.value}:
        return "continue_monitoring"
    if candidate_count > 0:
        return "fetch_candidate_to_layout"
    if state_value == AutolayoutState.FAILED.value:
        return "retry_or_resume_with_adjusted_options"
    if provider_job_ref:
        return "resume_with_additional_timeout"
    return "inspect_job_details"


def _summarize_autolayout_job(job: AutolayoutJob) -> dict[str, Any]:
    state_value = _autolayout_state_value(job.state)
    candidate_count = len(job.candidates)
    return {
        "job_id": job.job_id,
        "build_target": job.build_target,
        "provider": job.provider,
        "provider_job_ref": job.provider_job_ref,
        "state": state_value,
        "updated_at": job.updated_at,
        "created_at": job.created_at,
        "candidate_count": candidate_count,
        "selected_candidate_id": job.selected_candidate_id,
        "applied_candidate_id": job.applied_candidate_id,
        "recommended_action": _autolayout_recommended_action(
            state_value=state_value,
            candidate_count=candidate_count,
            provider_job_ref=job.provider_job_ref,
        ),
    }


def _select_latest_fetchable_job(jobs: list[AutolayoutJob]) -> AutolayoutJob | None:
    if not jobs:
        return None
    preferred_states = {
        AutolayoutState.AWAITING_SELECTION.value,
        AutolayoutState.COMPLETED.value,
    }
    for job in jobs:
        state_value = _autolayout_state_value(job.state)
        if state_value in preferred_states and (
            job.candidates or isinstance(job.provider_job_ref, str)
        ):
            return job
    for job in jobs:
        state_value = _autolayout_state_value(job.state)
        if state_value in {
            AutolayoutState.QUEUED.value,
            AutolayoutState.RUNNING.value,
        }:
            continue
        return job
    return jobs[0]


def _choose_autolayout_candidate_id(
    *,
    candidates: list[Any],
    requested_id: str | None,
) -> str | None:
    if requested_id:
        return requested_id
    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda item: (
            _extract_candidate_score(item)
            if _extract_candidate_score(item) is not None
            else float("-inf")
        ),
        reverse=True,
    )
    chosen = _extract_candidate_id(ranked[0])
    if chosen:
        return chosen
    return _extract_candidate_id(candidates[0])


def _safe_name_token(value: str, *, fallback: str) -> str:
    token = "".join(
        char if char.isalnum() or char in {".", "_", "-"} else "_"
        for char in value.strip()
    ).strip("._-")
    if not token:
        return fallback
    return token[:120]


def _archive_autolayout_iteration(
    *,
    source_layout: Path,
    destination_layout_dir: Path,
    layout_stem: str,
    build_target: str,
    job_id: str,
    candidate_id: str,
) -> Path:
    archive_dir = destination_layout_dir / "autolayout_iterations"
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_target = _safe_name_token(build_target, fallback="target")
    safe_job = _safe_name_token(job_id, fallback="job")
    safe_candidate = _safe_name_token(candidate_id, fallback="candidate")

    archive_path = archive_dir / (
        f"{layout_stem}.{safe_target}.{safe_job}.{safe_candidate}.{timestamp}.kicad_pcb"
    )
    shutil.copy2(source_layout, archive_path)
    return archive_path


def _discover_downloaded_artifacts(
    *,
    downloads_dir: Path,
    candidate_id: str,
) -> dict[str, str]:
    if not downloads_dir.exists():
        return {}

    artifacts: dict[str, str] = {}

    # Prefer candidate-id-prefixed artifacts, then fallback to the newest file
    # by suffix for provider responses that do not preserve candidate_id in name.
    def _pick_path(suffix: str) -> Path | None:
        preferred = downloads_dir / f"{candidate_id}{suffix}"
        if preferred.exists():
            return preferred

        matches = sorted(
            downloads_dir.glob(f"*{suffix}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]
        return None

    for key, suffix in (
        ("kicad_pcb", ".kicad_pcb"),
        ("zip", ".zip"),
    ):
        chosen = _pick_path(suffix)
        if chosen is not None:
            artifacts[key] = str(chosen)

    return artifacts


def _expected_screenshot_outputs(
    *,
    project_root: Path,
    target: str,
    view: str,
) -> dict[str, Any]:
    build_cfg = _resolve_build_target(project_root, target)
    output_base = build_cfg.paths.output_base

    want_2d = view in {"2d", "both"}
    want_3d = view in {"3d", "both"}

    outputs: dict[str, Any] = {
        "view": view,
        "target": target,
        "paths": {},
        "exists": {},
    }
    if want_2d:
        two_d = output_base.with_suffix(".pcba.svg")
        outputs["paths"]["2d"] = str(two_d)
        outputs["exists"]["2d"] = two_d.exists()
    if want_3d:
        three_d = output_base.with_suffix(".pcba.png")
        outputs["paths"]["3d"] = str(three_d)
        outputs["exists"]["3d"] = three_d.exists()
    return outputs


def _normalize_screenshot_layers(raw_layers: Any) -> list[str] | None:
    if raw_layers is None:
        return None

    tokens: list[str] = []
    if isinstance(raw_layers, str):
        tokens = [part.strip() for part in raw_layers.split(",")]
    elif isinstance(raw_layers, list):
        for entry in raw_layers:
            if not isinstance(entry, str):
                raise ValueError("layers entries must be strings")
            tokens.append(entry.strip())
    else:
        raise ValueError("layers must be an array of KiCad layer names")

    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if not token:
            continue
        if not all(char.isalnum() or char in {".", "_", "-"} for char in token):
            raise ValueError(
                "layers entries may contain only letters, digits, '.', '_' and '-'"
            )
        if token in seen:
            continue
        seen.add(token)
        cleaned.append(token)

    if not cleaned:
        raise ValueError("layers cannot be empty when provided")
    return cleaned


def _default_screenshot_layers(side: str) -> list[str]:
    if side == "bottom":
        return ["B.Cu", "B.Paste", "B.Mask", "Edge.Cuts"]
    if side == "both":
        return ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "Edge.Cuts"]
    return ["F.Cu", "F.Paste", "F.Mask", "Edge.Cuts"]


def _normalize_highlight_components(raw: Any) -> list[str]:
    if raw is None:
        return []

    tokens: list[str] = []
    if isinstance(raw, str):
        token = raw.strip()
        if token:
            tokens.append(token)
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, str):
                raise ValueError("highlight_components entries must be strings")
            token = item.strip()
            if token:
                tokens.append(token)
    else:
        raise ValueError("highlight_components must be a string or array of strings")

    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(token)
    return deduped


def _parse_svg_viewbox(root: ET.Element) -> tuple[float, float, float, float] | None:
    raw = root.attrib.get("viewBox")
    if not raw:
        return None

    parts = raw.replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        x_min, y_min, width, height = (float(part) for part in parts)
    except ValueError:
        return None
    return x_min, y_min, width, height


def _svg_namespace_from_tag(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1 : tag.find("}")]
    return ""


def _svg_tag(namespace: str, local_name: str) -> str:
    if namespace:
        return f"{{{namespace}}}{local_name}"
    return local_name


def _rotate_xy(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)


def _footprint_reference(footprint: Any) -> str:
    from faebryk.libs.kicad.fileformats import Property

    reference = Property.try_get_property(
        getattr(footprint, "propertys", None),
        "Reference",
    )
    if isinstance(reference, str) and reference.strip():
        return reference.strip()
    return ""


def _footprint_bbox_mm(footprint: Any) -> tuple[float, float, float, float] | None:
    fp_at = getattr(footprint, "at", None)
    pads = getattr(footprint, "pads", None)
    if fp_at is None or pads is None:
        return None

    fp_x = float(getattr(fp_at, "x", 0.0) or 0.0)
    fp_y = float(getattr(fp_at, "y", 0.0) or 0.0)
    fp_r = float(getattr(fp_at, "r", 0.0) or 0.0)

    points: list[tuple[float, float]] = []
    for pad in pads:
        pad_at = getattr(pad, "at", None)
        pad_size = getattr(pad, "size", None)
        if pad_at is None or pad_size is None:
            continue

        width = float(getattr(pad_size, "w", 0.0) or 0.0)
        height = float(getattr(pad_size, "h", width) or width)
        if width <= 0 or height <= 0:
            continue

        rel_x = float(getattr(pad_at, "x", 0.0) or 0.0)
        rel_y = float(getattr(pad_at, "y", 0.0) or 0.0)
        rel_r = float(getattr(pad_at, "r", 0.0) or 0.0)

        dx, dy = _rotate_xy(rel_x, rel_y, fp_r)
        center_x = fp_x + dx
        center_y = fp_y + dy
        absolute_rotation = fp_r + rel_r

        half_w = width / 2.0
        half_h = height / 2.0
        for offset_x, offset_y in (
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h),
        ):
            rx, ry = _rotate_xy(offset_x, offset_y, absolute_rotation)
            points.append((center_x + rx, center_y + ry))

    if not points:
        # Fallback when footprint has no pads in the layout object.
        return (fp_x - 0.1, fp_y - 0.1, fp_x + 0.1, fp_y + 0.1)

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_overlap_details(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> dict[str, float] | None:
    overlap_x = min(first[2], second[2]) - max(first[0], second[0])
    overlap_y = min(first[3], second[3]) - max(first[1], second[1])
    if overlap_x <= 0 or overlap_y <= 0:
        return None

    return {
        "overlap_dx_mm": overlap_x,
        "overlap_dy_mm": overlap_y,
        "overlap_area_mm2": overlap_x * overlap_y,
    }


def _extract_edge_cuts_points(kicad_pcb: Any) -> list[tuple[float, float]]:
    from faebryk.libs.kicad.fileformats import kicad

    points: list[tuple[float, float]] = []

    def is_edge_cuts(geo: Any) -> bool:
        layers = kicad.geo.get_layers(geo)
        return "Edge.Cuts" in layers

    def append_xy(coord: Any) -> None:
        points.append(
            (
                float(getattr(coord, "x", 0.0)),
                float(getattr(coord, "y", 0.0)),
            )
        )

    for line in getattr(kicad_pcb, "gr_lines", []) or []:
        if is_edge_cuts(line):
            append_xy(line.start)
            append_xy(line.end)
    for arc in getattr(kicad_pcb, "gr_arcs", []) or []:
        if is_edge_cuts(arc):
            append_xy(arc.start)
            append_xy(arc.mid)
            append_xy(arc.end)
    for rect in getattr(kicad_pcb, "gr_rects", []) or []:
        if is_edge_cuts(rect):
            append_xy(rect.start)
            append_xy(rect.end)
    for circle in getattr(kicad_pcb, "gr_circles", []) or []:
        if not is_edge_cuts(circle):
            continue
        cx = float(circle.center.x)
        cy = float(circle.center.y)
        radius = (
            (float(circle.end.x) - cx) ** 2 + (float(circle.end.y) - cy) ** 2
        ) ** 0.5
        points.extend(
            [
                (cx - radius, cy),
                (cx + radius, cy),
                (cx, cy - radius),
                (cx, cy + radius),
            ]
        )

    for footprint in getattr(kicad_pcb, "footprints", []) or []:
        fp_at = getattr(footprint, "at", None)
        fp_x = float(getattr(fp_at, "x", 0.0) or 0.0)
        fp_y = float(getattr(fp_at, "y", 0.0) or 0.0)
        fp_r = float(getattr(fp_at, "r", 0.0) or 0.0)

        def transform_local(coord: Any) -> tuple[float, float]:
            local_x = float(getattr(coord, "x", 0.0) or 0.0)
            local_y = float(getattr(coord, "y", 0.0) or 0.0)
            dx, dy = _rotate_xy(local_x, local_y, fp_r)
            return (fp_x + dx, fp_y + dy)

        for line in getattr(footprint, "fp_lines", []) or []:
            if is_edge_cuts(line):
                points.append(transform_local(line.start))
                points.append(transform_local(line.end))
        for arc in getattr(footprint, "fp_arcs", []) or []:
            if is_edge_cuts(arc):
                points.append(transform_local(arc.start))
                points.append(transform_local(arc.mid))
                points.append(transform_local(arc.end))

    return points


def _analyze_layout_component_placement(
    *,
    pcb_file: Any,
    moved_record: _LayoutComponentRecord,
    all_records: list[_LayoutComponentRecord],
) -> dict[str, Any]:
    moved_bbox = _footprint_bbox_mm(moved_record.footprint)
    result: dict[str, Any] = {
        "checked": moved_bbox is not None,
        "reference": moved_record.reference or None,
        "atopile_address": moved_record.atopile_address,
        "component_bbox_mm": None,
        "board_bbox_mm": None,
        "board_outline_available": False,
        "on_board": None,
        "outside_board_area_mm2": None,
        "collision_count": 0,
        "collisions": [],
    }
    if moved_bbox is None:
        return result

    result["component_bbox_mm"] = {
        "min_x": round(moved_bbox[0], 4),
        "min_y": round(moved_bbox[1], 4),
        "max_x": round(moved_bbox[2], 4),
        "max_y": round(moved_bbox[3], 4),
    }

    collisions: list[dict[str, Any]] = []
    for record in all_records:
        if record.footprint is moved_record.footprint:
            continue
        if (
            record.reference
            and moved_record.reference
            and record.reference == moved_record.reference
        ):
            continue

        other_bbox = _footprint_bbox_mm(record.footprint)
        if other_bbox is None:
            continue
        overlap = _bbox_overlap_details(moved_bbox, other_bbox)
        if overlap is None:
            continue

        collisions.append(
            {
                "reference": record.reference or None,
                "atopile_address": record.atopile_address,
                "overlap_dx_mm": round(overlap["overlap_dx_mm"], 4),
                "overlap_dy_mm": round(overlap["overlap_dy_mm"], 4),
                "overlap_area_mm2": round(overlap["overlap_area_mm2"], 4),
            }
        )

    collisions.sort(key=lambda item: item.get("overlap_area_mm2", 0.0), reverse=True)
    result["collisions"] = collisions
    result["collision_count"] = len(collisions)

    kicad_pcb = getattr(pcb_file, "kicad_pcb", None)
    if kicad_pcb is None:
        return result

    edge_points = _extract_edge_cuts_points(kicad_pcb)
    if not edge_points:
        return result

    min_x = min(point[0] for point in edge_points)
    min_y = min(point[1] for point in edge_points)
    max_x = max(point[0] for point in edge_points)
    max_y = max(point[1] for point in edge_points)
    result["board_outline_available"] = True
    result["board_bbox_mm"] = {
        "min_x": round(min_x, 4),
        "min_y": round(min_y, 4),
        "max_x": round(max_x, 4),
        "max_y": round(max_y, 4),
    }

    within_bbox = (
        moved_bbox[0] >= min_x
        and moved_bbox[1] >= min_y
        and moved_bbox[2] <= max_x
        and moved_bbox[3] <= max_y
    )

    outside_area_mm2: float | None = None
    try:
        from shapely.geometry import MultiPoint, box

        hull = MultiPoint(edge_points).convex_hull
        footprint_box = box(*moved_bbox)
        if not hull.is_empty and hull.geom_type in {"Polygon", "MultiPolygon"}:
            covered = bool(hull.buffer(1e-6).covers(footprint_box))
            outside_area_mm2 = float(footprint_box.difference(hull).area)
            result["on_board"] = covered
        else:
            result["on_board"] = within_bbox
    except Exception:
        result["on_board"] = within_bbox

    if outside_area_mm2 is None:
        footprint_area = max(
            0.0,
            (moved_bbox[2] - moved_bbox[0]) * (moved_bbox[3] - moved_bbox[1]),
        )
        if result["on_board"] is False:
            outside_area_mm2 = footprint_area
        else:
            outside_area_mm2 = 0.0

    result["outside_board_area_mm2"] = round(float(outside_area_mm2), 4)
    return result


def _resolve_highlight_components(
    *,
    layout_path: Path,
    queries: list[str],
    fuzzy_limit: int,
) -> tuple[list[_LayoutComponentRecord], list[dict[str, Any]]]:
    if not queries:
        return [], []

    _, records = _load_layout_component_index(layout_path)
    resolved: list[_LayoutComponentRecord] = []
    unresolved: list[dict[str, Any]] = []
    seen_refs: set[str] = set()

    for query in queries:
        lookup = _lookup_layout_component(
            records=records,
            query=query,
            fuzzy_limit=fuzzy_limit,
        )
        if not lookup.found or lookup.record is None:
            unresolved.append(
                {
                    "query": query,
                    "message": lookup.message,
                    "suggestions": lookup.suggestions,
                }
            )
            continue

        reference_key = lookup.record.reference_norm or lookup.record.address_norm
        if reference_key and reference_key in seen_refs:
            continue
        if reference_key:
            seen_refs.add(reference_key)
        resolved.append(lookup.record)

    return resolved, unresolved


def _apply_component_highlight_overlay(
    *,
    base_svg_path: Path,
    layout_path: Path,
    project_dir: Path,
    layers: list[str],
    highlighted_references: set[str],
    dim_opacity: float,
) -> dict[str, Any]:
    from faebryk.exporters.pcb.kicad.artifacts import export_svg
    from faebryk.libs.kicad.fileformats import kicad

    if not highlighted_references:
        return {"applied": False, "reason": "no_highlighted_references"}

    with tempfile.TemporaryDirectory(prefix="ato-highlight-") as tmpdir:
        try:
            tmp_root = Path(tmpdir)
            overlay_layout_path = tmp_root / "highlight.kicad_pcb"
            overlay_svg_path = tmp_root / "highlight.svg"

            if hasattr(kicad.loads, "cache"):
                kicad.loads.cache.pop(layout_path, None)
            pcb_file = kicad.loads(kicad.pcb.PcbFile, layout_path)
            pcb = pcb_file.kicad_pcb

            selected_footprints = []
            for footprint in pcb.footprints:
                if _footprint_reference(footprint) in highlighted_references:
                    selected_footprints.append(footprint)
            if not selected_footprints:
                return {"applied": False, "reason": "highlight_components_not_found"}

            pcb.footprints = selected_footprints
            kicad.dumps(pcb_file, overlay_layout_path)
            if hasattr(kicad.loads, "cache"):
                kicad.loads.cache.pop(overlay_layout_path, None)

            highlight_layers = [layer for layer in layers if layer != "Edge.Cuts"]
            if not highlight_layers:
                highlight_layers = list(layers)
            export_svg(
                pcb_file=overlay_layout_path,
                svg_file=overlay_svg_path,
                project_dir=project_dir,
                layers=",".join(highlight_layers),
            )

            base_tree = ET.parse(base_svg_path)
            base_root = base_tree.getroot()
            overlay_root = ET.parse(overlay_svg_path).getroot()

            viewbox = _parse_svg_viewbox(base_root)
            if viewbox is None:
                return {"applied": False, "reason": "missing_viewbox"}
            x_min, y_min, width, height = viewbox

            namespace = _svg_namespace_from_tag(base_root.tag)
            rect = ET.Element(
                _svg_tag(namespace, "rect"),
                {
                    "x": f"{x_min:.4f}",
                    "y": f"{y_min:.4f}",
                    "width": f"{width:.4f}",
                    "height": f"{height:.4f}",
                    "fill": "#000000",
                    "fill-opacity": f"{dim_opacity:.3f}",
                    "id": "atopile-dim-overlay",
                },
            )
            base_root.append(rect)

            highlight_group = ET.Element(
                _svg_tag(namespace, "g"),
                {
                    "id": "atopile-highlight-components",
                },
            )
            overlay_namespace = _svg_namespace_from_tag(overlay_root.tag)
            skip_tags = {
                _svg_tag(overlay_namespace, "title"),
                _svg_tag(overlay_namespace, "desc"),
            }
            for child in list(overlay_root):
                if child.tag in skip_tags:
                    continue
                highlight_group.append(deepcopy(child))
            base_root.append(highlight_group)

            if namespace:
                ET.register_namespace("", namespace)
            base_tree.write(base_svg_path, encoding="utf-8", xml_declaration=True)
        finally:
            if hasattr(kicad.loads, "cache"):
                kicad.loads.cache.pop(layout_path, None)

    return {
        "applied": True,
        "highlight_count": len(highlighted_references),
        "dim_opacity": dim_opacity,
    }


def _estimate_layout_component_count(layout_path: Path) -> int | None:
    if not layout_path.exists():
        return None
    try:
        text = layout_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return text.count("(footprint ")


def _recommended_autolayout_timeout(
    *,
    component_count: int | None,
    job_type: str,
) -> dict[str, Any]:
    normalized_job_type = job_type.strip().lower()
    if component_count is None:
        bucket = "unknown"
    elif component_count <= 50:
        bucket = "simple"
    elif component_count <= 100:
        bucket = "medium"
    elif component_count <= 200:
        bucket = "complex"
    else:
        bucket = "very_complex"

    return {
        "component_count": component_count,
        "bucket": bucket,
        "job_type": normalized_job_type or "routing",
        "start_timeout_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        "resume_increment_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        "per_run_cap_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        "note": (
            "Per-run timeout is capped to 2 minutes. Run a short pass, review "
            "candidate quality with autolayout_status/screenshots, then resume with "
            "resume_board_id if quality is not yet sufficient."
        ),
    }


def _normalize_plane_nets(raw: Any) -> list[str]:
    if raw is None:
        return ["GND"]
    if not isinstance(raw, list):
        raise ValueError("plane_nets must be an array of net names")
    normalized: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError("plane_nets entries must be strings")
        token = item.strip()
        if not token:
            continue
        if token not in normalized:
            normalized.append(token)
    if not normalized:
        normalized = ["GND"]
    return normalized


def _to_float_or_none(value: Any, *, field_name: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _to_int_or_none(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _normalize_domain_filters(raw: Any, *, field_name: str) -> list[str]:
    if raw is None:
        return []

    tokens: list[str] = []
    if isinstance(raw, str):
        tokens = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, str):
                raise ValueError(f"{field_name} entries must be strings")
            tokens.append(item.strip())
    else:
        raise ValueError(f"{field_name} must be an array of domains")

    normalized: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if not token:
            continue
        cleaned = token.lower()
        if cleaned.startswith("https://"):
            cleaned = cleaned[len("https://") :]
        elif cleaned.startswith("http://"):
            cleaned = cleaned[len("http://") :]
        cleaned = cleaned.strip().strip("/")
        if not cleaned:
            continue
        if any(char.isspace() for char in cleaned):
            raise ValueError(
                f"{field_name} entries must not contain whitespace: '{token}'"
            )
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _get_exa_api_key() -> str:
    api_key = os.getenv("ATOPILE_AGENT_EXA_API_KEY") or os.getenv("EXA_API_KEY")
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()
    raise RuntimeError(
        "Missing Exa API key. Set ATOPILE_AGENT_EXA_API_KEY or EXA_API_KEY."
    )


def _extract_http_error_detail(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    if response is None:
        return str(exc)
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("detail")
            if isinstance(message, str) and message.strip():
                return message.strip()
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    text = (response.text or "").strip()
    if text:
        return _trim_message(text, 280)
    return str(exc)


def _exa_web_search(
    *,
    query: str,
    num_results: int,
    search_type: str,
    include_domains: list[str],
    exclude_domains: list[str],
    include_text: bool,
    timeout_s: float,
) -> dict[str, Any]:
    api_key = _get_exa_api_key()
    endpoint = os.getenv("ATOPILE_AGENT_EXA_SEARCH_URL", "https://api.exa.ai/search")

    payload: dict[str, Any] = {
        "query": query,
        "numResults": num_results,
        "type": search_type,
    }
    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains
    if include_text:
        payload["contents"] = {"text": True}

    headers = {
        "x-api-key": api_key,
        "authorization": f"Bearer {api_key}",
        "accept": "application/json",
        "content-type": "application/json",
    }
    timeout = httpx.Timeout(timeout_s, connect=min(5.0, timeout_s))

    try:
        with httpx.Client(timeout=timeout, verify=True) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _extract_http_error_detail(exc)
        raise RuntimeError(
            f"Exa search failed ({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Exa search request failed: {exc}") from exc

    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("Exa search response was not a JSON object")

    raw_results = body.get("results")
    if not isinstance(raw_results, list):
        raw_results = []

    normalized_results: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_results, start=1):
        if not isinstance(raw, dict):
            continue
        text = raw.get("text")
        normalized_results.append(
            {
                "rank": index,
                "title": str(raw.get("title", "") or ""),
                "url": str(raw.get("url", "") or ""),
                "published_date": raw.get("publishedDate"),
                "author": raw.get("author"),
                "score": raw.get("score"),
                "text": _trim_message(str(text), 2200)
                if isinstance(text, str) and text
                else None,
            }
        )

    return {
        "query": query,
        "search_type": search_type,
        "requested_results": num_results,
        "returned_results": len(normalized_results),
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
        "results": normalized_results,
        "request_id": body.get("requestId"),
        "cost_dollars": body.get("costDollars"),
        "source": "exa",
    }


@dataclass
class _LayoutComponentRecord:
    reference: str
    atopile_address: str | None
    layer: str
    x_mm: float
    y_mm: float
    rotation_deg: float
    footprint: Any

    @property
    def reference_norm(self) -> str:
        return _normalize_component_lookup_token(self.reference)

    @property
    def address_norm(self) -> str:
        return _normalize_component_lookup_token(self.atopile_address or "")

    @property
    def address_tail_norm(self) -> str:
        return _extract_component_address_tail(self.atopile_address or "")


@dataclass
class _LayoutComponentLookup:
    found: bool
    matched_by: str | None
    record: _LayoutComponentRecord | None
    message: str
    suggestions: list[dict[str, Any]]


def _normalize_component_lookup_token(value: str) -> str:
    return str(value or "").strip().lower()


def _extract_component_address_tail(value: str) -> str:
    token = str(value or "").strip().lower()
    for separator in (".", "/", ":"):
        if separator in token:
            token = token.split(separator)[-1]
    return token


def _normalize_layout_layer(layer: Any, *, fallback: str) -> str:
    if not isinstance(layer, str) or not layer.strip():
        return fallback
    normalized = layer.strip()
    lowered = normalized.lower()
    aliases = {
        "top": "F.Cu",
        "front": "F.Cu",
        "f.cu": "F.Cu",
        "bottom": "B.Cu",
        "back": "B.Cu",
        "b.cu": "B.Cu",
    }
    return aliases.get(lowered, normalized)


def _resolve_layout_file_for_tool(
    *,
    project_root: Path,
    target: str,
) -> Path:
    errors: list[str] = []
    try:
        build_cfg = _resolve_build_target(project_root, target)
        layout_path = build_cfg.paths.layout
        if layout_path.exists() and layout_path.suffix.lower() == ".kicad_pcb":
            return layout_path
        errors.append(f"build target layout missing at {layout_path}")
    except Exception as exc:
        errors.append(str(exc))

    fallback = resolve_layout_path(project_root, target)
    if isinstance(fallback, Path):
        if fallback.is_file() and fallback.suffix.lower() == ".kicad_pcb":
            return fallback.resolve()
        if fallback.is_dir():
            candidates = sorted(
                path
                for path in fallback.glob("*.kicad_pcb")
                if path.is_file()
                and not path.name.startswith("_autosave-")
                and not path.name.endswith("-save.kicad_pcb")
            )
            if len(candidates) == 1:
                return candidates[0].resolve()
            if len(candidates) > 1:
                raise ValueError(
                    f"Multiple layout files found under {fallback}; specify target."
                )

    detail = "; ".join(part for part in errors if part) or "no layout candidates found"
    raise ValueError(
        f"Layout file for target '{target}' was not found. Details: {detail}"
    )


def _layout_component_payload(record: _LayoutComponentRecord) -> dict[str, Any]:
    return {
        "reference": record.reference or None,
        "atopile_address": record.atopile_address,
        "x_mm": record.x_mm,
        "y_mm": record.y_mm,
        "rotation_deg": record.rotation_deg,
        "layer": record.layer,
    }


def _load_layout_component_index(
    layout_path: Path,
) -> tuple[Any, list[_LayoutComponentRecord]]:
    from faebryk.libs.kicad.fileformats import Property, kicad

    if hasattr(kicad.loads, "cache"):
        kicad.loads.cache.pop(layout_path, None)

    pcb_file = kicad.loads(kicad.pcb.PcbFile, layout_path)
    pcb = pcb_file.kicad_pcb

    records: list[_LayoutComponentRecord] = []
    for footprint in pcb.footprints:
        reference_raw = Property.try_get_property(footprint.propertys, "Reference")
        address_raw = Property.try_get_property(footprint.propertys, "atopile_address")

        reference = (
            str(reference_raw).strip()
            if isinstance(reference_raw, str) and reference_raw.strip()
            else ""
        )
        atopile_address = (
            str(address_raw).strip()
            if isinstance(address_raw, str) and address_raw.strip()
            else None
        )
        if not reference and not atopile_address:
            continue

        at = getattr(footprint, "at", None)
        if at is None:
            continue

        x_mm = float(getattr(at, "x", 0.0) or 0.0)
        y_mm = float(getattr(at, "y", 0.0) or 0.0)
        rotation_deg = float(getattr(at, "r", 0.0) or 0.0)
        layer = str(getattr(footprint, "layer", "") or "")

        records.append(
            _LayoutComponentRecord(
                reference=reference,
                atopile_address=atopile_address,
                layer=layer,
                x_mm=x_mm,
                y_mm=y_mm,
                rotation_deg=rotation_deg,
                footprint=footprint,
            )
        )

    return pcb_file, records


def _write_layout_component_file(layout_path: Path, pcb_file: Any) -> None:
    from faebryk.libs.kicad.fileformats import kicad

    kicad.dumps(pcb_file, layout_path)
    if hasattr(kicad.loads, "cache"):
        kicad.loads.cache.pop(layout_path, None)


def _build_layout_component_suggestions(
    *,
    records: list[_LayoutComponentRecord],
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    query_norm = _normalize_component_lookup_token(query)
    if not query_norm or not records or limit <= 0:
        return []

    scored: list[tuple[float, _LayoutComponentRecord]] = []
    for record in records:
        candidates = [
            record.reference_norm,
            record.address_norm,
            record.address_tail_norm,
        ]
        best_score = 0.0
        for candidate in candidates:
            if not candidate:
                continue
            if candidate == query_norm:
                score = 1.0
            elif candidate.startswith(query_norm):
                score = 0.95
            elif query_norm in candidate:
                score = 0.85
            else:
                score = difflib.SequenceMatcher(None, query_norm, candidate).ratio()
            if score > best_score:
                best_score = score
        if best_score >= 0.35:
            scored.append((best_score, record))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].reference_norm,
            item[1].address_norm,
        ),
        reverse=True,
    )

    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for score, record in scored:
        dedupe_key = (record.reference_norm, record.address_norm)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        suggestion = _layout_component_payload(record)
        suggestion["score"] = round(score, 3)
        suggestions.append(suggestion)
        if len(suggestions) >= limit:
            break
    return suggestions


def _lookup_layout_component(
    *,
    records: list[_LayoutComponentRecord],
    query: str,
    fuzzy_limit: int,
) -> _LayoutComponentLookup:
    query_clean = str(query or "").strip()
    query_norm = _normalize_component_lookup_token(query_clean)
    if not query_norm:
        raise ValueError("address is required")

    address_exact = [
        record
        for record in records
        if record.address_norm and record.address_norm == query_norm
    ]
    if len(address_exact) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="atopile_address_exact",
            record=address_exact[0],
            message="Matched exact atopile_address.",
            suggestions=[],
        )
    if len(address_exact) > 1:
        return _LayoutComponentLookup(
            found=False,
            matched_by=None,
            record=None,
            message="Multiple components matched this atopile_address query.",
            suggestions=[
                _layout_component_payload(record)
                for record in address_exact[: max(1, fuzzy_limit)]
            ],
        )

    reference_exact = [
        record
        for record in records
        if record.reference_norm and record.reference_norm == query_norm
    ]
    if len(reference_exact) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="reference_exact",
            record=reference_exact[0],
            message="Matched exact reference.",
            suggestions=[],
        )

    query_tail = _extract_component_address_tail(query_clean)
    tail_matches = [
        record
        for record in records
        if record.address_tail_norm and record.address_tail_norm == query_tail
    ]
    if len(tail_matches) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="atopile_address_tail",
            record=tail_matches[0],
            message="Matched atopile_address tail token.",
            suggestions=[],
        )

    suffix_matches = [
        record
        for record in records
        if record.address_norm and record.address_norm.endswith(query_norm)
    ]
    if len(suffix_matches) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="atopile_address_suffix",
            record=suffix_matches[0],
            message="Matched atopile_address suffix.",
            suggestions=[],
        )

    return _LayoutComponentLookup(
        found=False,
        matched_by=None,
        record=None,
        message=(
            "Component not found by atopile_address/reference. "
            "Use one of the suggested similar components."
        ),
        suggestions=_build_layout_component_suggestions(
            records=records,
            query=query_clean,
            limit=max(1, min(20, fuzzy_limit)),
        ),
    )


def _layout_get_component_position(
    *,
    project_root: Path,
    target: str,
    address: str,
    fuzzy_limit: int,
) -> dict[str, Any]:
    layout_path = _resolve_layout_file_for_tool(
        project_root=project_root, target=target
    )
    _, records = _load_layout_component_index(layout_path)
    lookup = _lookup_layout_component(
        records=records,
        query=address,
        fuzzy_limit=fuzzy_limit,
    )
    if not lookup.found or lookup.record is None:
        return {
            "found": False,
            "target": target,
            "layout_path": str(layout_path),
            "query": str(address),
            "message": lookup.message,
            "suggestions": lookup.suggestions,
        }

    return {
        "found": True,
        "target": target,
        "layout_path": str(layout_path),
        "query": str(address),
        "matched_by": lookup.matched_by,
        "component": _layout_component_payload(lookup.record),
    }


def _layout_set_component_position(
    *,
    project_root: Path,
    target: str,
    address: str,
    mode: str,
    x_mm: float | None,
    y_mm: float | None,
    rotation_deg: float | None,
    dx_mm: float | None,
    dy_mm: float | None,
    drotation_deg: float | None,
    layer: str | None,
    fuzzy_limit: int,
) -> dict[str, Any]:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from faebryk.libs.kicad.fileformats import kicad

    layout_path = _resolve_layout_file_for_tool(
        project_root=project_root, target=target
    )
    pcb_file, records = _load_layout_component_index(layout_path)
    lookup = _lookup_layout_component(
        records=records,
        query=address,
        fuzzy_limit=fuzzy_limit,
    )
    if not lookup.found or lookup.record is None:
        return {
            "found": False,
            "target": target,
            "layout_path": str(layout_path),
            "query": str(address),
            "message": lookup.message,
            "suggestions": lookup.suggestions,
        }

    record = lookup.record
    before = _layout_component_payload(record)

    mode_clean = str(mode or "absolute").strip().lower() or "absolute"
    if mode_clean not in {"absolute", "relative"}:
        raise ValueError("mode must be one of: absolute, relative")

    if mode_clean == "absolute":
        if x_mm is None or y_mm is None:
            raise ValueError("x_mm and y_mm are required in absolute mode")
        target_x = float(x_mm)
        target_y = float(y_mm)
        target_rotation = (
            float(rotation_deg) if rotation_deg is not None else record.rotation_deg
        )
    else:
        if rotation_deg is not None:
            raise ValueError(
                "rotation_deg is not used in relative mode. Use drotation_deg."
            )
        delta_x = float(dx_mm or 0.0)
        delta_y = float(dy_mm or 0.0)
        delta_rotation = float(drotation_deg or 0.0)
        target_x = record.x_mm + delta_x
        target_y = record.y_mm + delta_y
        target_rotation = record.rotation_deg + delta_rotation

    target_layer = _normalize_layout_layer(layer, fallback=record.layer)
    target_coord = kicad.pcb.Xyr(
        x=target_x,
        y=target_y,
        r=target_rotation,
    )
    PCB_Transformer.move_fp(record.footprint, target_coord, target_layer)
    _write_layout_component_file(layout_path, pcb_file)

    after_record = _LayoutComponentRecord(
        reference=record.reference,
        atopile_address=record.atopile_address,
        layer=str(getattr(record.footprint, "layer", target_layer) or target_layer),
        x_mm=float(getattr(record.footprint.at, "x", target_x) or target_x),
        y_mm=float(getattr(record.footprint.at, "y", target_y) or target_y),
        rotation_deg=float(
            getattr(record.footprint.at, "r", target_rotation) or target_rotation
        ),
        footprint=record.footprint,
    )
    after = _layout_component_payload(after_record)
    placement_check = _analyze_layout_component_placement(
        pcb_file=pcb_file,
        moved_record=after_record,
        all_records=records,
    )

    return {
        "found": True,
        "updated": True,
        "target": target,
        "layout_path": str(layout_path),
        "query": str(address),
        "matched_by": lookup.matched_by,
        "mode": mode_clean,
        "before": before,
        "after": after,
        "delta": {
            "dx_mm": after["x_mm"] - before["x_mm"],
            "dy_mm": after["y_mm"] - before["y_mm"],
            "drotation_deg": after["rotation_deg"] - before["rotation_deg"],
        },
        "placement_check": placement_check,
    }


def _stdlib_matches_child_query(item: Any, query: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True

    stack = list(getattr(item, "children", []))
    while stack:
        child = stack.pop()
        child_name = str(getattr(child, "name", "")).lower()
        child_type = str(getattr(child, "type", "")).lower()
        child_item_type = str(getattr(child, "item_type", "")).lower()
        if needle in child_name or needle in child_type or needle in child_item_type:
            return True
        nested = getattr(child, "children", None)
        if isinstance(nested, list):
            stack.extend(nested)
    return False


def _stdlib_matches_parameter_query(item: Any, query: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True

    parameters = getattr(item, "parameters", [])
    if isinstance(parameters, list):
        for parameter in parameters:
            if not isinstance(parameter, dict):
                continue
            name = str(parameter.get("name", "")).lower()
            value = str(parameter.get("value", "")).lower()
            if needle in name or needle in value:
                return True
    return False


def _resolve_examples_root(project_root: Path) -> Path:
    """Resolve the curated examples directory used for reference `.ato` code."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add_candidate(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(resolved)

    # Prefer workspace-relative discovery first.
    for parent in (project_root, *project_root.parents):
        add_candidate(parent / "examples")

    # Fallback to repository-relative discovery from this source file.
    try:
        repo_root = Path(__file__).resolve().parents[4]
    except IndexError:
        repo_root = Path(__file__).resolve().parent
    add_candidate(repo_root / "examples")

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    raise ValueError(
        "Reference examples directory not found. Expected an 'examples/' folder."
    )


def _collect_example_projects(
    examples_root: Path,
    *,
    include_without_ato_yaml: bool = False,
) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    for child in sorted(examples_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        ato_yaml = child / "ato.yaml"
        has_ato_yaml = ato_yaml.exists()
        if not has_ato_yaml and not include_without_ato_yaml:
            continue

        ato_files = sorted(
            str(path.relative_to(child))
            for path in child.rglob("*.ato")
            if path.is_file()
        )
        projects.append(
            {
                "name": child.name,
                "path": str(child),
                "has_ato_yaml": has_ato_yaml,
                "ato_files": ato_files,
            }
        )
    return projects


def _resolve_example_project(example_root: Path, example_name: str) -> Path:
    cleaned = str(example_name).strip()
    if not cleaned:
        raise ValueError("example is required")
    if "/" in cleaned or "\\" in cleaned:
        raise ValueError("example must be a top-level example directory name")

    candidate = (example_root / cleaned).resolve()
    if not candidate.is_relative_to(example_root.resolve()):
        raise ValueError("example path escapes examples root")
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError(f"Unknown example: {cleaned}")
    return candidate


def _resolve_example_ato_file(example_project_root: Path, path: str | None) -> Path:
    if isinstance(path, str) and path.strip():
        candidate = (example_project_root / path.strip()).resolve()
        if not candidate.is_relative_to(example_project_root.resolve()):
            raise ValueError("path escapes selected example root")
        if not candidate.exists() or not candidate.is_file():
            raise ValueError(f"Example file does not exist: {path}")
        if candidate.suffix.lower() != ".ato":
            raise ValueError("Only .ato files are supported by examples_read_ato")
        return candidate

    ato_files = sorted(
        candidate
        for candidate in example_project_root.rglob("*.ato")
        if candidate.is_file()
    )
    if not ato_files:
        raise ValueError("No .ato files found in selected example")
    return ato_files[0]


def _search_example_ato_files(
    *,
    examples_root: Path,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle:
        return []

    matches: list[dict[str, Any]] = []
    projects = _collect_example_projects(
        examples_root,
        include_without_ato_yaml=True,
    )
    for project in projects:
        example_name = str(project["name"])
        project_dir = examples_root / example_name
        for rel_path in project.get("ato_files", []):
            if not isinstance(rel_path, str) or not rel_path:
                continue
            file_path = project_dir / rel_path
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for line_no, line in enumerate(text.splitlines(), start=1):
                if needle not in line.lower():
                    continue
                matches.append(
                    {
                        "example": example_name,
                        "path": f"{example_name}/{rel_path}",
                        "line": line_no,
                        "text": line.strip()[:260],
                    }
                )
                if len(matches) >= limit:
                    return matches
    return matches


def _resolve_package_reference_roots(project_root: Path) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    def add_root(path: Path | None) -> None:
        if path is None:
            return
        resolved = path.resolve()
        if resolved in seen:
            return
        if not resolved.exists() or not resolved.is_dir():
            return
        seen.add(resolved)
        roots.append(resolved)

    project_cfg = ProjectConfig.from_path(project_root)
    if project_cfg is not None:
        add_root(project_cfg.paths.modules)
    else:
        add_root(project_root / ".ato" / "modules")

    raw_extra_roots = os.getenv("ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS", "")
    if raw_extra_roots.strip():
        for token in raw_extra_roots.split(","):
            cleaned = token.strip()
            if not cleaned:
                continue
            candidate = Path(cleaned).expanduser()
            if not candidate.is_absolute():
                candidate = (project_root / candidate).resolve()
            add_root(candidate)

    return roots


def _infer_package_reference_metadata(
    *,
    root: Path,
    file_path: Path,
) -> tuple[str | None, str, str]:
    rel = file_path.relative_to(root)
    rel_path = str(rel)
    parts = rel.parts

    if len(parts) >= 3:
        package_identifier = f"{parts[0]}/{parts[1]}"
        path_in_package = str(Path(*parts[2:]))
    else:
        package_identifier = None
        path_in_package = rel_path

    return package_identifier, path_in_package, rel_path


def _iter_package_reference_files(
    *,
    roots: list[Path],
    package_query: str | None = None,
    path_query: str | None = None,
    max_files_scanned: int = _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
) -> tuple[list[dict[str, Any]], int, bool]:
    package_needle = (package_query or "").strip().lower()
    path_needle = (path_query or "").strip().lower()
    scanned = 0
    truncated = False
    records: list[dict[str, Any]] = []

    for root in roots:
        for file_path in root.rglob("*.ato"):
            rel = file_path.relative_to(root)
            if any(part.startswith(".") for part in rel.parts[:-1]):
                continue
            if ".cache" in rel.parts:
                continue

            scanned += 1
            if scanned > max_files_scanned:
                truncated = True
                return records, scanned, truncated

            package_identifier, path_in_package, rel_path = (
                _infer_package_reference_metadata(
                    root=root,
                    file_path=file_path,
                )
            )
            package_value = package_identifier or ""

            if package_needle and package_needle not in package_value.lower():
                continue
            if path_needle and path_needle not in rel_path.lower():
                continue

            records.append(
                {
                    "source_root": str(root),
                    "path": rel_path,
                    "absolute_path": str(file_path),
                    "package_identifier": package_identifier,
                    "path_in_package": path_in_package,
                }
            )

    return records, scanned, truncated


def _list_package_reference_files(
    *,
    project_root: Path,
    package_query: str | None,
    path_query: str | None,
    limit: int,
) -> dict[str, Any]:
    roots = _resolve_package_reference_roots(project_root)
    if not roots:
        return {
            "roots": [],
            "files": [],
            "packages": [],
            "total_files": 0,
            "returned": 0,
            "message": (
                "No package reference roots found. Install dependencies (creating "
                "`.ato/modules`) or configure ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS."
            ),
        }

    records, scanned, truncated = _iter_package_reference_files(
        roots=roots,
        package_query=package_query,
        path_query=path_query,
    )
    returned = records[:limit]

    package_counts: dict[str, int] = {}
    for record in records:
        package_identifier = record.get("package_identifier")
        key = (
            str(package_identifier)
            if isinstance(package_identifier, str) and package_identifier
            else "<unscoped>"
        )
        package_counts[key] = package_counts.get(key, 0) + 1
    top_packages = sorted(
        package_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )

    return {
        "roots": [str(root) for root in roots],
        "filters": {
            "package_query": package_query,
            "path_query": path_query,
        },
        "files": returned,
        "packages": [
            {"package_identifier": package_identifier, "file_count": count}
            for package_identifier, count in top_packages[:50]
        ],
        "total_files": len(records),
        "returned": len(returned),
        "scanned_files": scanned,
        "scan_truncated": truncated,
        "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
    }


def _search_package_reference_files(
    *,
    project_root: Path,
    query: str,
    package_query: str | None,
    path_query: str | None,
    limit: int,
) -> dict[str, Any]:
    needle = query.strip().lower()
    if not needle:
        return {
            "roots": [],
            "query": query,
            "matches": [],
            "total": 0,
            "scanned_files": 0,
            "scan_truncated": False,
            "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
        }

    roots = _resolve_package_reference_roots(project_root)
    if not roots:
        return {
            "roots": [],
            "query": query,
            "matches": [],
            "total": 0,
            "message": (
                "No package reference roots found. Install dependencies (creating "
                "`.ato/modules`) or configure ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS."
            ),
        }

    records, scanned, truncated = _iter_package_reference_files(
        roots=roots,
        package_query=package_query,
        path_query=path_query,
    )

    matches: list[dict[str, Any]] = []
    for record in records:
        file_path = Path(str(record["absolute_path"]))
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if needle not in line.lower():
                continue
            matches.append(
                {
                    "package_identifier": record.get("package_identifier"),
                    "path": record.get("path"),
                    "path_in_package": record.get("path_in_package"),
                    "source_root": record.get("source_root"),
                    "line": line_no,
                    "text": line.strip()[:260],
                }
            )
            if len(matches) >= limit:
                return {
                    "roots": [str(root) for root in roots],
                    "query": query,
                    "filters": {
                        "package_query": package_query,
                        "path_query": path_query,
                    },
                    "matches": matches,
                    "total": len(matches),
                    "scanned_files": scanned,
                    "scan_truncated": truncated,
                    "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
                }

    return {
        "roots": [str(root) for root in roots],
        "query": query,
        "filters": {
            "package_query": package_query,
            "path_query": path_query,
        },
        "matches": matches,
        "total": len(matches),
        "scanned_files": scanned,
        "scan_truncated": truncated,
        "scan_cap_files": _PACKAGE_REFERENCE_MAX_FILES_SCANNED,
    }


def _read_package_reference_file(
    *,
    project_root: Path,
    package_identifier: str,
    path_in_package: str | None,
    start_line: int,
    max_lines: int,
) -> dict[str, Any]:
    roots = _resolve_package_reference_roots(project_root)
    if not roots:
        raise ValueError(
            "No package reference roots found. Install dependencies (creating "
            "`.ato/modules`) or configure ATOPILE_AGENT_PACKAGE_REFERENCE_ROOTS."
        )

    package_clean = package_identifier.strip().strip("/")
    if not package_clean or "/" not in package_clean:
        raise ValueError("package_identifier must look like 'owner/package'")

    rel_hint = (
        str(path_in_package).strip().lstrip("/")
        if isinstance(path_in_package, str) and path_in_package.strip()
        else None
    )

    selected_root: Path | None = None
    selected_file: Path | None = None
    selected_rel_path: str | None = None
    candidates_for_suggestions: list[str] = []
    for root in roots:
        package_root = (root / package_clean).resolve()
        if not package_root.exists() or not package_root.is_dir():
            continue

        candidates_for_suggestions.append(str(package_clean))
        if rel_hint:
            candidate = (package_root / rel_hint).resolve()
            if (
                candidate.exists()
                and candidate.is_file()
                and candidate.suffix.lower() == ".ato"
                and candidate.is_relative_to(package_root)
            ):
                selected_root = root
                selected_file = candidate
                selected_rel_path = str(candidate.relative_to(root))
                break
        else:
            ato_files = sorted(
                path for path in package_root.rglob("*.ato") if path.is_file()
            )
            if ato_files:
                selected_root = root
                selected_file = ato_files[0]
                selected_rel_path = str(ato_files[0].relative_to(root))
                break

    if selected_root is None or selected_file is None or selected_rel_path is None:
        available_records, _, _ = _iter_package_reference_files(roots=roots)
        available_packages = sorted(
            {
                str(record["package_identifier"])
                for record in available_records
                if isinstance(record.get("package_identifier"), str)
                and str(record["package_identifier"]).strip()
            }
        )
        suggestions = difflib.get_close_matches(
            package_clean,
            available_packages,
            n=8,
            cutoff=0.45,
        )
        raise ValueError(
            f"Package reference '{package_clean}' not found."
            + (f" Try one of: {', '.join(suggestions)}" if suggestions else "")
        )

    chunk = policy.read_file_chunk(
        selected_root,
        selected_rel_path,
        start_line=start_line,
        max_lines=max_lines,
    )
    return {
        "package_identifier": package_clean,
        "source_root": str(selected_root),
        "path_in_package": str(Path(selected_rel_path).relative_to(package_clean)),
        **chunk,
    }


def get_tool_definitions() -> list[dict[str, Any]]:
    """OpenAI Responses API function-tool definitions."""
    return [
        {
            "type": "function",
            "name": "project_list_files",
            "description": "List source/config files in the selected project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 600,
                        "default": 300,
                    }
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_read_file",
            "description": (
                "Read a file chunk from the selected project (including package"
                " files under .ato/modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 220,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_search",
            "description": "Search source/config files by substring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 60,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "web_search",
            "description": (
                "Search the public web using Exa and return ranked sources "
                "for current/unknown external facts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 8,
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["auto", "fast", "neural", "deep", "instant"],
                        "default": "auto",
                    },
                    "include_domains": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "exclude_domains": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "include_text": {"type": "boolean", "default": True},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "examples_list",
            "description": (
                "List curated atopile reference examples with available .ato files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 60,
                    },
                    "include_without_ato_yaml": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "examples_search",
            "description": ("Search across curated example .ato files by substring."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 100,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "examples_read_ato",
            "description": ("Read a curated example .ato file by example name."),
            "parameters": {
                "type": "object",
                "properties": {
                    "example": {"type": "string"},
                    "path": {"type": ["string", "null"]},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 220,
                    },
                },
                "required": ["example"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "package_ato_list",
            "description": (
                "List available package .ato reference files from `.ato/modules` "
                "and optional configured package reference roots."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "package_query": {"type": ["string", "null"]},
                    "path_query": {"type": ["string", "null"]},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 200,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "package_ato_search",
            "description": (
                "Search package .ato reference files by substring with optional "
                "package/path filtering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "package_query": {"type": ["string", "null"]},
                    "path_query": {"type": ["string", "null"]},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 120,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "package_ato_read",
            "description": (
                "Read one package .ato reference file by package identifier "
                "(owner/package) and optional path within that package."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "package_identifier": {"type": "string"},
                    "path_in_package": {"type": ["string", "null"]},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 220,
                    },
                },
                "required": ["package_identifier"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_list_modules",
            "description": (
                "Primary structure tool. List project "
                "module/interface/component definitions for architecture "
                "overview."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type_filter": {"type": ["string", "null"]},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 200,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_module_children",
            "description": (
                "Primary deep-structure tool. Inspect hierarchical "
                "children/interfaces/parameters for one module entry point "
                "(use after project_list_modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_point": {"type": "string"},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 5,
                        "default": 2,
                    },
                },
                "required": ["entry_point"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "stdlib_list",
            "description": (
                "Browse atopile stdlib modules/interfaces/traits/components with "
                "optional filtering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type_filter": {"type": ["string", "null"]},
                    "search": {"type": ["string", "null"]},
                    "child_query": {"type": ["string", "null"]},
                    "parameter_query": {"type": ["string", "null"]},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 5,
                        "default": 2,
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 400,
                        "default": 120,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "stdlib_get_item",
            "description": "Get details for one stdlib item by id/name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                },
                "required": ["item_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_edit_file",
            "description": "Apply hash-anchored edits to a project file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "edits": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "set_line": {
                                            "type": "object",
                                            "properties": {
                                                "anchor": {"type": "string"},
                                                "new_text": {"type": "string"},
                                            },
                                            "required": ["anchor", "new_text"],
                                            "additionalProperties": False,
                                        }
                                    },
                                    "required": ["set_line"],
                                    "additionalProperties": False,
                                },
                                {
                                    "type": "object",
                                    "properties": {
                                        "replace_lines": {
                                            "type": "object",
                                            "properties": {
                                                "start_anchor": {"type": "string"},
                                                "end_anchor": {"type": "string"},
                                                "new_text": {"type": "string"},
                                            },
                                            "required": [
                                                "start_anchor",
                                                "end_anchor",
                                                "new_text",
                                            ],
                                            "additionalProperties": False,
                                        }
                                    },
                                    "required": ["replace_lines"],
                                    "additionalProperties": False,
                                },
                                {
                                    "type": "object",
                                    "properties": {
                                        "insert_after": {
                                            "type": "object",
                                            "properties": {
                                                "anchor": {"type": "string"},
                                                "text": {"type": "string"},
                                            },
                                            "required": ["anchor", "text"],
                                            "additionalProperties": False,
                                        }
                                    },
                                    "required": ["insert_after"],
                                    "additionalProperties": False,
                                },
                            ]
                        },
                    },
                },
                "required": ["path", "edits"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_create_path",
            "description": (
                "Create an in-scope directory or allowed file type. Allowed file "
                "extensions: .ato, .md, and .py (restricted to "
                "src/faebryk/library for fabll modules)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["file", "directory"],
                        "default": "file",
                    },
                    "content": {"type": "string", "default": ""},
                    "overwrite": {"type": "boolean", "default": False},
                    "parents": {"type": "boolean", "default": True},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_move_path",
            "description": (
                "Rearrange project files/directories by moving or renaming within "
                "the selected project scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "old_path": {"type": "string"},
                    "new_path": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["old_path", "new_path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_rename_path",
            "description": (
                "Rename or move a file/directory within the selected project scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "old_path": {"type": "string"},
                    "new_path": {"type": "string"},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["old_path", "new_path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "project_delete_path",
            "description": (
                "Delete a file/directory within the selected project scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean", "default": True},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "parts_search",
            "description": (
                "Search physical LCSC/JLC parts (ICs, passives, connectors)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 80,
                        "default": 20,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "parts_install",
            "description": "Install an LCSC part into the selected project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lcsc_id": {"type": "string"},
                },
                "required": ["lcsc_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "datasheet_read",
            "description": (
                "Resolve a datasheet PDF, upload it to OpenAI Files, and attach "
                "it for model-native reading. Prefer lcsc_id for graph-first "
                "project resolution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lcsc_id": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "path": {"type": ["string", "null"]},
                    "target": {"type": ["string", "null"]},
                    "query": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "packages_search",
            "description": (
                "Search atopile registry packages (module/library dependencies)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "packages_install",
            "description": "Install an atopile package into the selected project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string"},
                    "version": {"type": ["string", "null"]},
                },
                "required": ["identifier"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_run",
            "description": "Queue a build for one or more targets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "entry": {"type": ["string", "null"]},
                    "standalone": {"type": "boolean", "default": False},
                    "frozen": {"type": "boolean", "default": False},
                    "include_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "exclude_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_create",
            "description": "Create a new build target in ato.yaml.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "entry": {"type": "string"},
                },
                "required": ["name", "entry"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_rename",
            "description": "Rename or update an existing build target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_name": {"type": "string"},
                    "new_name": {"type": ["string", "null"]},
                    "new_entry": {"type": ["string", "null"]},
                },
                "required": ["old_name"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_logs_search",
            "description": (
                "Search build logs or list recent builds with status/error "
                "summaries. Defaults to INFO/WARNING/ERROR/ALERT levels."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_id": {"type": ["string", "null"]},
                    "query": {"type": ["string", "null"]},
                    "stage": {"type": ["string", "null"]},
                    "log_levels": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "string",
                            "enum": [
                                "DEBUG",
                                "INFO",
                                "WARNING",
                                "ERROR",
                                "ALERT",
                            ],
                        },
                    },
                    "audience": {
                        "type": "string",
                        "enum": ["user", "developer", "agent", "all", "*"],
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 200,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "design_diagnostics",
            "description": (
                "Run quick diagnostics for the selected project (recent failures, "
                "problems, and module overview)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_problems": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 25,
                    },
                    "max_failure_logs": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 50,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_run",
            "description": (
                "Start an autolayout placement or routing run as a background task. "
                "Per-run timeout is capped at 2 minutes; use resume cycles for "
                "longer optimization."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_target": {"type": "string", "default": "default"},
                    "job_type": {
                        "type": "string",
                        "enum": ["Routing", "Placement"],
                        "default": "Routing",
                    },
                    "routing_type": {"type": ["string", "null"]},
                    "timeout_minutes": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 2,
                    },
                    "max_batch_timeout": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 3600,
                    },
                    "resume_board_id": {"type": ["string", "null"]},
                    "resume_stop_first": {"type": "boolean", "default": True},
                    "webhook_url": {"type": ["string", "null"]},
                    "webhook_token": {"type": ["string", "null"]},
                    "constraints": {"type": "object", "default": {}},
                    "options": {"type": "object", "default": {}},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_status",
            "description": (
                "Refresh an autolayout job and return state, candidates, and "
                "DeepPCB refs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": ["string", "null"]},
                    "refresh": {"type": "boolean", "default": True},
                    "include_candidates": {"type": "boolean", "default": True},
                    "wait_seconds": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 1800,
                        "default": 0,
                    },
                    "poll_interval_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 120,
                        "default": 10,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_fetch_to_layout",
            "description": (
                "Fetch one autolayout candidate into layouts/, apply it, archive "
                "an iteration snapshot, and return downloaded artifact paths "
                "(.kicad_pcb when available). If the job is "
                "still queued/running, return a check-back hint instead of "
                "applying early."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": ["string", "null"]},
                    "candidate_id": {"type": ["string", "null"]},
                    "archive_iteration": {"type": "boolean", "default": True},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_request_screenshot",
            "description": (
                "Render screenshot(s) of the current board layout (2D/3D) and "
                "return artifact paths. 2D rendering excludes the drawing sheet "
                "by default and can spotlight selected components by dimming the "
                "rest of the board."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "view": {
                        "type": "string",
                        "enum": ["2d", "3d", "both"],
                        "default": "2d",
                    },
                    "side": {
                        "type": "string",
                        "enum": ["top", "bottom", "both"],
                        "default": "top",
                    },
                    "layers": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "highlight_components": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "highlight_fuzzy_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 6,
                    },
                    "dim_others": {"type": "boolean", "default": True},
                    "dim_opacity": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.72,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "layout_get_component_position",
            "description": (
                "Get one component footprint position/layer from the current "
                "KiCad layout by atopile_address (or reference fallback). "
                "Returns fuzzy suggestions when not found."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "target": {"type": "string", "default": "default"},
                    "fuzzy_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 6,
                    },
                },
                "required": ["address"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "layout_set_component_position",
            "description": (
                "Set or nudge one component footprint transform in the current "
                "KiCad layout by atopile_address/reference. Supports absolute "
                "(x_mm/y_mm/rotation_deg) and relative "
                "(dx_mm/dy_mm/drotation_deg) modes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "target": {"type": "string", "default": "default"},
                    "mode": {
                        "type": "string",
                        "enum": ["absolute", "relative"],
                        "default": "absolute",
                    },
                    "x_mm": {"type": ["number", "null"]},
                    "y_mm": {"type": ["number", "null"]},
                    "rotation_deg": {"type": ["number", "null"]},
                    "dx_mm": {"type": ["number", "null"]},
                    "dy_mm": {"type": ["number", "null"]},
                    "drotation_deg": {"type": ["number", "null"]},
                    "layer": {"type": ["string", "null"]},
                    "fuzzy_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 6,
                    },
                },
                "required": ["address"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "layout_run_drc",
            "description": (
                "Run KiCad PCB DRC for the current layout and return summary counts "
                "plus a saved JSON report path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "max_findings": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 120,
                    },
                    "max_items_per_finding": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 4,
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_configure_board_intent",
            "description": (
                "Set board plane/stackup intent for a build target in ato.yaml so "
                "the agent can express ground pour and impedance assumptions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_target": {"type": "string", "default": "default"},
                    "enable_ground_pours": {"type": "boolean", "default": True},
                    "plane_nets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["GND"],
                    },
                    "plane_mode": {
                        "type": "string",
                        "enum": ["solid", "hatched"],
                        "default": "solid",
                    },
                    "min_plane_clearance_mm": {
                        "type": ["number", "null"],
                    },
                    "layer_count": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 64,
                    },
                    "board_thickness_mm": {"type": ["number", "null"]},
                    "outer_copper_oz": {"type": ["number", "null"]},
                    "inner_copper_oz": {"type": ["number", "null"]},
                    "dielectric_er": {"type": ["number", "null"]},
                    "preserve_existing_routing": {"type": ["boolean", "null"]},
                    "notes": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "report_bom",
            "description": (
                "Primary BOM report tool. Read generated BOM artifact data for "
                "a target."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "report_variables",
            "description": (
                "Primary parameter/variables report tool. Read computed "
                "variables artifact data for a target."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "manufacturing_generate",
            "description": (
                "Generate manufacturing artifacts by queueing a build with the "
                "mfg-data target. Use this to create gerbers, pick-and-place, "
                "3D outputs, and PCB summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "frozen": {"type": "boolean", "default": False},
                    "include_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["mfg-data"],
                    },
                    "exclude_targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "manufacturing_summary",
            "description": "Get build outputs and a basic manufacturing cost estimate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "default": "default"},
                    "quantity": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5000,
                        "default": 10,
                    },
                },
                "additionalProperties": False,
            },
        },
    ]


async def execute_tool(
    *,
    name: str,
    arguments: dict[str, Any],
    project_root: Path,
    ctx: AppContext,
) -> dict[str, Any]:
    """Execute a named agent tool with typed arguments."""
    if name == "project_list_files":
        limit = int(arguments.get("limit", 300))
        files = await asyncio.to_thread(policy.list_context_files, project_root, limit)
        return {"files": files, "total": len(files)}

    if name == "project_read_file":
        return await asyncio.to_thread(
            policy.read_file_chunk,
            project_root,
            str(arguments.get("path", "")),
            start_line=int(arguments.get("start_line", 1)),
            max_lines=int(arguments.get("max_lines", 220)),
        )

    if name == "project_search":
        matches = await asyncio.to_thread(
            policy.search_in_files,
            project_root,
            str(arguments.get("query", "")),
            limit=int(arguments.get("limit", 60)),
        )
        return {
            "matches": [asdict(match) for match in matches],
            "total": len(matches),
        }

    if name == "web_search":
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        num_results = max(1, min(25, int(arguments.get("num_results", 8))))
        search_type = str(arguments.get("search_type", "auto")).strip().lower()
        if search_type not in {"auto", "fast", "neural", "deep", "instant"}:
            raise ValueError(
                "search_type must be one of: auto, fast, neural, deep, instant"
            )
        include_domains = _normalize_domain_filters(
            arguments.get("include_domains"),
            field_name="include_domains",
        )
        exclude_domains = _normalize_domain_filters(
            arguments.get("exclude_domains"),
            field_name="exclude_domains",
        )
        include_text = bool(arguments.get("include_text", True))
        timeout_s = float(os.getenv("ATOPILE_AGENT_EXA_TIMEOUT_S", "30"))
        timeout_s = max(3.0, min(timeout_s, 120.0))

        return await asyncio.to_thread(
            _exa_web_search,
            query=query,
            num_results=num_results,
            search_type=search_type,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_text=include_text,
            timeout_s=timeout_s,
        )

    if name == "examples_list":
        limit = int(arguments.get("limit", 60))
        include_without_ato_yaml = bool(
            arguments.get("include_without_ato_yaml", False)
        )
        examples_root = _resolve_examples_root(project_root)
        projects = _collect_example_projects(
            examples_root,
            include_without_ato_yaml=include_without_ato_yaml,
        )
        returned = projects[:limit]
        return {
            "examples_root": str(examples_root),
            "examples": returned,
            "total": len(projects),
            "returned": len(returned),
        }

    if name == "examples_search":
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        limit = int(arguments.get("limit", 100))
        examples_root = _resolve_examples_root(project_root)
        matches = _search_example_ato_files(
            examples_root=examples_root,
            query=query,
            limit=limit,
        )
        return {
            "examples_root": str(examples_root),
            "query": query,
            "matches": matches,
            "total": len(matches),
        }

    if name == "examples_read_ato":
        example = str(arguments.get("example", "")).strip()
        examples_root = _resolve_examples_root(project_root)
        example_project_root = _resolve_example_project(examples_root, example)
        example_file = _resolve_example_ato_file(
            example_project_root,
            arguments.get("path") if isinstance(arguments.get("path"), str) else None,
        )
        relative_path = str(example_file.relative_to(example_project_root))
        chunk = await asyncio.to_thread(
            policy.read_file_chunk,
            example_project_root,
            relative_path,
            start_line=int(arguments.get("start_line", 1)),
            max_lines=int(arguments.get("max_lines", 220)),
        )
        return {
            "example": example,
            "example_root": str(example_project_root),
            **chunk,
        }

    if name == "package_ato_list":
        package_query = (
            str(arguments.get("package_query")).strip()
            if isinstance(arguments.get("package_query"), str)
            and str(arguments.get("package_query")).strip()
            else None
        )
        path_query = (
            str(arguments.get("path_query")).strip()
            if isinstance(arguments.get("path_query"), str)
            and str(arguments.get("path_query")).strip()
            else None
        )
        limit = max(1, min(1000, int(arguments.get("limit", 200))))
        return _list_package_reference_files(
            project_root=project_root,
            package_query=package_query,
            path_query=path_query,
            limit=limit,
        )

    if name == "package_ato_search":
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        package_query = (
            str(arguments.get("package_query")).strip()
            if isinstance(arguments.get("package_query"), str)
            and str(arguments.get("package_query")).strip()
            else None
        )
        path_query = (
            str(arguments.get("path_query")).strip()
            if isinstance(arguments.get("path_query"), str)
            and str(arguments.get("path_query")).strip()
            else None
        )
        limit = max(1, min(1000, int(arguments.get("limit", 120))))
        return _search_package_reference_files(
            project_root=project_root,
            query=query,
            package_query=package_query,
            path_query=path_query,
            limit=limit,
        )

    if name == "package_ato_read":
        package_identifier = str(arguments.get("package_identifier", "")).strip()
        if not package_identifier:
            raise ValueError("package_identifier is required")
        path_in_package = (
            str(arguments.get("path_in_package")).strip()
            if isinstance(arguments.get("path_in_package"), str)
            and str(arguments.get("path_in_package")).strip()
            else None
        )
        start_line = max(1, int(arguments.get("start_line", 1)))
        max_lines = max(1, min(400, int(arguments.get("max_lines", 220))))
        return _read_package_reference_file(
            project_root=project_root,
            package_identifier=package_identifier,
            path_in_package=path_in_package,
            start_line=start_line,
            max_lines=max_lines,
        )

    if name == "project_list_modules":
        type_filter = arguments.get("type_filter")
        limit = int(arguments.get("limit", 200))
        response = await asyncio.to_thread(
            projects_domain.handle_get_modules,
            str(project_root),
            str(type_filter) if isinstance(type_filter, str) and type_filter else None,
        )
        if response is None:
            return {"modules": [], "total": 0, "returned": 0, "types": {}}
        modules = [module.model_dump(by_alias=True) for module in response.modules][
            :limit
        ]
        return {
            "modules": modules,
            "total": response.total,
            "returned": len(modules),
            "types": _count_modules_by_type(modules),
        }

    if name == "project_module_children":
        entry_point = str(arguments.get("entry_point", "")).strip()
        if not entry_point:
            raise ValueError("entry_point is required")
        max_depth = int(arguments.get("max_depth", 2))
        max_depth = max(0, min(5, max_depth))
        children = await asyncio.to_thread(
            module_introspection.introspect_module,
            project_root,
            entry_point,
            max_depth,
        )
        if children is None:
            return {
                "entry_point": entry_point,
                "found": False,
                "children": [],
                "counts": {},
            }
        return {
            "entry_point": entry_point,
            "found": True,
            "children": [child.model_dump(by_alias=True) for child in children],
            "counts": _count_module_children(children),
        }

    if name == "stdlib_list":
        type_filter = arguments.get("type_filter")
        search = arguments.get("search")
        child_query = arguments.get("child_query")
        parameter_query = arguments.get("parameter_query")
        max_depth = int(arguments.get("max_depth", 2))
        limit = int(arguments.get("limit", 120))

        response = await asyncio.to_thread(
            stdlib_domain.handle_get_stdlib,
            str(type_filter) if isinstance(type_filter, str) and type_filter else None,
            str(search) if isinstance(search, str) and search else None,
            False,
            max_depth,
        )
        items = list(response.items)
        if isinstance(child_query, str) and child_query.strip():
            items = [
                item for item in items if _stdlib_matches_child_query(item, child_query)
            ]
        if isinstance(parameter_query, str) and parameter_query.strip():
            items = [
                item
                for item in items
                if _stdlib_matches_parameter_query(item, parameter_query)
            ]

        items = items[:limit]
        return {
            "items": [item.model_dump() for item in items],
            "total": response.total,
            "returned": len(items),
            "filters": {
                "type_filter": type_filter,
                "search": search,
                "child_query": child_query,
                "parameter_query": parameter_query,
            },
            "hints": [
                "Try search='usb' and child_query='i2c' for bus-related modules.",
                "Try type_filter='component' and parameter_query='voltage'.",
                "Use stdlib_get_item on a returned id for full details and usage.",
            ],
        }

    if name == "stdlib_get_item":
        item_id = str(arguments.get("item_id", "")).strip()
        if not item_id:
            raise ValueError("item_id is required")
        item = await asyncio.to_thread(stdlib_domain.handle_get_stdlib_item, item_id)
        if item is None:
            return {"found": False, "item_id": item_id}
        return {
            "found": True,
            "item_id": item_id,
            "item": item.model_dump(),
        }

    if name == "project_edit_file":
        edits = arguments.get("edits")
        if not isinstance(edits, list):
            raise ValueError("edits must be a list")
        return await asyncio.to_thread(
            policy.apply_hashline_edits,
            project_root,
            str(arguments.get("path", "")),
            edits,
        )

    if name == "project_create_path":
        content = arguments.get("content", "")
        if content is None:
            content = ""
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        kind = str(arguments.get("kind", "file")).strip().lower()
        return await asyncio.to_thread(
            policy.create_path,
            project_root,
            str(arguments.get("path", "")),
            kind=kind,
            content=content,
            overwrite=bool(arguments.get("overwrite", False)),
            parents=bool(arguments.get("parents", True)),
        )

    if name in {"project_rename_path", "project_move_path"}:
        return await asyncio.to_thread(
            policy.rename_path,
            project_root,
            str(arguments.get("old_path", "")),
            str(arguments.get("new_path", "")),
            overwrite=bool(arguments.get("overwrite", False)),
        )

    if name == "project_delete_path":
        return await asyncio.to_thread(
            policy.delete_path,
            project_root,
            str(arguments.get("path", "")),
            recursive=bool(arguments.get("recursive", True)),
        )

    if name == "project_write_file":
        return await asyncio.to_thread(
            policy.write_file,
            project_root,
            str(arguments.get("path", "")),
            str(arguments.get("content", "")),
        )

    if name == "project_replace_text":
        return await asyncio.to_thread(
            policy.apply_text_replace,
            project_root,
            str(arguments.get("path", "")),
            str(arguments.get("find_text", "")),
            str(arguments.get("replace_with", "")),
            max_replacements=int(arguments.get("max_replacements", 1)),
        )

    if name == "parts_search":
        parts, error = await asyncio.to_thread(
            parts_domain.handle_search_parts,
            str(arguments.get("query", "")).strip(),
            limit=int(arguments.get("limit", 20)),
        )
        return {"parts": parts, "total": len(parts), "error": error}

    if name == "parts_install":
        lcsc_id = str(arguments.get("lcsc_id", "")).strip().upper()
        result = await asyncio.to_thread(
            parts_domain.handle_install_part,
            lcsc_id,
            str(project_root),
        )
        return {
            "success": True,
            "lcsc_id": lcsc_id,
            "implementation_hint": (
                "For complex parts (MCUs/sensors/PMICs/radios), call "
                "datasheet_read next and verify required support circuitry."
            ),
            **result,
        }

    if name == "datasheet_read":
        raw_lcsc_id = arguments.get("lcsc_id")
        raw_url = arguments.get("url")
        raw_path = arguments.get("path")
        raw_target = arguments.get("target")
        raw_query = arguments.get("query")
        lcsc_id = (
            str(raw_lcsc_id).strip()
            if isinstance(raw_lcsc_id, str) and raw_lcsc_id.strip()
            else None
        )
        url = (
            str(raw_url).strip()
            if isinstance(raw_url, str) and raw_url.strip()
            else None
        )
        path = (
            str(raw_path).strip()
            if isinstance(raw_path, str) and raw_path.strip()
            else None
        )
        target = (
            str(raw_target).strip()
            if isinstance(raw_target, str) and raw_target.strip()
            else None
        )
        query = (
            str(raw_query).strip()
            if isinstance(raw_query, str) and raw_query.strip()
            else None
        )

        provided = [bool(lcsc_id), bool(url), bool(path)]
        if sum(1 for value in provided if value) != 1:
            raise ValueError("Provide exactly one of lcsc_id, url, or path")

        request_cache_keys = _datasheet_cache_keys(
            project_root=project_root,
            lcsc_id=lcsc_id,
            url=url,
            path=path,
        )
        for cache_ref in request_cache_keys:
            cached_payload = _cache_get_lru(_datasheet_read_cache, cache_ref)
            if not cached_payload:
                continue
            result = dict(cached_payload)
            result["query"] = query
            result["message"] = "Reusing previously attached datasheet file."
            result["openai_file_cached"] = True
            result["datasheet_cache_hit"] = True
            return result

        source_url = url
        source_path = path
        source_meta: dict[str, Any] = {}
        resolution: dict[str, Any] = {}
        fallback_sources: list[dict[str, Any]] = []
        if lcsc_id:
            cached_path = await asyncio.to_thread(
                parts_domain.handle_get_cached_datasheet_path,
                lcsc_id,
                str(project_root),
            )
            if cached_path:
                source_path = cached_path
                source_url = None
                resolution = {
                    "mode": "install_cache",
                    "path": cached_path,
                }
                if target:
                    resolution["requested_target"] = target

            if not source_path:
                details = await asyncio.to_thread(
                    parts_domain.handle_get_part_details,
                    lcsc_id,
                )
                if details is None:
                    return {
                        "found": False,
                        "lcsc_id": lcsc_id,
                        "message": f"Part not found: {lcsc_id}",
                    }

                datasheet_url = str(details.get("datasheet_url") or "").strip()
                if not datasheet_url:
                    return {
                        "found": False,
                        "lcsc_id": lcsc_id,
                        "message": "No datasheet URL available for this part",
                    }
                source_url = datasheet_url
                source_path = None
                resolution = {
                    "mode": "parts_api_fallback",
                    "reason": (
                        "No cached datasheet was found for this lcsc_id in the "
                        "project install cache."
                    ),
                }
                if target:
                    resolution["requested_target"] = target
                source_meta["part"] = {
                    "manufacturer": details.get("manufacturer"),
                    "part_number": details.get("part_number"),
                    "description": details.get("description"),
                }
                fallback_sources.append(
                    {
                        "source": "parts_api",
                        "url": datasheet_url,
                    }
                )

            source_meta = {
                "lcsc_id": lcsc_id.upper(),
                **source_meta,
            }

        datasheet_bytes: bytes
        metadata: dict[str, Any]
        if source_path:
            datasheet_bytes, metadata = await asyncio.to_thread(
                policy.read_datasheet_file,
                project_root,
                path=source_path,
                url=None,
            )
        else:
            candidate_urls: list[str] = []
            if source_url:
                candidate_urls.append(source_url)

            if lcsc_id:
                try:
                    jlc_candidates, jlc_error = await asyncio.to_thread(
                        parts_domain.search_jlc_parts,
                        lcsc_id,
                        limit=6,
                    )
                    if isinstance(jlc_error, str) and jlc_error.strip():
                        fallback_sources.append(
                            {
                                "source": "jlc_search_error",
                                "error": _trim_message(jlc_error, 220),
                            }
                        )
                    for item in jlc_candidates or []:
                        if not isinstance(item, dict):
                            continue
                        candidate_url = str(item.get("datasheet_url") or "").strip()
                        if not candidate_url:
                            continue
                        candidate_urls.append(candidate_url)
                        fallback_sources.append(
                            {
                                "source": "jlc_search",
                                "url": candidate_url,
                                "lcsc": item.get("lcsc"),
                                "mpn": item.get("mpn"),
                            }
                        )
                except Exception as exc:
                    fallback_sources.append(
                        {
                            "source": "jlc_search_error",
                            "error": _trim_message(
                                f"{type(exc).__name__}: {exc}",
                                220,
                            ),
                        }
                    )

            deduped_urls: list[str] = []
            for candidate_url in candidate_urls:
                if candidate_url and candidate_url not in deduped_urls:
                    deduped_urls.append(candidate_url)

            if not deduped_urls:
                raise policy.ScopeError(
                    "No datasheet URL could be resolved for this request."
                )

            last_error: Exception | None = None
            selected_url: str | None = None
            attempted_errors: list[str] = []
            for candidate_url in deduped_urls:
                try:
                    datasheet_bytes, metadata = await asyncio.to_thread(
                        policy.read_datasheet_file,
                        project_root,
                        path=None,
                        url=candidate_url,
                    )
                    selected_url = candidate_url
                    break
                except Exception as exc:
                    last_error = exc
                    attempted_errors.append(
                        _trim_message(f"{candidate_url} -> {exc}", 320)
                    )
            else:
                details = "; ".join(attempted_errors[:3]) or "unknown"
                raise policy.ScopeError(
                    f"Failed to fetch datasheet from all resolved URLs ({details})"
                ) from last_error

            if selected_url and source_url and selected_url != source_url:
                resolution = {
                    **resolution,
                    "url_fallback": {
                        "selected_url": selected_url,
                        "primary_url": source_url,
                        "attempted_urls": len(deduped_urls),
                    },
                }

        if fallback_sources:
            resolution = {
                **resolution,
                "fallback_sources": fallback_sources[:8],
            }
        cache_key = str(
            metadata.get("sha256")
            or f"{metadata.get('source_kind')}:{metadata.get('source')}"
        )
        filename = str(metadata.get("filename") or "datasheet.pdf")
        file_id, cached = await _upload_openai_user_file(
            filename=filename,
            content=datasheet_bytes,
            cache_key=cache_key,
        )

        result_payload = {
            "found": True,
            "query": query,
            "message": (
                "Datasheet uploaded and attached for model-native PDF reasoning."
            ),
            "openai_file_id": file_id,
            "openai_file_cached": cached,
            "datasheet_cache_hit": False,
            "bytes_uploaded": len(datasheet_bytes),
            "resolution": resolution or None,
            **source_meta,
            **metadata,
        }

        metadata_source_kind = metadata.get("source_kind")
        metadata_source = metadata.get("source")
        source_kind = (
            str(metadata_source_kind).strip()
            if isinstance(metadata_source_kind, str) and metadata_source_kind.strip()
            else None
        )
        source_value = (
            str(metadata_source).strip()
            if isinstance(metadata_source, str) and metadata_source.strip()
            else None
        )

        for cache_ref in _datasheet_cache_keys(
            project_root=project_root,
            lcsc_id=lcsc_id,
            url=url,
            path=path,
            source_kind=source_kind,
            source=source_value,
        ):
            _cache_set_lru(
                _datasheet_read_cache,
                cache_ref,
                dict(result_payload),
                max_entries=_DATASHEET_READ_CACHE_MAX_ENTRIES,
            )

        return result_payload

    if name == "packages_search":
        result = await asyncio.to_thread(
            packages_domain.handle_search_registry,
            str(arguments.get("query", "")),
            project_root,
        )
        return result.model_dump(by_alias=True)

    if name == "packages_install":
        identifier = str(arguments.get("identifier", ""))
        version = arguments.get("version")
        clean_version = str(version) if isinstance(version, str) and version else None
        await asyncio.to_thread(
            packages_domain.install_package_to_project,
            project_root,
            identifier,
            clean_version,
        )
        return {
            "success": True,
            "identifier": identifier,
            "version": clean_version,
            "message": "Package installed",
        }

    if name == "build_run":
        targets = arguments.get("targets") or []
        if not isinstance(targets, list):
            raise ValueError("targets must be a list")
        include_targets = arguments.get("include_targets") or []
        if not isinstance(include_targets, list):
            raise ValueError("include_targets must be a list")
        exclude_targets = arguments.get("exclude_targets") or []
        if not isinstance(exclude_targets, list):
            raise ValueError("exclude_targets must be a list")

        request = BuildRequest(
            project_root=str(project_root),
            targets=[str(target) for target in targets],
            entry=(str(arguments["entry"]) if arguments.get("entry") else None),
            standalone=bool(arguments.get("standalone", False)),
            frozen=bool(arguments.get("frozen", False)),
            include_targets=[str(target) for target in include_targets],
            exclude_targets=[str(target) for target in exclude_targets],
        )
        response = await asyncio.to_thread(builds_domain.handle_start_build, request)
        return response.model_dump(by_alias=True)

    if name == "build_create":
        request = AddBuildTargetRequest(
            project_root=str(project_root),
            name=str(arguments.get("name", "")),
            entry=str(arguments.get("entry", "")),
        )
        result = await asyncio.to_thread(
            projects_domain.handle_add_build_target, request
        )
        return result.model_dump(by_alias=True)

    if name == "build_rename":
        request = UpdateBuildTargetRequest(
            project_root=str(project_root),
            old_name=str(arguments.get("old_name", "")),
            new_name=(
                str(arguments["new_name"]) if arguments.get("new_name") else None
            ),
            new_entry=(
                str(arguments["new_entry"]) if arguments.get("new_entry") else None
            ),
        )
        result = await asyncio.to_thread(
            projects_domain.handle_update_build_target,
            request,
        )
        return result.model_dump(by_alias=True)

    if name == "build_logs_search":
        limit = int(arguments.get("limit", 200))
        build_id = arguments.get("build_id")
        raw_query = arguments.get("query")
        query = raw_query.strip().lower() if isinstance(raw_query, str) else ""
        stage = arguments.get("stage")
        stage_filter = (
            str(stage).strip()
            if isinstance(stage, str) and str(stage).strip()
            else None
        )
        log_levels = _parse_build_log_levels(arguments.get("log_levels"))
        audience = _parse_build_log_audience(arguments.get("audience"))

        if not build_id:
            builds = await asyncio.to_thread(BuildHistory.get_all, min(limit, 120))
            active_ids = _active_or_pending_build_ids()
            normalized = [
                _normalize_history_build(build, active_ids) for build in builds
            ]
            if query:
                normalized = [
                    build
                    for build in normalized
                    if query
                    in " ".join(
                        [
                            str(build.get("build_id", "")),
                            str(build.get("target", "")),
                            str(build.get("status", "")),
                            str(build.get("error", "")),
                        ]
                    ).lower()
                ]
            return {
                "builds": normalized[:limit],
                "total": len(normalized[:limit]),
                "active_ids": sorted(_active_or_pending_build_ids()),
                "filters": {
                    "query": query or None,
                    "stage": stage_filter,
                    "log_levels": log_levels,
                    "audience": audience,
                },
            }

        clean_build_id = str(build_id)
        history_build = await asyncio.to_thread(BuildHistory.get, clean_build_id)
        logs = await asyncio.to_thread(
            load_build_logs,
            build_id=clean_build_id,
            stage=stage_filter,
            log_levels=log_levels,
            audience=audience,
            count=min(limit, 1000),
        )

        if query:
            logs = [
                entry
                for entry in logs
                if query in str(entry.get("message", "")).lower()
            ]

        synthesized_stub = False
        if not logs:
            logs = [
                _build_empty_log_stub(
                    build_id=clean_build_id,
                    query=query,
                    build=history_build,
                )
            ]
            synthesized_stub = True

        status = None
        error = None
        return_code = None
        if history_build is not None:
            raw_status = _get_build_attr(history_build, "status")
            if isinstance(raw_status, BuildStatus):
                status = raw_status.value
            elif raw_status is not None:
                status = str(raw_status)
            error = _get_build_attr(history_build, "error")
            return_code = _get_build_attr(history_build, "return_code")

        return {
            "build_id": clean_build_id,
            "logs": logs,
            "total": len(logs),
            "synthesized_stub": synthesized_stub,
            "status": status,
            "return_code": return_code,
            "error": error,
            "stage_summary": _summarize_build_stages(history_build),
            "filters": {
                "query": query or None,
                "stage": stage_filter,
                "log_levels": log_levels,
                "audience": audience,
            },
        }

    if name == "design_diagnostics":
        max_problems = int(arguments.get("max_problems", 25))
        max_failure_logs = int(arguments.get("max_failure_logs", 50))

        module_response = await asyncio.to_thread(
            projects_domain.handle_get_modules,
            str(project_root),
            None,
        )
        modules = (
            [module.model_dump(by_alias=True) for module in module_response.modules]
            if module_response
            else []
        )

        active_ids = _active_or_pending_build_ids()
        recent_builds = await asyncio.to_thread(BuildHistory.get_all, 25)
        recent_for_project = [
            _normalize_history_build(build, active_ids)
            for build in recent_builds
            if str(_get_build_attr(build, "project_root", "")) == str(project_root)
        ]

        latest_failed = next(
            (
                build
                for build in recent_for_project
                if build.get("status")
                in {BuildStatus.FAILED.value, BuildStatus.CANCELLED.value}
            ),
            None,
        )
        failure_logs: list[dict[str, Any]] = []
        if latest_failed and latest_failed.get("build_id"):
            failure_logs = await asyncio.to_thread(
                load_build_logs,
                build_id=str(latest_failed["build_id"]),
                stage=None,
                log_levels=["ERROR", "ALERT", "WARNING"],
                audience=None,
                count=min(max_failure_logs, 200),
            )
            if not failure_logs:
                failure_logs = [
                    _build_empty_log_stub(
                        build_id=str(latest_failed["build_id"]),
                        query="",
                        build=await asyncio.to_thread(
                            BuildHistory.get, str(latest_failed["build_id"])
                        ),
                    )
                ]

        problems = await asyncio.to_thread(
            problems_domain.handle_get_problems,
            project_root=str(project_root),
            build_name=None,
            level=None,
            developer_mode=False,
        )
        problems_list = [
            problem.model_dump(by_alias=True) for problem in problems.problems
        ][:max_problems]

        recommendations: list[str] = []
        if latest_failed:
            recommendations.append(
                "Inspect latest_failed_build and latest_failure_logs before rerunning."
            )
        if problems.error_count > 0:
            recommendations.append(
                "Resolve top ERROR-level problems before full rebuild."
            )
        if not recommendations:
            recommendations.append(
                "No immediate blockers detected by quick diagnostics."
            )

        return {
            "project_root": str(project_root),
            "modules_total": len(modules),
            "module_types": _count_modules_by_type(modules),
            "module_examples": [module.get("entry") for module in modules[:12]],
            "recent_builds": recent_for_project[:10],
            "latest_failed_build": latest_failed,
            "latest_failure_logs": failure_logs,
            "problems": {
                "total": problems.total,
                "error_count": problems.error_count,
                "warning_count": problems.warning_count,
                "items": problems_list,
            },
            "recommendations": recommendations,
        }

    if name == "autolayout_run":
        build_target = (
            str(arguments.get("build_target", "default")).strip() or "default"
        )

        raw_constraints = arguments.get("constraints")
        if raw_constraints is None:
            constraints: dict[str, Any] = {}
        elif isinstance(raw_constraints, dict):
            constraints = dict(raw_constraints)
        else:
            raise ValueError("constraints must be an object")

        raw_options = arguments.get("options")
        if raw_options is None:
            options: dict[str, Any] = {}
        elif isinstance(raw_options, dict):
            options = dict(raw_options)
        else:
            raise ValueError("options must be an object")

        job_type = arguments.get("job_type")
        if isinstance(job_type, str) and job_type.strip():
            options.setdefault("jobType", job_type.strip())

        routing_type = arguments.get("routing_type")
        if isinstance(routing_type, str) and routing_type.strip():
            options.setdefault("routingType", routing_type.strip())

        guidance_job_type = str(options.get("jobType", "Routing"))
        component_count: int | None = None
        try:
            build_cfg = _resolve_build_target(project_root, build_target)
            component_count = _estimate_layout_component_count(build_cfg.paths.layout)
        except Exception:
            component_count = None
        timeout_guidance = _recommended_autolayout_timeout(
            component_count=component_count,
            job_type=guidance_job_type,
        )

        timeout_source = "service_default"
        timeout_minutes = arguments.get("timeout_minutes")
        requested_timeout_minutes: int
        if timeout_minutes is not None:
            requested_timeout_minutes = int(timeout_minutes)
            timeout_source = "explicit_argument"
        elif "timeout" in options:
            requested_timeout_minutes = int(options["timeout"])
            timeout_source = "options_object"
        elif "timeout_minutes" in options:
            requested_timeout_minutes = int(options["timeout_minutes"])
            timeout_source = "options_object"
        else:
            requested_timeout_minutes = int(timeout_guidance["start_timeout_minutes"])
            timeout_source = "heuristic_component_count"

        normalized_requested_timeout = max(1, requested_timeout_minutes)
        applied_timeout_minutes = min(
            normalized_requested_timeout,
            _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        )
        timeout_capped = applied_timeout_minutes != normalized_requested_timeout
        options["timeout"] = applied_timeout_minutes
        options.pop("timeout_minutes", None)

        max_batch_timeout = arguments.get("max_batch_timeout")
        if max_batch_timeout is not None:
            options.setdefault("maxBatchTimeout", int(max_batch_timeout))

        webhook_url = arguments.get("webhook_url")
        if isinstance(webhook_url, str) and webhook_url.strip():
            options.setdefault("webhook_url", webhook_url.strip())

        webhook_token = arguments.get("webhook_token")
        if isinstance(webhook_token, str) and webhook_token.strip():
            options.setdefault("webhook_token", webhook_token.strip())

        resume_board_id = arguments.get("resume_board_id")
        if isinstance(resume_board_id, str) and resume_board_id.strip():
            options.setdefault("resume_board_id", resume_board_id.strip())
            options.setdefault(
                "resume_stop_first",
                bool(arguments.get("resume_stop_first", True)),
            )

        service = get_autolayout_service()
        job = await asyncio.to_thread(
            service.start_job,
            str(project_root),
            build_target,
            constraints,
            options,
        )

        return {
            "job_id": job.job_id,
            "provider": job.provider,
            "build_target": job.build_target,
            "state": _autolayout_state_value(job.state),
            "provider_job_ref": job.provider_job_ref,
            "requested_timeout_minutes": normalized_requested_timeout,
            "applied_timeout_minutes": applied_timeout_minutes,
            "timeout_cap_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
            "timeout_capped": timeout_capped,
            "timeout_source": timeout_source,
            "timeout_guidance": timeout_guidance,
            "options": dict(job.options),
            "constraints": dict(job.constraints),
            "background": True,
            "job": job.to_dict(),
            "next_step": (
                "Use autolayout_status with this job_id to monitor candidates, "
                "then autolayout_fetch_to_layout to apply one into layouts/."
            ),
        }

    if name == "autolayout_status":
        requested_job_id = arguments.get("job_id")
        job_id = (
            str(requested_job_id).strip()
            if isinstance(requested_job_id, str) and str(requested_job_id).strip()
            else ""
        )
        refresh = bool(arguments.get("refresh", True))
        include_candidates = bool(arguments.get("include_candidates", True))
        wait_seconds = max(0, int(arguments.get("wait_seconds", 0)))
        poll_interval_seconds = max(
            1,
            int(arguments.get("poll_interval_seconds", 10)),
        )

        service = get_autolayout_service()
        if not job_id:
            jobs = await asyncio.to_thread(service.list_jobs, str(project_root))
            summaries = [_summarize_autolayout_job(job) for job in jobs[:20]]
            latest_job = jobs[0] if jobs else None
            return {
                "job_id": None,
                "project_root": str(project_root),
                "total_jobs": len(summaries),
                "latest_job_id": latest_job.job_id if latest_job else None,
                "latest_build_target": latest_job.build_target if latest_job else None,
                "recommended_action": (
                    "inspect_or_fetch_latest_job"
                    if latest_job is not None
                    else "run_autolayout"
                ),
                "message": (
                    "No job_id provided; returning recent autolayout history for "
                    "this project."
                ),
                "jobs": summaries,
            }

        try:
            if refresh:
                job = await asyncio.to_thread(service.refresh_job, job_id)
            else:
                job = await asyncio.to_thread(service.get_job, job_id)
        except KeyError:
            jobs = await asyncio.to_thread(service.list_jobs, str(project_root))
            summaries = [_summarize_autolayout_job(item) for item in jobs[:20]]
            latest_job = jobs[0] if jobs else None
            return {
                "job_id": job_id,
                "found": False,
                "recommended_action": (
                    "inspect_or_fetch_latest_job"
                    if latest_job is not None
                    else "run_autolayout"
                ),
                "latest_job_id": latest_job.job_id if latest_job else None,
                "message": (
                    f"Unknown autolayout job '{job_id}'. Returning recent jobs "
                    "for this project."
                ),
                "jobs": summaries,
            }

        polls = 0
        waited_seconds = 0
        if refresh and wait_seconds > 0:
            while (
                _autolayout_state_value(job.state)
                in {AutolayoutState.QUEUED.value, AutolayoutState.RUNNING.value}
                and isinstance(job.provider_job_ref, str)
                and job.provider_job_ref.strip()
                and waited_seconds < wait_seconds
            ):
                sleep_for = min(poll_interval_seconds, wait_seconds - waited_seconds)
                await asyncio.sleep(sleep_for)
                waited_seconds += sleep_for
                polls += 1
                job = await asyncio.to_thread(service.refresh_job, job_id)

        candidates_payload: list[dict[str, Any]] = []
        if include_candidates:
            candidates = await asyncio.to_thread(
                service.list_candidates,
                job_id,
                False,
            )
            candidates_payload = [candidate.to_dict() for candidate in candidates]

        state_value = _autolayout_state_value(job.state)
        terminal = state_value in {
            AutolayoutState.COMPLETED.value,
            AutolayoutState.FAILED.value,
            AutolayoutState.CANCELLED.value,
        }

        candidate_count = (
            len(candidates_payload) if include_candidates else len(job.candidates)
        )
        recommended_action = _autolayout_recommended_action(
            state_value=state_value,
            candidate_count=candidate_count,
            provider_job_ref=job.provider_job_ref,
        )
        recent_jobs = await asyncio.to_thread(service.list_jobs, str(project_root))
        recent_summaries = [
            _summarize_autolayout_job(item)
            for item in recent_jobs[:10]
            if item.job_id != job.job_id
        ]

        return {
            "job_id": job.job_id,
            "provider_job_ref": job.provider_job_ref,
            "state": state_value,
            "terminal": terminal,
            "candidate_count": candidate_count,
            "selected_candidate_id": job.selected_candidate_id,
            "applied_candidate_id": job.applied_candidate_id,
            "check_in": {
                "wait_seconds": wait_seconds,
                "waited_seconds": waited_seconds,
                "poll_interval_seconds": poll_interval_seconds,
                "polls": polls,
            },
            "recommended_action": recommended_action,
            "job": job.to_dict(),
            "candidates": candidates_payload if include_candidates else None,
            "recent_jobs": recent_summaries,
        }

    if name == "autolayout_fetch_to_layout":
        requested_job_id = arguments.get("job_id")
        job_id = (
            str(requested_job_id).strip()
            if isinstance(requested_job_id, str) and str(requested_job_id).strip()
            else ""
        )
        requested_candidate_id = arguments.get("candidate_id")
        candidate_id = (
            str(requested_candidate_id).strip()
            if isinstance(requested_candidate_id, str)
            and str(requested_candidate_id).strip()
            else None
        )
        archive_iteration = bool(arguments.get("archive_iteration", True))

        service = get_autolayout_service()
        if not job_id:
            known_jobs = await asyncio.to_thread(service.list_jobs, str(project_root))
            selected_job = _select_latest_fetchable_job(known_jobs)
            if selected_job is None:
                return {
                    "job_id": None,
                    "ready_to_apply": False,
                    "applied": False,
                    "recommended_action": "run_autolayout",
                    "message": (
                        "No autolayout jobs found for this project. Run "
                        "autolayout_run first."
                    ),
                    "jobs": [],
                }
            job_id = selected_job.job_id

        try:
            job = await asyncio.to_thread(service.refresh_job, job_id)
        except KeyError:
            known_jobs = await asyncio.to_thread(service.list_jobs, str(project_root))
            summaries = [_summarize_autolayout_job(item) for item in known_jobs[:20]]
            latest_job = known_jobs[0] if known_jobs else None
            return {
                "job_id": job_id,
                "ready_to_apply": False,
                "applied": False,
                "found": False,
                "recommended_action": (
                    "inspect_or_fetch_latest_job"
                    if latest_job is not None
                    else "run_autolayout"
                ),
                "latest_job_id": latest_job.job_id if latest_job else None,
                "message": (
                    f"Unknown autolayout job '{job_id}'. Returning recent jobs "
                    "for this project."
                ),
                "jobs": summaries,
            }

        candidates = await asyncio.to_thread(service.list_candidates, job_id, False)
        state_value = _autolayout_state_value(job.state)
        candidate_count = len(candidates)

        if state_value in {AutolayoutState.QUEUED.value, AutolayoutState.RUNNING.value}:
            recommended_wait_seconds = _recommended_autolayout_check_back_seconds(
                state=state_value,
                candidate_count=candidate_count,
            )
            return {
                "job_id": job.job_id,
                "provider_job_ref": job.provider_job_ref,
                "state": state_value,
                "candidate_count": candidate_count,
                "ready_to_apply": False,
                "applied": False,
                "recommended_wait_seconds": recommended_wait_seconds,
                "recommended_action": "check_status_then_retry_fetch",
                "message": (
                    f"Autolayout is still {state_value}; do not fetch/apply yet. "
                    f"Check back in {recommended_wait_seconds} seconds with "
                    "autolayout_status, then call autolayout_fetch_to_layout when "
                    "state is awaiting_selection or completed."
                ),
                "job": job.to_dict(),
            }

        if state_value in {
            AutolayoutState.FAILED.value,
            AutolayoutState.CANCELLED.value,
        }:
            return {
                "job_id": job.job_id,
                "provider_job_ref": job.provider_job_ref,
                "state": state_value,
                "candidate_count": candidate_count,
                "ready_to_apply": False,
                "applied": False,
                "recommended_action": "retry_or_resume_with_adjusted_options",
                "message": (
                    f"Autolayout is {state_value}; no candidate can be applied yet. "
                    "Use autolayout_status for details, then rerun or resume with "
                    "autolayout_run."
                ),
                "job": job.to_dict(),
            }

        selected_candidate_id = _choose_autolayout_candidate_id(
            candidates=candidates,
            requested_id=candidate_id,
        )
        if not selected_candidate_id and isinstance(job.provider_job_ref, str):
            selected_candidate_id = job.provider_job_ref
        if not selected_candidate_id:
            raise ValueError(
                "No candidate available yet. Wait for autolayout_status to show "
                "candidates and retry."
            )

        if any(
            _extract_candidate_id(candidate) == selected_candidate_id
            for candidate in candidates
        ):
            await asyncio.to_thread(
                service.select_candidate,
                job_id,
                selected_candidate_id,
            )

        applied = await asyncio.to_thread(
            service.apply_candidate,
            job_id,
            selected_candidate_id,
        )

        downloaded_candidate_path: str | None = None
        downloaded_artifacts: dict[str, str] = {}
        archived_iteration_path: str | None = None
        work_dir_str = str(applied.work_dir or "").strip()
        if work_dir_str:
            work_dir = Path(work_dir_str)
            downloads_dir = work_dir / "downloads"
            downloaded_artifacts = _discover_downloaded_artifacts(
                downloads_dir=downloads_dir,
                candidate_id=selected_candidate_id,
            )
            downloaded_candidate_path = downloaded_artifacts.get("kicad_pcb")

        applied_layout_str = str(
            applied.applied_layout_path or applied.layout_path or ""
        ).strip()
        applied_layout: Path | None = None
        if archive_iteration and applied_layout_str:
            candidate_layout = Path(applied_layout_str)
            if candidate_layout.exists():
                applied_layout = candidate_layout

        if archive_iteration and applied_layout is not None:
            source_for_archive = (
                Path(downloaded_candidate_path)
                if isinstance(downloaded_candidate_path, str)
                and downloaded_candidate_path
                and Path(downloaded_candidate_path).exists()
                else applied_layout
            )
            archived = await asyncio.to_thread(
                _archive_autolayout_iteration,
                source_layout=source_for_archive,
                destination_layout_dir=applied_layout.parent,
                layout_stem=applied_layout.stem,
                build_target=applied.build_target,
                job_id=applied.job_id,
                candidate_id=selected_candidate_id,
            )
            archived_iteration_path = str(archived)

        return {
            "job_id": applied.job_id,
            "provider_job_ref": applied.provider_job_ref,
            "selected_candidate_id": selected_candidate_id,
            "applied_layout_path": applied.applied_layout_path,
            "backup_layout_path": applied.backup_layout_path,
            "downloaded_candidate_path": downloaded_candidate_path,
            "downloaded_artifacts": downloaded_artifacts,
            "archived_iteration_path": archived_iteration_path,
            "job": applied.to_dict(),
        }

    if name == "autolayout_request_screenshot":
        from faebryk.exporters.pcb.kicad.artifacts import (
            KicadCliExportError,
            export_3d_board_render,
            export_svg,
        )

        target = str(arguments.get("target", "default")).strip() or "default"
        view = str(arguments.get("view", "2d")).strip().lower() or "2d"
        if view not in {"2d", "3d", "both"}:
            raise ValueError("view must be one of: 2d, 3d, both")
        side = str(arguments.get("side", "top")).strip().lower() or "top"
        if side not in {"top", "bottom", "both"}:
            raise ValueError("side must be one of: top, bottom, both")

        explicit_layers = _normalize_screenshot_layers(arguments.get("layers"))
        layers = explicit_layers or _default_screenshot_layers(side)
        highlight_components = _normalize_highlight_components(
            arguments.get("highlight_components")
        )
        highlight_fuzzy_limit = max(
            1, min(20, int(arguments.get("highlight_fuzzy_limit", 6)))
        )
        dim_others = bool(arguments.get("dim_others", True))
        dim_opacity = float(arguments.get("dim_opacity", 0.72))
        if dim_opacity < 0.0 or dim_opacity > 1.0:
            raise ValueError("dim_opacity must be between 0.0 and 1.0")

        build_cfg = _resolve_build_target(project_root, target)
        layout_path = build_cfg.paths.layout
        if not layout_path.exists():
            raise ValueError(f"Layout file does not exist: {layout_path}")

        highlighted_records: list[_LayoutComponentRecord] = []
        unresolved_highlights: list[dict[str, Any]] = []
        if highlight_components:
            highlighted_records, unresolved_highlights = await asyncio.to_thread(
                _resolve_highlight_components,
                layout_path=layout_path,
                queries=highlight_components,
                fuzzy_limit=highlight_fuzzy_limit,
            )
        highlighted_references = {
            record.reference
            for record in highlighted_records
            if isinstance(record.reference, str) and record.reference.strip()
        }

        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        output_dir = build_cfg.paths.output_base.parent / "autolayout" / "screenshots"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_paths: dict[str, str] = {}
        highlight_overlay_result: dict[str, Any] | None = None
        try:
            if view in {"2d", "both"}:
                two_d = output_dir / f"{target}.{timestamp}.2d.svg"
                await asyncio.to_thread(
                    export_svg,
                    pcb_file=layout_path,
                    svg_file=two_d,
                    project_dir=layout_path.parent,
                    layers=",".join(layers),
                )
                output_paths["2d"] = str(two_d)

                if dim_others and highlighted_references:
                    highlight_overlay_result = await asyncio.to_thread(
                        _apply_component_highlight_overlay,
                        base_svg_path=two_d,
                        layout_path=layout_path,
                        project_dir=layout_path.parent,
                        layers=layers,
                        highlighted_references=highlighted_references,
                        dim_opacity=dim_opacity,
                    )

            if view in {"3d", "both"}:
                three_d = output_dir / f"{target}.{timestamp}.3d.png"
                await asyncio.to_thread(
                    export_3d_board_render,
                    pcb_file=layout_path,
                    image_file=three_d,
                    project_dir=layout_path.parent,
                )
                output_paths["3d"] = str(three_d)
        except KicadCliExportError as exc:
            raise RuntimeError(f"Failed to render screenshot: {exc}") from exc

        return {
            "success": True,
            "target": target,
            "view": view,
            "side": side,
            "layout_path": str(layout_path),
            "output_dir": str(output_dir),
            "layers": layers if view in {"2d", "both"} else None,
            "drawing_sheet_excluded": True,
            "screenshot_paths": output_paths,
            "highlight": {
                "requested": highlight_components,
                "resolved": [
                    _layout_component_payload(record) for record in highlighted_records
                ],
                "unresolved": unresolved_highlights,
                "dim_others": dim_others,
                "dim_opacity": dim_opacity if dim_others else None,
                "applied": bool(
                    highlight_overlay_result and highlight_overlay_result.get("applied")
                ),
                "overlay_result": highlight_overlay_result,
            },
        }

    if name == "layout_get_component_position":
        target = str(arguments.get("target", "default")).strip() or "default"
        address = str(arguments.get("address", "")).strip()
        if not address:
            raise ValueError("address is required")
        fuzzy_limit = max(1, min(20, int(arguments.get("fuzzy_limit", 6))))

        return await asyncio.to_thread(
            _layout_get_component_position,
            project_root=project_root,
            target=target,
            address=address,
            fuzzy_limit=fuzzy_limit,
        )

    if name == "layout_set_component_position":
        target = str(arguments.get("target", "default")).strip() or "default"
        address = str(arguments.get("address", "")).strip()
        if not address:
            raise ValueError("address is required")

        mode = str(arguments.get("mode", "absolute")).strip().lower() or "absolute"
        x_mm = _to_float_or_none(arguments.get("x_mm"), field_name="x_mm")
        y_mm = _to_float_or_none(arguments.get("y_mm"), field_name="y_mm")
        rotation_deg = _to_float_or_none(
            arguments.get("rotation_deg"),
            field_name="rotation_deg",
        )
        dx_mm = _to_float_or_none(arguments.get("dx_mm"), field_name="dx_mm")
        dy_mm = _to_float_or_none(arguments.get("dy_mm"), field_name="dy_mm")
        drotation_deg = _to_float_or_none(
            arguments.get("drotation_deg"),
            field_name="drotation_deg",
        )
        layer_raw = arguments.get("layer")
        layer = str(layer_raw).strip() if isinstance(layer_raw, str) else None
        fuzzy_limit = max(1, min(20, int(arguments.get("fuzzy_limit", 6))))

        return await asyncio.to_thread(
            _layout_set_component_position,
            project_root=project_root,
            target=target,
            address=address,
            mode=mode,
            x_mm=x_mm,
            y_mm=y_mm,
            rotation_deg=rotation_deg,
            dx_mm=dx_mm,
            dy_mm=dy_mm,
            drotation_deg=drotation_deg,
            layer=layer,
            fuzzy_limit=fuzzy_limit,
        )

    if name == "layout_run_drc":
        from faebryk.libs.kicad.drc import run_drc

        target = str(arguments.get("target", "default")).strip() or "default"
        max_findings = max(1, min(500, int(arguments.get("max_findings", 120))))
        max_items_per_finding = max(
            1, min(20, int(arguments.get("max_items_per_finding", 4)))
        )

        build_cfg = _resolve_build_target(project_root, target)
        layout_path = _resolve_layout_file_for_tool(
            project_root=project_root,
            target=target,
        )
        if not layout_path.exists():
            raise ValueError(f"Layout file does not exist: {layout_path}")

        try:
            drc_report = await asyncio.to_thread(run_drc, layout_path)
        except Exception as exc:  # pragma: no cover - passthrough for runtime failures
            raise RuntimeError(f"Failed to run KiCad DRC: {exc}") from exc

        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        report_dir = build_cfg.paths.output_base.parent / "autolayout" / "drc"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{target}.{timestamp}.drc.json"
        await asyncio.to_thread(drc_report.dumps, report_path)

        severity_rank = {
            "error": 0,
            "warning": 1,
            "action": 2,
            "info": 3,
            "debug": 4,
            "exclusion": 5,
            "": 6,
        }

        findings: list[dict[str, Any]] = []
        severity_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}

        for category_name, entries in (
            ("violations", list(getattr(drc_report, "violations", []) or [])),
            (
                "unconnected_items",
                list(getattr(drc_report, "unconnected_items", []) or []),
            ),
            (
                "schematic_parity",
                list(getattr(drc_report, "schematic_parity", []) or []),
            ),
        ):
            for entry in entries:
                severity = str(getattr(entry, "severity", "") or "").lower()
                violation_type = str(getattr(entry, "type", "") or "").lower()
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                type_counts[violation_type] = type_counts.get(violation_type, 0) + 1

                if len(findings) >= max_findings:
                    continue

                items_payload: list[dict[str, Any]] = []
                for item in list(getattr(entry, "items", []) or [])[
                    :max_items_per_finding
                ]:
                    position = getattr(item, "pos", None)
                    items_payload.append(
                        {
                            "description": str(
                                getattr(item, "description", "") or ""
                            ).strip(),
                            "uuid": str(getattr(item, "uuid", "") or "").strip(),
                            "x_mm": float(getattr(position, "x", 0.0) or 0.0)
                            if position is not None
                            else None,
                            "y_mm": float(getattr(position, "y", 0.0) or 0.0)
                            if position is not None
                            else None,
                        }
                    )

                findings.append(
                    {
                        "category": category_name,
                        "severity": severity or None,
                        "type": violation_type or None,
                        "description": str(
                            getattr(entry, "description", "") or ""
                        ).strip(),
                        "item_count": len(list(getattr(entry, "items", []) or [])),
                        "items": items_payload,
                    }
                )

        findings.sort(
            key=lambda finding: (
                severity_rank.get(str(finding.get("severity", "")).lower(), 99),
                str(finding.get("category", "")),
                str(finding.get("type", "")),
            )
        )

        total_findings = (
            len(list(getattr(drc_report, "violations", []) or []))
            + len(list(getattr(drc_report, "unconnected_items", []) or []))
            + len(list(getattr(drc_report, "schematic_parity", []) or []))
        )

        error_count = severity_counts.get("error", 0)
        warning_count = severity_counts.get("warning", 0)

        top_types = sorted(
            type_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return {
            "success": True,
            "target": target,
            "layout_path": str(layout_path),
            "report_path": str(report_path),
            "kicad_version": str(getattr(drc_report, "kicad_version", "") or ""),
            "date": str(getattr(drc_report, "date", "") or ""),
            "total_findings": total_findings,
            "error_count": error_count,
            "warning_count": warning_count,
            "severity_counts": severity_counts,
            "top_types": [
                {"type": violation_type, "count": count}
                for violation_type, count in top_types[:20]
                if violation_type
            ],
            "clean": error_count == 0 and warning_count == 0 and total_findings == 0,
            "findings": findings,
            "findings_truncated": total_findings > len(findings),
        }

    if name == "autolayout_configure_board_intent":
        build_target = (
            str(arguments.get("build_target", "default")).strip() or "default"
        )
        enable_ground_pours = bool(arguments.get("enable_ground_pours", True))
        plane_nets = _normalize_plane_nets(arguments.get("plane_nets"))
        plane_mode = (
            str(arguments.get("plane_mode", "solid")).strip().lower() or "solid"
        )
        if plane_mode not in {"solid", "hatched"}:
            raise ValueError("plane_mode must be one of: solid, hatched")

        min_plane_clearance_mm = _to_float_or_none(
            arguments.get("min_plane_clearance_mm"),
            field_name="min_plane_clearance_mm",
        )
        layer_count = _to_int_or_none(
            arguments.get("layer_count"),
            field_name="layer_count",
        )
        board_thickness_mm = _to_float_or_none(
            arguments.get("board_thickness_mm"),
            field_name="board_thickness_mm",
        )
        outer_copper_oz = _to_float_or_none(
            arguments.get("outer_copper_oz"),
            field_name="outer_copper_oz",
        )
        inner_copper_oz = _to_float_or_none(
            arguments.get("inner_copper_oz"),
            field_name="inner_copper_oz",
        )
        dielectric_er = _to_float_or_none(
            arguments.get("dielectric_er"),
            field_name="dielectric_er",
        )
        preserve_existing_raw = arguments.get("preserve_existing_routing")
        preserve_existing_routing = (
            bool(preserve_existing_raw)
            if isinstance(preserve_existing_raw, bool)
            else None
        )
        notes = arguments.get("notes")
        notes_clean = (
            str(notes).strip() if isinstance(notes, str) and notes.strip() else None
        )

        data, ato_file = await asyncio.to_thread(
            projects_domain.load_ato_yaml,
            project_root,
        )
        builds = data.get("builds")
        if not isinstance(builds, dict):
            raise ValueError("Invalid ato.yaml: missing builds mapping")
        if build_target not in builds:
            known = ", ".join(sorted(str(key) for key in builds.keys()))
            raise ValueError(
                f"Unknown build_target '{build_target}'. Available: {known}"
            )

        build_cfg = builds.get(build_target)
        if not isinstance(build_cfg, dict):
            raise ValueError(
                "Unsupported build target shape for "
                f"'{build_target}'; expected mapping."
            )

        autolayout_cfg = build_cfg.get("autolayout")
        if not isinstance(autolayout_cfg, dict):
            autolayout_cfg = {}
            build_cfg["autolayout"] = autolayout_cfg

        constraints = autolayout_cfg.get("constraints")
        if not isinstance(constraints, dict):
            constraints = {}
            autolayout_cfg["constraints"] = constraints

        previous_constraints = json.loads(json.dumps(constraints))

        plane_intent: dict[str, Any] = {
            "enabled": enable_ground_pours,
            "nets": plane_nets,
            "mode": plane_mode,
        }
        if min_plane_clearance_mm is not None:
            plane_intent["min_clearance_mm"] = min_plane_clearance_mm
        constraints["plane_intent"] = plane_intent

        stackup_intent: dict[str, Any] = {}
        if layer_count is not None:
            stackup_intent["layer_count"] = layer_count
        if board_thickness_mm is not None:
            stackup_intent["board_thickness_mm"] = board_thickness_mm
        if outer_copper_oz is not None:
            stackup_intent["outer_copper_oz"] = outer_copper_oz
        if inner_copper_oz is not None:
            stackup_intent["inner_copper_oz"] = inner_copper_oz
        if dielectric_er is not None:
            stackup_intent["dielectric_er"] = dielectric_er
        if notes_clean is not None:
            stackup_intent["notes"] = notes_clean
        if stackup_intent:
            constraints["stackup_intent"] = stackup_intent

        if preserve_existing_routing is not None:
            constraints["preserve_existing_routing"] = preserve_existing_routing

        await asyncio.to_thread(projects_domain.save_ato_yaml, ato_file, data)

        return {
            "success": True,
            "build_target": build_target,
            "ato_yaml_path": str(ato_file),
            "plane_intent": plane_intent,
            "stackup_intent": constraints.get("stackup_intent"),
            "preserve_existing_routing": constraints.get("preserve_existing_routing"),
            "constraints_before": previous_constraints,
            "constraints_after": constraints,
            "provider_note": (
                "DeepPCB public API does not currently document first-class "
                "ground-pour/stackup parameters; this stores intent in project "
                "config for agent workflows and future DeepPCB mapping."
            ),
            "next_step": (
                "Run autolayout_run for placement/routing so the updated board "
                "intent is applied."
            ),
        }

    if name == "report_bom":
        target = str(arguments.get("target", "default"))
        data = await asyncio.to_thread(
            artifacts_domain.handle_get_bom, str(project_root), target
        )
        if data is None:
            return {
                "target": target,
                "found": False,
                "message": "BOM not found for target. Run build_run and retry.",
            }
        return {
            "target": target,
            "found": True,
            "bom": data,
            "summary": _build_artifact_summary(
                data,
                preferred_list_keys=(
                    "items",
                    "line_items",
                    "rows",
                    "components",
                    "bom",
                    "entries",
                ),
            ),
        }

    if name == "report_variables":
        target = str(arguments.get("target", "default"))
        data = await asyncio.to_thread(
            artifacts_domain.handle_get_variables,
            str(project_root),
            target,
        )
        if data is None:
            return {
                "target": target,
                "found": False,
                "message": (
                    "Variables report not found for target. Run build_run and retry."
                ),
            }
        return {
            "target": target,
            "found": True,
            "variables": data,
            "summary": _build_artifact_summary(
                data,
                preferred_list_keys=(
                    "variables",
                    "parameters",
                    "params",
                    "values",
                    "entries",
                    "items",
                ),
            ),
        }

    if name == "manufacturing_generate":
        target = str(arguments.get("target", "default")).strip() or "default"
        frozen = bool(arguments.get("frozen", False))

        raw_include_targets = arguments.get("include_targets")
        if raw_include_targets is None:
            include_targets = ["mfg-data"]
        elif isinstance(raw_include_targets, list):
            include_targets = [
                str(value).strip()
                for value in raw_include_targets
                if str(value).strip()
            ]
        else:
            raise ValueError("include_targets must be a list")
        if not include_targets:
            include_targets = ["mfg-data"]

        raw_exclude_targets = arguments.get("exclude_targets")
        if raw_exclude_targets is None:
            exclude_targets: list[str] = []
        elif isinstance(raw_exclude_targets, list):
            exclude_targets = [
                str(value).strip()
                for value in raw_exclude_targets
                if str(value).strip()
            ]
        else:
            raise ValueError("exclude_targets must be a list")

        outputs_before_obj = await asyncio.to_thread(
            manufacturing_domain.get_build_outputs,
            str(project_root),
            target,
        )
        outputs_before = _manufacturing_outputs_dict(outputs_before_obj)
        present_before = _present_output_keys(outputs_before)

        request = BuildRequest(
            project_root=str(project_root),
            targets=[target],
            frozen=frozen,
            include_targets=include_targets,
            exclude_targets=exclude_targets,
        )
        response = await asyncio.to_thread(builds_domain.handle_start_build, request)
        build_targets = [
            {"target": entry.target, "build_id": entry.build_id}
            for entry in response.build_targets
        ]
        queued_build_id = build_targets[0]["build_id"] if build_targets else None

        return {
            "success": response.success,
            "message": response.message,
            "target": target,
            "frozen": frozen,
            "include_targets": include_targets,
            "exclude_targets": exclude_targets,
            "build_targets": build_targets,
            "queued_build_id": queued_build_id,
            "expected_outputs": list(_EXPECTED_MANUFACTURING_OUTPUT_KEYS),
            "outputs_before": outputs_before,
            "present_outputs_before": present_before,
            "missing_outputs_before": [
                key
                for key in _EXPECTED_MANUFACTURING_OUTPUT_KEYS
                if key not in set(present_before)
            ],
            "next_step": (
                "Use build_logs_search with queued_build_id to track progress, "
                "then use manufacturing_summary after completion."
            ),
        }

    if name == "manufacturing_summary":
        target = str(arguments.get("target", "default"))
        quantity = int(arguments.get("quantity", 10))

        outputs = await asyncio.to_thread(
            manufacturing_domain.get_build_outputs,
            str(project_root),
            target,
        )
        estimate = await asyncio.to_thread(
            manufacturing_domain.estimate_cost,
            str(project_root),
            [target],
            quantity,
        )

        return {
            "target": target,
            "outputs": _manufacturing_outputs_dict(outputs),
            "cost_estimate": {
                "total_cost": estimate.total_cost,
                "currency": estimate.currency,
                "quantity": estimate.quantity,
                "pcb_cost": estimate.pcb_cost,
                "components_cost": estimate.components_cost,
                "assembly_cost": estimate.assembly_cost,
            },
        }

    raise ValueError(f"Unknown tool: {name}")


def parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    """Parse JSON function arguments safely."""
    if not raw_arguments:
        return {}
    parsed = json.loads(raw_arguments)
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments must be an object")
    return parsed


def validate_tool_scope(project_root: str, ctx: AppContext) -> Path:
    """Validate and resolve project root for tool execution."""
    return policy.resolve_project_root(project_root, ctx)
