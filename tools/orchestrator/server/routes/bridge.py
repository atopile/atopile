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
    """Get the agent ID for a named agent in a pipeline.

    First checks the in-memory context, then falls back to searching the agent store.
    """
    # First check in-memory context
    with _context_lock:
        ctx = _pipeline_contexts.get(pipeline_id)
        if ctx is not None:
            agent_id = ctx["agents"].get(agent_name)
            if agent_id:
                return agent_id

    # Fall back to searching agent store (for persistence across restarts)
    # This requires access to the agent store, which we'll get from the dependency
    return None


def find_pipeline_agent_in_store(
    agent_store: "AgentStateStore",
    pipeline_id: str,
    agent_name: str,
) -> str | None:
    """Find an agent in the store by pipeline_id and agent name.

    This is used as a fallback when the in-memory context doesn't have the agent.
    """
    for agent_id in agent_store.list_ids():
        agent = agent_store.get(agent_id)
        if agent is None:
            continue

        # Check if agent belongs to this pipeline
        if agent.pipeline_id != pipeline_id:
            continue

        # Check if the agent's config environment has the matching AGENT_NAME
        if agent.config.environment:
            if agent.config.environment.get("AGENT_NAME") == agent_name:
                return agent_id

    return None


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
    2. If target agent exists in pipeline and has a session_id, resume it
    3. Otherwise spawn a new agent with the message as prompt
    4. Wait for target agent to complete
    5. Return target agent's output as the response
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

    # Build the prompt with context about the request
    # IMPORTANT: Tell the worker NOT to use send_and_receive to reply - just output text
    prompt = f"""You received a message from agent '{from_agent}'.

MESSAGE:
{message}

Respond to this message by outputting your answer as text. Do NOT use the send_and_receive tool to reply - your text output will automatically be sent back to '{from_agent}'.
"""

    # Check if we can resume an existing pipeline agent
    existing_agent_id = None
    if pipeline_id:
        # First try in-memory context
        existing_agent_id = get_pipeline_agent_id(pipeline_id, to_agent)
        # Fall back to searching the store
        if not existing_agent_id:
            existing_agent_id = find_pipeline_agent_in_store(agent_store, pipeline_id, to_agent)
            if existing_agent_id:
                logger.info(f"Found agent '{to_agent}' in store: {existing_agent_id}")

    existing_agent = agent_store.get(existing_agent_id) if existing_agent_id else None

    if existing_agent and existing_agent.session_id and existing_agent.is_finished():
        # Resume the existing agent with the new message
        logger.info(f"Resuming existing agent '{to_agent}' (id={existing_agent_id})")
        return await _resume_agent_for_message(
            existing_agent_id,
            prompt,
            from_agent,
            to_agent,
            process_manager,
            agent_store,
        )
    else:
        # Spawn a new agent
        if existing_agent:
            logger.info(f"Agent '{to_agent}' exists but cannot be resumed: session_id={existing_agent.session_id}, status={existing_agent.status}")
        else:
            logger.info(f"No existing agent found for '{to_agent}', spawning new one")
        return await _spawn_agent_for_message(
            prompt,
            from_agent,
            to_agent,
            process_manager,
            agent_store,
        )


async def _resume_agent_for_message(
    agent_id: str,
    prompt: str,
    from_agent: str,
    to_agent: str,
    process_manager: ProcessManager,
    agent_store: AgentStateStore,
) -> SendResponse:
    """Resume an existing agent with a new message."""
    agent = agent_store.get(agent_id)
    if agent is None:
        return SendResponse(status="error", message=f"Agent not found: {agent_id}")

    logger.info(f"Resuming agent '{to_agent}' (id={agent_id}) for bridge request from '{from_agent}'")

    # Prepare agent for resume
    def prepare_updater(a: AgentState) -> AgentState:
        a.config.prompt = prompt
        a.config.session_id = a.session_id
        a.config.resume_session = True
        a.config.max_turns = 5  # Limit for response
        a.status = AgentStatus.STARTING
        a.exit_code = None
        a.error_message = None
        a.finished_at = None
        resume_count = a.metadata.get("resume_count", 0)
        a.metadata["resume_count"] = resume_count + 1
        return a

    agent_store.update(agent_id, prepare_updater)
    agent = agent_store.get(agent_id)

    try:
        managed = process_manager.spawn(agent)

        def running_updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            return a

        agent_store.update(agent_id, running_updater)

        # Wait for agent to complete
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _wait_and_extract_result(process_manager, agent_store, agent_id, cleanup=False)
        )

        return SendResponse(status="response", response=result)

    except Exception as e:
        logger.error(f"Failed to resume agent for bridge request: {e}")
        return SendResponse(status="error", message=str(e))


async def _spawn_agent_for_message(
    prompt: str,
    from_agent: str,
    to_agent: str,
    process_manager: ProcessManager,
    agent_store: AgentStateStore,
) -> SendResponse:
    """Spawn a new agent to handle a message."""
    # Add identity context to the prompt for new agents
    full_prompt = f"You are agent '{to_agent}'.\n\n{prompt}"

    config = AgentConfig(
        backend=AgentBackendType.CLAUDE_CODE,
        prompt=full_prompt,
        max_turns=5,  # Reasonable limit for a worker task
    )

    agent = AgentState(config=config, status=AgentStatus.STARTING)
    agent_store.set(agent.id, agent)

    try:
        managed = process_manager.spawn(agent)

        def updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            return a

        agent_store.update(agent.id, updater)
        logger.info(f"Spawned new agent '{to_agent}' (id={agent.id}) for bridge request from '{from_agent}'")

        # Wait for agent to complete
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _wait_and_extract_result(process_manager, agent_store, agent.id, cleanup=True)
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
    cleanup: bool = True,
) -> str:
    """Wait for agent to complete and extract its result.

    Args:
        process_manager: Process manager instance
        agent_store: Agent state store
        agent_id: ID of the agent to wait for
        timeout: Maximum time to wait in seconds
        cleanup: Whether to cleanup the process after extracting result.
                 Set to False when resuming agents to preserve session for future resumes.
    """
    import time

    start = time.time()
    logger.info(f"Waiting for agent {agent_id} to complete (timeout={timeout}s)")

    while time.time() - start < timeout:
        # Check if process finished
        exit_code = process_manager.get_exit_code(agent_id)

        if exit_code is not None:
            logger.info(f"Agent {agent_id} finished with exit code {exit_code}")

            # Wait for output threads to finish and capture session_id
            session_id = process_manager.wait_for_output_and_get_session_id(agent_id, timeout=2.0)
            logger.info(f"Agent {agent_id} session_id: {session_id}")

            # Update agent state
            new_status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

            def updater(a: AgentState) -> AgentState:
                a.status = new_status
                a.exit_code = exit_code
                a.finished_at = datetime.now()
                # Capture session_id for future resumes
                if session_id:
                    a.session_id = session_id
                return a

            agent_store.update(agent_id, updater)

            # Extract result from output
            logger.info(f"Extracting result from agent {agent_id}")
            result = _extract_result(process_manager, agent_id)
            logger.info(f"Agent {agent_id} result: {result[:100]}..." if len(result) > 100 else f"Agent {agent_id} result: {result}")

            # Cleanup only if requested (not for resumed agents we want to reuse)
            if cleanup:
                logger.info(f"Cleaning up agent {agent_id}")
                process_manager.cleanup(agent_id)

            logger.info(f"Returning result for agent {agent_id}")
            return result

        time.sleep(0.5)

    # Timeout - kill the agent
    logger.warning(f"Agent {agent_id} timed out after {timeout}s")
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
