"""
Log WebSocket routes for querying build and test logs.

Endpoints:
- WS /ws/logs - Query build or test logs from the central log database
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from atopile.dataclasses import Log
from atopile.logging import load_build_logs, load_test_logs

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


def _parse_filter_params(
    query: Log.Query | Log.TestQuery,
) -> tuple[list[str] | None, str | None]:
    """Parse common log_levels and audience from a query into string values."""
    log_levels_str = (
        [str(level) for level in query.log_levels] if query.log_levels else None
    )
    audience_str = str(query.audience) if query.audience else None
    return log_levels_str, audience_str


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for querying build or test logs from the central log database.

    Common payload:
    - log_levels (list[str] enum, optional)
    - audience (str enum, optional)
    - count (int, default 500)

    Build log payload:
    - build_id (str)
    - stage (str, optional)

    Test log payload:
    - test_run_id (str)
    - test (str, optional)

    The endpoint auto-detects the mode based on the presence of build_id vs test_run_id.
    """
    await websocket.accept()
    log.info("Logs WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()

            # Guard: reject requests with both build_id and test_run_id
            has_build_id = "build_id" in data
            has_test_run_id = "test_run_id" in data

            if has_build_id and has_test_run_id:
                await websocket.send_json(
                    Log.Error(
                        error="Cannot specify both build_id and test_run_id"
                    ).model_dump()
                )
                continue

            if has_test_run_id:
                # Test logs mode
                try:
                    query = Log.TestQuery.model_validate(data)
                except ValidationError as exc:
                    await websocket.send_json(Log.Error(error=str(exc)).model_dump())
                    continue

                log_levels_str, audience_str = _parse_filter_params(query)
                logs = load_test_logs(
                    test_run_id=query.test_run_id,
                    test_name=query.test_name,
                    log_levels=log_levels_str,
                    audience=audience_str,
                    count=query.count,
                )

                entries = [
                    Log.TestEntryPydantic.model_validate(entry) for entry in logs
                ]
                await websocket.send_json(Log.TestResult(logs=entries).model_dump())
            else:
                # Build logs mode (default)
                try:
                    query = Log.Query.model_validate(data)
                except ValidationError as exc:
                    await websocket.send_json(Log.Error(error=str(exc)).model_dump())
                    continue

                log_levels_str, audience_str = _parse_filter_params(query)
                logs = load_build_logs(
                    build_id=query.build_id,
                    stage=query.stage,
                    log_levels=log_levels_str,
                    audience=audience_str,
                    count=query.count,
                )

                entries = [Log.EntryPydantic.model_validate(entry) for entry in logs]
                await websocket.send_json(Log.Result(logs=entries).model_dump())
    except WebSocketDisconnect:
        log.info("Logs WebSocket client disconnected")
    except Exception as exc:
        log.exception(f"Logs WebSocket error: {exc}")
