"""
Log WebSocket routes for querying build logs.

Endpoints:
- WS /ws/logs - Query build logs from the central log database
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from atopile.logging import (
    LOGS_DEFAULT_COUNT,
    LOGS_MAX_COUNT,
    load_build_logs,
    normalize_log_audience,
    normalize_log_level,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for querying build logs from the central log database.

    Client message payload:
    - build_id (str)
    - stage (str)
    - log_level (str enum)
    - audience (str enum)
    - count (int, default 500)
    """
    await websocket.accept()
    log.info("Logs WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                await websocket.send_json(
                    {"type": "logs_error", "error": "Invalid payload"}
                )
                continue

            build_id = data.get("build_id")
            stage = data.get("stage")
            log_level_raw = data.get("log_level")
            audience_raw = data.get("audience")
            count = data.get("count", LOGS_DEFAULT_COUNT)

            if not isinstance(build_id, str) or not build_id:
                await websocket.send_json(
                    {"type": "logs_error", "error": "build_id is required"}
                )
                continue

            if stage is not None and not isinstance(stage, str):
                await websocket.send_json(
                    {"type": "logs_error", "error": "stage must be a string"}
                )
                continue

            log_level = normalize_log_level(log_level_raw)
            if log_level_raw is not None and log_level is None:
                await websocket.send_json(
                    {
                        "type": "logs_error",
                        "error": f"Invalid log_level: {log_level_raw}",
                    }
                )
                continue

            audience = normalize_log_audience(audience_raw)
            if audience_raw is not None and audience is None:
                await websocket.send_json(
                    {
                        "type": "logs_error",
                        "error": f"Invalid audience: {audience_raw}",
                    }
                )
                continue

            try:
                count_int = int(count)
            except (TypeError, ValueError):
                count_int = LOGS_DEFAULT_COUNT
            count_int = max(1, min(count_int, LOGS_MAX_COUNT))

            logs = load_build_logs(
                build_id=build_id,
                stage=stage if isinstance(stage, str) and stage else None,
                log_level=log_level,
                audience=audience,
                count=count_int,
            )

            await websocket.send_json({"type": "logs_result", "logs": logs})
    except WebSocketDisconnect:
        log.info("Logs WebSocket client disconnected")
    except Exception as exc:
        log.exception(f"Logs WebSocket error: {exc}")
