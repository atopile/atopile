"""Shared layout-editor API router factory.

Used by both the standalone server (``__main__``) and the backend
integration server (``atopile.server.routes.layout``).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from atopile.layout_server.models import (
    ActionRequest,
    FootprintSummary,
    RedoCommand,
    RenderModel,
    StatusResponse,
    UndoCommand,
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
        action_id = req.client_action_id

        # undo and redo are not added to the history stack, so we handle them here
        if isinstance(req, UndoCommand):
            ok = await asyncio.to_thread(service.manager.undo)
            if ok:
                await service.save_and_broadcast(action_id=action_id)
                return StatusResponse(status="ok", code="ok", action_id=action_id)
            return StatusResponse(
                status="error",
                code="nothing_to_undo",
                message="No action available to undo.",
                action_id=action_id,
            )
        if isinstance(req, RedoCommand):
            ok = await asyncio.to_thread(service.manager.redo)
            if ok:
                await service.save_and_broadcast(action_id=action_id)
                return StatusResponse(status="ok", code="ok", action_id=action_id)
            return StatusResponse(
                status="error",
                code="nothing_to_redo",
                message="No action available to redo.",
                action_id=action_id,
            )

        try:
            await asyncio.to_thread(service.manager.dispatch_action, req)
        except ValueError as e:
            return StatusResponse(
                status="error",
                code="invalid_action_target",
                message=str(e),
                action_id=action_id,
            )

        delta = await asyncio.to_thread(
            service.manager.get_render_delta_for_uuids, req.uuids
        )
        if delta is None:
            await service.save_and_broadcast(action_id=action_id)
            return StatusResponse(status="ok", code="ok", action_id=action_id)

        await service.save_and_broadcast(delta=delta, action_id=action_id)
        return StatusResponse(
            status="ok",
            code="ok",
            delta=delta,
            action_id=action_id,
        )

    @router.get(f"{api_prefix}/bom")
    async def get_layout_bom(
        project_root: str | None = Query(None),
        target_name: str | None = Query(None),
    ):
        """Return BOM data for a build target.

        When *project_root* and *target_name* are supplied the BOM path
        is constructed directly.  Otherwise the endpoint falls back to
        deriving both values from the currently loaded PCB path.
        """
        resolved_root: Path | None = None
        resolved_target: str | None = None

        if project_root and target_name:
            resolved_root = Path(project_root)
            resolved_target = target_name
        else:
            _require_loaded()
            pcb_path = service.current_path
            if pcb_path is None:
                raise HTTPException(status_code=404, detail="No PCB loaded")

            resolved_target = pcb_path.stem

            candidate = pcb_path.parent
            while candidate != candidate.parent:
                if (candidate / "ato.yaml").exists():
                    resolved_root = candidate
                    break
                candidate = candidate.parent

        if resolved_root is None:
            raise HTTPException(
                status_code=404, detail="Could not find project root (ato.yaml)"
            )

        bom_path = (
            resolved_root
            / "build"
            / "builds"
            / resolved_target
            / f"{resolved_target}.bom.json"
        )
        if not bom_path.exists():
            raise HTTPException(
                status_code=404,
                detail="BOM file not found. Run 'ato build' first.",
            )
        try:
            data = await asyncio.to_thread(lambda: json.loads(bom_path.read_text()))
            return data
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Invalid BOM JSON: {exc}")

    @router.websocket(ws_path)
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await service.add_ws_client(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            service.remove_ws_client(websocket)

    return router
