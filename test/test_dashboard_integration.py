"""
Integration tests for the dashboard server that actually run builds.

These tests start a real HTTP server and run actual `ato build` commands.
They are slower than unit tests and should be run separately.

Usage:
    pytest test/test_dashboard_integration.py -v

Note: These tests require the quickstart example project to exist.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

QUICKSTART_PROJECT = Path(__file__).parent.parent / "examples" / "quickstart"
SERVER_PORT = 8502  # Use different port to avoid conflicts


@pytest.fixture
def quickstart_project() -> Path:
    """Return the path to the quickstart example project."""
    if not QUICKSTART_PROJECT.exists():
        pytest.skip("Quickstart project not found")
    return QUICKSTART_PROJECT


@pytest.fixture
def dashboard_server(tmp_path: Path, quickstart_project: Path):
    """Start a real dashboard server for integration testing."""
    summary_file = tmp_path / "summary.json"
    summary_file.write_text('{"builds": [], "totals": {}}')

    # Start the server as a subprocess
    server_cmd = [
        sys.executable,
        "-m",
        "atopile.dashboard",
        "--port",
        str(SERVER_PORT),
        "--workspace",
        str(quickstart_project.parent),
        "--logs-dir",
        str(tmp_path),
    ]

    proc = subprocess.Popen(
        server_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    base_url = f"http://localhost:{SERVER_PORT}"
    max_wait = 10
    started = False
    for _ in range(max_wait * 10):
        try:
            resp = requests.get(f"{base_url}/api/projects", timeout=1)
            if resp.status_code == 200:
                started = True
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass
        time.sleep(0.1)

    if not started:
        stdout, stderr = proc.communicate(timeout=2)
        proc.kill()
        pytest.fail(
            f"Server did not start within {max_wait}s. "
            f"stdout: {stdout.decode()[:500]}, stderr: {stderr.decode()[:500]}"
        )

    yield base_url

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


class TestRealBuilds:
    """Integration tests that run actual builds."""

    def test_build_quickstart_and_poll_status(
        self, dashboard_server: str, quickstart_project: Path
    ):
        """
        Start a build via API and poll until completion.

        This test:
        1. POSTs to /api/build to start a build
        2. Polls /api/build/{id}/status until completion
        3. Verifies the build succeeded
        """
        # Start the build
        response = requests.post(
            f"{dashboard_server}/api/build",
            json={
                "project_root": str(quickstart_project),
                "targets": ["default"],
                "frozen": False,
            },
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        build_id = data["build_id"]
        print(f"Started build: {build_id}")

        # Poll for status
        max_wait = 120  # 2 minutes max
        poll_interval = 1.0
        elapsed = 0
        last_status = None

        while elapsed < max_wait:
            status_response = requests.get(
                f"{dashboard_server}/api/build/{build_id}/status",
                timeout=5,
            )
            assert status_response.status_code == 200
            status_data = status_response.json()

            print(f"  Status: {status_data['status']} (elapsed: {elapsed:.1f}s)")
            last_status = status_data

            if status_data["status"] in ["success", "failed"]:
                break

            time.sleep(poll_interval)
            elapsed += poll_interval

        # Verify final status
        assert last_status is not None
        assert last_status["status"] == "success", (
            f"Build failed: {last_status.get('error')}"
        )
        assert last_status["return_code"] == 0
        print(f"Build completed successfully in {elapsed:.1f}s")

    def test_build_appears_in_summary_while_building(
        self, dashboard_server: str, quickstart_project: Path
    ):
        """
        Build should appear in /api/summary while in progress.

        This verifies that the UI will see the build status during execution.
        """
        # Start the build
        response = requests.post(
            f"{dashboard_server}/api/build",
            json={
                "project_root": str(quickstart_project),
                "targets": ["default"],
                "frozen": False,
            },
            timeout=10,
        )
        build_id = response.json()["build_id"]

        # Immediately check summary
        summary_response = requests.get(
            f"{dashboard_server}/api/summary",
            timeout=5,
        )
        assert summary_response.status_code == 200
        summary_data = summary_response.json()

        # Build should be in the summary (either in progress or completed)
        builds = summary_data.get("builds", [])
        found = any(
            b.get("name") == build_id
            or "quickstart" in b.get("display_name", "").lower()
            for b in builds
        )

        # If not found immediately, wait a bit and check again
        if not found:
            time.sleep(0.5)
            summary_response = requests.get(
                f"{dashboard_server}/api/summary",
                timeout=5,
            )
            summary_data = summary_response.json()
            builds = summary_data.get("builds", [])
            found = any(
                b.get("name") == build_id
                or "quickstart" in b.get("display_name", "").lower()
                for b in builds
            )

        # Wait for build to complete before exiting
        max_wait = 120
        elapsed = 0
        while elapsed < max_wait:
            status = requests.get(
                f"{dashboard_server}/api/build/{build_id}/status"
            ).json()
            if status["status"] in ["success", "failed"]:
                break
            time.sleep(1)
            elapsed += 1

        assert found, "Build was not visible in /api/summary"

    def test_project_discovery_via_api(
        self, dashboard_server: str, quickstart_project: Path
    ):
        """GET /api/projects should discover the quickstart project."""
        response = requests.get(
            f"{dashboard_server}/api/projects",
            timeout=5,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Find quickstart
        quickstart = None
        for p in data["projects"]:
            if p["name"] == "quickstart":
                quickstart = p
                break

        assert quickstart is not None, "Quickstart not found in projects"
        assert quickstart["root"] == str(quickstart_project)
        assert len(quickstart["targets"]) >= 1
        assert any(t["name"] == "default" for t in quickstart["targets"])
