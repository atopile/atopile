"""
Log WebSocket routes for querying build and test logs.

Endpoints:
- WS /ws/logs - Query build or test logs (request/response or streaming)

Supports two modes:
1. One-shot: Send query, receive all matching logs
2. Streaming: Send query with subscribe=true, receive continuous updates
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from atopile.dataclasses import Log
from atopile.logging import (
    load_build_logs,
    load_build_logs_stream,
    load_test_logs,
    load_test_logs_stream,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])

STREAM_POLL_INTERVAL = 0.25  # 250ms between polls when streaming


def _parse_filter_params(
    query: Log.BuildQuery | Log.TestQuery | Log.BuildStreamQuery | Log.TestStreamQuery,
) -> tuple[list[str] | None, str | None]:
    """Parse common log_levels and audience from a query into string values."""
    log_levels_str = (
        [str(level) for level in query.log_levels] if query.log_levels else None
    )
    audience_str = str(query.audience) if query.audience else None
    return log_levels_str, audience_str


async def _push_build_stream(
    websocket: WebSocket,
    query: Log.BuildStreamQuery,
    after_id: int,
) -> int:
    """Push build log updates to client. Returns new last_id."""
    log_levels_str, audience_str = _parse_filter_params(query)
    logs, new_last_id = load_build_logs_stream(
        build_id=query.build_id,
        stage=query.stage,
        log_levels=log_levels_str,
        audience=audience_str,
        after_id=after_id,
        count=query.count,
    )

    if logs:
        entries = [Log.BuildStreamEntryPydantic.model_validate(entry) for entry in logs]
        await websocket.send_json(
            Log.BuildStreamResult(logs=entries, last_id=new_last_id).model_dump()
        )
        return new_last_id
    return after_id


async def _push_test_stream(
    websocket: WebSocket,
    query: Log.TestStreamQuery,
    after_id: int,
) -> int:
    """Push test log updates to client. Returns new last_id."""
    log_levels_str, audience_str = _parse_filter_params(query)
    logs, new_last_id = load_test_logs_stream(
        test_run_id=query.test_run_id,
        test_name=query.test_name,
        log_levels=log_levels_str,
        audience=audience_str,
        after_id=after_id,
        count=query.count,
    )

    if logs:
        entries = [Log.TestStreamEntryPydantic.model_validate(entry) for entry in logs]
        await websocket.send_json(
            Log.TestStreamResult(logs=entries, last_id=new_last_id).model_dump()
        )
        return new_last_id
    return after_id


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for querying build or test logs.

    Supports two modes:
    1. One-shot: Send query, receive all matching logs
    2. Streaming: Send query with subscribe=true, receive continuous updates

    For streaming, the response includes last_id which tracks the cursor position.
    New logs are pushed automatically as they appear in the database.

    Common payload:
    - log_levels (list[str] enum, optional)
    - audience (str enum, optional)
    - count (int, default 500 for one-shot, 100 for streaming)
    - subscribe (bool, default false) - enable streaming mode

    Build log payload:
    - build_id (str)
    - stage (str, optional)
    - after_id (int, optional) - cursor for streaming, only logs with id > after_id

    Test log payload:
    - test_run_id (str)
    - test_name (str, optional)
    - after_id (int, optional) - cursor for streaming
    """
    await websocket.accept()
    log.info("Logs WebSocket client connected")

    # Streaming state
    streaming = False
    stream_query: Log.BuildStreamQuery | Log.TestStreamQuery | None = None
    last_id = 0
    is_test_mode = False

    try:
        while True:
            # In streaming mode, use short timeout to allow periodic polling
            # In normal mode, wait indefinitely for next message
            try:
                if streaming and stream_query:
                    # Non-blocking check for new client message
                    data = await asyncio.wait_for(
                        websocket.receive_json(), timeout=STREAM_POLL_INTERVAL
                    )
                else:
                    # Blocking wait for client message
                    data = await websocket.receive_json()
            except asyncio.TimeoutError:
                # No new message during streaming - push any new logs
                if streaming and stream_query:
                    if is_test_mode:
                        last_id = await _push_test_stream(
                            websocket,
                            stream_query,  # type: ignore
                            last_id,
                        )
                    else:
                        last_id = await _push_build_stream(
                            websocket,
                            stream_query,  # type: ignore
                            last_id,
                        )
                continue

            # Check for subscribe mode
            subscribe = data.pop("subscribe", False)

            # Check for unsubscribe
            if data.get("unsubscribe"):
                streaming = False
                stream_query = None
                log.debug("Client unsubscribed from log streaming")
                continue

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
                is_test_mode = True
                # Test logs mode
                if subscribe:
                    try:
                        stream_query = Log.TestStreamQuery.model_validate(data)
                    except ValidationError as exc:
                        err = Log.Error(error=str(exc)).model_dump()
                        await websocket.send_json(err)
                        continue

                    streaming = True
                    last_id = stream_query.after_id
                    log.debug(
                        f"Client subscribed to test logs: {stream_query.test_run_id}"
                    )
                    # Send initial batch immediately
                    last_id = await _push_test_stream(websocket, stream_query, last_id)
                else:
                    # One-shot query (existing behavior)
                    streaming = False
                    stream_query = None
                    try:
                        query = Log.TestQuery.model_validate(data)
                    except ValidationError as exc:
                        err = Log.Error(error=str(exc)).model_dump()
                        await websocket.send_json(err)
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
                is_test_mode = False
                # Build logs mode (default)
                if subscribe:
                    try:
                        stream_query = Log.BuildStreamQuery.model_validate(data)
                    except ValidationError as exc:
                        err = Log.Error(error=str(exc)).model_dump()
                        await websocket.send_json(err)
                        continue

                    streaming = True
                    last_id = stream_query.after_id
                    log.debug(
                        f"Client subscribed to build logs: {stream_query.build_id}"
                    )
                    # Send initial batch immediately
                    last_id = await _push_build_stream(
                        websocket, stream_query, last_id
                    )
                else:
                    # One-shot query (existing behavior)
                    streaming = False
                    stream_query = None
                    try:
                        query = Log.BuildQuery.model_validate(data)
                    except ValidationError as exc:
                        err = Log.Error(error=str(exc)).model_dump()
                        await websocket.send_json(err)
                        continue

                    log_levels_str, audience_str = _parse_filter_params(query)
                    logs = load_build_logs(
                        build_id=query.build_id,
                        stage=query.stage,
                        log_levels=log_levels_str,
                        audience=audience_str,
                        count=query.count,
                    )

                    entries = [
                        Log.BuildEntryPydantic.model_validate(entry) for entry in logs
                    ]
                    await websocket.send_json(
                        Log.BuildResult(logs=entries).model_dump()
                    )

    except WebSocketDisconnect:
        log.info("Logs WebSocket client disconnected")
    except Exception as exc:
        log.exception(f"Logs WebSocket error: {exc}")
