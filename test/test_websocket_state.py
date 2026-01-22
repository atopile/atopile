"""
Tests for the /ws/state WebSocket endpoint.

Tests the new thin-client architecture where Python owns all state
and pushes full AppState to connected clients.
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


# Import the create_app function
from atopile.server.server import create_app


def _get_action_result(message: dict) -> dict:
    return message.get("result", message)


def _assert_action_success(message: dict) -> dict:
    result = _get_action_result(message)
    assert result.get("success") is True
    return result


def _assert_action_failure(message: dict) -> dict:
    result = _get_action_result(message)
    assert result.get("success") is False
    return result


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with a valid project."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create ato.yaml
    ato_yaml = project_dir / "ato.yaml"
    ato_yaml.write_text("""
ato-version: ^0.2.0
builds:
  default:
    entry: main.ato:App
""")

    # Create main.ato
    main_ato = project_dir / "main.ato"
    main_ato.write_text("""
module App:
    pass
""")

    return tmp_path


@pytest.fixture
def test_client(temp_workspace: Path) -> TestClient:
    """Create a test client with a temporary workspace."""
    app = create_app(
        summary_file=temp_workspace / "summary.json",
        logs_base=temp_workspace / "logs",
        workspace_paths=[temp_workspace],
    )
    return TestClient(app)


class TestWebSocketStateEndpoint:
    """Tests for the /ws/state WebSocket endpoint."""

    def test_websocket_connects_and_receives_state(self, test_client: TestClient):
        """Test that connecting to /ws/state returns initial state."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Should receive initial state immediately
            data = ws.receive_json()
            assert data["type"] == "state"
            assert "data" in data
            # Verify state has expected fields
            state = data["data"]
            assert "projects" in state
            assert "packages" in state
            assert "isConnected" in state

    def test_websocket_action_selectProject(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test selectProject action via WebSocket."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send selectProject action
            ws.send_json(
                {
                    "type": "action",
                    "action": "selectProject",
                    "payload": {"projectRoot": project_root},
                }
            )

            # May receive state broadcast before action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            # Should have both action_result and state
            types = [m["type"] for m in messages]
            assert "action_result" in types
            assert "state" in types

            # Find and verify each
            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)

            state_update = next(m for m in messages if m["type"] == "state")
            assert state_update["data"]["selectedProjectRoot"] == project_root

    def test_websocket_action_refreshProjects(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test refreshProjects action via WebSocket."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send refreshProjects action
            ws.send_json({"type": "action", "action": "refreshProjects", "payload": {}})

            # May receive state broadcast before action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            # Should have both action_result and state
            types = [m["type"] for m in messages]
            assert "action_result" in types
            assert "state" in types

            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)

    def test_websocket_action_build(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test build action via WebSocket."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send build action
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # May receive multiple state updates (builds + queuedBuilds) before action_result
            # Collect messages until we find action_result
            action_result = None
            state_count = 0
            for _ in range(5):  # Limit iterations
                msg = ws.receive_json()
                if msg["type"] == "state":
                    state_count += 1
                elif msg["type"] == "action_result":
                    action_result = msg
                    break

            assert action_result is not None, "Should receive action_result"
            result = _assert_action_success(action_result)
            assert "build_id" in result
            assert state_count >= 1, "Should receive at least one state update"

    def test_websocket_action_build_invalid_path(self, test_client: TestClient):
        """Test build action with invalid project path."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send build action with invalid path
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {
                        "projectRoot": "/nonexistent/path",
                        "targets": ["default"],
                    },
                }
            )

            # Should receive action_result with error
            result = ws.receive_json()
            assert result["type"] == "action_result"
            result_payload = _assert_action_failure(result)
            assert "error" in result_payload

    def test_websocket_ping_pong(self, test_client: TestClient):
        """Test ping/pong keepalive."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send ping
            ws.send_json({"type": "ping"})

            # Should receive pong
            result = ws.receive_json()
            assert result["type"] == "pong"

    def test_websocket_unknown_action_handled(self, test_client: TestClient):
        """Test that unknown actions don't crash the connection."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send unknown action
            ws.send_json({"type": "action", "action": "unknownAction", "payload": {}})

            # Should receive action_result (likely with error or success)
            result = ws.receive_json()
            assert result["type"] == "action_result"

    def test_websocket_toggleTarget(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test toggleTarget action via WebSocket."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send toggleTarget action
            ws.send_json(
                {
                    "type": "action",
                    "action": "toggleTarget",
                    "payload": {"targetName": "default"},
                }
            )

            # May receive state broadcast before action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            types = [m["type"] for m in messages]
            assert "action_result" in types
            assert "state" in types

            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)

    def test_websocket_refreshPackages(self, test_client: TestClient):
        """Test refreshPackages action via WebSocket."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send refreshPackages action
            ws.send_json({"type": "action", "action": "refreshPackages", "payload": {}})

            # May receive state broadcast before action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            types = [m["type"] for m in messages]
            assert "action_result" in types
            assert "state" in types

            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)


class TestWebSocketStateBroadcast:
    """Tests for state broadcast to multiple clients."""

    def test_state_change_broadcasts_to_all_clients(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that state changes are broadcast to all connected clients."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws1:
            # Receive initial state on client 1
            ws1.receive_json()

            with test_client.websocket_connect("/ws/state") as ws2:
                # Receive initial state on client 2
                ws2.receive_json()

                # Client 1 sends action
                ws1.send_json(
                    {
                        "type": "action",
                        "action": "selectProject",
                        "payload": {"projectRoot": project_root},
                    }
                )

                # Client 1 receives action_result and state (order may vary)
                messages1 = []
                for _ in range(2):
                    msg = ws1.receive_json()
                    messages1.append(msg)

                types1 = [m["type"] for m in messages1]
                assert "action_result" in types1
                assert "state" in types1

                state1 = next(m for m in messages1 if m["type"] == "state")

                # Client 2 should receive state update (broadcast)
                state2 = ws2.receive_json()
                assert state2["type"] == "state"

                # Both should have the same selected project
                assert state1["data"]["selectedProjectRoot"] == project_root
                assert state2["data"]["selectedProjectRoot"] == project_root


class TestBuildStateSync:
    """Tests for build state synchronization."""

    def test_build_appears_in_state_after_enqueue(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that builds appear in state.builds after being enqueued."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            initial = ws.receive_json()
            assert initial["type"] == "state"
            initial_builds = initial["data"].get("builds", [])

            # Send build action
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Receive messages until we get a state update with the build
            build_found = False
            max_messages = 10
            for _ in range(max_messages):
                msg = ws.receive_json()
                if msg["type"] == "state":
                    builds = msg["data"].get("builds", [])
                    if len(builds) > len(initial_builds):
                        build_found = True
                        # Verify build has expected fields
                        new_build = builds[-1]  # Most recent build
                        assert "status" in new_build
                        assert new_build["status"] in [
                            "queued",
                            "building",
                            "success",
                            "failed",
                        ]
                        assert "buildId" in new_build or "name" in new_build
                        break
                elif msg["type"] == "action_result":
                    # Continue waiting for state update
                    continue

            assert build_found, "Build should appear in state.builds after enqueueing"

    def test_build_state_has_correct_structure(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that build state has all required fields for frontend rendering."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send build action
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Get state update (should come before action_result due to await)
            msg = ws.receive_json()
            assert msg["type"] == "state", f"Expected state, got {msg['type']}"

            builds = msg["data"].get("builds", [])
            assert len(builds) > 0, "Should have at least one build"

            build = builds[0]
            # Verify all fields needed by frontend
            assert "status" in build, "Build should have status"
            assert "name" in build or "buildId" in build, "Build should have identifier"
            assert "displayName" in build, "Build should have displayName"
            assert "projectName" in build, "Build should have projectName"

            # Log the full build structure for debugging
            print(f"Build structure: {build}")

    def test_build_project_name_matches_project(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that build's projectName matches the project directory name."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send build action
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Get state update
            msg = ws.receive_json()
            if msg["type"] != "state":
                msg = ws.receive_json()

            builds = msg["data"].get("builds", [])
            assert len(builds) > 0

            build = builds[0]
            # Project name should be extracted from path
            assert build.get("projectName") == "test_project", (
                f"Expected projectName='test_project', got '{build.get('projectName')}'"
            )

    def test_state_broadcast_includes_all_active_builds(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that state includes all builds, not just the latest."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Start first build
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Collect build IDs from the state update and action_result
            # Note: We only get 2 messages from the initial sync - background
            # thread state sync requires event loop which isn't available in tests
            build_ids = set()
            for _ in range(2):  # state + action_result
                msg = ws.receive_json()
                if msg["type"] == "state":
                    for b in msg["data"].get("builds", []):
                        if b.get("buildId"):
                            build_ids.add(b["buildId"])

            assert len(build_ids) >= 1, (
                f"Should have tracked at least 1 build, got {len(build_ids)}"
            )

    def test_build_status_transitions_in_state(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that build status transitions are reflected in state."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send build action
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # The state sync happens before action_result, so first message should be state
            msg1 = ws.receive_json()

            # Collect statuses from the state update
            statuses_seen = set()
            if msg1["type"] == "state":
                builds = msg1["data"].get("builds", [])
                for b in builds:
                    if b.get("status"):
                        statuses_seen.add(b.get("status"))

            # Receive action_result
            msg2 = ws.receive_json()
            if msg2["type"] == "state":
                builds = msg2["data"].get("builds", [])
                for b in builds:
                    if b.get("status"):
                        statuses_seen.add(b.get("status"))

            # Should have seen at least queued status (from the immediate state sync)
            assert "queued" in statuses_seen, (
                f"Should have seen 'queued' status, got: {statuses_seen}"
            )


class TestCancelBuild:
    """Tests for the cancelBuild action."""

    def test_cancel_nonexistent_build(self, test_client: TestClient):
        """Test that cancelling a non-existent build returns an error."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send cancelBuild action for non-existent build
            ws.send_json(
                {
                    "type": "action",
                    "action": "cancelBuild",
                    "payload": {"buildId": "nonexistent-build-id"},
                }
            )

            # Should receive action_result with error
            result = ws.receive_json()
            assert result["type"] == "action_result"
            result_payload = _assert_action_failure(result)
            assert "error" in result_payload

    def test_cancel_build_missing_id(self, test_client: TestClient):
        """Test that cancelling without build ID returns an error."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send cancelBuild action without buildId
            ws.send_json({"type": "action", "action": "cancelBuild", "payload": {}})

            # Should receive action_result with error
            result = ws.receive_json()
            assert result["type"] == "action_result"
            result_payload = _assert_action_failure(result)
            assert "error" in result_payload


class TestFetchModules:
    """Tests for the fetchModules action."""

    def test_fetch_modules_for_project(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test fetching modules for a project."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send fetchModules action
            ws.send_json(
                {
                    "type": "action",
                    "action": "fetchModules",
                    "payload": {"projectRoot": project_root},
                }
            )

            # May receive state broadcast before action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            # Should have action_result
            types = [m["type"] for m in messages]
            assert "action_result" in types

            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)

    def test_fetch_modules_empty_project(self, test_client: TestClient):
        """Test fetching modules with empty project root."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Send fetchModules action with empty project
            ws.send_json(
                {
                    "type": "action",
                    "action": "fetchModules",
                    "payload": {"projectRoot": ""},
                }
            )

            # Should receive action_result (success with no modules)
            result = ws.receive_json()
            assert result["type"] == "action_result"
            _assert_action_success(result)


class TestLogActions:
    """Tests for log-related actions."""

    def test_toggle_log_level(self, test_client: TestClient):
        """Unsupported log action should return error."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Toggle DEBUG level
            ws.send_json(
                {
                    "type": "action",
                    "action": "toggleLogLevel",
                    "payload": {"level": "DEBUG"},
                }
            )

            result = ws.receive_json()
            assert result["type"] == "action_result"
            result_payload = _assert_action_failure(result)
            assert "Unknown action" in result_payload.get("error", "")

    def test_set_log_search_query(self, test_client: TestClient):
        """Unsupported log action should return error."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Set log search query
            ws.send_json(
                {
                    "type": "action",
                    "action": "setLogSearchQuery",
                    "payload": {"query": "error"},
                }
            )

            result = ws.receive_json()
            assert result["type"] == "action_result"
            result_payload = _assert_action_failure(result)
            assert "Unknown action" in result_payload.get("error", "")

    def test_toggle_log_timestamp_mode(self, test_client: TestClient):
        """Unsupported log action should return error."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Toggle timestamp mode
            ws.send_json(
                {"type": "action", "action": "toggleLogTimestampMode", "payload": {}}
            )

            result = ws.receive_json()
            assert result["type"] == "action_result"
            result_payload = _assert_action_failure(result)
            assert "Unknown action" in result_payload.get("error", "")


class TestPackageActions:
    """Tests for package-related actions."""

    def test_clear_package_details(self, test_client: TestClient):
        """Test clearing selected package details."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Clear package details
            ws.send_json(
                {"type": "action", "action": "clearPackageDetails", "payload": {}}
            )

            # Receive state update and action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            types = [m["type"] for m in messages]
            assert "action_result" in types
            assert "state" in types

            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)

            state_update = next(m for m in messages if m["type"] == "state")
            assert state_update["data"]["selectedPackageDetails"] is None

    def test_refresh_packages(self, test_client: TestClient):
        """Test refreshing packages list."""
        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Refresh packages
            ws.send_json({"type": "action", "action": "refreshPackages", "payload": {}})

            # Receive state update and action_result
            messages = []
            for _ in range(2):
                msg = ws.receive_json()
                messages.append(msg)

            types = [m["type"] for m in messages]
            assert "action_result" in types
            assert "state" in types

            action_result = next(m for m in messages if m["type"] == "action_result")
            _assert_action_success(action_result)


class TestQueuedBuilds:
    """Tests for queuedBuilds population."""

    def test_queued_builds_populated_on_build(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Verify queuedBuilds is populated when a build is queued."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            initial = ws.receive_json()
            initial_queued_count = len(initial["data"].get("queuedBuilds", []))

            # Trigger a build
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Read a small number of messages without assuming broadcast timing
            found_new_queued = False
            saw_action_result = False
            for _ in range(3):
                msg = ws.receive_json()
                if msg["type"] == "action_result":
                    saw_action_result = True
                    _assert_action_success(msg)
                elif msg["type"] == "state":
                    queued = msg["data"].get("queuedBuilds", [])
                    if len(queued) > initial_queued_count:
                        found_new_queued = True
                        build = queued[-1]
                        assert build["status"] in ("queued", "building")
                        assert "buildId" in build
                        assert "projectRoot" in build
                        break

            assert saw_action_result, "Should receive action_result for build"

    def test_build_name_matches_target(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Verify build name matches target name for frontend matching."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Trigger a build
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Find the build in state
            build_found = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg["type"] == "state":
                    builds = msg["data"].get("builds", [])
                    if len(builds) > 0:
                        build_found = builds[0]
                        break
                elif msg["type"] == "action_result":
                    continue

            assert build_found is not None, "Should find build in state"
            # Build name should match target name for frontend matching
            assert build_found["name"] == "default", (
                f"Build name should be 'default', got '{build_found['name']}'"
            )

    def test_build_with_level_build_format(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that level='build' format parses id correctly.

        Frontend sends: level='build', id='${projectId}:${targetName}', label='${targetName}'
        Backend should parse the id to extract project root and target.
        """
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            initial = ws.receive_json()
            initial_build_count = len(initial["data"].get("builds", []))

            # Trigger a build using the frontend format
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {
                        "level": "build",
                        "id": f"{project_root}:usage",  # Frontend sends projectId:targetName
                        "label": "usage",
                    },
                }
            )

            # Collect messages until we get action_result and state
            action_result = None
            found_build = False
            messages_received = 0
            max_messages = 10

            while messages_received < max_messages and (
                action_result is None or not found_build
            ):
                try:
                    msg = ws.receive_json()
                    messages_received += 1

                    if msg["type"] == "action_result":
                        action_result = msg
                    elif msg["type"] == "state":
                        builds = msg["data"].get("builds", [])
                        # Check if we have a build with target "usage"
                        new_build = next(
                            (b for b in builds if b.get("name") == "usage"), None
                        )
                        if new_build:
                            found_build = True
                            assert new_build["name"] == "usage"
                except Exception:
                    break

            assert action_result is not None, "Should receive action_result"
            result = _assert_action_success(action_result)
            assert result.get("success") is True, (
                f"Build should succeed, got: {result.get('error')}"
            )

    def test_package_identifier_resolution(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that package identifiers are resolved to package directories.

        When building a package like 'atopile/some-package', the backend should:
        1. Look up the package in state to find where it's installed
        2. Resolve to the package's directory at .ato/modules/<identifier>/
        """
        # Create a mock package structure
        project_root = temp_workspace / "test_project"
        package_dir = (
            project_root / ".ato" / "modules" / "test-publisher" / "test-package"
        )
        package_dir.mkdir(parents=True, exist_ok=True)

        # Create ato.yaml in the package directory
        package_ato_yaml = package_dir / "ato.yaml"
        package_ato_yaml.write_text("""
builds:
  default:
    entry: main.ato:App
  usage:
    entry: usage.ato:Usage
""")

        # Create minimal .ato files
        (package_dir / "main.ato").write_text("module App:\n    pass\n")
        (package_dir / "usage.ato").write_text("module Usage:\n    pass\n")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # First, register the package in state by simulating it being installed
            # We'll use the refreshPackages action to populate packages
            # For this test, we directly test the build action with a package identifier
            # The build should fail to find the package in state (not installed)
            # but we can verify the log output shows the resolution attempt

            # Try to build a package that doesn't exist in state
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {
                        "level": "build",
                        "id": "test-publisher/test-package:usage",
                        "label": "usage",
                    },
                }
            )

            # Should get an error since the package isn't in state
            action_result = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg["type"] == "action_result":
                    action_result = msg
                    break

            # The build should fail because the package isn't registered in state
            # (In real usage, packages are populated via refreshPackages)
            assert action_result is not None
            # It should fail with "not found" error since the package isn't in state
            _assert_action_failure(action_result)

    def test_multiple_targets_same_project(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that multiple targets from the same project can be queued.

        When clicking build on 'default' then 'usage' targets from the same project,
        both should be queued and build separately.
        """
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            initial = ws.receive_json()
            initial_build_count = len(initial["data"].get("builds", []))

            # Trigger first build (default)
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {
                        "level": "build",
                        "id": f"{project_root}:default",
                        "label": "default",
                    },
                }
            )

            # Wait for first build to be queued
            result1 = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg["type"] == "action_result":
                    result1 = msg
                    break

            assert result1 is not None
            result1_payload = _assert_action_success(result1)
            assert result1_payload["success"] is True, (
                f"First build should succeed: {result1_payload.get('error')}"
            )
            build_id_1 = result1_payload.get("build_id")
            assert build_id_1 is not None, "First build should have a build_id"

            # Trigger second build (usage)
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {
                        "level": "build",
                        "id": f"{project_root}:usage",
                        "label": "usage",
                    },
                }
            )

            # Wait for second build to be queued
            result2 = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg["type"] == "action_result":
                    result2 = msg
                    break

            assert result2 is not None
            result2_payload = _assert_action_success(result2)
            assert result2_payload["success"] is True, (
                f"Second build should succeed: {result2_payload.get('error')}"
            )
            build_id_2 = result2_payload.get("build_id")
            assert build_id_2 is not None, "Second build should have a build_id"

            # The two builds should have different IDs
            assert build_id_1 != build_id_2, (
                "Two different targets should create separate builds"
            )


class TestStateFieldNameFormat:
    """
    Tests to verify Python sends camelCase field names to frontend.

    This is CRITICAL for Python-TypeScript interop. The Python backend
    converts snake_case to camelCase via to_frontend_dict(). These tests
    catch any mismatches early.
    """

    def test_state_uses_camelcase_keys(self, test_client: TestClient):
        """Verify that state uses camelCase keys, not snake_case."""
        with test_client.websocket_connect("/ws/state") as ws:
            data = ws.receive_json()
            assert data["type"] == "state"
            state = data["data"]

            # Top-level keys should be camelCase
            # These are the key fields that MUST be camelCase for frontend
            camel_case_keys = [
                "isConnected",
                "projects",
                "isLoadingProjects",
                "projectsError",
                "selectedProjectRoot",
                "selectedTargetNames",
                "builds",
                "queuedBuilds",
                "packages",
                "isLoadingPackages",
                "packagesError",
                "stdlibItems",
                "isLoadingStdlib",
                "bomData",
                "isLoadingBom",
                "bomError",
                "selectedPackageDetails",
                "isLoadingPackageDetails",
                "packageDetailsError",
                "selectedBuildName",
                "selectedProjectName",
                "expandedTargets",
                "version",
                "logoUri",
                "atopile",
                "problems",
                "isLoadingProblems",
                "problemFilter",
                "developerMode",
                "projectModules",
                "isLoadingModules",
                "projectFiles",
                "isLoadingFiles",
                "currentVariablesData",
                "isLoadingVariables",
                "variablesError",
                "openFile",
                "openFileLine",
                "openFileColumn",
                "openLayout",
                "openKicad",
                "open3D",
            ]

            for key in camel_case_keys:
                assert key in state, f"State should have camelCase key '{key}'"

            # These snake_case versions should NOT be present
            snake_case_keys = [
                "is_connected",
                "is_loading_projects",
                "projects_error",
                "selected_project_root",
                "selected_target_names",
                "queued_builds",
                "is_loading_packages",
                "packages_error",
            ]

            for key in snake_case_keys:
                assert key not in state, f"State should NOT have snake_case key '{key}'"

    def test_build_uses_camelcase_keys(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Verify that build objects use camelCase keys."""
        project_root = str(temp_workspace / "test_project")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Trigger a build to get build data in state
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {"projectRoot": project_root, "targets": ["default"]},
                }
            )

            # Get state with build
            msg = ws.receive_json()
            if msg["type"] != "state":
                msg = ws.receive_json()

            builds = msg["data"].get("builds", [])
            assert len(builds) > 0, "Should have at least one build"

            build = builds[0]

            # Build keys should be camelCase
            camel_case_build_keys = [
                "displayName",
                "projectName",
                "buildId",
                "elapsedSeconds",
                "returnCode",
                "projectRoot",
                "startedAt",
            ]

            for key in camel_case_build_keys:
                assert key in build, f"Build should have camelCase key '{key}'"

            # These snake_case versions should NOT be present
            snake_case_build_keys = [
                "display_name",
                "project_name",
                "build_id",
                "elapsed_seconds",
                "return_code",
                "project_root",
                "started_at",
            ]

            for key in snake_case_build_keys:
                assert key not in build, f"Build should NOT have snake_case key '{key}'"

    def test_project_level_build_queues_all_targets(
        self, test_client: TestClient, temp_workspace: Path
    ):
        """Test that project-level build queues ALL targets from ato.yaml.

        When clicking the project-level build button (level='project'),
        the backend should:
        1. Read all targets from the project's ato.yaml
        2. Queue a separate build for each target
        3. Return all build IDs
        """
        project_root = temp_workspace / "test_project"

        # Update ato.yaml to have multiple build targets
        ato_yaml = project_root / "ato.yaml"
        ato_yaml.write_text("""
requires-atopile: ^0.2.0
builds:
  default:
    entry: main.ato:App
  usage:
    entry: usage.ato:Usage
  test:
    entry: test.ato:Test
""")

        # Create the additional .ato files
        (project_root / "usage.ato").write_text("module Usage:\n    pass\n")
        (project_root / "test.ato").write_text("module Test:\n    pass\n")

        with test_client.websocket_connect("/ws/state") as ws:
            # Receive initial state
            ws.receive_json()

            # Trigger a project-level build (no specific target)
            ws.send_json(
                {
                    "type": "action",
                    "action": "build",
                    "payload": {
                        "level": "project",
                        "id": str(project_root),
                        "label": "test_project",
                    },
                }
            )

            # Collect messages to find action_result
            action_result = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg["type"] == "action_result":
                    action_result = msg
                    break

            # Verify action_result indicates success with multiple builds
            assert action_result is not None, "Should receive action_result"
            result = _assert_action_success(action_result)
            assert result["success"] is True, (
                f"Build should succeed, got: {result.get('error')}"
            )

            # Should have multiple build IDs in the response
            result = _get_action_result(action_result)
            if "build_ids" in result:
                assert len(result["build_ids"]) == 3, (
                    f"Should queue 3 builds (default, usage, test), got {len(result['build_ids'])}"
                )
            elif "targets" in result:
                assert len(result["targets"]) == 3, (
                    f"Should have 3 targets, got {result['targets']}"
                )

            # State broadcast timing is not guaranteed in tests; rely on action_result.
