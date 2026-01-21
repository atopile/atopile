"""
WebSocket routes for real-time updates.

Endpoints:
- WS /ws/events - Event streaming (logs, builds, etc.)
- WS /ws/state - Full state synchronization
"""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..domains.actions import handle_data_action

log = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def _get_ws_manager():
    """Get the WebSocket manager from server module."""
    from ..server import ws_manager

    return ws_manager


def _get_server_state():
    """Get the server state singleton."""
    from ..state import server_state

    return server_state


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.

    Clients can subscribe to channels (builds, logs, summary, problems)
    and receive filtered updates in real-time.
    """
    ws_manager = _get_ws_manager()

    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@router.websocket("/ws/state")
async def websocket_state(websocket: WebSocket):
    """
    WebSocket endpoint for full state synchronization.

    The Python backend pushes the full AppState to clients on:
    1. Initial connection
    2. Any state change

    Clients can send actions which modify state and trigger broadcasts.
    """
    server_state = _get_server_state()

    client_id = await server_state.connect_client(websocket)
    log.info(f"State WebSocket client connected: {client_id}")

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "action":
                # Handle action from client
                action = data.get("action", "")
                payload = data.get("payload")
                if not isinstance(payload, dict):
                    payload = {}
                inline_payload = {
                    k: v
                    for k, v in data.items()
                    if k not in ("type", "action", "payload")
                }
                if inline_payload:
                    payload = {**inline_payload, **payload}

                log.info(
                    f"WebSocket action received: {action}, payload keys: {list(payload.keys())}"
                )

                try:
                    ctx = websocket.app.state.ctx
                    result = await handle_data_action(action, payload, ctx)
                    log.info(
                        f"handle_data_action returned for {action}: success={result.get('success')}"
                    )

                    if not result.get("success") and str(
                        result.get("error", "")
                    ).startswith("Unknown action:"):
                        log.info(
                            f"Falling back to server_state.handle_action for {action}"
                        )
                        result = await server_state.handle_action(action, payload)

                    # Send result back to client
                    await websocket.send_json(
                        {"type": "action_result", "action": action, "result": result}
                    )
                except Exception as action_exc:
                    log.exception(f"Exception handling action {action}: {action_exc}")
                    await websocket.send_json(
                        {
                            "type": "action_result",
                            "action": action,
                            "result": {"success": False, "error": str(action_exc)},
                        }
                    )

    except WebSocketDisconnect:
        await server_state.disconnect_client(client_id)
        log.info(f"State WebSocket client disconnected: {client_id}")
    except Exception as e:
        # Treat "not connected" errors as disconnects (common during hot reload)
        error_msg = str(e).lower()
        if "not connected" in error_msg or "accept" in error_msg:
            log.debug(f"State WebSocket client {client_id} disconnected early: {e}")
        else:
            log.error(f"State WebSocket error: {e}")
        await server_state.disconnect_client(client_id)
