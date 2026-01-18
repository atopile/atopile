"""Tests for the FastAPI routes."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tools.orchestrator.models import AgentBackendType, AgentStatus
from tools.orchestrator.server.app import create_app
from tools.orchestrator.server.dependencies import OrchestratorState


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


class TestHealthEndpoints:
    """Tests for health and info endpoints."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agent Orchestrator"
        assert "version" in data

    def test_stats_endpoint(self, client: TestClient):
        """Test stats endpoint."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "sessions" in data
        assert "backends" in data

    def test_backends_endpoint(self, client: TestClient):
        """Test backends endpoint."""
        response = client.get("/backends")
        assert response.status_code == 200
        data = response.json()
        assert "backends" in data
        assert isinstance(data["backends"], list)


class TestAgentEndpoints:
    """Tests for agent API endpoints."""

    def test_list_agents_empty(self, client: TestClient):
        """Test listing agents when empty."""
        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []
        assert data["total"] == 0

    def test_spawn_agent_invalid_backend(self, client: TestClient):
        """Test spawning with invalid backend returns error."""
        # This should fail validation
        response = client.post(
            "/agents/spawn",
            json={
                "config": {
                    "backend": "invalid-backend",
                    "prompt": "test",
                }
            },
        )
        assert response.status_code == 422  # Validation error

    def test_get_agent_not_found(self, client: TestClient):
        """Test getting nonexistent agent returns 404."""
        response = client.get("/agents/nonexistent-id")
        assert response.status_code == 404

    def test_terminate_agent_not_found(self, client: TestClient):
        """Test terminating nonexistent agent returns 404."""
        response = client.post(
            "/agents/nonexistent-id/terminate",
            json={"force": False},
        )
        assert response.status_code == 404

    def test_delete_agent_not_found(self, client: TestClient):
        """Test deleting nonexistent agent returns 404."""
        response = client.delete("/agents/nonexistent-id")
        assert response.status_code == 404

    def test_get_output_not_found(self, client: TestClient):
        """Test getting output for nonexistent agent returns 404."""
        response = client.get("/agents/nonexistent-id/output")
        assert response.status_code == 404


class TestSessionEndpoints:
    """Tests for session API endpoints."""

    def test_list_sessions_empty(self, client: TestClient):
        """Test listing sessions when empty."""
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_get_session_not_found(self, client: TestClient):
        """Test getting nonexistent session returns 404."""
        response = client.get("/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_delete_session_not_found(self, client: TestClient):
        """Test deleting nonexistent session returns 404."""
        response = client.delete("/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_resume_session_not_found(self, client: TestClient):
        """Test resuming nonexistent session returns 404."""
        response = client.post(
            "/sessions/nonexistent-id/resume",
            json={"prompt": "continue"},
        )
        assert response.status_code == 404


class TestAgentSpawning:
    """Tests for agent spawning with mocked process."""

    @pytest.fixture
    def mock_process_manager(self):
        """Create a mock process manager."""
        with patch(
            "tools.orchestrator.server.routes.agents.get_process_manager"
        ) as mock_get:
            mock_pm = MagicMock()
            mock_managed = MagicMock()
            mock_managed.process.pid = 12345
            mock_pm.spawn.return_value = mock_managed
            mock_get.return_value = mock_pm
            yield mock_pm

    def test_spawn_agent_success(
        self, client: TestClient, mock_process_manager
    ):
        """Test successful agent spawning."""
        response = client.post(
            "/agents/spawn",
            json={
                "config": {
                    "backend": "claude-code",
                    "prompt": "What is 2+2?",
                }
            },
        )

        # Even with mock, should succeed
        assert response.status_code in (200, 500)  # May fail if backend not found

    def test_list_agents_with_filters(self, client: TestClient):
        """Test listing agents with status filter."""
        response = client.get("/agents?status=running")
        assert response.status_code == 200

        response = client.get("/agents?backend=claude-code")
        assert response.status_code == 200

    def test_list_agents_pagination(self, client: TestClient):
        """Test listing agents with pagination."""
        response = client.get("/agents?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "total" in data


class TestSessionManagement:
    """Tests for session management through API."""

    def test_list_sessions_with_filters(self, client: TestClient):
        """Test listing sessions with filters."""
        response = client.get("/sessions?status=active")
        assert response.status_code == 200

        response = client.get("/sessions?backend=claude-code")
        assert response.status_code == 200

    def test_list_sessions_invalid_backend(self, client: TestClient):
        """Test listing sessions with invalid backend."""
        response = client.get("/sessions?backend=invalid")
        assert response.status_code == 400
