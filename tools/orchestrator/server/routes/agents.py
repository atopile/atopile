"""Agent API routes for the orchestrator server."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core import AgentStateStore, ProcessManager
from ...exceptions import AgentNotFoundError, AgentNotRunningError, BackendSpawnError
from ...models import (
    AgentConfig,
    AgentHistoryResponse,
    AgentListResponse,
    AgentOutputResponse,
    AgentState,
    AgentStateResponse,
    AgentStatus,
    ImportSessionRequest,
    ResumeAgentRequest,
    RunOutput,
    SendInputRequest,
    SendInputResponse,
    SpawnAgentRequest,
    SpawnAgentResponse,
    TerminateAgentRequest,
    TerminateAgentResponse,
    UpdateAgentRequest,
)
from ..dependencies import broadcast_agent_spawned, broadcast_agent_status_changed, get_agent_store, get_process_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/spawn", response_model=SpawnAgentResponse)
async def spawn_agent(
    request: SpawnAgentRequest,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> SpawnAgentResponse:
    """Spawn a new agent.

    Creates a new agent with the given configuration and starts it immediately.
    Returns the agent ID which can be used to track progress and retrieve output.
    """
    # Create agent state
    agent = AgentState(
        config=request.config,
        name=request.name,
        status=AgentStatus.STARTING,
    )
    agent_store.set(agent.id, agent)

    logger.info(f"Spawning agent {agent.id} with backend {request.config.backend}")

    try:
        # Spawn the process
        managed = process_manager.spawn(agent)

        # Update state
        def updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            a.run_count = 0  # First run
            # Track prompt for this run
            a.metadata["prompts"] = [{"run": 0, "prompt": a.config.prompt}]
            return a

        agent_store.update(agent.id, updater)

        # Broadcast agent spawned event
        broadcast_agent_spawned(agent.id)

        return SpawnAgentResponse(
            agent_id=agent.id,
            status=AgentStatus.RUNNING,
            message=f"Agent spawned with PID {managed.process.pid}",
        )

    except BackendSpawnError as e:
        # Capture error message before defining closure
        error_msg = str(e)

        def make_fail_updater(msg: str):
            def updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.FAILED
                a.error_message = msg
                a.finished_at = datetime.now()
                return a
            return updater

        agent_store.update(agent.id, make_fail_updater(error_msg))
        raise HTTPException(status_code=500, detail=error_msg) from e

    except Exception as e:
        error_msg = str(e)

        def make_fail_updater(msg: str):
            def updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.FAILED
                a.error_message = msg
                a.finished_at = datetime.now()
                return a
            return updater

        agent_store.update(agent.id, make_fail_updater(error_msg))
        logger.exception(f"Failed to spawn agent {agent.id}")
        raise HTTPException(
            status_code=500, detail=f"Failed to spawn agent: {error_msg}"
        ) from e


@router.post("/import", response_model=SpawnAgentResponse)
async def import_session(
    request: ImportSessionRequest,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> SpawnAgentResponse:
    """Import and resume an external session not started through the orchestrator.

    This allows resuming sessions that were started in Claude Code CLI or other
    tools outside of the orchestrator. The session is imported as a new agent
    and resumed with the given prompt.
    """
    # Create agent config for resume
    config = AgentConfig(
        backend=request.backend,
        prompt=request.prompt,
        session_id=request.session_id,
        resume_session=True,
        working_directory=request.working_directory,
        model=request.model,
        max_turns=request.max_turns,
        max_budget_usd=request.max_budget_usd,
    )

    # Create agent state
    agent = AgentState(
        config=config,
        name=request.name or f"Imported: {request.session_id[:8]}",
        status=AgentStatus.STARTING,
        session_id=request.session_id,  # Set session_id immediately
    )
    agent_store.set(agent.id, agent)

    logger.info(f"Importing session {request.session_id} as agent {agent.id}")

    try:
        # Spawn the process
        managed = process_manager.spawn(agent)

        # Update state
        def updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            a.run_count = 0  # First run in orchestrator (original session runs not tracked)
            # Track prompt for this run
            a.metadata["prompts"] = [{"run": 0, "prompt": a.config.prompt}]
            a.metadata["imported_session"] = request.session_id
            return a

        agent_store.update(agent.id, updater)

        # Broadcast agent spawned event
        broadcast_agent_spawned(agent.id)

        return SpawnAgentResponse(
            agent_id=agent.id,
            status=AgentStatus.RUNNING,
            message=f"Session imported and resumed with PID {managed.process.pid}",
        )

    except BackendSpawnError as e:
        error_msg = str(e)

        def make_fail_updater(msg: str):
            def updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.FAILED
                a.error_message = msg
                a.finished_at = datetime.now()
                return a
            return updater

        agent_store.update(agent.id, make_fail_updater(error_msg))
        raise HTTPException(status_code=500, detail=error_msg) from e

    except Exception as e:
        error_msg = str(e)

        def make_fail_updater(msg: str):
            def updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.FAILED
                a.error_message = msg
                a.finished_at = datetime.now()
                return a
            return updater

        agent_store.update(agent.id, make_fail_updater(error_msg))
        logger.exception(f"Failed to import session as agent {agent.id}")
        raise HTTPException(
            status_code=500, detail=f"Failed to import session: {error_msg}"
        ) from e


@router.get("", response_model=AgentListResponse)
async def list_agents(
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    status: AgentStatus | None = None,
    backend: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> AgentListResponse:
    """List all agents with optional filtering."""
    agents = agent_store.values()

    # Apply filters
    if status is not None:
        agents = [a for a in agents if a.status == status]
    if backend is not None:
        agents = [a for a in agents if str(a.config.backend) == backend]

    # Sort by created_at descending
    agents.sort(key=lambda a: a.created_at, reverse=True)

    total = len(agents)
    agents = agents[offset : offset + limit]

    return AgentListResponse(agents=agents, total=total)


@router.get("/{agent_id}", response_model=AgentStateResponse)
async def get_agent(
    agent_id: str,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
) -> AgentStateResponse:
    """Get the state of a specific agent."""
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    return AgentStateResponse(agent=agent)


@router.get("/{agent_id}/todos")
async def get_agent_todos(
    agent_id: str,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
):
    """Get the current todo list for an agent."""
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    return {
        "agent_id": agent_id,
        "todos": [t.model_dump() for t in agent.todos],
        "total": len(agent.todos),
        "completed": sum(1 for t in agent.todos if t.status == "completed"),
        "in_progress": sum(1 for t in agent.todos if t.status == "in_progress"),
        "pending": sum(1 for t in agent.todos if t.status == "pending"),
    }


@router.patch("/{agent_id}", response_model=AgentStateResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
) -> AgentStateResponse:
    """Update an agent's metadata (e.g., rename)."""
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    def updater(a: AgentState) -> AgentState:
        if request.name is not None:
            a.name = request.name
        return a

    agent_store.update(agent_id, updater)
    agent = agent_store.get(agent_id)

    return AgentStateResponse(agent=agent)


@router.post("/{agent_id}/input", response_model=SendInputResponse)
async def send_input(
    agent_id: str,
    request: SendInputRequest,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> SendInputResponse:
    """Send input to a running agent."""
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    if not agent.is_running():
        raise HTTPException(
            status_code=400,
            detail=f"Agent is not running (status: {agent.status})",
        )

    try:
        success = process_manager.send_input(agent_id, request.input, request.newline)
        if success:
            return SendInputResponse(success=True, message="Input sent successfully")
        else:
            return SendInputResponse(success=False, message="Failed to send input")
    except AgentNotRunningError:
        raise HTTPException(status_code=400, detail="Agent is not running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{agent_id}/resume", response_model=SpawnAgentResponse)
async def resume_agent(
    agent_id: str,
    request: ResumeAgentRequest,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> SpawnAgentResponse:
    """Resume a completed agent with a new prompt.

    Reuses the same agent entry and continues the session with Claude Code's
    --resume flag. The conversation history is maintained in the same agent.
    Returns the same agent ID.
    """
    # Get the agent
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # Check if agent has a session_id to resume
    if not agent.session_id:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have a session ID to resume. The agent may not have completed successfully.",
        )

    # Check if agent is finished (can only resume completed agents)
    if not agent.is_finished():
        raise HTTPException(
            status_code=400,
            detail=f"Agent is still running (status: {agent.status}). Wait for it to complete or terminate it first.",
        )

    logger.info(f"Resuming agent {agent_id} with session {agent.session_id}")

    # Update config with new prompt and resume settings
    def prepare_updater(prompt: str, max_turns: int | None, max_budget: float | None):
        def updater(a: AgentState) -> AgentState:
            # Update config for resume
            a.config.prompt = prompt
            a.config.session_id = a.session_id  # Use the captured session_id
            a.config.resume_session = True
            if max_turns is not None:
                a.config.max_turns = max_turns
            if max_budget is not None:
                a.config.max_budget_usd = max_budget

            # Update state for new run
            a.status = AgentStatus.STARTING
            a.exit_code = None
            a.error_message = None
            a.finished_at = None

            # Increment run_count for versioned logs
            a.run_count += 1

            # Track prompt for this run
            prompts = a.metadata.get("prompts", [])
            prompts.append({"run": a.run_count, "prompt": prompt})
            a.metadata["prompts"] = prompts

            # Track resume count in metadata (legacy)
            resume_count = a.metadata.get("resume_count", 0)
            a.metadata["resume_count"] = resume_count + 1

            return a
        return updater

    agent_store.update(
        agent_id,
        prepare_updater(request.prompt, request.max_turns, request.max_budget_usd)
    )

    # Get updated agent
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent disappeared during update")

    try:
        # Spawn the process (reusing the same agent)
        managed = process_manager.spawn(agent)

        # Update state to running
        def running_updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            return a

        agent_store.update(agent_id, running_updater)

        # Broadcast status change so all connected clients update
        broadcast_agent_status_changed(agent_id)

        return SpawnAgentResponse(
            agent_id=agent_id,
            status=AgentStatus.RUNNING,
            message=f"Agent resumed with PID {managed.process.pid} (resume #{agent.metadata.get('resume_count', 1)})",
        )

    except Exception as e:
        error_msg = str(e)

        def fail_updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.FAILED
            a.error_message = error_msg
            a.finished_at = datetime.now()
            return a

        agent_store.update(agent_id, fail_updater)
        logger.exception(f"Failed to resume agent {agent_id}")
        raise HTTPException(
            status_code=500, detail=f"Failed to resume agent: {error_msg}"
        ) from e


@router.post("/{agent_id}/terminate", response_model=TerminateAgentResponse)
async def terminate_agent(
    agent_id: str,
    request: TerminateAgentRequest,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> TerminateAgentResponse:
    """Terminate a running agent.

    If the process manager can't find the process but we have a PID,
    we'll try to kill by PID directly when force=true.
    """
    import os
    import signal

    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    if agent.is_finished():
        return TerminateAgentResponse(
            agent_id=agent_id,
            success=True,
            message=f"Agent already finished with status: {agent.status}",
        )

    killed_by_pid = False

    try:
        if request.force:
            process_manager.kill(agent_id)
        else:
            process_manager.terminate(agent_id, timeout=request.timeout_seconds)

    except AgentNotFoundError:
        # Process manager doesn't have the process, try by PID if force
        if request.force and agent.pid:
            try:
                os.kill(agent.pid, signal.SIGKILL)
                killed_by_pid = True
                logger.info(f"Force killed agent {agent_id} by PID {agent.pid}")
            except ProcessLookupError:
                # Process already dead
                killed_by_pid = True
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Process manager lost track and PID kill failed: {e}"
                ) from e
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Agent process not found. Use force=true to kill by PID."
            )

    except Exception as e:
        # Other error - try PID kill if force
        if request.force and agent.pid:
            try:
                os.kill(agent.pid, signal.SIGKILL)
                killed_by_pid = True
                logger.info(f"Force killed agent {agent_id} by PID {agent.pid} after error: {e}")
            except ProcessLookupError:
                killed_by_pid = True
            except Exception as kill_err:
                raise HTTPException(
                    status_code=500,
                    detail=f"Terminate failed ({e}) and PID kill failed ({kill_err})"
                ) from kill_err
        else:
            raise HTTPException(status_code=500, detail=str(e)) from e

    # Update state
    def updater(a: AgentState) -> AgentState:
        a.status = AgentStatus.TERMINATED
        a.finished_at = datetime.now()
        return a

    agent_store.update(agent_id, updater)

    # Broadcast status change
    broadcast_agent_status_changed(agent_id)

    msg = "Agent terminated successfully"
    if killed_by_pid:
        msg = f"Agent terminated by PID {agent.pid} (process manager lost track)"

    return TerminateAgentResponse(
        agent_id=agent_id,
        success=True,
        message=msg,
    )


@router.get("/{agent_id}/output", response_model=AgentOutputResponse)
async def get_output(
    agent_id: str,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
    since_sequence: int = Query(default=0, ge=0),
    max_chunks: int = Query(default=1000, ge=1, le=10000),
) -> AgentOutputResponse:
    """Get buffered output from an agent."""
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    chunks = process_manager.get_output(
        agent_id,
        since_sequence=since_sequence,
        max_chunks=max_chunks,
        backend_type=agent.config.backend,
    )

    return AgentOutputResponse(
        agent_id=agent_id,
        chunks=[c.model_dump() for c in chunks],
        total_chunks=agent.output_chunks,
    )


@router.get("/{agent_id}/history", response_model=AgentHistoryResponse)
async def get_full_history(
    agent_id: str,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> AgentHistoryResponse:
    """Get all output from all runs of this agent.

    Returns combined output from all versioned log files for this agent,
    organized by run number. This is useful for viewing the complete
    conversation history across multiple resume operations.
    """
    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # Get prompts from metadata (keyed by run number)
    prompts_list = agent.metadata.get("prompts", [])
    prompts_by_run = {p["run"]: p["prompt"] for p in prompts_list if isinstance(p, dict)}

    # Get all run logs (use agent's backend type for correct parsing)
    run_logs = process_manager.get_all_run_logs(agent_id, backend_type=agent.config.backend)

    # Convert to response format
    runs = []
    total_chunks = 0
    for run_number, chunks in run_logs:
        runs.append(
            RunOutput(
                run_number=run_number,
                prompt=prompts_by_run.get(run_number),
                chunks=[c.model_dump() for c in chunks],
            )
        )
        total_chunks += len(chunks)

    return AgentHistoryResponse(
        agent_id=agent_id,
        runs=runs,
        total_runs=len(runs),
        total_chunks=total_chunks,
    )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
    force: bool = Query(default=False, description="Force kill by PID if process manager fails"),
) -> dict:
    """Delete an agent and its associated data.

    If the agent is still running, it will be terminated first.
    Use force=true to kill by PID directly if the process manager can't terminate it.
    """
    import os
    import signal

    agent = agent_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    killed_by_pid = False

    # Terminate if running
    if agent.is_running():
        try:
            process_manager.terminate(agent_id, timeout=2.0)
        except Exception as e:
            logger.warning(f"Process manager terminate failed for {agent_id}: {e}")
            # If force and we have a PID, try to kill directly
            if force and agent.pid:
                try:
                    os.kill(agent.pid, signal.SIGKILL)
                    killed_by_pid = True
                    logger.info(f"Force killed agent {agent_id} by PID {agent.pid}")
                except ProcessLookupError:
                    # Process already dead
                    killed_by_pid = True
                except Exception as kill_err:
                    logger.error(f"Failed to force kill PID {agent.pid}: {kill_err}")

        try:
            process_manager.cleanup(agent_id)
        except Exception:
            pass

    # If force delete with PID but process manager didn't have it tracked,
    # still try to kill by PID
    elif force and agent.pid:
        try:
            os.kill(agent.pid, signal.SIGKILL)
            killed_by_pid = True
            logger.info(f"Force killed orphaned agent {agent_id} by PID {agent.pid}")
        except ProcessLookupError:
            # Process already dead, that's fine
            pass
        except Exception as e:
            logger.warning(f"Could not kill PID {agent.pid}: {e}")

    # Delete from store
    agent_store.delete(agent_id)

    msg = "Agent deleted"
    if killed_by_pid:
        msg = f"Agent deleted (force killed PID {agent.pid})"

    return {"status": "deleted", "agent_id": agent_id, "message": msg}
