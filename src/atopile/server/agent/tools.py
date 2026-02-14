"""Typed agent tools for atopile operations."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from atopile.server.domains import datasheets as datasheets_domain
from atopile.server.domains import manufacturing as manufacturing_domain
from atopile.server.domains import packages as packages_domain
from atopile.server.domains import parts_search as parts_domain
from atopile.server.domains import problems as problems_domain
from atopile.server.domains import projects as projects_domain
from atopile.server.domains import stdlib as stdlib_domain
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutState,
)
from atopile.server.domains.autolayout.service import get_autolayout_service

_openai_file_client: AsyncOpenAI | None = None
_openai_file_cache: dict[str, str] = {}
_datasheet_read_cache: dict[str, dict[str, Any]] = {}
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


def _datasheet_cache_key(*, project_root: Path, source_type: str, source: str) -> str:
    root = str(project_root.resolve())
    return f"{root}|{source_type}:{source.strip()}"


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
    cached = _openai_file_cache.get(cache_key)
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

    _openai_file_cache[cache_key] = file_id
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
        key=lambda item: _extract_candidate_score(item)
        if _extract_candidate_score(item) is not None
        else float("-inf"),
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
        return {
            "component_count": None,
            "bucket": "unknown",
            "start_timeout_minutes": 10,
            "resume_increment_minutes": 10,
            "note": (
                "Could not estimate component count from layout. Start at 10 minutes "
                "and resume in 10-minute increments."
            ),
        }

    if component_count <= 50:
        start = 2 if normalized_job_type == "placement" else 4
        resume = 2 if normalized_job_type == "placement" else 4
        bucket = "simple"
    elif component_count <= 100:
        start = 10 if normalized_job_type == "placement" else 15
        resume = 5 if normalized_job_type == "placement" else 10
        bucket = "medium"
    elif component_count <= 200:
        start = 20 if normalized_job_type == "placement" else 30
        resume = 10 if normalized_job_type == "placement" else 15
        bucket = "complex"
    else:
        start = 30 if normalized_job_type == "placement" else 45
        resume = 15 if normalized_job_type == "placement" else 20
        bucket = "very_complex"

    return {
        "component_count": component_count,
        "bucket": bucket,
        "start_timeout_minutes": start,
        "resume_increment_minutes": resume,
        "note": (
            "Heuristic guidance based on component count and DeepPCB's stop/resume "
            "workflow. Use autolayout_status checkpoints and resume when quality is "
            "not sufficient."
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
                "Start an autolayout placement or routing run as a background task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "build_target": {"type": "string", "default": "default"},
                    "provider": {"type": ["string", "null"]},
                    "job_type": {
                        "type": "string",
                        "enum": ["Routing", "Placement"],
                        "default": "Routing",
                    },
                    "routing_type": {"type": ["string", "null"]},
                    "timeout_minutes": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 240,
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
                "provider refs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
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
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_fetch_to_layout",
            "description": (
                "Fetch one autolayout candidate into layouts/, apply it, and archive "
                "an iteration snapshot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "candidate_id": {"type": ["string", "null"]},
                    "archive_iteration": {"type": "boolean", "default": True},
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "autolayout_request_screenshot",
            "description": (
                "Queue screenshot render(s) of the current board layout (2D/3D) "
                "as a background build."
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
                    "frozen": {"type": "boolean", "default": False},
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

    if name == "project_rename_path":
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
            cached_payload = _datasheet_read_cache.get(cache_ref)
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
            graph_result: dict[str, Any] | None = None
            graph_error: dict[str, str] | None = None
            try:
                graph_result = await asyncio.to_thread(
                    datasheets_domain.handle_collect_project_datasheets,
                    str(project_root),
                    build_target=target,
                    lcsc_ids=[lcsc_id],
                )
            except Exception as exc:
                graph_error = {
                    "type": type(exc).__name__,
                    "message": _trim_message(str(exc), 420),
                }

            if graph_result is not None:
                matches = graph_result.get("matches", [])
                match = matches[0] if isinstance(matches, list) and matches else None
                if isinstance(match, dict):
                    candidate_path = str(match.get("path") or "").strip()
                    if candidate_path:
                        source_path = candidate_path
                        source_url = None
                        resolution = {
                            "mode": "project_graph",
                            "build_target": graph_result.get("build_target"),
                            "directory": graph_result.get("directory"),
                            "record": {
                                "url": match.get("url"),
                                "filename": match.get("filename"),
                                "lcsc_ids": match.get("lcsc_ids"),
                                "modules": match.get("modules"),
                                "downloaded": match.get("downloaded"),
                                "skipped_existing": match.get("skipped_existing"),
                            },
                        }

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
                    "build_target": (
                        graph_result.get("build_target")
                        if isinstance(graph_result, dict)
                        else target
                    ),
                    "reason": (
                        "No datasheet match for the requested lcsc_id was found in "
                        "the instantiated project graph."
                    ),
                }
                if graph_error is not None:
                    resolution["graph_error"] = graph_error
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
            _datasheet_read_cache[cache_ref] = dict(result_payload)

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
        provider = arguments.get("provider")
        provider_name = (
            str(provider).strip()
            if isinstance(provider, str) and str(provider).strip()
            else None
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

        timeout_source = "provider_default"
        timeout_minutes = arguments.get("timeout_minutes")
        if timeout_minutes is not None:
            options.setdefault("timeout", int(timeout_minutes))
            timeout_source = "explicit_argument"
        elif "timeout" in options or "timeout_minutes" in options:
            timeout_source = "options_object"
        else:
            options.setdefault(
                "timeout",
                int(timeout_guidance["start_timeout_minutes"]),
            )
            timeout_source = "heuristic_component_count"

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
            provider_name,
            constraints,
            options,
        )

        return {
            "job_id": job.job_id,
            "provider": job.provider,
            "build_target": job.build_target,
            "state": _autolayout_state_value(job.state),
            "provider_job_ref": job.provider_job_ref,
            "applied_timeout_minutes": int(options.get("timeout", 10)),
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
        job_id = str(arguments.get("job_id", "")).strip()
        if not job_id:
            raise ValueError("job_id is required")
        refresh = bool(arguments.get("refresh", True))
        include_candidates = bool(arguments.get("include_candidates", True))
        wait_seconds = max(0, int(arguments.get("wait_seconds", 0)))
        poll_interval_seconds = max(
            1,
            int(arguments.get("poll_interval_seconds", 10)),
        )

        service = get_autolayout_service()
        if refresh:
            job = await asyncio.to_thread(service.refresh_job, job_id)
        else:
            job = await asyncio.to_thread(service.get_job, job_id)

        polls = 0
        waited_seconds = 0
        if refresh and wait_seconds > 0:
            while (
                _autolayout_state_value(job.state)
                in {AutolayoutState.QUEUED.value, AutolayoutState.RUNNING.value}
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
        recommended_action: str
        if state_value in {AutolayoutState.QUEUED.value, AutolayoutState.RUNNING.value}:
            recommended_action = "continue_monitoring"
        elif candidate_count > 0:
            recommended_action = "fetch_candidate_to_layout"
        elif state_value == AutolayoutState.FAILED.value:
            recommended_action = "retry_or_resume_with_adjusted_options"
        elif job.provider_job_ref:
            recommended_action = "resume_with_additional_timeout"
        else:
            recommended_action = "inspect_job_details"

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
        }

    if name == "autolayout_fetch_to_layout":
        job_id = str(arguments.get("job_id", "")).strip()
        if not job_id:
            raise ValueError("job_id is required")
        requested_candidate_id = arguments.get("candidate_id")
        candidate_id = (
            str(requested_candidate_id).strip()
            if isinstance(requested_candidate_id, str)
            and str(requested_candidate_id).strip()
            else None
        )
        archive_iteration = bool(arguments.get("archive_iteration", True))

        service = get_autolayout_service()
        job = await asyncio.to_thread(service.refresh_job, job_id)
        candidates = await asyncio.to_thread(service.list_candidates, job_id, False)

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
            None,
        )

        downloaded_candidate_path: str | None = None
        archived_iteration_path: str | None = None
        work_dir_str = str(applied.work_dir or "").strip()
        if work_dir_str:
            work_dir = Path(work_dir_str)
            downloaded = work_dir / "downloads" / f"{selected_candidate_id}.kicad_pcb"
            if downloaded.exists():
                downloaded_candidate_path = str(downloaded)

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
            "archived_iteration_path": archived_iteration_path,
            "job": applied.to_dict(),
        }

    if name == "autolayout_request_screenshot":
        target = str(arguments.get("target", "default")).strip() or "default"
        view = str(arguments.get("view", "2d")).strip().lower() or "2d"
        if view not in {"2d", "3d", "both"}:
            raise ValueError("view must be one of: 2d, 3d, both")
        frozen = bool(arguments.get("frozen", False))

        include_targets: list[str] = []
        if view in {"2d", "both"}:
            include_targets.append("2d-image")
        if view in {"3d", "both"}:
            include_targets.append("3d-image")

        request = BuildRequest(
            project_root=str(project_root),
            targets=[target],
            frozen=frozen,
            include_targets=include_targets,
            exclude_targets=[],
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
            "view": view,
            "frozen": frozen,
            "include_targets": include_targets,
            "build_targets": build_targets,
            "queued_build_id": queued_build_id,
            "expected_outputs": _expected_screenshot_outputs(
                project_root=project_root,
                target=target,
                view=view,
            ),
            "next_step": (
                "Use build_logs_search with queued_build_id until complete, then "
                "read expected_outputs.paths for the generated image files."
            ),
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
                "config for agent workflows and future provider mapping."
            ),
            "next_step": (
                "Run autolayout_run for placement/routing so provider options can "
                "use the updated board intent."
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
