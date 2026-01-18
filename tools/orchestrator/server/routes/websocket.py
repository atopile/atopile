"""WebSocket routes for real-time agent streaming."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ...core import AgentStateStore, ProcessManager
from ...models import StreamEvent, StreamEventType
from ..dependencies import (
    ConnectionManager,
    get_agent_store,
    get_orchestrator_state,
    get_process_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def get_ws_manager() -> ConnectionManager:
    """Get or create the WebSocket connection manager."""
    state = get_orchestrator_state()
    if state._ws_manager is None:
        state._ws_manager = ConnectionManager()
    return state._ws_manager


@router.websocket("/ws/agents/{agent_id}")
async def websocket_agent_stream(
    websocket: WebSocket,
    agent_id: str,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
):
    """WebSocket endpoint for streaming agent output.

    Connect to receive real-time output chunks from an agent.
    The connection will be closed when the agent finishes.

    Query parameters:
    - include_history: If true, send all buffered output first (default: true)
    """
    ws_manager = get_ws_manager()

    # Check agent exists
    agent = agent_store.get(agent_id)
    if agent is None:
        await websocket.close(code=4004, reason=f"Agent not found: {agent_id}")
        return

    # Accept connection
    await ws_manager.connect(websocket, agent_id)

    try:
        # Send connected event
        connected_event = StreamEvent(
            type=StreamEventType.CONNECTED,
            agent_id=agent_id,
            data={"status": str(agent.status)},
        )
        await websocket.send_json(connected_event.model_dump(mode="json"))

        # Send buffered output history
        chunks = process_manager.get_output(agent_id)
        for chunk in chunks:
            event = StreamEvent(
                type=StreamEventType.AGENT_OUTPUT,
                agent_id=agent_id,
                chunk=chunk,
            )
            await websocket.send_json(event.model_dump(mode="json"))

        # If agent is already finished, send final status and close
        if agent.is_finished():
            final_event = StreamEvent(
                type=_status_to_event_type(agent.status),
                agent_id=agent_id,
                data={"status": str(agent.status), "exit_code": agent.exit_code},
            )
            await websocket.send_json(final_event.model_dump(mode="json"))
            await websocket.close()
            return

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong, or commands)
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0,
                )

                # Handle ping
                if message.get("type") == "ping":
                    pong = StreamEvent(
                        type=StreamEventType.PONG,
                        agent_id=agent_id,
                    )
                    await websocket.send_json(pong.model_dump(mode="json"))

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                ping = StreamEvent(
                    type=StreamEventType.PING,
                    agent_id=agent_id,
                )
                await websocket.send_json(ping.model_dump(mode="json"))

                # Check if agent is still running
                agent = agent_store.get(agent_id)
                if agent and agent.is_finished():
                    final_event = StreamEvent(
                        type=_status_to_event_type(agent.status),
                        agent_id=agent_id,
                        data={
                            "status": str(agent.status),
                            "exit_code": agent.exit_code,
                        },
                    )
                    await websocket.send_json(final_event.model_dump(mode="json"))
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for agent {agent_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for agent {agent_id}: {e}")
        try:
            error_event = StreamEvent(
                type=StreamEventType.ERROR,
                agent_id=agent_id,
                message=str(e),
            )
            await websocket.send_json(error_event.model_dump(mode="json"))
        except Exception:
            pass
    finally:
        ws_manager.disconnect(websocket, agent_id)


def _status_to_event_type(status) -> StreamEventType:
    """Convert agent status to stream event type."""
    from ...models import AgentStatus

    return {
        AgentStatus.COMPLETED: StreamEventType.AGENT_COMPLETED,
        AgentStatus.FAILED: StreamEventType.AGENT_FAILED,
        AgentStatus.TERMINATED: StreamEventType.AGENT_TERMINATED,
    }.get(status, StreamEventType.AGENT_OUTPUT)
