"""FastAPI dependency injection for the orchestrator server."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING

from ..core import AgentStateStore, PipelineExecutor, PipelineStateStore, ProcessManager, SessionManager
from ..models import AgentState, AgentStatus, OutputChunk

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OrchestratorState:
    """Global state for the orchestrator server.

    This class holds all the stateful components needed by the server:
    - Process manager for spawning and controlling agents
    - Agent state store for tracking agent states
    - Session manager for session persistence
    - WebSocket connection manager
    """

    _instance: "OrchestratorState | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._agent_store = AgentStateStore(persist=True)
        self._session_manager = SessionManager(persist=True)
        self._pipeline_store = PipelineStateStore(persist=True)
        self._process_manager = ProcessManager(
            on_output=self._handle_output,
            on_status_change=self._handle_status_change,
        )
        self._pipeline_executor = PipelineExecutor(
            process_manager=self._process_manager,
            agent_store=self._agent_store,
            pipeline_store=self._pipeline_store,
            on_node_status_change=self._handle_node_status_change,
        )
        self._ws_manager: "ConnectionManager | None" = None
        self._monitor_thread: threading.Thread | None = None
        self._running = False
        self._event_loop = None  # Will be set when server starts

        # Load persisted state from disk
        self._load_persisted_state()

    def _load_persisted_state(self) -> None:
        """Load all persisted state from disk on startup."""
        agents_loaded = self._agent_store.load_all()
        pipelines_loaded = self._pipeline_store.load_all()
        sessions_loaded = self._session_manager._store.load_all()

        logger.info(
            f"Loaded persisted state: {agents_loaded} agents, "
            f"{pipelines_loaded} pipelines, {sessions_loaded} sessions"
        )

    @classmethod
    def get_instance(cls) -> "OrchestratorState":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
            cls._instance = None

    @property
    def agent_store(self) -> AgentStateStore:
        return self._agent_store

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def pipeline_store(self) -> PipelineStateStore:
        return self._pipeline_store

    @property
    def process_manager(self) -> ProcessManager:
        return self._process_manager

    @property
    def pipeline_executor(self) -> PipelineExecutor:
        return self._pipeline_executor

    def set_ws_manager(self, manager: "ConnectionManager") -> None:
        """Set the WebSocket connection manager."""
        self._ws_manager = manager

    def set_event_loop(self, loop) -> None:
        """Set the event loop for async operations from background threads."""
        self._event_loop = loop

    def start_monitor(self) -> None:
        """Start the background process monitor."""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("Process monitor started")

    def stop_monitor(self) -> None:
        """Stop the background process monitor."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    def _monitor_loop(self) -> None:
        """Background loop to monitor process health."""
        import time

        while self._running:
            try:
                self._check_processes()
            except Exception as e:
                logger.warning(f"Monitor error: {e}")
            time.sleep(1.0)

    def _check_processes(self) -> None:
        """Check all processes and update states."""
        exit_codes = self._process_manager.poll_all()

        for agent_id, exit_code in exit_codes.items():
            if exit_code is None:
                continue  # Still running

            # Process has finished
            agent = self._agent_store.get(agent_id)
            if agent is None or agent.is_finished():
                continue

            # Update state based on exit code
            if exit_code == 0:
                new_status = AgentStatus.COMPLETED
            else:
                new_status = AgentStatus.FAILED

            # Use default args to capture current values (avoid closure capture bug)
            def make_updater(status: AgentStatus, code: int):
                def updater(a: AgentState) -> AgentState:
                    a.status = status
                    a.exit_code = code
                    a.finished_at = datetime.now()
                    return a
                return updater

            self._agent_store.update(agent_id, make_updater(new_status, exit_code))
            self._handle_status_change(agent_id, new_status)

            # Wait for output processing to complete and get session ID
            # This is important because the output reader threads might still
            # be processing the final output lines containing the session_id
            session_id = self._process_manager.wait_for_output_and_get_session_id(
                agent_id, timeout=2.0
            )

            if session_id:
                logger.debug(f"Captured session_id {session_id} for agent {agent_id}")
                # Save backend session ID directly to agent state for resume capability
                def make_session_updater(sid: str):
                    def session_updater(a: AgentState) -> AgentState:
                        a.session_id = sid
                        return a
                    return session_updater

                self._agent_store.update(agent_id, make_session_updater(session_id))

                # Also update session object if it exists
                agent = self._agent_store.get(agent_id)
                if agent and agent.config.session_id:
                    try:
                        self._session_manager.update_session(
                            agent.config.session_id,
                            backend_session_id=session_id,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update session: {e}")
            else:
                logger.warning(f"No session_id captured for agent {agent_id}")

            # Cleanup
            self._process_manager.cleanup(agent_id)

    def _handle_output(self, agent_id: str, chunk: OutputChunk) -> None:
        """Handle new output from an agent."""
        # Update agent state
        def updater(agent: AgentState) -> AgentState:
            agent.output_chunks += 1
            agent.last_activity_at = datetime.now()
            return agent

        self._agent_store.update(agent_id, updater)

        # Broadcast to WebSocket clients
        if self._ws_manager and self._event_loop:
            import asyncio

            try:
                # Schedule the coroutine from this background thread
                asyncio.run_coroutine_threadsafe(
                    self._ws_manager.broadcast_output(agent_id, chunk),
                    self._event_loop
                )
            except Exception as e:
                logger.debug(f"Failed to broadcast output: {e}")

    def _handle_status_change(self, agent_id: str, status: AgentStatus) -> None:
        """Handle agent status change."""
        logger.info(f"Agent {agent_id} status changed to {status}")

        # Broadcast to WebSocket clients
        if self._ws_manager and self._event_loop:
            import asyncio

            try:
                asyncio.run_coroutine_threadsafe(
                    self._ws_manager.broadcast_status(agent_id, status),
                    self._event_loop
                )
            except Exception as e:
                logger.debug(f"Failed to broadcast status: {e}")

    def _handle_node_status_change(
        self, pipeline_id: str, node_id: str, status: str
    ) -> None:
        """Handle pipeline node status change."""
        logger.debug(f"Pipeline {pipeline_id} node {node_id} status: {status}")

        # Update pipeline state with node status
        def updater(p):
            p.node_status[node_id] = status
            p.touch()
            return p

        self._pipeline_store.update(pipeline_id, updater)

        # Could broadcast via WebSocket here for real-time updates

    def shutdown(self) -> None:
        """Shutdown all components."""
        self.stop_monitor()
        self._process_manager.cleanup_all()


# FastAPI dependency functions


def get_orchestrator_state() -> OrchestratorState:
    """Get the orchestrator state singleton."""
    return OrchestratorState.get_instance()


def get_agent_store() -> AgentStateStore:
    """Get the agent state store."""
    return get_orchestrator_state().agent_store


def get_session_manager() -> SessionManager:
    """Get the session manager."""
    return get_orchestrator_state().session_manager


def get_pipeline_store() -> PipelineStateStore:
    """Get the pipeline state store."""
    return get_orchestrator_state().pipeline_store


def get_process_manager() -> ProcessManager:
    """Get the process manager."""
    return get_orchestrator_state().process_manager


def get_pipeline_executor() -> PipelineExecutor:
    """Get the pipeline executor."""
    return get_orchestrator_state().pipeline_executor


# WebSocket connection manager (imported lazily to avoid circular imports)


class ConnectionManager:
    """Manages WebSocket connections for streaming output."""

    def __init__(self) -> None:
        self._connections: dict[str, list] = {}  # agent_id -> list of WebSocket
        self._lock = threading.Lock()

    async def connect(self, websocket, agent_id: str) -> None:
        """Register a new WebSocket connection."""
        await websocket.accept()
        with self._lock:
            if agent_id not in self._connections:
                self._connections[agent_id] = []
            self._connections[agent_id].append(websocket)

    def disconnect(self, websocket, agent_id: str) -> None:
        """Remove a WebSocket connection."""
        with self._lock:
            if agent_id in self._connections:
                try:
                    self._connections[agent_id].remove(websocket)
                except ValueError:
                    pass
                if not self._connections[agent_id]:
                    del self._connections[agent_id]

    async def broadcast_output(self, agent_id: str, chunk: OutputChunk) -> None:
        """Broadcast an output chunk to all connections for an agent."""
        with self._lock:
            connections = list(self._connections.get(agent_id, []))

        from ..models import StreamEvent, StreamEventType

        event = StreamEvent(
            type=StreamEventType.AGENT_OUTPUT,
            agent_id=agent_id,
            chunk=chunk,
        )

        for websocket in connections:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                self.disconnect(websocket, agent_id)

    async def broadcast_status(self, agent_id: str, status: AgentStatus) -> None:
        """Broadcast a status change to all connections for an agent."""
        with self._lock:
            connections = list(self._connections.get(agent_id, []))

        from ..models import StreamEvent, StreamEventType

        event_type = {
            AgentStatus.RUNNING: StreamEventType.AGENT_STARTED,
            AgentStatus.COMPLETED: StreamEventType.AGENT_COMPLETED,
            AgentStatus.FAILED: StreamEventType.AGENT_FAILED,
            AgentStatus.TERMINATED: StreamEventType.AGENT_TERMINATED,
        }.get(status, StreamEventType.AGENT_OUTPUT)

        event = StreamEvent(
            type=event_type,
            agent_id=agent_id,
            data={"status": str(status)},
        )

        for websocket in connections:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                self.disconnect(websocket, agent_id)

    def get_connection_count(self, agent_id: str | None = None) -> int:
        """Get number of connections."""
        with self._lock:
            if agent_id:
                return len(self._connections.get(agent_id, []))
            return sum(len(conns) for conns in self._connections.values())
