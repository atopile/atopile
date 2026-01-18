"""Tests for pipeline API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tools.orchestrator.server.app import create_app
from tools.orchestrator.server.dependencies import OrchestratorState


@pytest.fixture
def client():
    """Create a test client with fresh state."""
    OrchestratorState.reset()
    app = create_app()
    with TestClient(app) as client:
        yield client
    OrchestratorState.reset()


class TestPipelineEndpoints:
    """Tests for pipeline CRUD endpoints."""

    def test_list_pipelines_empty(self, client):
        """Test listing pipelines when none exist."""
        response = client.get("/pipelines")
        assert response.status_code == 200
        data = response.json()
        assert data["pipelines"] == []
        assert data["total"] == 0

    def test_create_pipeline(self, client):
        """Test creating a new pipeline."""
        response = client.post(
            "/pipelines",
            json={
                "name": "Test Pipeline",
                "description": "A test pipeline",
                "nodes": [],
                "edges": [],
                "config": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Pipeline"
        assert data["description"] == "A test pipeline"
        assert data["status"] == "draft"
        assert "id" in data

    def test_create_pipeline_minimal(self, client):
        """Test creating a pipeline with minimal data."""
        response = client.post(
            "/pipelines",
            json={"name": "Minimal Pipeline"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Pipeline"
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_get_pipeline(self, client):
        """Test getting a specific pipeline."""
        # Create a pipeline first
        create_response = client.post(
            "/pipelines",
            json={"name": "Get Test"},
        )
        pipeline_id = create_response.json()["id"]

        # Get it
        response = client.get(f"/pipelines/{pipeline_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pipeline_id
        assert data["name"] == "Get Test"

    def test_get_pipeline_not_found(self, client):
        """Test getting a non-existent pipeline."""
        response = client.get("/pipelines/nonexistent-id")
        assert response.status_code == 404

    def test_update_pipeline(self, client):
        """Test updating a pipeline."""
        # Create a pipeline first
        create_response = client.post(
            "/pipelines",
            json={"name": "Original Name"},
        )
        pipeline_id = create_response.json()["id"]

        # Update it
        response = client.put(
            f"/pipelines/{pipeline_id}",
            json={"name": "Updated Name", "description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    def test_update_pipeline_not_found(self, client):
        """Test updating a non-existent pipeline."""
        response = client.put(
            "/pipelines/nonexistent-id",
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    def test_delete_pipeline(self, client):
        """Test deleting a pipeline."""
        # Create a pipeline first
        create_response = client.post(
            "/pipelines",
            json={"name": "To Delete"},
        )
        pipeline_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/pipelines/{pipeline_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify it's gone
        get_response = client.get(f"/pipelines/{pipeline_id}")
        assert get_response.status_code == 404

    def test_delete_pipeline_not_found(self, client):
        """Test deleting a non-existent pipeline."""
        response = client.delete("/pipelines/nonexistent-id")
        assert response.status_code == 404

    def test_list_pipelines_with_filter(self, client):
        """Test listing pipelines with status filter."""
        # Create a pipeline
        client.post("/pipelines", json={"name": "Draft Pipeline"})

        # List with status filter
        response = client.get("/pipelines?status=draft")
        assert response.status_code == 200
        data = response.json()
        assert len(data["pipelines"]) == 1

        # List with different status (should be empty)
        response = client.get("/pipelines?status=running")
        assert response.status_code == 200
        data = response.json()
        assert len(data["pipelines"]) == 0

    def test_list_pipelines_with_limit(self, client):
        """Test listing pipelines with limit."""
        # Create multiple pipelines
        for i in range(5):
            client.post("/pipelines", json={"name": f"Pipeline {i}"})

        # List with limit
        response = client.get("/pipelines?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["pipelines"]) == 2
        assert data["total"] == 5


class TestPipelineExecution:
    """Tests for pipeline execution endpoints."""

    def test_run_pipeline(self, client):
        """Test starting a pipeline."""
        # Create a pipeline with nodes
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Runnable Pipeline",
                "nodes": [
                    {
                        "id": "trigger",
                        "type": "trigger",
                        "position": {"x": 0, "y": 0},
                        "data": {"trigger_type": "manual"},
                    },
                    {
                        "id": "agent1",
                        "type": "agent",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "name": "Test Agent",
                            "backend": "claude-code",
                            "prompt": "Hello",
                        },
                    },
                ],
                "edges": [{"id": "e1", "source": "trigger", "target": "agent1"}],
            },
        )
        pipeline_id = create_response.json()["id"]

        # Run it
        response = client.post(f"/pipelines/{pipeline_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["pipeline_id"] == pipeline_id

    def test_run_pipeline_already_running(self, client):
        """Test running an already running pipeline."""
        # Create and start a pipeline
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Running Pipeline",
                "nodes": [{"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}}],
            },
        )
        pipeline_id = create_response.json()["id"]
        client.post(f"/pipelines/{pipeline_id}/run")

        # Try to run again
        response = client.post(f"/pipelines/{pipeline_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_running"

    def test_run_pipeline_no_nodes(self, client):
        """Test running a pipeline with no nodes."""
        # Create an empty pipeline
        create_response = client.post(
            "/pipelines",
            json={"name": "Empty Pipeline"},
        )
        pipeline_id = create_response.json()["id"]

        # Try to run
        response = client.post(f"/pipelines/{pipeline_id}/run")
        assert response.status_code == 400

    def test_run_pipeline_not_found(self, client):
        """Test running a non-existent pipeline."""
        response = client.post("/pipelines/nonexistent-id/run")
        assert response.status_code == 404

    def test_pause_pipeline(self, client):
        """Test pausing a running pipeline."""
        # Create and start a pipeline
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Pausable Pipeline",
                "nodes": [{"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}}],
            },
        )
        pipeline_id = create_response.json()["id"]
        client.post(f"/pipelines/{pipeline_id}/run")

        # Pause it
        response = client.post(f"/pipelines/{pipeline_id}/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    def test_pause_pipeline_not_running(self, client):
        """Test pausing a non-running pipeline."""
        # Create a pipeline (draft status)
        create_response = client.post(
            "/pipelines",
            json={"name": "Draft Pipeline"},
        )
        pipeline_id = create_response.json()["id"]

        # Try to pause
        response = client.post(f"/pipelines/{pipeline_id}/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_running"

    def test_resume_pipeline(self, client):
        """Test resuming a paused pipeline."""
        # Create, start, and pause a pipeline
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Resumable Pipeline",
                "nodes": [{"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}}],
            },
        )
        pipeline_id = create_response.json()["id"]
        client.post(f"/pipelines/{pipeline_id}/run")
        client.post(f"/pipelines/{pipeline_id}/pause")

        # Resume it
        response = client.post(f"/pipelines/{pipeline_id}/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"

    def test_resume_pipeline_not_paused(self, client):
        """Test resuming a non-paused pipeline."""
        # Create a pipeline (draft status)
        create_response = client.post(
            "/pipelines",
            json={"name": "Draft Pipeline"},
        )
        pipeline_id = create_response.json()["id"]

        # Try to resume
        response = client.post(f"/pipelines/{pipeline_id}/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_paused"

    def test_stop_pipeline(self, client):
        """Test stopping a running pipeline."""
        # Create and start a pipeline
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Stoppable Pipeline",
                "nodes": [{"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}}],
            },
        )
        pipeline_id = create_response.json()["id"]
        client.post(f"/pipelines/{pipeline_id}/run")

        # Stop it
        response = client.post(f"/pipelines/{pipeline_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_stop_pipeline_not_running(self, client):
        """Test stopping a non-running pipeline."""
        # Create a pipeline (draft status)
        create_response = client.post(
            "/pipelines",
            json={"name": "Draft Pipeline"},
        )
        pipeline_id = create_response.json()["id"]

        # Try to stop
        response = client.post(f"/pipelines/{pipeline_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_running"

    def test_get_pipeline_status(self, client):
        """Test getting pipeline status."""
        # Create a pipeline
        create_response = client.post(
            "/pipelines",
            json={"name": "Status Pipeline"},
        )
        pipeline_id = create_response.json()["id"]

        # Get status
        response = client.get(f"/pipelines/{pipeline_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["pipeline"]["id"] == pipeline_id
        assert data["pipeline"]["status"] == "draft"

    def test_get_pipeline_status_not_found(self, client):
        """Test getting status of non-existent pipeline."""
        response = client.get("/pipelines/nonexistent-id/status")
        assert response.status_code == 404


class TestPipelineConstraints:
    """Tests for pipeline operation constraints."""

    def test_cannot_update_running_pipeline(self, client):
        """Test that running pipelines cannot be updated."""
        # Create and start a pipeline
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Running Pipeline",
                "nodes": [{"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}}],
            },
        )
        pipeline_id = create_response.json()["id"]
        client.post(f"/pipelines/{pipeline_id}/run")

        # Try to update
        response = client.put(
            f"/pipelines/{pipeline_id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 400

    def test_cannot_delete_running_pipeline(self, client):
        """Test that running pipelines cannot be deleted."""
        # Create and start a pipeline
        create_response = client.post(
            "/pipelines",
            json={
                "name": "Running Pipeline",
                "nodes": [{"id": "t1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}}],
            },
        )
        pipeline_id = create_response.json()["id"]
        client.post(f"/pipelines/{pipeline_id}/run")

        # Try to delete
        response = client.delete(f"/pipelines/{pipeline_id}")
        assert response.status_code == 400
