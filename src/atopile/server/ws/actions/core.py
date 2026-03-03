"""Core self-registered WebSocket actions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from atopile.dataclasses import AppContext, EventType
from atopile.model.model_state import model_state
from atopile.server.connections import server_state
from atopile.server.domains import packages as packages_domain
from atopile.server.domains import projects as projects_domain

from .registry import register_action


@register_action("ping")
async def handle_ping(_payload: dict[str, Any], _ctx: AppContext) -> dict[str, Any]:
    return {"success": True}


@register_action("refreshProjects")
async def handle_refresh_projects(
    _payload: dict[str, Any], ctx: AppContext
) -> dict[str, Any]:
    if ctx.workspace_paths:
        await asyncio.to_thread(
            projects_domain.discover_projects_in_paths, ctx.workspace_paths
        )
        await server_state.emit_event(EventType.PROJECTS_CHANGED)
    return {"success": True}


@register_action("refreshPackages")
async def handle_refresh_packages(
    _payload: dict[str, Any], ctx: AppContext
) -> dict[str, Any]:
    scan_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
    await packages_domain.refresh_packages_state(scan_path=scan_path)
    return {"success": True}


@register_action("refreshStdlib")
async def handle_refresh_stdlib(
    _payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    await server_state.emit_event(EventType.STDLIB_CHANGED)
    return {"success": True}


@register_action("refreshProblems")
async def handle_refresh_problems(
    _payload: dict[str, Any], _ctx: AppContext
) -> dict[str, Any]:
    await server_state.emit_event(EventType.PROBLEMS_CHANGED)
    return {"success": True}


@register_action("setWorkspaceFolders")
async def handle_set_workspace_folders(
    payload: dict[str, Any], ctx: AppContext
) -> dict[str, Any]:
    folders = payload.get("folders", [])
    if not isinstance(folders, list):
        return {"success": False, "error": "folders must be a list"}
    if not all(isinstance(folder, str) for folder in folders):
        return {"success": False, "error": "folders must contain only strings"}

    workspace_paths = [Path(folder) for folder in folders]
    ctx.workspace_paths = workspace_paths
    model_state.set_workspace_paths(workspace_paths)

    await handle_refresh_projects({}, ctx)
    await handle_refresh_packages({}, ctx)
    return {"success": True}
