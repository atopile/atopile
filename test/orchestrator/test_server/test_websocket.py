"""Tests for WebSocket streaming."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tools.orchestrator.models import (
    AgentBackendType,
    AgentConfig,
    AgentState,
    AgentStatus,
    OutputChunk,
    OutputType,
    StreamEventType,
)
from tools.orchestrator.server.app import create_app
from tools.orchestrator.server.dependencies import ConnectionManager, OrchestratorState


@pytest.fixture
def temp_storage_env(tmp_path: Path):
    """Set up temporary storage for tests."""
    storage_dir = tmp_path / ".orchestrator"
    storage_dir.mkdir(parents=True)
    (storage_dir / "sessions").mkdir()
    (storage_dir / "agents").mkdir()
    (storage_dir / "logs").mkdir()

    old_env = os.environ.get("ORCHESTRATOR_STORAGE_DIR")
    os.environ["ORCHESTRATOR_STORAGE_DIR"] = str(storage_dir)

    # Reset singleton
    OrchestratorState.reset()

    yield storage_dir

    if old_env:
        os.environ["ORCHESTRATOR_STORAGE_DIR"] = old_env
    else:
        os.environ.pop("ORCHESTRATOR_STORAGE_DIR", None)

    OrchestratorState.reset()


@pytest.fixture
def client(temp_storage_env) -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


class TestConnectionManager:
    """Tests for the WebSocket ConnectionManager."""

    def test_create_connection_manager(self):
        """Test creating a connection manager."""
        manager = ConnectionManager()
        assert manager is not None
        assert manager.get_connection_count() == 0

    def test_get_connection_count_empty(self):
        """Test get_connection_count when empty."""
        manager = ConnectionManager()
        assert manager.get_connection_count() == 0
        assert manager.get_connection_count("some-agent") == 0

    def test_disconnect_nonexistent_sync(self):
        """Test disconnecting a nonexistent connection (sync version)."""
        manager = ConnectionManager()
        mock_websocket = MagicMock()

        # Should not raise
        manager.disconnect(mock_websocket, "nonexistent")

    def test_connection_tracking(self):
        """Test that connection tracking works correctly using internal methods."""
        manager = ConnectionManager()

        # Simulate adding connections directly (bypassing async connect)
        agent_id = "test-agent"
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()

        # Directly manipulate internal state for sync testing
        manager._connections[agent_id] = [mock_ws1, mock_ws2]

        assert manager.get_connection_count(agent_id) == 2
        assert manager.get_connection_count() == 2

        manager.disconnect(mock_ws1, agent_id)
        assert manager.get_connection_count(agent_id) == 1

        manager.disconnect(mock_ws2, agent_id)
        assert manager.get_connection_count(agent_id) == 0

    def test_disconnect_cleans_up_empty_list(self):
        """Test that disconnect removes empty connection lists."""
        manager = ConnectionManager()

        agent_id = "test-agent"
        mock_ws = MagicMock()

        # Add and remove
        manager._connections[agent_id] = [mock_ws]
        manager.disconnect(mock_ws, agent_id)

        # Connection list should be removed
        assert agent_id not in manager._connections


class TestWebSocketEndpoint:
    """Tests for the WebSocket endpoint."""

    def test_websocket_agent_not_found(self, client: TestClient):
        """Test WebSocket connection to nonexistent agent."""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/agents/nonexistent-id"):
                pass

    def test_websocket_connect_to_agent(self, client: TestClient, temp_storage_env):
        """Test WebSocket connection to an agent."""
        # First create an agent in the store
        state = OrchestratorState.get_instance()
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(
            config=config,
            status=AgentStatus.COMPLETED,  # Already completed so we don't need real process
        )
        state.agent_store.set(agent.id, agent)

        # Connect via WebSocket
        with client.websocket_connect(f"/ws/agents/{agent.id}") as websocket:
            # Should receive connected event
            data = websocket.receive_json()
            assert data["type"] == StreamEventType.CONNECTED.value
            assert data["agent_id"] == agent.id

            # Should receive completed event since agent is finished
            data = websocket.receive_json()
            assert data["type"] == StreamEventType.AGENT_COMPLETED.value

    def test_websocket_ping_pong(self, client: TestClient, temp_storage_env):
        """Test WebSocket ping/pong."""
        # Create a running agent
        state = OrchestratorState.get_instance()
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(
            config=config,
            status=AgentStatus.RUNNING,
        )
        state.agent_store.set(agent.id, agent)

        with client.websocket_connect(f"/ws/agents/{agent.id}") as websocket:
            # Receive connected event
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == StreamEventType.PONG.value


class TestStreamEventTypes:
    """Tests for stream event type mapping."""

    def test_status_to_event_type_completed(self):
        """Test status to event type mapping for completed."""
        from tools.orchestrator.server.routes.websocket import _status_to_event_type

        event_type = _status_to_event_type(AgentStatus.COMPLETED)
        assert event_type == StreamEventType.AGENT_COMPLETED

    def test_status_to_event_type_failed(self):
        """Test status to event type mapping for failed."""
        from tools.orchestrator.server.routes.websocket import _status_to_event_type

        event_type = _status_to_event_type(AgentStatus.FAILED)
        assert event_type == StreamEventType.AGENT_FAILED

    def test_status_to_event_type_terminated(self):
        """Test status to event type mapping for terminated."""
        from tools.orchestrator.server.routes.websocket import _status_to_event_type

        event_type = _status_to_event_type(AgentStatus.TERMINATED)
        assert event_type == StreamEventType.AGENT_TERMINATED

    def test_status_to_event_type_running(self):
        """Test status to event type mapping for running (default)."""
        from tools.orchestrator.server.routes.websocket import _status_to_event_type

        event_type = _status_to_event_type(AgentStatus.RUNNING)
        # Running maps to AGENT_OUTPUT as default
        assert event_type == StreamEventType.AGENT_OUTPUT
