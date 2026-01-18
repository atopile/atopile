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
    PipelineState,
    PipelineStatus,
)

if TYPE_CHECKING:
    from .process import ProcessManager
    from .state import AgentStateStore, PipelineStateStore

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
        on_node_status_change: Callable[[str, str, str], None] | None = None,
    ) -> None:
        """Initialize the pipeline executor.

        Args:
            process_manager: Process manager for spawning agents
            agent_store: Store for agent states
            pipeline_store: Store for pipeline states
            on_node_status_change: Callback(pipeline_id, node_id, status) for node status changes
        """
        self._process_manager = process_manager
        self._agent_store = agent_store
        self._pipeline_store = pipeline_store
        self._on_node_status_change = on_node_status_change
        self._running_pipelines: dict[str, PipelineExecution] = {}
        self._lock = threading.Lock()

    def start_pipeline(self, pipeline_id: str) -> bool:
        """Start executing a pipeline.

        Args:
            pipeline_id: ID of the pipeline to start

        Returns:
            True if started successfully
        """
        pipeline = self._pipeline_store.get(pipeline_id)
        if pipeline is None:
            logger.error(f"Pipeline not found: {pipeline_id}")
            return False

        if pipeline.status == PipelineStatus.RUNNING:
            logger.warning(f"Pipeline already running: {pipeline_id}")
            return False

        # Update status to RUNNING
        def updater(p: PipelineState) -> PipelineState:
            p.status = PipelineStatus.RUNNING
            p.node_status = {}  # Reset node status
            p.node_agent_map = {}  # Reset agent map
            if p.started_at is None:
                p.started_at = datetime.now()
            p.touch()
            return p

        self._pipeline_store.update(pipeline_id, updater)

        # Create execution context
        execution = PipelineExecution(
            pipeline_id=pipeline_id,
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
        logger.info(f"Pipeline execution started: {pipeline_id}")

        return True

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
        """Mark a pipeline as failed."""
        def updater(p: PipelineState) -> PipelineState:
            p.status = PipelineStatus.FAILED
            p.finished_at = datetime.now()
            p.touch()
            return p

        self._pipeline_store.update(pipeline_id, updater)


class PipelineExecution:
    """Represents an active pipeline execution."""

    def __init__(
        self,
        pipeline_id: str,
        executor: PipelineExecutor,
    ) -> None:
        self.pipeline_id = pipeline_id
        self.executor = executor
        self.node_agents: dict[str, str] = {}  # node_id -> agent_id
        self.node_status: dict[str, str] = {}  # node_id -> status
        self.node_outputs: dict[str, str] = {}  # node_id -> output result (for communication)
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
        pipeline = self.executor._pipeline_store.get(self.pipeline_id)
        if pipeline is None:
            raise RuntimeError(f"Pipeline not found: {self.pipeline_id}")

        logger.info(f"Starting pipeline execution: {self.pipeline_id}")
        logger.info(f"Pipeline has {len(pipeline.nodes)} nodes and {len(pipeline.edges)} edges")

        # Find execution order (topological sort from trigger nodes)
        execution_order = self._get_execution_order(pipeline)
        logger.info(f"Execution order: {execution_order}")

        if not execution_order:
            logger.warning(f"No executable nodes in pipeline: {self.pipeline_id}")
            self._mark_completed()
            return

        # Execute nodes in order
        for node_id in execution_order:
            if self._should_stop:
                logger.info(f"Pipeline stopped: {self.pipeline_id}")
                self._mark_stopped()
                return

            node = self._find_node(pipeline, node_id)
            if node is None:
                logger.warning(f"Node not found: {node_id}")
                continue

            logger.debug(f"Executing node {node_id} (type={node.type})")
            self._update_node_status(node_id, "running")

            try:
                if node.type == "agent":
                    self._execute_agent_node(pipeline, node)
                elif node.type == "trigger":
                    # Trigger nodes just mark as complete
                    pass
                elif node.type == "loop":
                    # Loop nodes - for now just pass through
                    pass
                elif node.type == "condition":
                    # Condition nodes - for now just pass through
                    pass

                self._update_node_status(node_id, "completed")

            except Exception as e:
                logger.error(f"Node {node_id} failed: {e}")
                self._update_node_status(node_id, "failed")

                if pipeline.config.stop_on_failure:
                    self._mark_failed(str(e))
                    return

        self._mark_completed()

    def _get_execution_order(self, pipeline: PipelineState) -> list[str]:
        """Get nodes in execution order (BFS from trigger nodes)."""
        from ..models import PipelineNode, PipelineEdge

        # Build adjacency list from edges
        adjacency: dict[str, list[str]] = {}
        for node in pipeline.nodes:
            adjacency[node.id] = []

        for edge in pipeline.edges:
            source = edge.source
            target = edge.target
            if source and target:
                if source not in adjacency:
                    adjacency[source] = []
                adjacency[source].append(target)

        # Find trigger nodes (nodes with no incoming edges)
        has_incoming: set[str] = set()
        for edge in pipeline.edges:
            if edge.target:
                has_incoming.add(edge.target)

        trigger_nodes = [
            node.id
            for node in pipeline.nodes
            if node.id not in has_incoming or node.type == "trigger"
        ]

        # BFS to get execution order
        order: list[str] = []
        visited: set[str] = set()
        queue = list(trigger_nodes)

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue

            visited.add(node_id)
            order.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    queue.append(neighbor)

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
        """Build context string from parent node outputs for agent communication."""
        parent_ids = self._get_parent_node_ids(pipeline, node_id)
        if not parent_ids:
            return ""

        context_parts = []
        for parent_id in parent_ids:
            if parent_id in self.node_outputs:
                parent_node = self._find_node(pipeline, parent_id)
                parent_name = "Unknown"
                if parent_node and hasattr(parent_node.data, 'name'):
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
        """Execute an agent node by spawning an agent."""
        from ..models import PipelineNode, AgentNodeData
        from ..server.routes.bridge import register_pipeline_context

        node_id = node.id
        data = node.data

        # Build agent config from node data (data is AgentNodeData)
        backend = data.backend if hasattr(data, 'backend') else AgentBackendType.CLAUDE_CODE
        prompt = data.prompt if hasattr(data, 'prompt') else ""
        name = data.name if hasattr(data, 'name') else "Pipeline Agent"

        # Validate prompt - must not be empty
        if not prompt or not prompt.strip():
            raise ValueError(f"Agent node '{name}' ({node_id}) has an empty prompt. Please specify a prompt.")

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

        # Set up environment - only add bridge env vars if there are connected agents
        environment = {}
        if hasattr(data, 'environment') and data.environment:
            environment.update(data.environment)

        if connected_agents:
            # Add bridge instructions to prompt
            bridge_instructions = f"""
You have access to the send_and_receive tool to communicate with other agents in this pipeline.
Connected agents you can talk to: {', '.join(connected_agents)}

To send a message and get a response: send_and_receive(to="agent_name", message="your message")
"""
            prompt = f"{bridge_instructions}\n{prompt}"

            # Set up bridge environment variables
            environment["AGENT_NAME"] = name
            environment["PIPELINE_ID"] = self.pipeline_id
            environment["BRIDGE_URL"] = "http://127.0.0.1:8765"  # Orchestrator URL

            # Register pipeline edges with the bridge
            edges = [(e.source, e.target) for e in pipeline.edges if e.source and e.target]
            # Map node IDs to agent names for edge lookup
            node_names = {}
            for n in pipeline.nodes:
                if n.type == "agent" and hasattr(n.data, 'name'):
                    node_names[n.id] = n.data.name or n.id
            # Convert edges to use names instead of node IDs
            named_edges = []
            for src, tgt in edges:
                src_name = node_names.get(src, src)
                tgt_name = node_names.get(tgt, tgt)
                named_edges.append((src_name, tgt_name))
            register_pipeline_context(self.pipeline_id, named_edges, {})

        config = AgentConfig(
            backend=backend,
            prompt=prompt,
            max_turns=getattr(data, 'max_turns', None) or 10,  # Default max turns for pipeline agents
            max_budget_usd=getattr(data, 'max_budget_usd', None),
            system_prompt=getattr(data, 'system_prompt', None),
            working_directory=getattr(data, 'working_directory', None),
            environment=environment if environment else None,  # Only pass if not empty
        )

        # Create and spawn agent
        agent = AgentState(config=config, status=AgentStatus.STARTING)
        self.executor._agent_store.set(agent.id, agent)

        logger.info(f"Spawning agent for node {node_id}: {agent.id}")

        try:
            managed = self.executor._process_manager.spawn(agent)

            # Update agent state
            def agent_updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.RUNNING
                a.pid = managed.process.pid
                a.started_at = datetime.now()
                return a

            self.executor._agent_store.update(agent.id, agent_updater)

            # Track agent
            self.node_agents[node_id] = agent.id
            self._current_agent_id = agent.id

            # Update pipeline with agent mapping
            def pipeline_updater(p: PipelineState) -> PipelineState:
                p.current_node_id = node_id
                p.node_agent_map[node_id] = agent.id
                p.execution_history.append(agent.id)
                p.touch()
                return p

            self.executor._pipeline_store.update(self.pipeline_id, pipeline_updater)

            # Wait for agent to complete
            self._wait_for_agent(agent.id)

            # Capture the agent's output for downstream nodes (before cleanup!)
            output = self._extract_agent_result(agent.id)
            self.node_outputs[node_id] = output
            logger.info(f"Captured output from node {node_id}: {len(output)} chars")

            # Now we can cleanup the process
            self.executor._process_manager.cleanup(agent.id)

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
                # Wait for output threads to finish processing before we extract output
                self.executor._process_manager.wait_for_output_and_get_session_id(agent_id, timeout=2.0)

                # Process finished, update agent state
                new_status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

                def updater(a: AgentState) -> AgentState:
                    a.status = new_status
                    a.exit_code = exit_code
                    a.finished_at = datetime.now()
                    return a

                self.executor._agent_store.update(agent_id, updater)
                # NOTE: cleanup is called AFTER output extraction in _execute_agent_node
                break

            # Wait a bit before checking again
            time.sleep(0.5)

    def _update_node_status(self, node_id: str, status: str) -> None:
        """Update node status and notify."""
        self.node_status[node_id] = status

        if self.executor._on_node_status_change:
            try:
                self.executor._on_node_status_change(self.pipeline_id, node_id, status)
            except Exception as e:
                logger.warning(f"Node status callback failed: {e}")

    def _mark_completed(self) -> None:
        """Mark pipeline as completed."""
        def updater(p: PipelineState) -> PipelineState:
            p.status = PipelineStatus.COMPLETED
            p.current_node_id = None
            p.finished_at = datetime.now()
            p.touch()
            return p

        self.executor._pipeline_store.update(self.pipeline_id, updater)
        logger.info(f"Pipeline completed: {self.pipeline_id}")

    def _mark_stopped(self) -> None:
        """Mark pipeline as stopped."""
        def updater(p: PipelineState) -> PipelineState:
            p.status = PipelineStatus.COMPLETED
            p.current_node_id = None
            p.finished_at = datetime.now()
            p.touch()
            return p

        self.executor._pipeline_store.update(self.pipeline_id, updater)
        logger.info(f"Pipeline stopped: {self.pipeline_id}")

    def _mark_failed(self, error: str) -> None:
        """Mark pipeline as failed."""
        def updater(p: PipelineState) -> PipelineState:
            p.status = PipelineStatus.FAILED
            p.current_node_id = None
            p.finished_at = datetime.now()
            p.touch()
            return p

        self.executor._pipeline_store.update(self.pipeline_id, updater)
        logger.info(f"Pipeline failed: {self.pipeline_id}: {error}")

    def _get_connected_agent_names(self, pipeline: PipelineState, node_id: str) -> list[str]:
        """Get names of agents connected to this node via pipeline edges.

        Returns names of agent nodes that have edges connecting to/from the given node,
        so the agent knows which other agents it can communicate with.
        """
        connected_node_ids = set()

        # Find nodes connected by edges (both directions)
        for edge in pipeline.edges:
            if edge.source == node_id and edge.target:
                connected_node_ids.add(edge.target)
            elif edge.target == node_id and edge.source:
                connected_node_ids.add(edge.source)

        # Get names of connected agent nodes
        agent_names = []
        for connected_id in connected_node_ids:
            connected_node = self._find_node(pipeline, connected_id)
            if connected_node and connected_node.type == "agent":
                if hasattr(connected_node.data, 'name') and connected_node.data.name:
                    agent_names.append(connected_node.data.name)
                else:
                    agent_names.append(connected_id)

        return agent_names
