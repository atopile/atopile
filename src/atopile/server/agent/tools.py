"""Typed agent tools for atopile operations."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

import pytest
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
)
from atopile.model import builds as builds_domain
from atopile.model.sqlite import BuildHistory
from atopile.server import module_introspection
from atopile.server.agent import package_workers, policy, tool_layout
from atopile.server.agent.tool_build_helpers import (
    _active_or_pending_build_ids,
    _build_empty_log_stub,
    _get_build_attr,
    _normalize_history_build,
    _parse_build_log_audience,
    _parse_build_log_levels,
    _summarize_build_stages,
    _trim_message,
)
from atopile.server.agent.tool_layout import (
    _layout_get_component_position,
    _layout_set_component_position,
    _resolve_layout_file_for_tool,
)
from atopile.server.agent.tool_references import (
    _collect_example_projects,
    _list_package_reference_files,
    _read_package_reference_file,
    _resolve_example_ato_file,
    _resolve_example_project,
    _resolve_examples_root,
    _search_example_ato_files,
    _search_package_reference_files,
)
from atopile.server.agent.tool_web_helpers import _exa_web_search
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import manufacturing as manufacturing_domain
from atopile.server.domains import packages as packages_domain
from atopile.server.domains import parts_search as parts_domain
from atopile.server.domains import problems as problems_domain
from atopile.server.domains import projects as projects_domain
from atopile.server.domains import stdlib as stdlib_domain

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


def _dedupe_non_empty_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = str(value).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


async def _append_lcsc_jlc_datasheet_candidates(
    *,
    lcsc_id: str,
    candidate_urls: list[str],
    fallback_sources: list[dict[str, Any]],
) -> None:
    try:
        jlc_candidates, jlc_error = await asyncio.to_thread(
            parts_domain.search_jlc_parts,
            lcsc_id,
            limit=6,
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
        return

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


async def _read_first_datasheet_from_urls(
    *,
    project_root: Path,
    candidate_urls: list[str],
) -> tuple[bytes, dict[str, Any], str]:
    last_error: Exception | None = None
    attempted_errors: list[str] = []

    for candidate_url in candidate_urls:
        try:
            datasheet_bytes, metadata = await asyncio.to_thread(
                policy.read_datasheet_file,
                project_root,
                path=None,
                url=candidate_url,
            )
            return datasheet_bytes, metadata, candidate_url
        except Exception as exc:
            last_error = exc
            attempted_errors.append(_trim_message(f"{candidate_url} -> {exc}", 320))

    details = "; ".join(attempted_errors[:3]) or "unknown"
    raise policy.ScopeError(
        f"Failed to fetch datasheet from all resolved URLs ({details})"
    ) from last_error


def _resolve_web_search_content_mode(arguments: dict[str, Any]) -> str:
    raw_mode = arguments.get("content_mode")
    content_mode = str(raw_mode).strip().lower() if raw_mode is not None else ""
    if content_mode and content_mode not in {"none", "highlights", "text"}:
        raise ValueError("content_mode must be one of: none, highlights, text")
    if content_mode:
        return content_mode
    return "highlights"


def _resolve_web_search_max_characters(
    arguments: dict[str, Any],
    *,
    content_mode: str,
) -> int | None:
    raw_max_characters = arguments.get("max_characters")
    if raw_max_characters is None:
        if content_mode == "highlights":
            return 2_000
        if content_mode == "text":
            return 10_000
        return None

    max_characters = int(raw_max_characters)
    return max(200, min(max_characters, 100_000))


def _resolve_web_search_max_age_hours(arguments: dict[str, Any]) -> int | None:
    raw_max_age_hours = arguments.get("max_age_hours")
    if raw_max_age_hours is None:
        return None
    max_age_hours = int(raw_max_age_hours)
    return max(-1, min(max_age_hours, 24 * 365))


def _normalize_domain_filters(raw: Any, *, field_name: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} must be an array of domain strings")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must contain only strings")
        domain = item.strip().lower()
        if not domain or domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)
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


_TOOL_REGISTRY_VALIDATED = False
_INTERNAL_ONLY_TOOL_HANDLERS = frozenset({"datasheet_read"})


def _ensure_tool_registry_consistency(definitions: list[dict[str, Any]]) -> None:
    schema_tool_names = {
        str(item.get("name"))
        for item in definitions
        if isinstance(item, dict)
        and item.get("type") == "function"
        and isinstance(item.get("name"), str)
        and str(item.get("name")).strip()
    }
    handler_tool_names = set(_TOOL_HANDLERS.keys())

    missing_handlers = sorted(schema_tool_names - handler_tool_names)
    missing_schemas = sorted(
        (handler_tool_names - schema_tool_names) - _INTERNAL_ONLY_TOOL_HANDLERS
    )
    if missing_handlers or missing_schemas:
        parts: list[str] = []
        if missing_handlers:
            parts.append("schema without handler: " + ", ".join(missing_handlers[:20]))
        if missing_schemas:
            parts.append("handler without schema: " + ", ".join(missing_schemas[:20]))
        raise RuntimeError("Tool registry/schema mismatch: " + " | ".join(parts))


def get_tool_definitions() -> list[dict[str, Any]]:
    from atopile.server.agent.tool_definitions import get_tool_definitions as _impl

    definitions = _impl()

    global _TOOL_REGISTRY_VALIDATED
    if not _TOOL_REGISTRY_VALIDATED:
        _ensure_tool_registry_consistency(definitions)
        _TOOL_REGISTRY_VALIDATED = True

    return definitions


ToolHandler = Callable[[dict[str, Any], Path, AppContext], Awaitable[dict[str, Any]]]
_TOOL_HANDLERS: dict[str, ToolHandler] = {}


def _register_tool(name: str):
    def _decorator(func: ToolHandler) -> ToolHandler:
        _TOOL_HANDLERS[name] = func
        return func

    return _decorator


def get_tool_names() -> list[str]:
    """Return registered runtime tool handler names."""
    return sorted(_TOOL_HANDLERS.keys())


def _resolve_nested_project_path(project_root: Path, raw_project_path: object) -> Path:
    if not isinstance(raw_project_path, str) or not raw_project_path.strip():
        return project_root

    candidate = (project_root / raw_project_path.strip()).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError("project_path must stay within the selected project") from exc
    return candidate


@_register_tool("project_list_files")
async def _tool_project_list_files(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    limit = int(arguments.get("limit", 300))
    files = await asyncio.to_thread(policy.list_context_files, project_root, limit)
    return {"files": files, "total": len(files)}


@_register_tool("project_read_file")
async def _tool_project_read_file(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    return await asyncio.to_thread(
        policy.read_file_chunk,
        project_root,
        str(arguments.get("path", "")),
        start_line=int(arguments.get("start_line", 1)),
        max_lines=int(arguments.get("max_lines", 220)),
    )


@_register_tool("project_search")
async def _tool_project_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("package_create_local")
async def _tool_package_create_local(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    result = await asyncio.to_thread(
        projects_domain.create_local_package,
        project_root,
        str(arguments.get("name", "")),
        str(arguments.get("entry_module", "")),
        (
            str(arguments.get("description"))
            if isinstance(arguments.get("description"), str)
            else None
        ),
    )
    return {"success": True, **result}


@_register_tool("workspace_list_targets")
async def _tool_workspace_list_targets(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    _ = arguments, ctx
    return await asyncio.to_thread(projects_domain.list_workspace_targets, project_root)


@_register_tool("package_agent_spawn")
async def _tool_package_agent_spawn(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    session_id = getattr(ctx, "agent_session_id", None)
    if not session_id:
        raise RuntimeError("package_agent_spawn requires an agent session context")

    raw_project_path = arguments.get("project_path")
    if not isinstance(raw_project_path, str) or not raw_project_path.strip():
        raise ValueError("project_path is required")
    goal = str(arguments.get("goal", "")).strip()
    if not goal:
        raise ValueError("goal is required")

    comments = str(arguments.get("comments", "")).strip() or None
    selected_targets_raw = arguments.get("selected_targets")
    if isinstance(selected_targets_raw, list):
        selected_targets = [
            str(target).strip()
            for target in selected_targets_raw
            if str(target).strip()
        ]
    else:
        selected_targets = []

    worker = await package_workers.spawn_package_worker(
        ctx=ctx,
        parent_session_id=session_id,
        parent_run_id=getattr(ctx, "agent_run_id", None),
        parent_project_root=project_root,
        package_project_path=raw_project_path.strip(),
        goal=goal,
        comments=comments,
        selected_targets=selected_targets,
    )
    return {
        "success": True,
        "worker_id": worker["worker_id"],
        "package_project_path": worker["package_project_path"],
        "status": worker["status"],
    }


@_register_tool("package_agent_list")
async def _tool_package_agent_list(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    _ = arguments, project_root
    session_id = getattr(ctx, "agent_session_id", None)
    if not session_id:
        raise RuntimeError("package_agent_list requires an agent session context")
    workers = package_workers.list_package_workers(
        session_id=session_id, parent_run_id=getattr(ctx, "agent_run_id", None)
    )
    return {"workers": workers, "total": len(workers)}


@_register_tool("package_agent_get")
async def _tool_package_agent_get(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    _ = project_root, ctx
    worker_id = str(arguments.get("worker_id", "")).strip()
    if not worker_id:
        raise ValueError("worker_id is required")
    worker = package_workers.get_package_worker(worker_id)
    if worker is None:
        raise ValueError(f"Unknown package worker: {worker_id}")
    return worker


@_register_tool("package_agent_wait")
async def _tool_package_agent_wait(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    _ = project_root, ctx
    worker_id = str(arguments.get("worker_id", "")).strip()
    if not worker_id:
        raise ValueError("worker_id is required")
    raw_timeout = arguments.get("timeout_seconds")
    timeout_seconds = float(raw_timeout) if raw_timeout is not None else None
    worker = await package_workers.wait_for_package_worker(
        worker_id, timeout_seconds=timeout_seconds
    )
    if worker is None:
        raise ValueError(f"Unknown package worker: {worker_id}")
    return worker


@_register_tool("package_agent_message")
async def _tool_package_agent_message(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    _ = project_root, ctx
    worker_id = str(arguments.get("worker_id", "")).strip()
    message = str(arguments.get("message", "")).strip()
    if not worker_id:
        raise ValueError("worker_id is required")
    if not message:
        raise ValueError("message is required")
    worker = package_workers.message_package_worker(worker_id, message)
    if worker is None:
        raise ValueError(f"Unknown package worker: {worker_id}")
    return {
        "success": True,
        "worker_id": worker["worker_id"],
        "status": worker["status"],
        "queued_message": message,
    }


@_register_tool("package_agent_stop")
async def _tool_package_agent_stop(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    _ = project_root, ctx
    worker_id = str(arguments.get("worker_id", "")).strip()
    if not worker_id:
        raise ValueError("worker_id is required")
    worker = package_workers.stop_package_worker(worker_id)
    if worker is None:
        raise ValueError(f"Unknown package worker: {worker_id}")
    return {
        "success": True,
        "worker_id": worker["worker_id"],
        "status": worker["status"],
    }


@_register_tool("web_search")
async def _tool_web_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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
    content_mode = _resolve_web_search_content_mode(arguments)
    max_characters = _resolve_web_search_max_characters(
        arguments,
        content_mode=content_mode,
    )
    max_age_hours = _resolve_web_search_max_age_hours(arguments)
    timeout_s = float(os.getenv("ATOPILE_AGENT_EXA_TIMEOUT_S", "30"))
    timeout_s = max(3.0, min(timeout_s, 120.0))
    hard_timeout_s = timeout_s + 5.0

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _exa_web_search,
                query=query,
                num_results=num_results,
                search_type=search_type,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                content_mode=content_mode,
                max_characters=max_characters,
                max_age_hours=max_age_hours,
                timeout_s=timeout_s,
            ),
            timeout=hard_timeout_s,
        )
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            f"web_search timed out after {hard_timeout_s:.0f}s "
            f"(HTTP timeout={timeout_s:.0f}s)"
        ) from exc


@_register_tool("examples_list")
async def _tool_examples_list(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    limit = int(arguments.get("limit", 60))
    include_without_ato_yaml = bool(arguments.get("include_without_ato_yaml", False))
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


@_register_tool("examples_search")
async def _tool_examples_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("examples_read_ato")
async def _tool_examples_read_ato(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("package_ato_list")
async def _tool_package_ato_list(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("package_ato_search")
async def _tool_package_ato_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("package_ato_read")
async def _tool_package_ato_read(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("project_list_modules")
async def _tool_project_list_modules(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    type_filter = arguments.get("type_filter")
    limit = int(arguments.get("limit", 200))
    response = await asyncio.to_thread(
        projects_domain.handle_get_modules,
        str(project_root),
        str(type_filter) if isinstance(type_filter, str) and type_filter else None,
    )
    if response is None:
        return {"modules": [], "total": 0, "returned": 0, "types": {}}
    modules = [module.model_dump(by_alias=True) for module in response.modules][:limit]
    return {
        "modules": modules,
        "total": response.total,
        "returned": len(modules),
        "types": _count_modules_by_type(modules),
    }


@_register_tool("project_module_children")
async def _tool_project_module_children(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("stdlib_list")
async def _tool_stdlib_list(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("stdlib_get_item")
async def _tool_stdlib_get_item(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("project_edit_file")
async def _tool_project_edit_file(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    edits = arguments.get("edits")
    if not isinstance(edits, list):
        raise ValueError("edits must be a list")
    return await asyncio.to_thread(
        policy.apply_hashline_edits,
        project_root,
        str(arguments.get("path", "")),
        edits,
    )


@_register_tool("project_create_path")
async def _tool_project_create_path(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("project_move_path")
async def _tool_project_move_path(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    return await asyncio.to_thread(
        policy.rename_path,
        project_root,
        str(arguments.get("old_path", "")),
        str(arguments.get("new_path", "")),
        overwrite=bool(arguments.get("overwrite", False)),
    )


@_register_tool("project_delete_path")
async def _tool_project_delete_path(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    return await asyncio.to_thread(
        policy.delete_path,
        project_root,
        str(arguments.get("path", "")),
        recursive=bool(arguments.get("recursive", True)),
    )


@_register_tool("parts_search")
async def _tool_parts_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    parts, error = await asyncio.to_thread(
        parts_domain.handle_search_parts,
        str(arguments.get("query", "")).strip(),
        limit=int(arguments.get("limit", 20)),
    )
    return {"parts": parts, "total": len(parts), "error": error}


@_register_tool("parts_install")
async def _tool_parts_install(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    lcsc_id = str(arguments.get("lcsc_id", "")).strip().upper()
    create_package = bool(arguments.get("create_package", False))
    install_root = _resolve_nested_project_path(
        project_root, arguments.get("project_path")
    )

    if not create_package:
        result = await asyncio.to_thread(
            parts_domain.handle_install_part,
            lcsc_id,
            str(install_root),
        )
        payload = {
            "success": True,
            "lcsc_id": lcsc_id,
            "implementation_hint": (
                "For complex parts (MCUs/sensors/PMICs/radios), use "
                "web_search next to inspect the vendor datasheet, hardware "
                "design guides, and required support circuitry."
            ),
            **result,
        }
        if install_root != project_root:
            payload["projectPath"] = str(install_root.relative_to(project_root))
        return payload

    result = await asyncio.to_thread(
        parts_domain.handle_install_part_as_package,
        lcsc_id,
        str(install_root),
    )

    payload = {
        "success": True,
        "lcsc_id": lcsc_id,
        "implementation_hint": (
            "For complex parts (MCUs/sensors/PMICs/radios), use "
            "web_search next to inspect the vendor datasheet, hardware "
            "design guides, and required support circuitry."
        ),
        **result,
    }
    if install_root != project_root:
        payload["projectPath"] = str(install_root.relative_to(project_root))
    return payload


@_register_tool("datasheet_read")
async def _tool_datasheet_read(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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
    url = str(raw_url).strip() if isinstance(raw_url, str) and raw_url.strip() else None
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
            await _append_lcsc_jlc_datasheet_candidates(
                lcsc_id=lcsc_id,
                candidate_urls=candidate_urls,
                fallback_sources=fallback_sources,
            )

        candidate_urls = _dedupe_non_empty_strings(candidate_urls)
        if not candidate_urls:
            raise policy.ScopeError(
                "No datasheet URL could be resolved for this request."
            )

        datasheet_bytes, metadata, selected_url = await _read_first_datasheet_from_urls(
            project_root=project_root,
            candidate_urls=candidate_urls,
        )

        if selected_url and source_url and selected_url != source_url:
            resolution = {
                **resolution,
                "url_fallback": {
                    "selected_url": selected_url,
                    "primary_url": source_url,
                    "attempted_urls": len(candidate_urls),
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
        "message": ("Datasheet uploaded and attached for model-native PDF reasoning."),
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


@_register_tool("packages_search")
async def _tool_packages_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    result = await asyncio.to_thread(
        packages_domain.handle_search_registry,
        str(arguments.get("query", "")),
        project_root,
    )
    return result.model_dump(by_alias=True)


@_register_tool("packages_install")
async def _tool_packages_install(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("build_run")
async def _tool_build_run(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    targets = arguments.get("targets") or []
    if not isinstance(targets, list):
        raise ValueError("targets must be a list")
    include_targets = arguments.get("include_targets") or []
    if not isinstance(include_targets, list):
        raise ValueError("include_targets must be a list")
    exclude_targets = arguments.get("exclude_targets") or []
    if not isinstance(exclude_targets, list):
        raise ValueError("exclude_targets must be a list")
    build_root = _resolve_nested_project_path(
        project_root, arguments.get("project_path")
    )

    request = BuildRequest(
        project_root=str(build_root),
        targets=[str(target) for target in targets],
        entry=(str(arguments["entry"]) if arguments.get("entry") else None),
        standalone=bool(arguments.get("standalone", False)),
        frozen=bool(arguments.get("frozen", False)),
        include_targets=[str(target) for target in include_targets],
        exclude_targets=[str(target) for target in exclude_targets],
    )
    response = await asyncio.to_thread(builds_domain.handle_start_build, request)
    payload = response.model_dump(by_alias=True)
    if build_root != project_root:
        payload["projectPath"] = str(build_root.relative_to(project_root))
    return payload


@_register_tool("build_create")
async def _tool_build_create(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    request = AddBuildTargetRequest(
        project_root=str(project_root),
        name=str(arguments.get("name", "")),
        entry=str(arguments.get("entry", "")),
    )
    result = await asyncio.to_thread(projects_domain.handle_add_build_target, request)
    return result.model_dump(by_alias=True)


@_register_tool("build_rename")
async def _tool_build_rename(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    request = UpdateBuildTargetRequest(
        project_root=str(project_root),
        old_name=str(arguments.get("old_name", "")),
        new_name=(str(arguments["new_name"]) if arguments.get("new_name") else None),
        new_entry=(str(arguments["new_entry"]) if arguments.get("new_entry") else None),
    )
    result = await asyncio.to_thread(
        projects_domain.handle_update_build_target,
        request,
    )
    return result.model_dump(by_alias=True)


@_register_tool("build_logs_search")
async def _tool_build_logs_search(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    limit = int(arguments.get("limit", 200))
    build_id = arguments.get("build_id")
    raw_query = arguments.get("query")
    query = raw_query.strip().lower() if isinstance(raw_query, str) else ""
    stage = arguments.get("stage")
    stage_filter = (
        str(stage).strip() if isinstance(stage, str) and str(stage).strip() else None
    )
    log_levels = _parse_build_log_levels(arguments.get("log_levels"))
    audience = _parse_build_log_audience(arguments.get("audience"))

    if not build_id:
        builds = await asyncio.to_thread(BuildHistory.get_all, min(limit, 120))
        active_ids = _active_or_pending_build_ids()
        normalized = [_normalize_history_build(build, active_ids) for build in builds]
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
            entry for entry in logs if query in str(entry.get("message", "")).lower()
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
        raw_error = _get_build_attr(history_build, "error")
        if raw_error is not None:
            error = _trim_message(str(raw_error))
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


@_register_tool("design_diagnostics")
async def _tool_design_diagnostics(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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
        recommendations.append("Resolve top ERROR-level problems before full rebuild.")
    if not recommendations:
        recommendations.append("No immediate blockers detected by quick diagnostics.")

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


@_register_tool("layout_get_component_position")
async def _tool_layout_get_component_position(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("layout_set_component_position")
async def _tool_layout_set_component_position(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("layout_run_drc")
async def _tool_layout_run_drc(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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
    report_dir = build_cfg.paths.output_base.parent / "layout" / "drc"
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
            for item in list(getattr(entry, "items", []) or [])[:max_items_per_finding]:
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
                    "description": str(getattr(entry, "description", "") or "").strip(),
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


@_register_tool("report_bom")
async def _tool_report_bom(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("report_variables")
async def _tool_report_variables(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("manufacturing_generate")
async def _tool_manufacturing_generate(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    target = str(arguments.get("target", "default")).strip() or "default"
    frozen = bool(arguments.get("frozen", False))

    raw_include_targets = arguments.get("include_targets")
    if raw_include_targets is None:
        include_targets = ["mfg-data"]
    elif isinstance(raw_include_targets, list):
        include_targets = [
            str(value).strip() for value in raw_include_targets if str(value).strip()
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
            str(value).strip() for value in raw_exclude_targets if str(value).strip()
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


@_register_tool("manufacturing_summary")
async def _tool_manufacturing_summary(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
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


@_register_tool("checklist_create")
async def _tool_checklist_create(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("checklist_create is intercepted by the runner")


@_register_tool("checklist_update")
async def _tool_checklist_update(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("checklist_update is intercepted by the runner")


@_register_tool("checklist_add_items")
async def _tool_checklist_add_items(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("checklist_add_items is intercepted by the runner")


@_register_tool("message_acknowledge")
async def _tool_message_acknowledge(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("message_acknowledge is intercepted by the runner")


@_register_tool("message_log_query")
async def _tool_message_log_query(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("message_log_query is intercepted by the runner")


@_register_tool("design_questions")
async def _tool_design_questions(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("design_questions is intercepted by the runner")


@_register_tool("layout_set_board_shape")
async def _tool_layout_set_board_shape(
    arguments: dict[str, Any], project_root: Path, ctx: AppContext
) -> dict[str, Any]:
    raise RuntimeError("layout_set_board_shape is not yet implemented")


async def execute_tool(
    *,
    name: str,
    arguments: dict[str, Any],
    project_root: Path,
    ctx: AppContext,
) -> dict[str, Any]:
    """Execute a named agent tool with typed arguments."""
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return await handler(arguments, project_root, ctx)


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


# ----------------------------------------
#                 Tests
# ----------------------------------------

"""Agent module tests moved from colocated runtime modules."""


def _run(coro):
    return asyncio.run(coro)


def _agent_ctx(
    tmp_path: Path, *, session_id: str = "session-1", run_id: str = "run-1"
) -> AppContext:
    ctx = AppContext(workspace_paths=[tmp_path])
    setattr(ctx, "agent_session_id", session_id)
    setattr(ctx, "agent_run_id", run_id)
    return ctx


@pytest.fixture(autouse=True)
def _clear_agent_tool_caches() -> None:
    _openai_file_cache.clear()
    _datasheet_read_cache.clear()


@dataclass
class _FakeAt:
    x: float
    y: float
    r: float


@dataclass
class _FakeFootprint:
    at: _FakeAt
    layer: str


def _make_layout_record(
    *,
    reference: str,
    atopile_address: str,
    x: float,
    y: float,
    r: float,
    layer: str = "F.Cu",
) -> tool_layout._LayoutComponentRecord:
    footprint = _FakeFootprint(at=_FakeAt(x=x, y=y, r=r), layer=layer)
    return tool_layout._LayoutComponentRecord(
        reference=reference,
        atopile_address=atopile_address,
        layer=layer,
        x_mm=x,
        y_mm=y,
        rotation_deg=r,
        footprint=footprint,
    )


class TestAgentToolsHashline:
    def test_tool_definitions_advertise_hashline_editor(self) -> None:
        definitions = {
            tool_def["name"]: tool_def for tool_def in get_tool_definitions()
        }
        names = set(definitions)

        assert "package_create_local" in names
        assert "workspace_list_targets" in names
        assert "package_agent_spawn" in names
        assert "package_agent_list" in names
        assert "package_agent_get" in names
        assert "package_agent_wait" in names
        assert "package_agent_message" in names
        assert "package_agent_stop" in names
        assert "project_edit_file" in names
        assert "project_list_modules" in names
        assert "project_module_children" in names
        assert "web_search" in names
        assert "examples_list" in names
        assert "examples_search" in names
        assert "examples_read_ato" in names
        assert "stdlib_list" in names
        assert "stdlib_get_item" in names
        assert "design_diagnostics" in names
        assert "project_create_path" in names
        assert "project_move_path" in names
        assert "project_delete_path" in names
        assert "manufacturing_generate" in names
        assert "layout_get_component_position" in names
        assert "layout_set_component_position" in names
        assert "project_write_file" not in names
        assert "project_replace_text" not in names
        assert "create_package=true" in definitions["parts_install"]["description"]
        assert (
            "project_path" in definitions["parts_install"]["parameters"]["properties"]
        )
        assert "package-specialist" in definitions["package_agent_spawn"]["description"]
        assert (
            "project_path"
            in definitions["package_agent_spawn"]["parameters"]["properties"]
        )
        assert "local sub-package" in definitions["package_create_local"]["description"]
        assert (
            "discover new build targets"
            in definitions["workspace_list_targets"]["description"]
        )

    def test_package_agent_spawn_executes_with_parent_context(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        captured: dict[str, object] = {}

        async def fake_spawn_package_worker(**kwargs):
            captured.update(kwargs)
            return {
                "worker_id": "worker-123",
                "package_project_path": "packages/rp2350",
                "status": "running",
            }

        monkeypatch.setattr(
            package_workers, "spawn_package_worker", fake_spawn_package_worker
        )

        result = _run(
            execute_tool(
                name="package_agent_spawn",
                arguments={
                    "project_path": "packages/rp2350",
                    "goal": "Build a generic RP2350 wrapper package",
                    "comments": "Prioritize USB and SWD.",
                    "selected_targets": ["default"],
                },
                project_root=tmp_path,
                ctx=_agent_ctx(tmp_path),
            )
        )

        assert result["success"] is True
        assert result["worker_id"] == "worker-123"
        assert captured["parent_session_id"] == "session-1"
        assert captured["parent_run_id"] == "run-1"
        assert captured["package_project_path"] == "packages/rp2350"
        assert captured["goal"] == "Build a generic RP2350 wrapper package"
        assert captured["comments"] == "Prioritize USB and SWD."
        assert captured["selected_targets"] == ["default"]

    def test_package_agent_spawn_requires_agent_session_context(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(
            RuntimeError, match="package_agent_spawn requires an agent session context"
        ):
            _run(
                execute_tool(
                    name="package_agent_spawn",
                    arguments={
                        "project_path": "packages/rp2350",
                        "goal": "Build a generic RP2350 wrapper package",
                    },
                    project_root=tmp_path,
                    ctx=AppContext(workspace_paths=[tmp_path]),
                )
            )

    def test_execute_tool_allows_read_tool(self, tmp_path: Path) -> None:
        (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

        result = _run(
            execute_tool(
                name="project_read_file",
                arguments={"path": "main.ato", "start_line": 1, "max_lines": 20},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["path"] == "main.ato"
        assert "module App:" in result["content"]

    def test_web_search_executes_with_exa_adapter(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        captured: dict[str, object] = {}

        def fake_exa_web_search(
            *,
            query: str,
            num_results: int,
            search_type: str,
            include_domains: list[str],
            exclude_domains: list[str],
            content_mode: str,
            max_characters: int | None,
            max_age_hours: int | None,
            timeout_s: float,
        ) -> dict[str, object]:
            captured["query"] = query
            captured["num_results"] = num_results
            captured["search_type"] = search_type
            captured["include_domains"] = include_domains
            captured["exclude_domains"] = exclude_domains
            captured["content_mode"] = content_mode
            captured["max_characters"] = max_characters
            captured["max_age_hours"] = max_age_hours
            captured["timeout_s"] = timeout_s
            return {
                "query": query,
                "returned_results": 1,
                "results": [
                    {
                        "rank": 1,
                        "title": "Example",
                        "url": "https://example.com",
                        "text": "snippet",
                    }
                ],
                "source": "exa",
            }

        monkeypatch.setattr(
            sys.modules[__name__], "_exa_web_search", fake_exa_web_search
        )

        result = _run(
            execute_tool(
                name="web_search",
                arguments={
                    "query": "stm32 usb bootloader notes",
                    "num_results": 5,
                    "search_type": "neural",
                    "include_domains": ["st.com"],
                    "exclude_domains": ["example.com"],
                    "content_mode": "text",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["source"] == "exa"
        assert result["returned_results"] == 1
        assert captured["query"] == "stm32 usb bootloader notes"
        assert captured["num_results"] == 5
        assert captured["search_type"] == "neural"
        assert captured["include_domains"] == ["st.com"]
        assert captured["exclude_domains"] == ["example.com"]
        assert captured["content_mode"] == "text"
        assert captured["max_characters"] == 10_000
        assert captured["max_age_hours"] is None

    def test_layout_get_component_position_returns_exact_match(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        layout_path = tmp_path / "layouts" / "default" / "default.kicad_pcb"
        layout_path.parent.mkdir(parents=True)
        layout_path.write_text("(kicad_pcb)\n", encoding="utf-8")
        records = [
            _make_layout_record(
                reference="U1",
                atopile_address="App.mcu",
                x=12.5,
                y=8.0,
                r=90.0,
            )
        ]

        monkeypatch.setattr(
            tool_layout,
            "_resolve_layout_file_for_tool",
            lambda *, project_root, target: layout_path,
        )
        monkeypatch.setattr(
            tool_layout,
            "_load_layout_component_index",
            lambda _layout_path: (object(), records),
        )

        result = _layout_get_component_position(
            project_root=tmp_path,
            target="default",
            address="App.mcu",
            fuzzy_limit=5,
        )

        assert result["found"] is True
        assert result["matched_by"] == "atopile_address_exact"
        assert result["component"]["reference"] == "U1"
        assert result["component"]["x_mm"] == pytest.approx(12.5)
        assert result["component"]["rotation_deg"] == pytest.approx(90.0)

    def test_layout_get_component_position_returns_fuzzy_suggestions(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        layout_path = tmp_path / "layouts" / "default" / "default.kicad_pcb"
        layout_path.parent.mkdir(parents=True)
        layout_path.write_text("(kicad_pcb)\n", encoding="utf-8")
        records = [
            _make_layout_record(
                reference="U1",
                atopile_address="App.mcu",
                x=10.0,
                y=10.0,
                r=0.0,
            ),
            _make_layout_record(
                reference="J1",
                atopile_address="App.usb",
                x=2.0,
                y=4.0,
                r=180.0,
            ),
        ]

        monkeypatch.setattr(
            tool_layout,
            "_resolve_layout_file_for_tool",
            lambda *, project_root, target: layout_path,
        )
        monkeypatch.setattr(
            tool_layout,
            "_load_layout_component_index",
            lambda _layout_path: (object(), records),
        )

        result = _layout_get_component_position(
            project_root=tmp_path,
            target="default",
            address="App.mcc",
            fuzzy_limit=3,
        )

        assert result["found"] is False
        assert result["suggestions"]
        assert result["suggestions"][0]["reference"] == "U1"
        assert result["suggestions"][0]["score"] >= 0.35

    def test_layout_set_component_position_supports_absolute_and_relative(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        layout_path = tmp_path / "layouts" / "default" / "default.kicad_pcb"
        layout_path.parent.mkdir(parents=True)
        layout_path.write_text("(kicad_pcb)\n", encoding="utf-8")
        record = _make_layout_record(
            reference="U1",
            atopile_address="App.mcu",
            x=10.0,
            y=6.0,
            r=15.0,
            layer="F.Cu",
        )

        monkeypatch.setattr(
            tool_layout,
            "_resolve_layout_file_for_tool",
            lambda *, project_root, target: layout_path,
        )
        footprint = record.footprint

        def fake_load_layout_index(_layout_path: Path):
            refreshed = tool_layout._LayoutComponentRecord(
                reference="U1",
                atopile_address="App.mcu",
                layer=footprint.layer,
                x_mm=footprint.at.x,
                y_mm=footprint.at.y,
                rotation_deg=footprint.at.r,
                footprint=footprint,
            )
            return object(), [refreshed]

        monkeypatch.setattr(
            tool_layout,
            "_load_layout_component_index",
            fake_load_layout_index,
        )
        monkeypatch.setattr(
            tool_layout,
            "_write_layout_component_file",
            lambda _layout_path, _pcb_file: None,
        )

        def fake_move_fp(footprint: _FakeFootprint, coord, layer: str) -> None:
            footprint.at.x = float(coord.x)
            footprint.at.y = float(coord.y)
            footprint.at.r = float(coord.r)
            footprint.layer = layer

        monkeypatch.setattr(
            "faebryk.exporters.pcb.kicad.transformer.PCB_Transformer.move_fp",
            fake_move_fp,
        )

        absolute = _layout_set_component_position(
            project_root=tmp_path,
            target="default",
            address="App.mcu",
            mode="absolute",
            x_mm=25.0,
            y_mm=30.0,
            rotation_deg=45.0,
            dx_mm=None,
            dy_mm=None,
            drotation_deg=None,
            layer="B.Cu",
            fuzzy_limit=5,
        )
        assert absolute["updated"] is True
        assert absolute["after"]["x_mm"] == pytest.approx(25.0)
        assert absolute["after"]["y_mm"] == pytest.approx(30.0)
        assert absolute["after"]["rotation_deg"] == pytest.approx(45.0)
        assert absolute["after"]["layer"] == "B.Cu"

        relative = _layout_set_component_position(
            project_root=tmp_path,
            target="default",
            address="App.mcu",
            mode="relative",
            x_mm=None,
            y_mm=None,
            rotation_deg=None,
            dx_mm=-1.5,
            dy_mm=2.0,
            drotation_deg=10.0,
            layer=None,
            fuzzy_limit=5,
        )
        assert relative["updated"] is True
        assert relative["after"]["x_mm"] == pytest.approx(23.5)
        assert relative["after"]["y_mm"] == pytest.approx(32.0)
        assert relative["after"]["rotation_deg"] == pytest.approx(55.0)
        assert relative["delta"]["dx_mm"] == pytest.approx(-1.5)
        assert relative["delta"]["dy_mm"] == pytest.approx(2.0)
        assert relative["delta"]["drotation_deg"] == pytest.approx(10.0)

    def test_examples_tools_list_search_and_read(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        examples_root = tmp_path / "examples"
        quickstart = examples_root / "quickstart"
        quickstart.mkdir(parents=True)
        (quickstart / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
        (quickstart / "quickstart.ato").write_text(
            "import Resistor\n\nmodule App:\n    r1 = new Resistor\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            sys.modules[__name__],
            "_resolve_examples_root",
            lambda _project_root: examples_root,
        )

        listed = _run(
            execute_tool(
                name="examples_list",
                arguments={},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert listed["total"] == 1
        assert listed["examples"][0]["name"] == "quickstart"
        assert listed["examples"][0]["ato_files"] == ["quickstart.ato"]

        searched = _run(
            execute_tool(
                name="examples_search",
                arguments={"query": "new Resistor"},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert searched["total"] == 1
        assert searched["matches"][0]["example"] == "quickstart"
        assert searched["matches"][0]["line"] == 4

        read = _run(
            execute_tool(
                name="examples_read_ato",
                arguments={"example": "quickstart", "start_line": 1, "max_lines": 20},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert read["example"] == "quickstart"
        assert read["path"] == "quickstart.ato"
        assert "module App:" in read["content"]

    def test_project_read_file_returns_hashline_content(self, tmp_path: Path) -> None:
        file_path = tmp_path / "main.ato"
        file_path.write_text("a\nb\n", encoding="utf-8")

        result = _run(
            execute_tool(
                name="project_read_file",
                arguments={"path": "main.ato", "start_line": 1, "max_lines": 10},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["path"] == "main.ato"
        lines = result["content"].splitlines()
        assert re.fullmatch(r"1:[0-9a-f]{4}\|a", lines[0])
        assert re.fullmatch(r"2:[0-9a-f]{4}\|b", lines[1])

    def test_project_edit_file_executes_atomic_edit(self, tmp_path: Path) -> None:
        file_path = tmp_path / "main.ato"
        file_path.write_text("a\nb\nc\n", encoding="utf-8")
        anchor = f"2:{policy.compute_line_hash(2, 'b')}"

        result = _run(
            execute_tool(
                name="project_edit_file",
                arguments={
                    "path": "main.ato",
                    "edits": [
                        {
                            "set_line": {
                                "anchor": anchor,
                                "new_text": "B",
                            }
                        }
                    ],
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["operations_applied"] == 1
        assert result["first_changed_line"] == 2
        assert file_path.read_text(encoding="utf-8") == "a\nB\nc\n"

    def test_project_move_and_delete_path_execute(self, tmp_path: Path) -> None:
        source = tmp_path / "notes.md"
        source.write_text("hello\n", encoding="utf-8")

        moved = _run(
            execute_tool(
                name="project_move_path",
                arguments={"old_path": "notes.md", "new_path": "docs/notes.md"},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert moved["old_path"] == "notes.md"
        assert moved["new_path"] == "docs/notes.md"
        assert moved["kind"] == "file"
        assert (tmp_path / "docs" / "notes.md").exists()
        assert not source.exists()

        deleted = _run(
            execute_tool(
                name="project_delete_path",
                arguments={"path": "docs/notes.md"},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert deleted["path"] == "docs/notes.md"
        assert deleted["deleted"] is True
        assert not (tmp_path / "docs" / "notes.md").exists()

    def test_project_create_and_move_path_execute(self, tmp_path: Path) -> None:
        created_dir = _run(
            execute_tool(
                name="project_create_path",
                arguments={"path": "plans", "kind": "directory"},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert created_dir["path"] == "plans"
        assert created_dir["kind"] == "directory"
        assert created_dir["created"] is True

        created_file = _run(
            execute_tool(
                name="project_create_path",
                arguments={
                    "path": "plans/notes.md",
                    "kind": "file",
                    "content": "# Notes\n",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert created_file["path"] == "plans/notes.md"
        assert created_file["kind"] == "file"
        assert created_file["extension"] == ".md"

        created_fabll_py = _run(
            execute_tool(
                name="project_create_path",
                arguments={
                    "path": "src/faebryk/library/MyModule.py",
                    "content": "class MyModule:\n    pass\n",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert created_fabll_py["path"] == "src/faebryk/library/MyModule.py"
        assert created_fabll_py["extension"] == ".py"

        moved = _run(
            execute_tool(
                name="project_move_path",
                arguments={
                    "old_path": "plans/notes.md",
                    "new_path": "docs/notes.md",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        assert moved["old_path"] == "plans/notes.md"
        assert moved["new_path"] == "docs/notes.md"
        assert (tmp_path / "docs" / "notes.md").exists()

    def test_parts_install_returns_web_search_followup_hint(self, monkeypatch) -> None:
        def fake_install_part(lcsc_id: str, project_root: str) -> dict[str, str]:
            assert lcsc_id == "C521608"
            assert project_root == "/tmp/project"
            return {
                "identifier": "STMicroelectronics_STM32G474RET6_package",
                "path": "/tmp/project/elec/src/parts/stm32g4/stm32g4.ato",
            }

        monkeypatch.setattr(parts_domain, "handle_install_part", fake_install_part)

        result = _run(
            execute_tool(
                name="parts_install",
                arguments={"lcsc_id": "c521608"},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["success"] is True
        assert result["lcsc_id"] == "C521608"
        assert "web_search" in result["implementation_hint"]

    def test_parts_install_targets_nested_project_path(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        package_root = tmp_path / "packages" / "sensor-front-end"
        package_root.mkdir(parents=True)
        (package_root / "ato.yaml").write_text(
            (
                'requires-atopile: "^0.14.0"\n'
                "paths:\n"
                "  src: ./\n"
                "builds:\n"
                "  default:\n"
                "    entry: sensor_front_end.ato:SensorFrontEnd\n"
            ),
            encoding="utf-8",
        )

        def fake_install_part(lcsc_id: str, project_root: str) -> dict[str, str]:
            assert lcsc_id == "C12345"
            assert project_root == str(package_root)
            return {
                "identifier": "Yangxing_Tech_X322512MMB4SI",
                "path": str(package_root / "parts" / "Yangxing_Tech_X322512MMB4SI"),
            }

        monkeypatch.setattr(parts_domain, "handle_install_part", fake_install_part)

        result = _run(
            execute_tool(
                name="parts_install",
                arguments={
                    "lcsc_id": "c12345",
                    "project_path": "packages/sensor-front-end",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["success"] is True
        assert result["lcsc_id"] == "C12345"
        assert result["projectPath"] == "packages/sensor-front-end"

    def test_package_create_local_creates_dependency_and_stub(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "ato.yaml").write_text(
            (
                'requires-atopile: "^0.14.0"\n'
                "paths:\n"
                "  src: ./\n"
                "builds:\n"
                "  default:\n"
                "    entry: main.ato:App\n"
            ),
            encoding="utf-8",
        )

        result = _run(
            execute_tool(
                name="package_create_local",
                arguments={
                    "name": "power-stage",
                    "entry_module": "PowerStage",
                    "description": "Power stage wrapper",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["success"] is True
        assert result["identifier"] == "local/power-stage"
        assert (
            'from "local/power-stage/power_stage.ato" import PowerStage'
            == result["import_statement"]
        )
        assert (tmp_path / "packages" / "power-stage" / "power_stage.ato").exists()
        assert (tmp_path / "packages" / "power-stage" / "ato.yaml").exists()
        root_ato = (tmp_path / "ato.yaml").read_text(encoding="utf-8")
        assert "type: project" in root_ato
        assert "path: ./packages/power-stage" in root_ato

    def test_workspace_list_targets_includes_nested_packages(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "ato.yaml").write_text(
            'requires-atopile: "^0.14.0"\n'
            "builds:\n"
            "  default:\n"
            "    entry: main.ato:App\n",
            encoding="utf-8",
        )
        package_dir = tmp_path / "packages" / "sensor-front-end"
        package_dir.mkdir(parents=True)
        (package_dir / "ato.yaml").write_text(
            (
                'requires-atopile: "^0.14.0"\n'
                "builds:\n"
                "  usage:\n"
                "    entry: sensor_front_end.ato:SensorFrontEnd\n"
                "package:\n"
                "  identifier: local/sensor-front-end\n"
                "  version: 0.0.1\n"
            ),
            encoding="utf-8",
        )

        result = _run(
            execute_tool(
                name="workspace_list_targets",
                arguments={},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["total_targets"] == 2
        assert result["projects"][0]["path"] == "."
        assert result["projects"][1]["path"] == "packages/sensor-front-end"
        assert result["projects"][1]["package_identifier"] == "local/sensor-front-end"

    def test_parts_install_create_package_wraps_part(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        (tmp_path / "ato.yaml").write_text(
            (
                'requires-atopile: "^0.14.0"\n'
                "paths:\n"
                "  src: ./\n"
                "builds:\n"
                "  default:\n"
                "    entry: main.ato:App\n"
            ),
            encoding="utf-8",
        )

        def fake_get_install_identifier(
            lcsc_id: str, project_root: str | None = None
        ) -> dict[str, str]:
            assert lcsc_id == "C12345"
            assert project_root == str(tmp_path)
            return {
                "identifier": "Infineon_BSC010N04LS",
                "entry_module": "Infineon_BSC010N04LS",
            }

        def fake_install_part(lcsc_id: str, project_root: str) -> dict[str, str]:
            assert lcsc_id == "C12345"
            part_root = Path(project_root) / "parts" / "Infineon_BSC010N04LS"
            part_root.mkdir(parents=True, exist_ok=True)
            (part_root / "Infineon_BSC010N04LS.ato").write_text(
                "component Infineon_BSC010N04LS_package:\n    pass\n",
                encoding="utf-8",
            )
            return {
                "identifier": "Infineon_BSC010N04LS",
                "path": str(part_root),
            }

        monkeypatch.setattr(
            parts_domain,
            "handle_get_install_identifier",
            fake_get_install_identifier,
        )
        monkeypatch.setattr(parts_domain, "handle_install_part", fake_install_part)

        result = _run(
            execute_tool(
                name="parts_install",
                arguments={"lcsc_id": "c12345", "create_package": True},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        wrapper = (
            tmp_path / "packages" / "Infineon_BSC010N04LS" / "Infineon_BSC010N04LS.ato"
        ).read_text(encoding="utf-8")
        assert result["created_package"] is True
        assert result["identifier"] == "local/infineon-bsc010n04ls"
        assert (
            'from "parts/Infineon_BSC010N04LS/Infineon_BSC010N04LS.ato" '
            "import Infineon_BSC010N04LS_package" in wrapper
        )
        assert "module Infineon_BSC010N04LS:" in wrapper
        assert "    package = new Infineon_BSC010N04LS_package" in wrapper

    def test_datasheet_read_uploads_pdf_and_returns_file_id(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        def fake_get_part_details(lcsc_id: str) -> dict | None:
            assert lcsc_id == "C521608"
            return {
                "datasheet_url": "https://example.com/tps7a02.pdf",
                "manufacturer": "TI",
                "part_number": "TPS7A02",
                "description": "LDO",
            }

        def fake_read_datasheet_file(
            project_root: Path,
            *,
            path: str | None = None,
            url: str | None = None,
        ) -> tuple[bytes, dict[str, object]]:
            assert project_root == tmp_path
            assert url == "https://example.com/tps7a02.pdf"
            return (
                b"%PDF-1.4\n",
                {
                    "source_kind": "url",
                    "source": "https://example.com/tps7a02.pdf",
                    "format": "pdf",
                    "content_type": "application/pdf",
                    "filename": "tps7a02.pdf",
                    "sha256": "deadbeef",
                    "size_bytes": 9,
                },
            )

        async def fake_upload_openai_user_file(
            *,
            filename: str,
            content: bytes,
            cache_key: str,
        ) -> tuple[str, bool]:
            assert filename == "tps7a02.pdf"
            assert content.startswith(b"%PDF-")
            assert cache_key == "deadbeef"
            return ("file-test-123", False)

        monkeypatch.setattr(
            parts_domain,
            "handle_get_part_details",
            fake_get_part_details,
        )
        monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
        monkeypatch.setattr(
            sys.modules[__name__],
            "_upload_openai_user_file",
            fake_upload_openai_user_file,
        )

        result = _run(
            execute_tool(
                name="datasheet_read",
                arguments={
                    "lcsc_id": "C521608",
                    "target": "default",
                    "query": "decoupling around vdd/vdda/vref+",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["found"] is True
        assert result["openai_file_id"] == "file-test-123"
        assert result["openai_file_cached"] is False
        assert result["filename"] == "tps7a02.pdf"
        assert result["lcsc_id"] == "C521608"
        assert result["resolution"]["mode"] == "parts_api_fallback"

    def test_datasheet_read_falls_back_when_graph_resolution_fails(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        def fake_get_part_details(lcsc_id: str) -> dict | None:
            assert lcsc_id == "C521608"
            return {
                "datasheet_url": "https://example.com/stm32g4.pdf",
                "manufacturer": "STMicroelectronics",
                "part_number": "STM32G474RET6",
                "description": "MCU",
            }

        def fake_read_datasheet_file(
            project_root: Path,
            *,
            path: str | None = None,
            url: str | None = None,
        ) -> tuple[bytes, dict[str, object]]:
            assert project_root == tmp_path
            assert path is None
            assert url == "https://example.com/stm32g4.pdf"
            return (
                b"%PDF-1.7\n",
                {
                    "source_kind": "url",
                    "source": "https://example.com/stm32g4.pdf",
                    "format": "pdf",
                    "content_type": "application/pdf",
                    "filename": "stm32g4.pdf",
                    "sha256": "feedface",
                    "size_bytes": 9,
                },
            )

        async def fake_upload_openai_user_file(
            *,
            filename: str,
            content: bytes,
            cache_key: str,
        ) -> tuple[str, bool]:
            assert filename == "stm32g4.pdf"
            assert content.startswith(b"%PDF-")
            assert cache_key == "feedface"
            return ("file-test-fallback", False)

        monkeypatch.setattr(
            parts_domain,
            "handle_get_part_details",
            fake_get_part_details,
        )
        monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
        monkeypatch.setattr(
            sys.modules[__name__],
            "_upload_openai_user_file",
            fake_upload_openai_user_file,
        )

        result = _run(
            execute_tool(
                name="datasheet_read",
                arguments={"lcsc_id": "C521608", "target": "default"},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["found"] is True
        assert result["openai_file_id"] == "file-test-fallback"
        assert result["resolution"]["mode"] == "parts_api_fallback"
        assert result["resolution"]["fallback_sources"][0]["source"] == "parts_api"

    def test_datasheet_read_uses_cached_reference_for_repeat_calls(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        counters = {"details": 0, "read": 0, "upload": 0}

        def fake_get_part_details(lcsc_id: str) -> dict | None:
            counters["details"] += 1
            assert lcsc_id == "C123456"
            return {
                "datasheet_url": "https://example.com/component.pdf",
                "manufacturer": "Test",
                "part_number": "COMP-1",
                "description": "Test component",
            }

        def fake_read_datasheet_file(
            project_root: Path,
            *,
            path: str | None = None,
            url: str | None = None,
        ) -> tuple[bytes, dict[str, object]]:
            counters["read"] += 1
            assert project_root == tmp_path
            assert url == "https://example.com/component.pdf"
            return (
                b"%PDF-1.7\ncached\n",
                {
                    "source_kind": "url",
                    "source": "https://example.com/component.pdf",
                    "format": "pdf",
                    "content_type": "application/pdf",
                    "filename": "component.pdf",
                    "sha256": "cafebabe",
                    "size_bytes": 16,
                },
            )

        async def fake_upload_openai_user_file(
            *,
            filename: str,
            content: bytes,
            cache_key: str,
        ) -> tuple[str, bool]:
            counters["upload"] += 1
            assert filename == "component.pdf"
            assert content.startswith(b"%PDF-")
            assert cache_key == "cafebabe"
            return ("file-cached-1", False)

        monkeypatch.setattr(
            parts_domain,
            "handle_get_part_details",
            fake_get_part_details,
        )
        monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
        monkeypatch.setattr(
            sys.modules[__name__],
            "_upload_openai_user_file",
            fake_upload_openai_user_file,
        )

        first = _run(
            execute_tool(
                name="datasheet_read",
                arguments={
                    "lcsc_id": "C123456",
                    "target": "default",
                    "query": "first query",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )
        second = _run(
            execute_tool(
                name="datasheet_read",
                arguments={
                    "lcsc_id": "C123456",
                    "target": "default",
                    "query": "second query",
                },
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert first["openai_file_id"] == "file-cached-1"
        assert first["datasheet_cache_hit"] is False
        assert second["openai_file_id"] == "file-cached-1"
        assert second["datasheet_cache_hit"] is True
        assert second["openai_file_cached"] is True
        assert second["query"] == "second query"
        assert counters == {"details": 1, "read": 1, "upload": 1}

    def test_datasheet_read_tries_jlc_fallback_urls_when_primary_url_fails(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        read_attempts: list[str] = []

        def fake_get_part_details(lcsc_id: str) -> dict | None:
            assert lcsc_id == "C5360602"
            return {
                "datasheet_url": "https://example.com/dead.pdf",
                "manufacturer": "Sensirion",
                "part_number": "SHT4x",
                "description": "Humidity sensor",
            }

        def fake_search_jlc_parts(
            query: str,
            *,
            limit: int = 50,
        ) -> tuple[list[dict], str | None]:
            assert query == "C5360602"
            assert limit == 6
            return (
                [
                    {
                        "lcsc": "C5360602",
                        "mpn": "SHT40-AD1B-R2",
                        "datasheet_url": "https://example.com/working.pdf",
                    }
                ],
                None,
            )

        def fake_read_datasheet_file(
            project_root: Path,
            *,
            path: str | None = None,
            url: str | None = None,
        ) -> tuple[bytes, dict[str, object]]:
            assert project_root == tmp_path
            assert path is None
            assert url is not None
            read_attempts.append(url)
            if url.endswith("/dead.pdf"):
                raise policy.ScopeError("Failed to fetch datasheet url: dead")
            assert url.endswith("/working.pdf")
            return (
                b"%PDF-1.7\n",
                {
                    "source_kind": "url",
                    "source": url,
                    "format": "pdf",
                    "content_type": "application/pdf",
                    "filename": "sht4x.pdf",
                    "sha256": "11223344",
                    "size_bytes": 9,
                },
            )

        async def fake_upload_openai_user_file(
            *,
            filename: str,
            content: bytes,
            cache_key: str,
        ) -> tuple[str, bool]:
            assert filename == "sht4x.pdf"
            assert content.startswith(b"%PDF-")
            assert cache_key == "11223344"
            return ("file-sht4x", False)

        monkeypatch.setattr(
            parts_domain,
            "handle_get_part_details",
            fake_get_part_details,
        )
        monkeypatch.setattr(
            parts_domain,
            "search_jlc_parts",
            fake_search_jlc_parts,
        )
        monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
        monkeypatch.setattr(
            sys.modules[__name__],
            "_upload_openai_user_file",
            fake_upload_openai_user_file,
        )

        result = _run(
            execute_tool(
                name="datasheet_read",
                arguments={"lcsc_id": "C5360602", "target": "default"},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
            )
        )

        assert result["found"] is True
        assert result["openai_file_id"] == "file-sht4x"
        assert read_attempts == [
            "https://example.com/dead.pdf",
            "https://example.com/working.pdf",
        ]
        assert result["resolution"]["url_fallback"]["selected_url"].endswith(
            "/working.pdf"
        )

    def test_build_run_forwards_include_and_exclude_targets(self, monkeypatch) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            def model_dump(self, by_alias: bool = False) -> dict:
                _ = by_alias
                return {"success": True, "message": "queued", "buildTargets": []}

        def fake_start_build(request):
            captured["include_targets"] = list(request.include_targets)
            captured["exclude_targets"] = list(request.exclude_targets)
            return FakeResponse()

        monkeypatch.setattr(builds_domain, "handle_start_build", fake_start_build)

        result = _run(
            execute_tool(
                name="build_run",
                arguments={
                    "targets": ["default"],
                    "include_targets": ["power-tree"],
                    "exclude_targets": ["mfg-data"],
                },
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["success"] is True
        assert captured["include_targets"] == ["power-tree"]
        assert captured["exclude_targets"] == ["mfg-data"]

    def test_build_run_uses_nested_project_path(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        captured: dict[str, object] = {}
        nested = tmp_path / "packages" / "power-stage"
        nested.mkdir(parents=True)

        class FakeResponse:
            def model_dump(self, by_alias: bool = False) -> dict:
                _ = by_alias
                return {"success": True, "message": "queued", "buildTargets": []}

        def fake_start_build(request):
            captured["project_root"] = request.project_root
            return FakeResponse()

        monkeypatch.setattr(builds_domain, "handle_start_build", fake_start_build)

        result = _run(
            execute_tool(
                name="build_run",
                arguments={
                    "project_path": "packages/power-stage",
                    "targets": ["default"],
                },
                project_root=tmp_path,
                ctx=AppContext(),
            )
        )

        assert result["success"] is True
        assert result["projectPath"] == "packages/power-stage"
        assert captured["project_root"] == str(nested)

    def test_report_bom_returns_summary_fields(self, monkeypatch) -> None:
        def fake_get_bom(project_root: str, target: str):
            assert project_root == "/tmp/project"
            assert target == "default"
            return {
                "build_id": "abc123",
                "items": [
                    {"designator": "R1", "mpn": "RC0603", "quantity": 1},
                    {"designator": "C1", "mpn": "CL10A", "quantity": 2},
                ],
                "meta": {"currency": "USD"},
            }

        monkeypatch.setattr(artifacts_domain, "handle_get_bom", fake_get_bom)

        result = _run(
            execute_tool(
                name="report_bom",
                arguments={"target": "default"},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["found"] is True
        assert result["summary"]["records_key"] == "items"
        assert result["summary"]["records_count"] == 2
        assert "designator" in result["summary"]["sample_fields"]

    def test_report_variables_not_found_returns_actionable_message(
        self,
        monkeypatch,
    ) -> None:
        def fake_get_variables(project_root: str, target: str):
            assert project_root == "/tmp/project"
            assert target == "default"
            return None

        monkeypatch.setattr(
            artifacts_domain,
            "handle_get_variables",
            fake_get_variables,
        )

        result = _run(
            execute_tool(
                name="report_variables",
                arguments={"target": "default"},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["found"] is False
        assert "build_run" in result["message"]

    def test_manufacturing_generate_queues_mfg_data_build(self, monkeypatch) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            success = True
            message = "Build queued for project"

            @property
            def build_targets(self):
                @dataclass
                class _Target:
                    target: str
                    build_id: str

                return [_Target(target="default", build_id="build-xyz")]

        def fake_start_build(request):
            captured["project_root"] = request.project_root
            captured["targets"] = list(request.targets)
            captured["frozen"] = request.frozen
            captured["include_targets"] = list(request.include_targets)
            captured["exclude_targets"] = list(request.exclude_targets)
            return FakeResponse()

        @dataclass
        class FakeOutputs:
            gerbers: str | None = None
            bom_json: str | None = None
            bom_csv: str | None = None
            pick_and_place: str | None = None
            step: str | None = None
            glb: str | None = None
            kicad_pcb: str | None = None
            kicad_sch: str | None = None
            pcb_summary: str | None = None

        def fake_get_build_outputs(project_root: str, target: str):
            assert project_root == "/tmp/project"
            assert target == "default"
            return FakeOutputs(
                gerbers="/tmp/project/build/builds/default/default.gerber.zip",
                bom_json="/tmp/project/build/builds/default/default.bom.json",
            )

        monkeypatch.setattr(builds_domain, "handle_start_build", fake_start_build)
        monkeypatch.setattr(
            manufacturing_domain,
            "get_build_outputs",
            fake_get_build_outputs,
        )

        result = _run(
            execute_tool(
                name="manufacturing_generate",
                arguments={"target": "default"},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["success"] is True
        assert result["queued_build_id"] == "build-xyz"
        assert result["include_targets"] == ["mfg-data"]
        assert "gerbers" in result["present_outputs_before"]
        assert "pick_and_place" in result["missing_outputs_before"]
        assert captured == {
            "project_root": "/tmp/project",
            "targets": ["default"],
            "frozen": False,
            "include_targets": ["mfg-data"],
            "exclude_targets": [],
        }

    def test_build_logs_search_defaults_to_non_debug_levels(self, monkeypatch) -> None:
        @dataclass
        class FakeBuild:
            build_id: str = "abc123"
            status: BuildStatus = BuildStatus.FAILED
            return_code: int = 1
            error: str = "compile failed"
            stages: list[dict] = field(
                default_factory=lambda: [
                    {"name": "compile", "status": "success", "elapsedSeconds": 1.2},
                    {"name": "route", "status": "failed", "elapsedSeconds": 0.7},
                ]
            )
            total_stages: int = 2

        captured: dict[str, object] = {}

        def fake_build_get(build_id: str):
            assert build_id == "abc123"
            return FakeBuild()

        def fake_load_build_logs(
            *,
            build_id: str,
            stage: str | None,
            log_levels: list[str] | None,
            audience: str | None,
            count: int,
        ) -> list[dict]:
            captured.update(
                {
                    "build_id": build_id,
                    "stage": stage,
                    "log_levels": log_levels,
                    "audience": audience,
                    "count": count,
                }
            )
            return [
                {
                    "build_id": build_id,
                    "stage": "compile",
                    "level": "ERROR",
                    "audience": "developer",
                    "message": "compile failed",
                }
            ]

        monkeypatch.setattr(BuildHistory, "get", fake_build_get)
        monkeypatch.setattr(
            sys.modules[__name__], "load_build_logs", fake_load_build_logs
        )

        result = _run(
            execute_tool(
                name="build_logs_search",
                arguments={"build_id": "abc123", "limit": 25},
                project_root=Path("."),
                ctx=AppContext(),
            )
        )

        assert captured["log_levels"] == ["INFO", "WARNING", "ERROR", "ALERT"]
        assert captured["stage"] is None
        assert result["filters"]["log_levels"] == ["INFO", "WARNING", "ERROR", "ALERT"]
        assert result["stage_summary"]["counts"]["failed"] == 1

    def test_build_logs_search_honors_explicit_filters(self, monkeypatch) -> None:
        @dataclass
        class FakeBuild:
            build_id: str = "abc123"
            status: BuildStatus = BuildStatus.SUCCESS
            return_code: int = 0
            error: str | None = None
            stages: list[dict] = field(default_factory=list)
            total_stages: int = 0

        captured: dict[str, object] = {}

        def fake_build_get(build_id: str):
            assert build_id == "abc123"
            return FakeBuild()

        def fake_load_build_logs(
            *,
            build_id: str,
            stage: str | None,
            log_levels: list[str] | None,
            audience: str | None,
            count: int,
        ) -> list[dict]:
            captured.update(
                {
                    "build_id": build_id,
                    "stage": stage,
                    "log_levels": log_levels,
                    "audience": audience,
                    "count": count,
                }
            )
            return []

        monkeypatch.setattr(BuildHistory, "get", fake_build_get)
        monkeypatch.setattr(
            sys.modules[__name__], "load_build_logs", fake_load_build_logs
        )

        result = _run(
            execute_tool(
                name="build_logs_search",
                arguments={
                    "build_id": "abc123",
                    "stage": "compile",
                    "log_levels": ["DEBUG"],
                    "audience": "developer",
                    "limit": 10,
                },
                project_root=Path("."),
                ctx=AppContext(),
            )
        )

        assert captured["stage"] == "compile"
        assert captured["log_levels"] == ["DEBUG"]
        assert captured["audience"] == "developer"
        assert result["filters"]["stage"] == "compile"
        assert result["filters"]["log_levels"] == ["DEBUG"]

    def test_build_logs_search_null_query_does_not_filter_to_literal_none(
        self,
        monkeypatch,
    ) -> None:
        @dataclass
        class FakeBuild:
            build_id: str = "abc123"
            status: BuildStatus = BuildStatus.SUCCESS
            return_code: int = 0
            error: str | None = None
            stages: list[dict] = field(default_factory=list)
            total_stages: int = 0

        def fake_build_get(build_id: str):
            assert build_id == "abc123"
            return FakeBuild()

        def fake_load_build_logs(
            *,
            build_id: str,
            stage: str | None,
            log_levels: list[str] | None,
            audience: str | None,
            count: int,
        ) -> list[dict]:
            return [
                {
                    "build_id": build_id,
                    "stage": "compile",
                    "level": "INFO",
                    "audience": "developer",
                    "message": "compile started",
                }
            ]

        monkeypatch.setattr(BuildHistory, "get", fake_build_get)
        monkeypatch.setattr(
            sys.modules[__name__], "load_build_logs", fake_load_build_logs
        )

        result = _run(
            execute_tool(
                name="build_logs_search",
                arguments={"build_id": "abc123", "query": None, "limit": 10},
                project_root=Path("."),
                ctx=AppContext(),
            )
        )

        assert result["total"] == 1
        assert result["logs"][0]["message"] == "compile started"
        assert result["filters"]["query"] is None

    def test_stdlib_tools_execute_with_expected_shape(self, monkeypatch) -> None:
        @dataclass
        class FakeItem:
            id: str
            name: str

            def model_dump(self) -> dict:
                return {"id": self.id, "name": self.name}

        @dataclass
        class FakeResponse:
            items: list[FakeItem]
            total: int

        def fake_get_stdlib(
            type_filter: str | None,
            search: str | None,
            refresh: bool,
            max_depth: int | None,
        ) -> FakeResponse:
            assert type_filter == "module"
            assert search == "usb"
            assert refresh is False
            assert max_depth == 1
            return FakeResponse(
                items=[
                    FakeItem(id="USB_C", name="USB_C"),
                    FakeItem(id="Resistor", name="Resistor"),
                ],
                total=2,
            )

        def fake_get_item(item_id: str) -> FakeItem | None:
            if item_id == "USB_C":
                return FakeItem(id="USB_C", name="USB_C")
            return None

        monkeypatch.setattr(stdlib_domain, "handle_get_stdlib", fake_get_stdlib)
        monkeypatch.setattr(stdlib_domain, "handle_get_stdlib_item", fake_get_item)

        listed = _run(
            execute_tool(
                name="stdlib_list",
                arguments={
                    "type_filter": "module",
                    "search": "usb",
                    "max_depth": 1,
                    "limit": 1,
                },
                project_root=Path("."),
                ctx=AppContext(),
            )
        )
        assert listed["total"] == 2
        assert listed["returned"] == 1
        assert listed["items"][0]["id"] == "USB_C"

        found = _run(
            execute_tool(
                name="stdlib_get_item",
                arguments={"item_id": "USB_C"},
                project_root=Path("."),
                ctx=AppContext(),
            )
        )
        assert found["found"] is True
        assert found["item"]["id"] == "USB_C"

    def test_project_module_tools_execute_with_expected_shape(
        self, monkeypatch
    ) -> None:
        @dataclass
        class FakeModule:
            name: str
            type: str
            file: str
            entry: str

            def model_dump(self, by_alias: bool = False) -> dict:
                _ = by_alias
                return {
                    "name": self.name,
                    "type": self.type,
                    "file": self.file,
                    "entry": self.entry,
                }

        @dataclass
        class FakeModulesResponse:
            modules: list[FakeModule]
            total: int

        @dataclass
        class FakeChild:
            name: str
            item_type: str
            children: list["FakeChild"]

            def model_dump(self, by_alias: bool = False) -> dict:
                _ = by_alias
                return {
                    "name": self.name,
                    "itemType": self.item_type,
                    "children": [
                        child.model_dump(by_alias=True) for child in self.children
                    ],
                }

        def fake_get_modules(project_root: str, type_filter: str | None):
            assert project_root == "/tmp/project"
            assert type_filter == "module"
            return FakeModulesResponse(
                modules=[
                    FakeModule(
                        name="App",
                        type="module",
                        file="main.ato",
                        entry="main.ato:App",
                    )
                ],
                total=1,
            )

        def fake_introspect_module(
            project_root: Path, entry_point: str, max_depth: int
        ) -> list[FakeChild]:
            assert str(project_root) == "/tmp/project"
            assert entry_point == "main.ato:App"
            assert max_depth == 2
            return [FakeChild(name="i2c", item_type="interface", children=[])]

        monkeypatch.setattr(projects_domain, "handle_get_modules", fake_get_modules)
        monkeypatch.setattr(
            module_introspection,
            "introspect_module",
            fake_introspect_module,
        )

        listed = _run(
            execute_tool(
                name="project_list_modules",
                arguments={"type_filter": "module", "limit": 10},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )
        assert listed["total"] == 1
        assert listed["returned"] == 1
        assert listed["types"]["module"] == 1
        assert listed["modules"][0]["entry"] == "main.ato:App"

        children = _run(
            execute_tool(
                name="project_module_children",
                arguments={"entry_point": "main.ato:App", "max_depth": 2},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )
        assert children["found"] is True
        assert children["counts"]["interface"] == 1

    def test_build_logs_search_returns_stub_for_silent_failure(
        self, monkeypatch
    ) -> None:
        @dataclass
        class FakeBuild:
            build_id: str
            project_root: str
            target: str
            status: BuildStatus
            started_at: float
            elapsed_seconds: float
            warnings: int
            errors: int
            return_code: int | None
            error: str | None
            timestamp: str | None

        def fake_load_build_logs(**kwargs):
            assert kwargs["build_id"] == "build-123"
            return []

        def fake_get(build_id: str):
            assert build_id == "build-123"
            return FakeBuild(
                build_id="build-123",
                project_root="/tmp/project",
                target="default",
                status=BuildStatus.FAILED,
                started_at=1.0,
                elapsed_seconds=2.0,
                warnings=0,
                errors=0,
                return_code=1,
                error="compiler crashed",
                timestamp=None,
            )

        monkeypatch.setattr(
            sys.modules[__name__], "load_build_logs", fake_load_build_logs
        )
        monkeypatch.setattr(BuildHistory, "get", fake_get)

        result = _run(
            execute_tool(
                name="build_logs_search",
                arguments={"build_id": "build-123", "limit": 10},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["synthesized_stub"] is True
        assert result["total"] == 1
        assert "No log lines were captured" in result["logs"][0]["message"]
        assert result["status"] == "failed"

    def test_build_logs_search_normalizes_interrupted_history(
        self, monkeypatch
    ) -> None:
        @dataclass
        class FakeBuild:
            build_id: str
            project_root: str
            target: str
            status: BuildStatus
            started_at: float
            elapsed_seconds: float
            warnings: int
            errors: int
            return_code: int | None
            error: str | None
            timestamp: str | None

        def fake_get_all(limit: int):
            assert limit == 120
            return [
                FakeBuild(
                    build_id="stale-build",
                    project_root="/tmp/project",
                    target="default",
                    status=BuildStatus.BUILDING,
                    started_at=1.0,
                    elapsed_seconds=20.0,
                    warnings=0,
                    errors=0,
                    return_code=None,
                    error=None,
                    timestamp=None,
                )
            ]

        monkeypatch.setattr(BuildHistory, "get_all", fake_get_all)
        monkeypatch.setattr(
            sys.modules[__name__], "_active_or_pending_build_ids", lambda: set()
        )

        result = _run(
            execute_tool(
                name="build_logs_search",
                arguments={},
                project_root=Path("/tmp/project"),
                ctx=AppContext(),
            )
        )

        assert result["total"] == 1
        assert result["builds"][0]["status"] == "failed"
        assert "interrupted" in result["builds"][0]["error"]
