"""
Spawn Handler - Polls broker for spawn requests and creates agents.

This runs as part of the orchestrator and handles dynamic agent spawning
requested by other agents via broker_spawn_worker.
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ..core.process import ProcessManager
    from ..core.state import AgentStateStore

logger = logging.getLogger(__name__)


class SpawnHandler:
    """Handles spawn requests from the broker."""

    def __init__(
        self,
        broker_url: str,
        process_manager: "ProcessManager",
        agent_store: "AgentStateStore",
        on_agent_spawned: callable = None,
    ):
        self.broker_url = broker_url
        self.process_manager = process_manager
        self.agent_store = agent_store
        self.on_agent_spawned = on_agent_spawned
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start polling for spawn requests."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"Spawn handler started (broker: {self.broker_url})")

    def stop(self):
        """Stop polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _poll_loop(self):
        """Main polling loop."""
        import time
        from datetime import datetime

        from ..models import AgentBackendType, AgentConfig, AgentState, AgentStatus

        client = httpx.Client(timeout=10.0)

        while self._running:
            try:
                # Poll for spawn requests
                response = client.get(
                    f"{self.broker_url}/spawn/pending",
                    params={"timeout": 2.0}
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "pending":
                    request = data.get("request", {})
                    name = request.get("name", "worker")
                    prompt = request.get("prompt", "")
                    respond_to = request.get("respond_to")

                    logger.info(f"Processing spawn request: {name}")

                    # Create agent config
                    config = AgentConfig(
                        backend=AgentBackendType.CLAUDE_CODE,
                        prompt=prompt,
                        max_turns=10,  # Reasonable default for workers
                    )

                    # Create agent state
                    agent = AgentState(config=config, status=AgentStatus.STARTING)
                    self.agent_store.set(agent.id, agent)

                    # Spawn the agent
                    try:
                        managed = self.process_manager.spawn(agent)

                        # Update state
                        def updater(a: AgentState) -> AgentState:
                            a.status = AgentStatus.RUNNING
                            a.pid = managed.process.pid
                            a.started_at = datetime.now()
                            return a

                        self.agent_store.update(agent.id, updater)

                        logger.info(f"Spawned worker agent: {name} (id={agent.id})")

                        if self.on_agent_spawned:
                            self.on_agent_spawned(agent.id, name, respond_to)

                    except Exception as e:
                        logger.error(f"Failed to spawn worker {name}: {e}")

                        def error_updater(a: AgentState) -> AgentState:
                            a.status = AgentStatus.FAILED
                            a.error_message = str(e)
                            a.finished_at = datetime.now()
                            return a

                        self.agent_store.update(agent.id, error_updater)

            except httpx.ConnectError:
                # Broker not available, wait and retry
                time.sleep(5.0)
            except Exception as e:
                logger.exception(f"Spawn handler error: {e}")
                time.sleep(1.0)

        client.close()
