"""Pipeline execution engine for spawning and managing agent workflows."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from ..models import (
    AgentBackendType,
    AgentConfig,
    AgentState,
    AgentStatus,
    PipelineSession,
    PipelineSessionStatus,
    PipelineState,
    PipelineStatus,
)

if TYPE_CHECKING:
    from .process import ProcessManager
    from .state import AgentStateStore, PipelineSessionStore, PipelineStateStore

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Executes pipelines by traversing nodes and spawning agents.

    This executor handles:
    - Finding and executing agent nodes in order
    - Spawning agents and tracking their state
    - Updating pipeline state as execution progresses
    - Handling execution completion or failure
    """

    def __init__(
        self,
        process_manager: "ProcessManager",
        agent_store: "AgentStateStore",
        pipeline_store: "PipelineStateStore",
        pipeline_session_store: "PipelineSessionStore",
        on_node_status_change: Callable[[str, str, str, str | None], None] | None = None,
        on_session_status_change: Callable[[str, str, str], None] | None = None,
    ) -> None:
        """Initialize the pipeline executor.

        Args:
            process_manager: Process manager for spawning agents
            agent_store: Store for agent states
            pipeline_store: Store for pipeline states
            pipeline_session_store: Store for pipeline session states
            on_node_status_change: Callback(pipeline_id, node_id, status, session_id) for node status changes
            on_session_status_change: Callback(pipeline_id, session_id, status) for session status changes
        """
        self._process_manager = process_manager
        self._agent_store = agent_store
        self._pipeline_store = pipeline_store
        self._pipeline_session_store = pipeline_session_store
        self._on_node_status_change = on_node_status_change
        self._on_session_status_change = on_session_status_change
        self._running_pipelines: dict[str, PipelineExecution] = {}
        self._lock = threading.Lock()

    def start_pipeline(self, pipeline_id: str) -> str | None:
        """Start executing a pipeline.

        Args:
            pipeline_id: ID of the pipeline to start

        Returns:
            Session ID if started successfully, None otherwise
        """
        pipeline = self._pipeline_store.get(pipeline_id)
        if pipeline is None:
            logger.error(f"Pipeline not found: {pipeline_id}")
            return None

        # Note: We allow multiple sessions to run concurrently
        # The pipeline.status field is no longer used for blocking - sessions track execution state

        # Create a new session for this execution
        session = PipelineSession(
            pipeline_id=pipeline_id,
            status=PipelineSessionStatus.RUNNING,
        )
        self._pipeline_session_store.set(session.id, session)
        logger.info(f"Created pipeline session: {session.id} for pipeline {pipeline_id}")

        # Update pipeline metadata (don't set status - sessions track execution state)
        def updater(p: PipelineState) -> PipelineState:
            # Reset legacy node status/agent maps (UI uses session data now)
            p.node_status = {}
            p.node_agent_map = {}
            if p.started_at is None:
                p.started_at = datetime.now()
            p.touch()
            return p

        self._pipeline_store.update(pipeline_id, updater)

        # Create execution context with session
        execution = PipelineExecution(
            pipeline_id=pipeline_id,
            session_id=session.id,
            executor=self,
        )

        with self._lock:
            self._running_pipelines[pipeline_id] = execution

        # Start execution in background thread
        thread = threading.Thread(
            target=self._run_pipeline_thread,
            args=(execution,),
            daemon=True,
        )
        thread.start()
        logger.info(f"Pipeline execution started: {pipeline_id} (session: {session.id})")

        return session.id

    def stop_pipeline(self, pipeline_id: str) -> bool:
        """Stop a running pipeline.

        Args:
            pipeline_id: ID of the pipeline to stop

        Returns:
            True if stopped successfully
        """
        with self._lock:
            execution = self._running_pipelines.get(pipeline_id)

        if execution is None:
            return False

        execution.stop()
        return True

    def get_pipeline_agents(self, pipeline_id: str) -> list[str]:
        """Get agent IDs spawned by a pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            List of agent IDs
        """
        with self._lock:
            execution = self._running_pipelines.get(pipeline_id)

        if execution is None:
            # Check persisted state
            pipeline = self._pipeline_store.get(pipeline_id)
            if pipeline:
                return list(pipeline.node_agent_map.values())
            return []

        return list(execution.node_agents.values())

    def _run_pipeline_thread(self, execution: "PipelineExecution") -> None:
        """Run pipeline execution in a background thread."""
        logger.info(f"Pipeline thread started for {execution.pipeline_id}")
        try:
            execution.run()
            logger.info(f"Pipeline thread completed for {execution.pipeline_id}")
        except Exception as e:
            logger.exception(f"Pipeline execution failed: {execution.pipeline_id}")
            self._mark_pipeline_failed(execution.pipeline_id, str(e))
        finally:
            with self._lock:
                self._running_pipelines.pop(execution.pipeline_id, None)

    def _mark_pipeline_failed(self, pipeline_id: str, error: str) -> None:
        """Mark a pipeline thread as failed (error in execution engine)."""
        # Note: Pipeline status is managed by sessions now, so we just log the error
        # The session should be marked as failed by the execution context
        def updater(p: PipelineState) -> PipelineState:
            p.current_node_id = None
            p.touch()
            return p

        self._pipeline_store.update(pipeline_id, updater)
        logger.error(f"Pipeline execution thread failed for {pipeline_id}: {error}")


class PipelineExecution:
    """Represents an active pipeline execution."""

    def __init__(
        self,
        pipeline_id: str,
        session_id: str,
        executor: PipelineExecutor,
    ) -> None:
        self.pipeline_id = pipeline_id
        self.session_id = session_id
        self.executor = executor
        self.node_agents: dict[str, str] = {}  # node_id -> agent_id
        self.node_status: dict[str, str] = {}  # node_id -> status
        self.node_outputs: dict[str, str] = {}  # node_id -> output result (for communication)
        self.loop_iterations: dict[str, int] = {}  # loop_node_id -> iteration count
        self._should_stop = False
        self._current_agent_id: str | None = None

    def stop(self) -> None:
        """Signal the execution to stop."""
        self._should_stop = True

        # Terminate current agent if running
        if self._current_agent_id:
            try:
                self.executor._process_manager.terminate(self._current_agent_id, timeout=5.0)
            except Exception as e:
                logger.warning(f"Failed to terminate agent {self._current_agent_id}: {e}")

    def run(self) -> None:
        """Execute the pipeline."""
        from ..server.routes.bridge import register_pipeline_context

        pipeline = self.executor._pipeline_store.get(self.pipeline_id)
        if pipeline is None:
            raise RuntimeError(f"Pipeline not found: {self.pipeline_id}")

        logger.info(f"Starting pipeline execution: {self.pipeline_id}")
        logger.info(f"Pipeline has {len(pipeline.nodes)} nodes and {len(pipeline.edges)} edges")

        # Pre-register pipeline context with all agent nodes for bridge communication
        # This allows agents to find each other even before they've all executed
        self._register_pipeline_context(pipeline)

        # Find execution order (topological sort from trigger nodes)
        execution_order = self._get_execution_order(pipeline)
        logger.info(f"Execution order: {execution_order}")

        if not execution_order:
            logger.warning(f"No executable nodes in pipeline: {self.pipeline_id}")
            self._mark_completed()
            return

        # Track last executed node status for loop decisions
        last_node_failed = False

        # Execute nodes - use index to support jumping back for loops
        current_index = 0
        while current_index < len(execution_order):
            if self._should_stop:
                logger.info(f"Pipeline stopped: {self.pipeline_id}")
                self._mark_stopped()
                return

            node_id = execution_order[current_index]
            node = self._find_node(pipeline, node_id)
            if node is None:
                logger.warning(f"Node not found: {node_id}")
                current_index += 1
                continue

            logger.debug(f"Executing node {node_id} (type={node.type})")
            self._update_node_status(node_id, "running")

            try:
                if node.type == "agent":
                    self._execute_agent_node(pipeline, node)
                    last_node_failed = False
                elif node.type == "trigger":
                    # Trigger nodes just mark as complete
                    pass
                elif node.type == "loop":
                    # Loop nodes check conditions and may restart
                    restart_node_id = self._execute_loop_node(pipeline, node, last_node_failed)
                    if restart_node_id:
                        # Find the index of the restart node
                        try:
                            restart_index = execution_order.index(restart_node_id)
                            logger.info(f"Loop restarting from node {restart_node_id} (index {restart_index})")
                            current_index = restart_index
                            continue  # Skip the increment at the bottom
                        except ValueError:
                            logger.warning(f"Loop target node {restart_node_id} not in execution order")
                elif node.type == "condition":
                    # Condition nodes - for now just pass through
                    pass

                self._update_node_status(node_id, "completed")

            except Exception as e:
                logger.error(f"Node {node_id} failed: {e}")
                self._update_node_status(node_id, "failed")
                last_node_failed = True

                if pipeline.config.stop_on_failure:
                    self._mark_failed(str(e))
                    return

            current_index += 1

        self._mark_completed()

    def _get_execution_order(self, pipeline: PipelineState) -> list[str]:
        """Get nodes in execution order for MCP-based communication.

        For MCP communication to work, receivers must be spawned BEFORE senders.
        So we use REVERSE topological order for agent nodes:
        1. First: trigger nodes
        2. Then: agent nodes that RECEIVE from other agents (workers/receivers)
        3. Finally: agent nodes that SEND to other agents (coordinators/senders)

        This ensures when an agent tries to send an MCP message, the target is already running.
        """
        from ..models import PipelineNode, PipelineEdge

        # Separate nodes by type
        trigger_nodes = []
        agent_nodes = []
        other_nodes = []

        for node in pipeline.nodes:
            if node.type == "trigger":
                trigger_nodes.append(node.id)
            elif node.type == "agent":
                agent_nodes.append(node.id)
            else:
                other_nodes.append(node.id)

        # For agent nodes, determine which are receivers vs senders
        # An agent is a "receiver" if another agent has an edge pointing TO it
        # An agent is a "sender" if it has an edge pointing TO another agent
        agent_set = set(agent_nodes)
        has_incoming_from_agent: set[str] = set()  # Receivers
        has_outgoing_to_agent: set[str] = set()    # Senders

        for edge in pipeline.edges:
            source = edge.source
            target = edge.target
            if source and target:
                source_is_agent = source in agent_set
                target_is_agent = target in agent_set
                if source_is_agent and target_is_agent:
                    has_incoming_from_agent.add(target)  # target is a receiver
                    has_outgoing_to_agent.add(source)    # source is a sender

        # Order agent nodes: receivers first, then senders
        # Agents that are ONLY receivers go first
        # Agents that are ONLY senders go last
        # Agents that are both go in the middle
        receivers_only = [n for n in agent_nodes if n in has_incoming_from_agent and n not in has_outgoing_to_agent]
        both = [n for n in agent_nodes if n in has_incoming_from_agent and n in has_outgoing_to_agent]
        senders_only = [n for n in agent_nodes if n not in has_incoming_from_agent and n in has_outgoing_to_agent]
        neither = [n for n in agent_nodes if n not in has_incoming_from_agent and n not in has_outgoing_to_agent]

        # Build final order: triggers first, then receivers, then senders
        order = trigger_nodes + receivers_only + both + neither + senders_only + other_nodes

        logger.debug(f"Execution order breakdown - triggers: {trigger_nodes}, receivers: {receivers_only}, "
                    f"both: {both}, neither: {neither}, senders: {senders_only}")

        return order

    def _find_node(self, pipeline: PipelineState, node_id: str):
        """Find a node by ID."""
        from ..models import PipelineNode

        for node in pipeline.nodes:
            if node.id == node_id:
                return node
        return None

    def _get_parent_node_ids(self, pipeline: PipelineState, node_id: str) -> list[str]:
        """Get IDs of parent nodes (nodes that have edges pointing to this node)."""
        parent_ids = []
        for edge in pipeline.edges:
            if edge.target == node_id and edge.source:
                parent_ids.append(edge.source)
        return parent_ids

    def _build_context_from_parents(self, pipeline: PipelineState, node_id: str) -> str:
        """Build context string from NON-AGENT parent node outputs.

        For agent-to-agent communication, we use MCP (explicit messaging).
        Context injection is only used for non-agent sources (triggers, data nodes, etc.)
        to provide initial context to an agent.

        If you need implicit data passing from one agent to another, use an edge
        in the REVERSE direction (from receiver to sender) - but this isn't implemented yet.
        """
        parent_ids = self._get_parent_node_ids(pipeline, node_id)
        if not parent_ids:
            return ""

        context_parts = []
        for parent_id in parent_ids:
            parent_node = self._find_node(pipeline, parent_id)
            if not parent_node:
                continue

            # Skip agent parents - they communicate via MCP, not context injection
            if parent_node.type == "agent":
                continue

            if parent_id in self.node_outputs:
                parent_name = "Unknown"
                if hasattr(parent_node.data, 'name'):
                    parent_name = parent_node.data.name or parent_id

                output = self.node_outputs[parent_id]
                context_parts.append(f"[OUTPUT FROM '{parent_name}']\n{output}\n")

        if not context_parts:
            return ""

        # Use format that won't be misinterpreted as CLI options (avoid starting with dashes)
        return "[CONTEXT FROM PREVIOUS AGENTS]\n" + "\n".join(context_parts) + "[END CONTEXT]\n\n"

    def _extract_agent_result(self, agent_id: str) -> str:
        """Extract the final result from an agent's output."""
        # Get output chunks from process manager
        chunks = self.executor._process_manager.get_output(agent_id)

        # Look for the result chunk (contains the final summary)
        for chunk in reversed(chunks):
            if chunk.type.value == "result":
                # Result chunk has the final text
                if chunk.content:
                    return chunk.content
                if chunk.data and "result" in chunk.data:
                    return str(chunk.data["result"])

        # Fallback: collect all assistant text content
        assistant_text = []
        for chunk in chunks:
            if chunk.type.value == "assistant" and chunk.content:
                assistant_text.append(chunk.content)

        if assistant_text:
            return "\n".join(assistant_text)

        return "(No output captured)"

    def _execute_agent_node(self, pipeline: PipelineState, node) -> None:
        """Execute an agent node by spawning or resuming an agent.

        If this node already has an agent from a previous loop iteration that can be resumed,
        we resume it to preserve context. Otherwise, we spawn a new agent.
        """
        from ..models import PipelineNode, AgentNodeData

        node_id = node.id
        data = node.data

        # Build agent config from node data (data is AgentNodeData)
        backend = data.backend if hasattr(data, 'backend') else AgentBackendType.CLAUDE_CODE
        prompt = data.prompt if hasattr(data, 'prompt') else ""
        node_agent_name = data.name if hasattr(data, 'name') else "Pipeline Agent"

        # Generate full agent name: <pipeline_name>.<agent_name>
        full_agent_name = self._make_agent_name(pipeline, node_agent_name)

        # Validate prompt - must not be empty
        if not prompt or not prompt.strip():
            raise ValueError(f"Agent node '{node_agent_name}' ({node_id}) has an empty prompt. Please specify a prompt.")

        # Build context from parent node outputs (for inter-agent communication via context injection)
        parent_context = self._build_context_from_parents(pipeline, node_id)
        if parent_context:
            prompt = f"{parent_context}{prompt}"
            logger.info(f"Injected context from parent nodes into prompt for {node_id}")

        # Prepend planning file content if specified
        planning_file = getattr(data, 'planning_file', None)
        if planning_file:
            try:
                with open(planning_file, "r") as f:
                    planning_content = f.read()
                prompt = f"{planning_content}\n\n{prompt}"
            except Exception as e:
                logger.warning(f"Failed to read planning file: {e}")

        # Check for connected agents (for bridge communication)
        connected_agents = self._get_connected_agent_names(pipeline, node_id)

        # Set up environment - always add bridge env vars for pipeline agents
        environment = {}
        if hasattr(data, 'environment') and data.environment:
            environment.update(data.environment)

        # Always set up bridge environment variables for pipeline agents
        # (even if no connected agents, they might be contacted by others)
        environment["AGENT_NAME"] = node_agent_name
        environment["PIPELINE_ID"] = self.pipeline_id
        environment["BRIDGE_URL"] = "http://127.0.0.1:8765"  # Orchestrator URL

        # Check if this agent can receive messages from other agents (has incoming edges)
        can_receive = self._has_incoming_agent_edges(pipeline, node_id)

        if connected_agents:
            # This agent can SEND to other agents
            bridge_instructions = f"""You are part of a multi-agent pipeline. You can communicate with other agents using the send_and_receive tool.

Connected agents you can talk to: {', '.join(connected_agents)}

To send a message and get a response, use: send_and_receive(to="agent_name", message="your message")

IMPORTANT: When you receive a message from another agent (via the bridge), just respond with text output. Do NOT use send_and_receive to reply - your text output is automatically returned to the sender."""
            prompt = f"{bridge_instructions}\n\n{prompt}"

        elif can_receive:
            # This agent can only RECEIVE messages (no outgoing edges to agents)
            bridge_instructions = """You are a worker in a multi-agent pipeline. Other agents may send you requests.

When you receive a message, complete the requested task using your tools, then respond with text output.
Your response will be automatically returned to the agent that contacted you.

Do NOT try to contact other agents - just focus on completing the task you're given."""
            prompt = f"{bridge_instructions}\n\n{prompt}"

        # Check if we can resume an existing agent for this node
        existing_agent_id = self.node_agents.get(node_id)
        existing_agent = self.executor._agent_store.get(existing_agent_id) if existing_agent_id else None

        if existing_agent and existing_agent.session_id and existing_agent.is_finished():
            # Resume existing agent to preserve context
            logger.info(f"Resuming agent '{full_agent_name}' for node {node_id}: {existing_agent_id}")
            self._resume_agent(existing_agent_id, prompt, pipeline, node_id)
        else:
            # Spawn new agent
            if existing_agent:
                logger.info(f"Cannot resume agent for {node_id}: session_id={existing_agent.session_id}, status={existing_agent.status}")
            self._spawn_new_agent(prompt, full_agent_name, pipeline, node, backend, data, environment)

    def _resume_agent(
        self,
        agent_id: str,
        prompt: str,
        pipeline: PipelineState,
        node_id: str,
    ) -> None:
        """Resume an existing agent with a new prompt, preserving its context."""
        # Prepare agent for resume
        def prepare_updater(a: AgentState) -> AgentState:
            a.config.prompt = prompt
            a.config.session_id = a.session_id
            a.config.resume_session = True
            a.config.max_turns = a.config.max_turns or 10
            a.status = AgentStatus.STARTING
            a.exit_code = None
            a.error_message = None
            a.finished_at = None
            # Increment run_count for versioned log files
            a.run_count = (a.run_count or 0) + 1
            resume_count = a.metadata.get("resume_count", 0)
            a.metadata["resume_count"] = resume_count + 1
            return a

        self.executor._agent_store.update(agent_id, prepare_updater)
        agent = self.executor._agent_store.get(agent_id)

        try:
            logger.info(f"Spawning process for resumed agent {agent_id} (run_count={agent.run_count})")
            managed = self.executor._process_manager.spawn(agent)
            logger.info(f"Process spawned for agent {agent_id}: pid={managed.process.pid}")

            def running_updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.RUNNING
                a.pid = managed.process.pid
                a.started_at = datetime.now()
                return a

            self.executor._agent_store.update(agent_id, running_updater)
            self._current_agent_id = agent_id

            # Update pipeline state
            def pipeline_updater(p: PipelineState) -> PipelineState:
                p.current_node_id = node_id
                p.touch()
                return p

            self.executor._pipeline_store.update(self.pipeline_id, pipeline_updater)

            # Update bridge context
            self._register_pipeline_context(pipeline)

            # Wait for agent to complete
            self._wait_for_agent(agent_id)

            # Capture the agent's output
            output = self._extract_agent_result(agent_id)
            self.node_outputs[node_id] = output
            logger.info(f"Captured output from resumed agent {node_id}: {len(output)} chars")

            # Update bridge context again after completion
            self._register_pipeline_context(pipeline)

        except Exception as e:
            logger.error(f"Failed to resume agent for node {node_id}: {e}", exc_info=True)
            raise
        finally:
            self._current_agent_id = None

    def _spawn_new_agent(
        self,
        prompt: str,
        full_agent_name: str,
        pipeline: PipelineState,
        node,
        backend,
        data,
        environment: dict,
    ) -> None:
        """Spawn a new agent for a node."""
        node_id = node.id

        config = AgentConfig(
            backend=backend,
            prompt=prompt,
            max_turns=getattr(data, 'max_turns', None) or 10,
            max_budget_usd=getattr(data, 'max_budget_usd', None),
            system_prompt=getattr(data, 'system_prompt', None),
            working_directory=getattr(data, 'working_directory', None),
            environment=environment if environment else None,
        )

        # Create and spawn agent with proper naming and pipeline tracking
        agent = AgentState(
            config=config,
            status=AgentStatus.STARTING,
            name=full_agent_name,
            pipeline_id=self.pipeline_id,
            node_id=node_id,
        )
        self.executor._agent_store.set(agent.id, agent)

        logger.info(f"Spawning new agent '{full_agent_name}' for node {node_id}: {agent.id}")

        try:
            managed = self.executor._process_manager.spawn(agent)

            # Update agent state
            def agent_updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.RUNNING
                a.pid = managed.process.pid
                a.started_at = datetime.now()
                return a

            self.executor._agent_store.update(agent.id, agent_updater)

            # Track agent in local map
            self.node_agents[node_id] = agent.id
            self._current_agent_id = agent.id

            # Update session state with agent mapping
            def session_updater(s: PipelineSession) -> PipelineSession:
                s.node_agent_map[node_id] = agent.id
                s.execution_order.append(node_id)
                return s

            self.executor._pipeline_session_store.update(self.session_id, session_updater)

            # Also update pipeline state for backwards compatibility
            def pipeline_updater(p: PipelineState) -> PipelineState:
                p.current_node_id = node_id
                p.node_agent_map[node_id] = agent.id
                p.execution_history.append(agent.id)
                p.touch()
                return p

            self.executor._pipeline_store.update(self.pipeline_id, pipeline_updater)

            # Update bridge context with the new agent (for resume support)
            self._register_pipeline_context(pipeline)

            # Wait for agent to complete
            self._wait_for_agent(agent.id)

            # Capture the agent's output for downstream nodes (before cleanup!)
            output = self._extract_agent_result(agent.id)
            self.node_outputs[node_id] = output
            logger.info(f"Captured output from node {node_id}: {len(output)} chars")

            # Update bridge context again after agent completion (session_id now available)
            self._register_pipeline_context(pipeline)

            # Note: We don't cleanup immediately to allow the agent to be resumed
            # self.executor._process_manager.cleanup(agent.id)

        except Exception as e:
            logger.error(f"Failed to spawn agent for node {node_id}: {e}")
            # Try to cleanup on failure too
            try:
                self.executor._process_manager.cleanup(agent.id)
            except Exception:
                pass
            raise

        finally:
            self._current_agent_id = None

    def _execute_loop_node(
        self, pipeline: PipelineState, node, last_node_failed: bool
    ) -> str | None:
        """Execute a loop node - check conditions and return restart target if should loop.

        Args:
            pipeline: The pipeline state
            node: The loop node
            last_node_failed: Whether the previous node execution failed

        Returns:
            Node ID to restart from, or None to continue normally
        """
        import time
        from ..models import LoopNodeData

        node_id = node.id
        data = node.data

        # Get loop configuration
        duration_seconds = getattr(data, 'duration_seconds', 3600)
        restart_on_complete = getattr(data, 'restart_on_complete', True)
        restart_on_fail = getattr(data, 'restart_on_fail', False)
        max_iterations = getattr(data, 'max_iterations', None)

        # Get current iteration count (1-indexed for display)
        current_iteration = self.loop_iterations.get(node_id, 1)

        # Always update session with current iteration (so it shows during execution)
        def iteration_updater(s: PipelineSession) -> PipelineSession:
            s.loop_iterations[node_id] = current_iteration
            return s
        self.executor._pipeline_session_store.update(self.session_id, iteration_updater)

        # Check max iterations
        if max_iterations is not None and current_iteration > max_iterations:
            logger.info(f"Loop {node_id} reached max iterations ({max_iterations}), stopping")
            return None

        # Check restart conditions
        should_restart = False
        if last_node_failed:
            should_restart = restart_on_fail
            logger.info(f"Loop {node_id}: last node failed, restart_on_fail={restart_on_fail}")
        else:
            should_restart = restart_on_complete
            logger.info(f"Loop {node_id}: last node completed, restart_on_complete={restart_on_complete}")

        if not should_restart:
            logger.info(f"Loop {node_id}: conditions not met for restart")
            return None

        # Find the target node (where the loop connects TO)
        target_node_id = None
        for edge in pipeline.edges:
            if edge.source == node_id and edge.target:
                target_node_id = edge.target
                break

        if not target_node_id:
            logger.warning(f"Loop {node_id} has no outgoing edge, cannot restart")
            return None

        # Increment iteration count for next run
        self.loop_iterations[node_id] = current_iteration + 1
        logger.info(f"Loop {node_id}: completed iteration {current_iteration}, waiting {duration_seconds}s before starting iteration {current_iteration + 1}")

        # Wait for duration (check should_stop periodically)
        wait_start = time.time()
        while time.time() - wait_start < duration_seconds:
            if self._should_stop:
                logger.info(f"Loop {node_id}: stopping during wait")
                return None
            time.sleep(1.0)

        logger.info(f"Loop {node_id}: restarting from {target_node_id}")
        return target_node_id

    def _wait_for_agent(self, agent_id: str) -> None:
        """Wait for an agent to complete.

        Note: Does NOT cleanup the process - that's done after output extraction.
        """
        import time

        while not self._should_stop:
            agent = self.executor._agent_store.get(agent_id)
            if agent is None:
                break

            if agent.is_finished():
                logger.info(f"Agent completed: {agent_id} with status {agent.status}")
                break

            # Check process directly
            exit_code = self.executor._process_manager.get_exit_code(agent_id)
            if exit_code is not None:
                # Wait for output threads to finish processing and capture session_id
                session_id = self.executor._process_manager.wait_for_output_and_get_session_id(agent_id, timeout=2.0)

                # Process finished, update agent state
                new_status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

                def updater(a: AgentState) -> AgentState:
                    a.status = new_status
                    a.exit_code = exit_code
                    a.finished_at = datetime.now()
                    # Capture session_id for resume support
                    if session_id:
                        a.session_id = session_id
                    return a

                self.executor._agent_store.update(agent_id, updater)
                # NOTE: cleanup is called AFTER output extraction in _execute_agent_node
                break

            # Wait a bit before checking again
            time.sleep(0.5)

    def _update_node_status(self, node_id: str, status: str) -> None:
        """Update node status and notify."""
        self.node_status[node_id] = status

        # Update session state
        def session_updater(s: PipelineSession) -> PipelineSession:
            s.node_status[node_id] = status
            return s

        self.executor._pipeline_session_store.update(self.session_id, session_updater)

        if self.executor._on_node_status_change:
            try:
                self.executor._on_node_status_change(self.pipeline_id, node_id, status, self.session_id)
            except Exception as e:
                logger.warning(f"Node status callback failed: {e}")

    def _mark_completed(self) -> None:
        """Mark session as completed."""
        # Update session
        def session_updater(s: PipelineSession) -> PipelineSession:
            s.status = PipelineSessionStatus.COMPLETED
            s.finished_at = datetime.now()
            return s

        self.executor._pipeline_session_store.update(self.session_id, session_updater)

        # Update pipeline metadata (not status - sessions track execution state)
        def updater(p: PipelineState) -> PipelineState:
            p.current_node_id = None
            p.touch()
            return p

        self.executor._pipeline_store.update(self.pipeline_id, updater)
        logger.info(f"Session completed: {self.session_id} (pipeline: {self.pipeline_id})")

        # Notify callback
        if self.executor._on_session_status_change:
            try:
                self.executor._on_session_status_change(
                    self.pipeline_id, self.session_id, "completed"
                )
            except Exception as e:
                logger.warning(f"Session status callback failed: {e}")

    def _mark_stopped(self) -> None:
        """Mark session as stopped."""
        # Update session
        def session_updater(s: PipelineSession) -> PipelineSession:
            s.status = PipelineSessionStatus.STOPPED
            s.finished_at = datetime.now()
            return s

        self.executor._pipeline_session_store.update(self.session_id, session_updater)

        # Update pipeline metadata (not status - sessions track execution state)
        def updater(p: PipelineState) -> PipelineState:
            p.current_node_id = None
            p.touch()
            return p

        self.executor._pipeline_store.update(self.pipeline_id, updater)
        logger.info(f"Session stopped: {self.session_id} (pipeline: {self.pipeline_id})")

        # Notify callback
        if self.executor._on_session_status_change:
            try:
                self.executor._on_session_status_change(
                    self.pipeline_id, self.session_id, "stopped"
                )
            except Exception as e:
                logger.warning(f"Session status callback failed: {e}")

    def _mark_failed(self, error: str) -> None:
        """Mark session as failed."""
        # Update session
        def session_updater(s: PipelineSession) -> PipelineSession:
            s.status = PipelineSessionStatus.FAILED
            s.finished_at = datetime.now()
            s.error_message = error
            return s

        self.executor._pipeline_session_store.update(self.session_id, session_updater)

        # Update pipeline metadata (not status - sessions track execution state)
        def updater(p: PipelineState) -> PipelineState:
            p.current_node_id = None
            p.touch()
            return p

        self.executor._pipeline_store.update(self.pipeline_id, updater)
        logger.info(f"Session failed: {self.session_id} (pipeline: {self.pipeline_id}): {error}")

        # Notify callback
        if self.executor._on_session_status_change:
            try:
                self.executor._on_session_status_change(
                    self.pipeline_id, self.session_id, "failed"
                )
            except Exception as e:
                logger.warning(f"Session status callback failed: {e}")

    def _get_connected_agent_names(self, pipeline: PipelineState, node_id: str) -> list[str]:
        """Get names of agents this node can send messages TO via pipeline edges.

        Only returns agents connected via OUTGOING edges (source=this node).
        Incoming edges mean other agents can send TO us, but we can't send to them,
        so we don't list them as targets to avoid confusion.
        """
        target_node_ids = set()

        # Only find outgoing edges (agents we can send TO)
        for edge in pipeline.edges:
            if edge.source == node_id and edge.target:
                target_node_ids.add(edge.target)

        # Get names of target agent nodes
        agent_names = []
        for target_id in target_node_ids:
            target_node = self._find_node(pipeline, target_id)
            if target_node and target_node.type == "agent":
                if hasattr(target_node.data, 'name') and target_node.data.name:
                    agent_names.append(target_node.data.name)
                else:
                    agent_names.append(target_id)

        return agent_names

    def _has_incoming_agent_edges(self, pipeline: PipelineState, node_id: str) -> bool:
        """Check if this node has incoming edges from other agent nodes.

        Returns True if any agent can send messages TO this node.
        """
        for edge in pipeline.edges:
            if edge.target == node_id and edge.source:
                source_node = self._find_node(pipeline, edge.source)
                if source_node and source_node.type == "agent":
                    return True
        return False

    def _get_node_name_map(self, pipeline: PipelineState) -> dict[str, str]:
        """Build a map of node_id -> agent name for all agent nodes."""
        node_names = {}
        for node in pipeline.nodes:
            if node.type == "agent" and hasattr(node.data, 'name'):
                node_names[node.id] = node.data.name or node.id
        return node_names

    def _get_named_edges(self, pipeline: PipelineState) -> list[tuple[str, str]]:
        """Get pipeline edges using agent names instead of node IDs."""
        node_names = self._get_node_name_map(pipeline)
        named_edges = []
        for edge in pipeline.edges:
            if edge.source and edge.target:
                src_name = node_names.get(edge.source, edge.source)
                tgt_name = node_names.get(edge.target, edge.target)
                named_edges.append((src_name, tgt_name))
        return named_edges

    def _register_pipeline_context(self, pipeline: PipelineState) -> None:
        """Register the pipeline context with the bridge for inter-agent communication.

        This registers all agent nodes upfront so agents can find each other
        even before they've all executed.
        """
        from ..server.routes.bridge import register_pipeline_context

        named_edges = self._get_named_edges(pipeline)

        # Build agents map from already-executed agents
        agents_map = {}
        for node_id, agent_id in self.node_agents.items():
            node = self._find_node(pipeline, node_id)
            if node and node.type == "agent" and hasattr(node.data, 'name'):
                agents_map[node.data.name or node_id] = agent_id

        register_pipeline_context(self.pipeline_id, named_edges, agents_map)
        logger.info(f"Registered pipeline context: {len(named_edges)} edges, {len(agents_map)} agents")

    def _make_agent_name(self, pipeline: PipelineState, agent_node_name: str) -> str:
        """Generate a full agent name like '<pipeline_name>.<agent_name>'.

        Preserves the original names but sanitizes spaces to dots for readability.
        """
        # Use original names, just replace spaces with underscores for cleaner display
        pipeline_name = pipeline.name.replace(" ", "_")
        return f"{pipeline_name}.{agent_node_name}"
