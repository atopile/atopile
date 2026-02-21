"""Layout editor API routes.

Mirrors the standalone layout_server API — no path parameters.
The server manages which PCB is currently loaded via LayoutService.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from atopile.layout_server.models import (
    ActionRequest,
    FootprintSummary,
    RenderModel,
    StatusResponse,
    WsMessage,
)
from atopile.server.domains.layout import layout_service

log = logging.getLogger(__name__)

router = APIRouter(tags=["layout"])


def _require_loaded() -> None:
    if not layout_service.is_loaded:
        raise HTTPException(status_code=404, detail="No PCB loaded in layout editor")


@router.get("/api/layout/render-model", response_model=RenderModel)
async def get_render_model() -> RenderModel:
    _require_loaded()
    return await asyncio.to_thread(layout_service.manager.get_render_model)


@router.get("/api/layout/footprints", response_model=list[FootprintSummary])
async def get_footprints() -> list[FootprintSummary]:
    _require_loaded()
    return await asyncio.to_thread(layout_service.manager.get_footprints)


@router.post("/api/layout/execute-action", response_model=StatusResponse)
async def execute_action(req: ActionRequest) -> StatusResponse:
    _require_loaded()
    try:
        await asyncio.to_thread(layout_service.manager.dispatch_action, req)
    except ValueError as e:
        return StatusResponse(
            status="error",
            code="invalid_action_target",
            message=str(e),
        )
    model = await layout_service.save_and_broadcast()
    return StatusResponse(status="ok", code="ok", model=model)


@router.post("/api/layout/undo", response_model=StatusResponse)
async def undo() -> StatusResponse:
    _require_loaded()
    ok = await asyncio.to_thread(layout_service.manager.undo)
    if ok:
        model = await layout_service.save_and_broadcast()
        return StatusResponse(status="ok", code="ok", model=model)
    return StatusResponse(
        status="error",
        code="nothing_to_undo",
        message="No action available to undo.",
    )


@router.post("/api/layout/redo", response_model=StatusResponse)
async def redo() -> StatusResponse:
    _require_loaded()
    ok = await asyncio.to_thread(layout_service.manager.redo)
    if ok:
        model = await layout_service.save_and_broadcast()
        return StatusResponse(status="ok", code="ok", model=model)
    return StatusResponse(
        status="error",
        code="nothing_to_redo",
        message="No action available to redo.",
    )


@router.post("/api/layout/reload", response_model=StatusResponse)
async def reload() -> StatusResponse:
    _require_loaded()
    path = layout_service.current_path
    await asyncio.to_thread(layout_service.manager.load, path)
    model = await asyncio.to_thread(layout_service.manager.get_render_model)
    await layout_service.broadcast(WsMessage(type="layout_updated", model=model))
    return StatusResponse(status="ok", code="ok", model=model)


@router.get("/api/layout/bom")
async def get_bom():
    _require_loaded()
    project_root = layout_service.project_root
    target_name = layout_service.target_name
    if not project_root or not target_name:
        raise HTTPException(status_code=404, detail="No project context for BOM lookup")

    from atopile.server.domains import artifacts as artifacts_domain

    result = await asyncio.to_thread(
        artifacts_domain.handle_get_bom, str(project_root), target_name
    )
    if result is None:
        raise HTTPException(status_code=404, detail="BOM not found. Run a build first.")
    return result


@router.websocket("/ws/layout")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await layout_service.add_ws_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        layout_service.remove_ws_client(websocket)
