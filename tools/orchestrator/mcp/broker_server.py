"""
Central HTTP Message Broker Server

This is the central broker that all agents connect to.
Agents use the MCP client (broker_client.py) which calls this HTTP API.

Run with:
    python -m tools.orchestrator.mcp.broker_server

Endpoints:
    POST /register          - Register an agent
    POST /send              - Send a message
    GET  /receive/{name}    - Receive a message (long-poll)
    GET  /agents            - List registered agents
    GET  /messages/{name}   - Check pending message count
"""

import asyncio
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage
_agents: dict[str, dict] = {}
_message_queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
_spawn_queue: asyncio.Queue = asyncio.Queue()  # Queue of SpawnRequests for orchestrator
_lock = asyncio.Lock()


# Request/Response models
class RegisterRequest(BaseModel):
    name: str


class SendRequest(BaseModel):
    from_agent: str
    to: str
    message: str


class SpawnRequest(BaseModel):
    name: str  # Name for the new agent
    prompt: str  # Task for the agent
    respond_to: str | None = None  # Agent to send results back to


class Message(BaseModel):
    from_agent: str
    to: str
    message: str
    timestamp: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Message broker starting...")
    yield
    logger.info("Message broker shutting down...")


app = FastAPI(title="Agent Message Broker", lifespan=lifespan)


@app.post("/register")
async def register_agent(request: RegisterRequest):
    """Register an agent with the broker."""
    async with _lock:
        if request.name in _agents:
            # Allow re-registration (agent restart)
            logger.info(f"Re-registering agent: {request.name}")

        agent_id = f"agent-{int(time.time() * 1000)}"
        _agents[request.name] = {
            "id": agent_id,
            "name": request.name,
            "registered_at": time.time(),
        }

        # Ensure queue exists
        _ = _message_queues[request.name]

    logger.info(f"Registered agent: {request.name}")
    return {"status": "registered", "name": request.name, "id": agent_id}


@app.post("/send")
async def send_message(request: SendRequest):
    """Send a message to an agent or broadcast."""
    msg = Message(
        from_agent=request.from_agent,
        to=request.to,
        message=request.message,
        timestamp=time.time(),
    )

    async with _lock:
        if request.to == "*":
            # Broadcast to all agents
            count = 0
            for name in list(_message_queues.keys()):
                if name != request.from_agent:
                    await _message_queues[name].put(msg)
                    count += 1
            logger.info(f"Broadcast from {request.from_agent} to {count} agents")
            return {"status": "broadcast", "recipients": count}
        else:
            if request.to not in _agents:
                raise HTTPException(
                    status_code=404, detail=f"Agent '{request.to}' not registered"
                )

            await _message_queues[request.to].put(msg)
            logger.info(f"Message queued: {request.from_agent} -> {request.to}")
            return {"status": "sent", "to": request.to}


@app.get("/receive/{name}")
async def receive_message(
    name: str, timeout: float = 30.0, from_agent: str | None = None
):
    """Receive a message (long-poll). Blocks until message or timeout."""
    if name not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not registered")

    queue = _message_queues[name]
    start_time = time.time()

    # Long-poll loop
    while time.time() - start_time < timeout:
        try:
            msg = await asyncio.wait_for(
                queue.get(), timeout=min(1.0, timeout - (time.time() - start_time))
            )

            # Filter by sender if specified
            if from_agent and msg.from_agent != from_agent:
                # Put it back and continue
                await queue.put(msg)
                await asyncio.sleep(0.1)
                continue

            logger.info(f"Message delivered to {name}: from {msg.from_agent}")
            return {
                "status": "received",
                "from": msg.from_agent,
                "message": msg.message,
                "timestamp": msg.timestamp,
            }
        except asyncio.TimeoutError:
            continue

    return {"status": "timeout", "message": "No message received within timeout"}


@app.get("/agents")
async def list_agents():
    """List all registered agents."""
    async with _lock:
        return {"agents": list(_agents.values())}


@app.get("/messages/{name}")
async def check_messages(name: str):
    """Check pending message count without blocking."""
    if name not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not registered")

    return {"pending": _message_queues[name].qsize()}


@app.post("/spawn")
async def request_spawn(request: SpawnRequest):
    """Request the orchestrator to spawn a new agent.

    The orchestrator polls /spawn/pending to get spawn requests.
    """
    spawn_id = f"spawn-{int(time.time() * 1000)}"

    await _spawn_queue.put(
        {
            "id": spawn_id,
            "name": request.name,
            "prompt": request.prompt,
            "respond_to": request.respond_to,
            "requested_at": time.time(),
        }
    )

    logger.info(f"Spawn request queued: {request.name}")
    return {"status": "queued", "spawn_id": spawn_id, "name": request.name}


@app.get("/spawn/pending")
async def get_pending_spawns(timeout: float = 1.0):
    """Get pending spawn requests (for orchestrator to poll).

    Returns one spawn request at a time, or empty if none pending.
    """
    try:
        request = await asyncio.wait_for(_spawn_queue.get(), timeout=timeout)
        return {"status": "pending", "request": request}
    except asyncio.TimeoutError:
        return {"status": "empty"}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "agents": len(_agents)}


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8766)


if __name__ == "__main__":
    main()
