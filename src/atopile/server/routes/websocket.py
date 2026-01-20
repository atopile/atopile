"""
WebSocket routes for real-time updates.

Endpoints:
- WS /ws/events - Event streaming (logs, builds, etc.)
- WS /ws/state - Full state synchronization
"""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
                payload = data.get("payload", {})
                result = await server_state.handle_action(action, payload)

                # Also handle data-fetching actions that need server.py access
                from ..server import handle_data_action

                if not result.get("success"):
                    # Try the data action handler
                    result = await handle_data_action(action, payload)

                # Send result back to client
                await websocket.send_json(
                    {"type": "action_result", "action": action, "result": result}
                )

    except WebSocketDisconnect:
        await server_state.disconnect_client(client_id)
        log.info(f"State WebSocket client disconnected: {client_id}")
    except Exception as e:
        log.error(f"State WebSocket error: {e}")
        await server_state.disconnect_client(client_id)
