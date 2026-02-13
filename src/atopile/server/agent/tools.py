"""Typed agent tools for atopile operations."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

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
            part.strip().upper()
            for part in raw_levels.split(",")
            if part.strip()
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
        if isinstance(maybe_rows, list) and maybe_rows and isinstance(
            maybe_rows[0], dict
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
            "description": "Read a file chunk from the selected project.",
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
        modules = [
            module.model_dump(by_alias=True) for module in response.modules
        ][:limit]
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
                item
                for item in items
                if _stdlib_matches_child_query(item, child_query)
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
        result = await asyncio.to_thread(
            parts_domain.handle_install_part,
            str(arguments.get("lcsc_id", "")),
            str(project_root),
        )
        return {"success": True, **result}

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
        if lcsc_id:
            graph_result = await asyncio.to_thread(
                datasheets_domain.handle_collect_project_datasheets,
                str(project_root),
                build_target=target,
                lcsc_ids=[lcsc_id],
            )

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
                    "build_target": graph_result.get("build_target"),
                    "reason": (
                        "No datasheet match for the requested lcsc_id was found "
                        "in the instantiated project graph."
                    ),
                }
                source_meta["part"] = {
                    "manufacturer": details.get("manufacturer"),
                    "part_number": details.get("part_number"),
                    "description": details.get("description"),
                }

            source_meta = {
                "lcsc_id": lcsc_id.upper(),
                **source_meta,
            }

        datasheet_bytes, metadata = await asyncio.to_thread(
            policy.read_datasheet_file,
            project_root,
            path=source_path,
            url=source_url,
        )
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
                _normalize_history_build(build, active_ids)
                for build in builds
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
