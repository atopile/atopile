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

    def _execute_agent_node(self, pipeline: PipelineState, node) -> None:
        """Execute an agent node by spawning an agent."""
        from ..models import PipelineNode, AgentNodeData

        node_id = node.id
        data = node.data

        # Build agent config from node data (data is AgentNodeData)
        backend = data.backend if hasattr(data, 'backend') else AgentBackendType.CLAUDE_CODE
        prompt = data.prompt if hasattr(data, 'prompt') else "No prompt specified"
        name = data.name if hasattr(data, 'name') else "Pipeline Agent"

        # Prepend planning file content if specified
        planning_file = getattr(data, 'planning_file', None)
        if planning_file:
            try:
                with open(planning_file, "r") as f:
                    planning_content = f.read()
                prompt = f"{planning_content}\n\n{prompt}"
            except Exception as e:
                logger.warning(f"Failed to read planning file: {e}")

        config = AgentConfig(
            backend=backend,
            prompt=prompt,
            max_turns=getattr(data, 'max_turns', None),
            max_budget_usd=getattr(data, 'max_budget_usd', None),
            system_prompt=getattr(data, 'system_prompt', None),
            working_directory=getattr(data, 'working_directory', None),
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

        except Exception as e:
            logger.error(f"Failed to spawn agent for node {node_id}: {e}")
            raise

        finally:
            self._current_agent_id = None

    def _wait_for_agent(self, agent_id: str) -> None:
        """Wait for an agent to complete."""
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
                # Process finished, update agent state
                new_status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

                def updater(a: AgentState) -> AgentState:
                    a.status = new_status
                    a.exit_code = exit_code
                    a.finished_at = datetime.now()
                    return a

                self.executor._agent_store.update(agent_id, updater)
                self.executor._process_manager.cleanup(agent_id)
                break

            # Wait a bit before checking again
            import time
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
