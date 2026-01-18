"""Bridge routes for agent-to-agent communication."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...core import ProcessManager
from ...core.state import AgentStateStore, PipelineStateStore
from ...models import AgentBackendType, AgentConfig, AgentState, AgentStatus
from ..dependencies import get_agent_store, get_pipeline_store, get_process_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bridge", tags=["bridge"])

# Pipeline context for edge validation
# Maps: pipeline_id -> {edges: [(from, to), ...], agents: {name: agent_id}}
_pipeline_contexts: dict[str, dict] = {}
_context_lock = threading.Lock()


class SendRequest(BaseModel):
    from_agent: str
    to_agent: str
    message: str
    pipeline_id: str | None = None  # Optional pipeline context


class SendResponse(BaseModel):
    status: str
    response: str | None = None
    message: str | None = None


class RegisterPipelineRequest(BaseModel):
    pipeline_id: str
    edges: list[tuple[str, str]]  # List of (from_node, to_node) tuples
    agents: dict[str, str]  # Map of agent_name -> agent_id


def register_pipeline_context(pipeline_id: str, edges: list[tuple[str, str]], agents: dict[str, str]):
    """Register a pipeline's topology for edge validation."""
    with _context_lock:
        _pipeline_contexts[pipeline_id] = {
            "edges": set(edges),  # Set for O(1) lookup
            "agents": agents.copy(),
        }
    logger.info(f"Registered pipeline context: {pipeline_id} with {len(edges)} edges, {len(agents)} agents")


def unregister_pipeline_context(pipeline_id: str):
    """Remove a pipeline's context."""
    with _context_lock:
        _pipeline_contexts.pop(pipeline_id, None)
    logger.info(f"Unregistered pipeline context: {pipeline_id}")


def is_edge_allowed(pipeline_id: str | None, from_agent: str, to_agent: str) -> bool:
    """Check if communication is allowed between two agents."""
    if pipeline_id is None:
        # No pipeline context - allow all (for standalone testing)
        return True

    with _context_lock:
        ctx = _pipeline_contexts.get(pipeline_id)
        if ctx is None:
            # Pipeline not registered - allow all
            return True

        # Check if edge exists (in either direction for bidirectional)
        edges = ctx["edges"]
        return (from_agent, to_agent) in edges or (to_agent, from_agent) in edges


def get_pipeline_agent_id(pipeline_id: str, agent_name: str) -> str | None:
    """Get the agent ID for a named agent in a pipeline."""
    with _context_lock:
        ctx = _pipeline_contexts.get(pipeline_id)
        if ctx is None:
            return None
        return ctx["agents"].get(agent_name)


@router.post("/send", response_model=SendResponse)
async def send_and_receive(
    request: SendRequest,
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
) -> SendResponse:
    """
    Send a message to another agent and wait for response.

    This is the core of agent-to-agent communication:
    1. Validate that edge exists in pipeline (if pipeline_id provided)
    2. Spawn target agent with the message as prompt
    3. Wait for target agent to complete
    4. Return target agent's output as the response
    """
    from_agent = request.from_agent
    to_agent = request.to_agent
    message = request.message
    pipeline_id = request.pipeline_id

    logger.info(f"Bridge request: {from_agent} -> {to_agent} (pipeline={pipeline_id})")

    # Validate edge if in pipeline context
    if pipeline_id and not is_edge_allowed(pipeline_id, from_agent, to_agent):
        logger.warning(f"Edge not allowed: {from_agent} -> {to_agent} in pipeline {pipeline_id}")
        return SendResponse(
            status="error",
            message=f"Communication not allowed: no edge from '{from_agent}' to '{to_agent}' in pipeline"
        )

    # Check if target agent exists and get its config
    # For now, we'll spawn a new agent with the message as prompt
    # In the future, this should check pipeline topology

    # Create agent config for the target
    # The message becomes the prompt, with context about who's asking
    prompt = f"""You are agent '{to_agent}'. You received a request from agent '{from_agent}'.

REQUEST:
{message}

Process this request and provide your response. Your output will be sent back to '{from_agent}'.
"""

    config = AgentConfig(
        backend=AgentBackendType.CLAUDE_CODE,
        prompt=prompt,
        max_turns=5,  # Reasonable limit for a worker task
    )

    # Create and spawn the agent
    agent = AgentState(config=config, status=AgentStatus.STARTING)
    agent_store.set(agent.id, agent)

    try:
        managed = process_manager.spawn(agent)

        # Update state to running
        def updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            return a

        agent_store.update(agent.id, updater)
        logger.info(f"Spawned agent '{to_agent}' (id={agent.id}) for bridge request")

        # Wait for agent to complete (poll in background thread)
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _wait_and_extract_result(process_manager, agent_store, agent.id)
        )

        return SendResponse(status="response", response=result)

    except Exception as e:
        logger.error(f"Bridge request failed: {e}")
        return SendResponse(status="error", message=str(e))


def _wait_and_extract_result(
    process_manager: ProcessManager,
    agent_store: AgentStateStore,
    agent_id: str,
    timeout: float = 300.0,  # 5 minute timeout
) -> str:
    """Wait for agent to complete and extract its result."""
    import time

    start = time.time()

    while time.time() - start < timeout:
        # Check if process finished
        exit_code = process_manager.get_exit_code(agent_id)

        if exit_code is not None:
            # Wait for output threads to finish
            process_manager.wait_for_output_and_get_session_id(agent_id, timeout=2.0)

            # Update agent state
            new_status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

            def updater(a: AgentState) -> AgentState:
                a.status = new_status
                a.exit_code = exit_code
                a.finished_at = datetime.now()
                return a

            agent_store.update(agent_id, updater)

            # Extract result from output
            result = _extract_result(process_manager, agent_id)

            # Cleanup
            process_manager.cleanup(agent_id)

            return result

        time.sleep(0.5)

    # Timeout - kill the agent
    try:
        process_manager.terminate(agent_id, timeout=5.0)
    except Exception:
        pass

    return "(Agent timed out)"


def _extract_result(process_manager: ProcessManager, agent_id: str) -> str:
    """Extract the final result from agent output."""
    chunks = process_manager.get_output(agent_id)

    # Look for result chunk first
    for chunk in reversed(chunks):
        if chunk.type.value == "result":
            if chunk.content:
                return chunk.content
            if chunk.data and "result" in chunk.data:
                return str(chunk.data["result"])

    # Fallback: collect assistant text
    texts = []
    for chunk in chunks:
        if chunk.type.value == "assistant" and chunk.content:
            texts.append(chunk.content)

    if texts:
        return "\n".join(texts)

    return "(No output)"
