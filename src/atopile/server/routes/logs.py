"""
Log WebSocket routes for querying build logs.

Endpoints:
- WS /ws/logs - Query build logs from the central log database
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from atopile.dataclasses import LogEntryPydantic, LogQuery, LogsError, LogsResult
from atopile.logging import load_build_logs

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for querying build logs from the central log database.

    Client message payload:
    - build_id (str)
    - stage (str)
    - log_levels (list[str] enum)
    - audience (str enum)
    - count (int, default 500)
    """
    await websocket.accept()
    log.info("Logs WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()
            try:
                query = LogQuery.model_validate(data)
            except ValidationError as exc:
                await websocket.send_json(LogsError(error=str(exc)).model_dump())
                continue

            # Convert enum values to strings for load_build_logs (StrEnum values are strings)
            log_levels_str = (
                [str(level) for level in query.log_levels] if query.log_levels else None
            )
            audience_str = str(query.audience) if query.audience else None

            logs = load_build_logs(
                build_id=query.build_id,
                stage=query.stage,
                log_levels=log_levels_str,
                audience=audience_str,
                count=query.count,
            )

            entries = [LogEntryPydantic.model_validate(entry) for entry in logs]
            await websocket.send_json(LogsResult(logs=entries).model_dump())
    except WebSocketDisconnect:
        log.info("Logs WebSocket client disconnected")
    except Exception as exc:
        log.exception(f"Logs WebSocket error: {exc}")
