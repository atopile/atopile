"""UI-facing WebSocket actions (open signals and config sync)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from atopile.dataclasses import AppContext, EventType
from atopile.model import builds as builds_domain
from atopile.server import path_utils
from atopile.server.client_state import client_state
from atopile.server.connections import server_state
from atopile.server.domains.layout import layout_service

from .registry import register_action


def _resolve_build_target(
    project_root: str, build_id: str, payload: dict[str, Any]
) -> tuple[str | None, str | None]:
    target_name = payload.get("targetName") or payload.get("target")
    resolved_project_root = project_root

    if build_id:
        build_info = builds_domain.handle_get_build_info(build_id)
        if isinstance(build_info, dict):
            target_name = (
                target_name
                or build_info.get("target")
                or build_info.get("name")
                or build_info.get("build_name")
            )
            resolved_project_root = (
                resolved_project_root
                or build_info.get("project_root")
                or build_info.get("projectRoot")
            )

    return target_name, resolved_project_root


@register_action("openFile")
async def handle_open_file(payload: dict[str, Any], ctx: AppContext) -> dict[str, Any]:
    file_path = payload.get("file")
    line = payload.get("line")
    column = payload.get("column")

    if not file_path:
        return {"success": False, "error": "Missing file path"}

    workspace_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
    resolved = path_utils.resolve_workspace_file(file_path, workspace_path)
    if not resolved:
        return {
            "success": False,
            "error": f"File not found: {file_path}",
        }

    await server_state.emit_event(
        "open_file",
        {"path": str(resolved), "line": line, "column": column},
    )
    return {"success": True}


@register_action("openSource")
async def handle_open_source(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    project_root = payload.get("projectId", "")
    entry = payload.get("entry", "")

    if not project_root or not entry:
        return {"success": False, "error": "Missing projectId or entry"}

    project_path = Path(project_root)
    entry_path = path_utils.resolve_entry_path(project_path, entry)
    if not entry_path or not entry_path.exists():
        return {
            "success": False,
            "error": f"Entry file not found: {entry_path}",
        }

    await server_state.emit_event("open_file", {"path": str(entry_path)})
    return {"success": True}


@register_action("openLayout")
async def handle_open_layout(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    project_root = payload.get("projectId", "")
    build_id = payload.get("buildId", "")

    target_name, resolved_project_root = _resolve_build_target(
        project_root, build_id, payload
    )
    if not resolved_project_root or not target_name:
        return {
            "success": False,
            "error": "Missing projectId or buildId/target",
        }

    project_path = Path(resolved_project_root)
    target = path_utils.resolve_layout_file_path(project_path, target_name)

    if target.exists() and target.is_file():
        await asyncio.to_thread(layout_service.load, target)
    else:
        layout_service.set_target(target)
    await layout_service.start_watcher()

    await server_state.emit_event(
        EventType.OPEN_LAYOUT,
        {
            "path": str(target),
            "project_root": str(project_path),
            "target_name": target_name,
        },
    )
    return {"success": True, "path": str(target), "exists": target.exists()}


@register_action("openKiCad")
async def handle_open_kicad(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    project_root = payload.get("projectId", "")
    build_id = payload.get("buildId", "")

    target_name, resolved_project_root = _resolve_build_target(
        project_root, build_id, payload
    )
    if not resolved_project_root or not target_name:
        return {
            "success": False,
            "error": "Missing projectId or buildId/target",
        }

    project_path = Path(resolved_project_root)
    target = path_utils.resolve_layout_path(project_path, target_name)
    if not target or not target.exists():
        return {
            "success": False,
            "error": f"Layout not found for target: {target_name}",
        }

    await server_state.emit_event(EventType.OPEN_KICAD, {"path": str(target)})
    return {"success": True}


@register_action("open3D")
async def handle_open_3d(payload: dict[str, Any], _ctx: AppContext) -> dict[str, Any]:
    project_root = payload.get("projectId", "")
    build_id = payload.get("buildId", "")

    target_name, resolved_project_root = _resolve_build_target(
        project_root, build_id, payload
    )
    if not resolved_project_root or not target_name:
        return {
            "success": False,
            "error": "Missing projectId or buildId/target",
        }

    project_path = Path(resolved_project_root)
    target = path_utils.resolve_3d_path(project_path, target_name)
    if target is None:
        target = (
            project_path / "build" / "builds" / target_name / f"{target_name}.pcba.glb"
        )

    await server_state.emit_event(EventType.OPEN_3D, {"path": str(target)})
    return {"success": True}


@register_action("setLogViewCurrentId")
async def handle_set_log_view_current_id(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    build_id = payload.get("buildId")
    stage = payload.get("stage")
    client_state.log_view_current_id = build_id
    client_state.log_view_current_stage = stage
    await server_state.emit_event(
        EventType.LOG_VIEW_CURRENT_ID_CHANGED,
        {"buildId": build_id, "stage": stage},
    )
    return {"success": True}


@register_action("getLogViewCurrentId")
async def handle_get_log_view_current_id(
    _payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    return {
        "success": True,
        "buildId": client_state.log_view_current_id,
        "stage": client_state.log_view_current_stage,
    }


@register_action("setAtopileSource")
async def handle_set_atopile_source(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    await server_state.emit_event(
        EventType.ATOPILE_CONFIG_CHANGED,
        {"source": payload.get("source", "release")},
    )
    return {"success": True}


@register_action("setAtopileLocalPath")
async def handle_set_atopile_local_path(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    await server_state.emit_event(
        EventType.ATOPILE_CONFIG_CHANGED,
        {
            "local_path": payload.get("path"),
            "source": "local",
        },
    )
    return {"success": True}


@register_action("setAtopileInstalling")
async def handle_set_atopile_installing(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    installing = payload.get("installing", False)
    error = payload.get("error")
    await server_state.emit_event(
        EventType.ATOPILE_CONFIG_CHANGED,
        {"is_installing": installing, "error": error},
    )
    return {"success": True}


@register_action("browseAtopilePath")
async def handle_browse_atopile_path(
    _payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    return {
        "success": False,
        "error": "browseAtopilePath is not supported in the UI server",
    }


@register_action("validateAtopilePath")
async def handle_validate_atopile_path(
    payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    from atopile.server.domains import atopile_install

    path = payload.get("path", "")
    result = await atopile_install.validate_local_path(path)
    return {"success": True, **result}


@register_action("getAtopileConfig")
async def handle_get_atopile_config(
    _payload: dict[str, Any], ctx: AppContext
) -> dict[str, Any]:
    from atopile import version as ato_version

    try:
        version_obj = ato_version.get_installed_atopile_version()
        actual_version = str(version_obj)
    except Exception:
        actual_version = None

    actual_source = ctx.ato_source or "unknown"
    ui_source = "local" if actual_source == "explicit-path" else "release"

    await server_state.emit_event(
        EventType.ATOPILE_CONFIG_CHANGED,
        {
            "actual_version": actual_version,
            "actual_source": actual_source,
            "actual_binary_path": ctx.ato_binary_path,
            "source": ui_source,
            "local_path": ctx.ato_local_path,
            "from_branch": ctx.ato_from_branch,
            "from_spec": ctx.ato_from_spec,
        },
    )
    return {
        "success": True,
        "actual_version": actual_version,
        "actual_source": actual_source,
        "source": ui_source,
    }
