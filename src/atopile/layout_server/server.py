"""Shared layout-editor API router factory.

Used by both the standalone server (``__main__``) and the backend
integration server (``atopile.server.routes.layout``).
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
from atopile.server.domains.layout import LayoutService

log = logging.getLogger(__name__)


def create_layout_router(
    service: LayoutService,
    *,
    api_prefix: str = "/api/layout",
    ws_path: str = "/ws/layout",
) -> APIRouter:
    """Build an ``APIRouter`` wired to *service*.

    Parameters
    ----------
    service:
        The ``LayoutService`` instance that owns the ``PcbManager``.
    api_prefix:
        URL prefix for the REST endpoints (e.g. ``/api/layout``).
    ws_path:
        Full path for the WebSocket endpoint (e.g. ``/ws/layout``).
    """
    router = APIRouter(tags=["layout"])

    def _require_loaded() -> None:
        if not service.is_loaded:
            raise HTTPException(
                status_code=404, detail="No PCB loaded in layout editor"
            )

    @router.get(f"{api_prefix}/render-model", response_model=RenderModel)
    async def get_render_model() -> RenderModel:
        _require_loaded()
        return await asyncio.to_thread(service.manager.get_render_model)

    @router.get(f"{api_prefix}/footprints", response_model=list[FootprintSummary])
    async def get_footprints() -> list[FootprintSummary]:
        _require_loaded()
        return await asyncio.to_thread(service.manager.get_footprints)

    @router.post(f"{api_prefix}/execute-action", response_model=StatusResponse)
    async def execute_action(req: ActionRequest) -> StatusResponse:
        _require_loaded()
        try:
            await asyncio.to_thread(service.manager.dispatch_action, req)
        except ValueError as e:
            return StatusResponse(
                status="error",
                code="invalid_action_target",
                message=str(e),
            )
        model = await service.save_and_broadcast()
        return StatusResponse(status="ok", code="ok", model=model)

    @router.post(f"{api_prefix}/undo", response_model=StatusResponse)
    async def undo() -> StatusResponse:
        _require_loaded()
        ok = await asyncio.to_thread(service.manager.undo)
        if ok:
            model = await service.save_and_broadcast()
            return StatusResponse(status="ok", code="ok", model=model)
        return StatusResponse(
            status="error",
            code="nothing_to_undo",
            message="No action available to undo.",
        )

    @router.post(f"{api_prefix}/redo", response_model=StatusResponse)
    async def redo() -> StatusResponse:
        _require_loaded()
        ok = await asyncio.to_thread(service.manager.redo)
        if ok:
            model = await service.save_and_broadcast()
            return StatusResponse(status="ok", code="ok", model=model)
        return StatusResponse(
            status="error",
            code="nothing_to_redo",
            message="No action available to redo.",
        )

    @router.post(f"{api_prefix}/reload", response_model=StatusResponse)
    async def reload() -> StatusResponse:
        _require_loaded()
        path = service.current_path
        await asyncio.to_thread(service.manager.load, path)
        model = await asyncio.to_thread(service.manager.get_render_model)
        await service.broadcast(WsMessage(type="layout_updated", model=model))
        return StatusResponse(status="ok", code="ok", model=model)

    @router.websocket(ws_path)
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await service.add_ws_client(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            service.remove_ws_client(websocket)

    return router
