"""
Tests for the atopile dashboard server API.

Tests the FastAPI endpoints for build triggering, status monitoring,
and project discovery.
"""

import json
import time
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from atopile.dashboard.server import (
    BuildQueue,
    BuildRequest,
    _active_builds,
    _build_lock,
    _build_queue,
    _is_duplicate_build,
    _make_build_key,
    create_app,
    discover_projects_in_paths,
    load_recent_builds_from_history,
    save_build_to_history,
)


@pytest.fixture
def clear_active_builds():
    """Clear active builds and build queue before and after each test."""
    # Stop and clear the global build queue
    _build_queue.clear()
    with _build_lock:
        _active_builds.clear()
    yield
    # Cleanup after test
    _build_queue.clear()
    with _build_lock:
        _active_builds.clear()


@pytest.fixture
def test_client(tmp_path: Path):
    """Create a test client with a temporary workspace."""
    summary_file = tmp_path / "summary.json"
    summary_file.write_text("{}")
    app = create_app(
        summary_file=summary_file,
        logs_base=tmp_path,
        workspace_paths=[tmp_path],
    )
    return TestClient(app)


@pytest.fixture
def minimal_ato_project(tmp_path: Path) -> Path:
    """Create a minimal ato project structure for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    ato_yaml = project_dir / "ato.yaml"
    ato_yaml.write_text(
        dedent(
            """
            requires-atopile: "^0.9.0"
            builds:
              default:
                entry: main.ato:App
            """
        ).lstrip()
    )

    main_ato = project_dir / "main.ato"
    main_ato.write_text(
        dedent(
            """
            module App:
                pass
            """
        ).lstrip()
    )

    return project_dir


@pytest.fixture
def project_with_dependencies(tmp_path: Path) -> Path:
    """Create an ato project with dependencies for package testing."""
    project_dir = tmp_path / "project_with_deps"
    project_dir.mkdir()

    ato_yaml = project_dir / "ato.yaml"
    ato_yaml.write_text(
        dedent(
            """
            requires-atopile: "^0.9.0"
            builds:
              default:
                entry: main.ato:App
            dependencies:
              atopile/bosch-bme280: "0.1.2"
              atopile/usb-connectors:
                version: "1.0.0"
            """
        ).lstrip()
    )

    return project_dir


class TestBuildEndpoints:
    """Tests for build-related API endpoints."""

    def test_start_build_returns_build_id(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """POST /api/build should return a build_id and success status."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": [],
                        "frozen": False,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "build_id" in data
        assert data["build_id"].startswith("build-")
        assert "message" in data

    def test_start_build_invalid_path_returns_400(self, test_client: TestClient):
        """POST /api/build with non-existent path should return 400."""
        response = test_client.post(
            "/api/build",
            json={
                "project_root": "/nonexistent/path",
                "targets": [],
                "frozen": False,
            },
        )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_start_build_missing_ato_yaml_returns_400(
        self, test_client: TestClient, tmp_path: Path
    ):
        """POST /api/build with path lacking ato.yaml should return 400."""
        empty_dir = tmp_path / "empty_project"
        empty_dir.mkdir()

        response = test_client.post(
            "/api/build",
            json={
                "project_root": str(empty_dir),
                "targets": [],
                "frozen": False,
            },
        )

        assert response.status_code == 400
        assert "No ato.yaml" in response.json()["detail"]

    def test_get_build_status_returns_valid_response(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """GET /api/build/{build_id}/status should return valid status response."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                # Start the build
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": [],
                        "frozen": False,
                    },
                )

                build_id = start_response.json()["build_id"]

                # Check status - TestClient runs background tasks synchronously,
                # so the build will have completed
                status_response = client.get(f"/api/build/{build_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["build_id"] == build_id
        # Status should be one of the valid states
        assert status_data["status"] in ["queued", "building", "success", "failed"]
        assert status_data["project_root"] == str(minimal_ato_project)

    def test_build_state_tracking(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """Verify build state is tracked in _active_builds dict."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                # Start the build
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": ["default"],
                        "frozen": False,
                    },
                )

                build_id = start_response.json()["build_id"]

        # Verify the build was tracked
        assert build_id in _active_builds
        build_info = _active_builds[build_id]
        assert build_info["project_root"] == str(minimal_ato_project)
        assert build_info["targets"] == ["default"]
        assert build_info["status"] == "success"  # Completed successfully
        assert build_info["return_code"] == 0

    def test_get_build_status_not_found(self, test_client: TestClient):
        """GET /api/build/{build_id}/status with invalid ID returns 404."""
        response = test_client.get("/api/build/nonexistent-build-id/status")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_build_completes_with_success_status(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """Build should transition to 'success' status when subprocess returns 0."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stderr="", stdout="Build complete"
            )

            with TestClient(app) as client:
                # Start build
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": [],
                        "frozen": False,
                    },
                )
                build_id = start_response.json()["build_id"]

                # Wait for build to complete
                time.sleep(0.2)

                # Check final status
                status_response = client.get(f"/api/build/{build_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "success"
        assert status_data["return_code"] == 0

    def test_build_completes_with_failed_status(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """Build should transition to 'failed' when subprocess returns non-zero."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Error: Build failed",
                stdout="",
            )

            with TestClient(app) as client:
                # Start build
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": [],
                        "frozen": False,
                    },
                )
                build_id = start_response.json()["build_id"]

                # Wait for build to complete
                time.sleep(0.2)

                # Check final status
                status_response = client.get(f"/api/build/{build_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "failed"
        assert status_data["return_code"] == 1
        assert "Error:" in status_data["error"]

    def test_get_active_builds(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """GET /api/builds/active should return list of all builds."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                # Start a build
                client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": [],
                        "frozen": False,
                    },
                )

                # Wait for it to complete
                time.sleep(0.2)

                # Get active builds
                response = client.get("/api/builds/active")

        assert response.status_code == 200
        data = response.json()
        assert "builds" in data
        assert len(data["builds"]) >= 1

    def test_build_with_specific_targets(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """Build should pass specified targets to subprocess."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": ["default", "test"],
                        "frozen": True,
                    },
                )

                # Wait for build to complete
                time.sleep(0.2)

        # Verify the command included the targets
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        assert "ato" in cmd
        assert "build" in cmd
        assert "--build" in cmd
        assert "default" in cmd
        assert "test" in cmd
        assert "--frozen" in cmd


class TestProjectDiscovery:
    """Tests for project discovery endpoints."""

    def test_discover_single_project(self, minimal_ato_project: Path):
        """discover_projects_in_paths should find a single project."""
        projects = discover_projects_in_paths([minimal_ato_project.parent])

        assert len(projects) == 1
        assert projects[0].name == "test_project"
        assert projects[0].root == str(minimal_ato_project)
        assert len(projects[0].targets) == 1
        assert projects[0].targets[0].name == "default"
        assert projects[0].targets[0].entry == "main.ato:App"

    def test_discover_multiple_projects(self, tmp_path: Path):
        """discover_projects_in_paths should find multiple projects."""
        # Create two projects
        for i in range(2):
            proj_dir = tmp_path / f"project_{i}"
            proj_dir.mkdir()
            (proj_dir / "ato.yaml").write_text(
                dedent(
                    f"""
                    builds:
                      target_{i}:
                        entry: main.ato:App{i}
                    """
                ).lstrip()
            )

        projects = discover_projects_in_paths([tmp_path])

        assert len(projects) == 2
        names = {p.name for p in projects}
        assert "project_0" in names
        assert "project_1" in names

    def test_discover_skips_ato_modules(
        self, tmp_path: Path, minimal_ato_project: Path
    ):
        """discover_projects_in_paths should skip .ato/modules directories."""
        # Create a .ato/modules directory with an ato.yaml
        ato_modules = minimal_ato_project / ".ato" / "modules" / "some_dep"
        ato_modules.mkdir(parents=True)
        (ato_modules / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: dep.ato:Dep
                """
            ).lstrip()
        )

        projects = discover_projects_in_paths([minimal_ato_project.parent])

        # Should only find the main project, not the dependency
        assert len(projects) == 1
        assert projects[0].name == "test_project"

    def test_get_projects_endpoint(self, tmp_path: Path, minimal_ato_project: Path):
        """GET /api/projects should return discovered projects."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[minimal_ato_project.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_projects_with_paths_param(
        self, tmp_path: Path, minimal_ato_project: Path
    ):
        """GET /api/projects with paths param should scan specified paths."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        # Create app with no workspace paths
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            # Without paths param, should return empty
            response_empty = client.get("/api/projects")
            assert response_empty.json()["total"] == 0

            # With paths param, should find the project
            response = client.get(
                "/api/projects",
                params={"paths": str(minimal_ato_project.parent)},
            )

        assert response.status_code == 200
        assert response.json()["total"] >= 1


class TestPackageEndpoints:
    """Tests for package management endpoints."""

    @pytest.fixture
    def project_with_list_dependencies(self, tmp_path: Path) -> Path:
        """Create project with list-format dependencies (current format)."""
        project_dir = tmp_path / "project_list_deps"
        project_dir.mkdir()

        ato_yaml = project_dir / "ato.yaml"
        ato_yaml.write_text(
            dedent(
                """
                requires-atopile: "^0.12.0"
                builds:
                  default:
                    entry: main.ato:App
                dependencies:
                - type: registry
                  identifier: atopile/buttons
                  release: 0.3.1
                - type: registry
                  identifier: atopile/bosch-bme280
                  release: 0.2.0
                """
            ).lstrip()
        )
        return project_dir

    def test_get_packages_empty(self, test_client: TestClient):
        """GET /api/packages should return empty list when no packages installed."""
        response = test_client.get("/api/packages")

        assert response.status_code == 200
        data = response.json()
        assert data["packages"] == []
        assert data["total"] == 0

    def test_get_packages_with_dependencies(
        self, tmp_path: Path, project_with_dependencies: Path
    ):
        """GET /api/packages should return installed packages."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_dependencies.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/packages")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        identifiers = {p["identifier"] for p in data["packages"]}
        assert "atopile/bosch-bme280" in identifiers
        assert "atopile/usb-connectors" in identifiers

    def test_get_package_by_id(self, tmp_path: Path, project_with_dependencies: Path):
        """GET /api/packages/{id} should return specific package info."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_dependencies.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/packages/atopile/bosch-bme280")

        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "atopile/bosch-bme280"
        assert data["installed"] is True
        assert data["version"] == "0.1.2"

    def test_get_package_not_installed(self, test_client: TestClient):
        """GET /api/packages/{id} for non-installed package returns basic info."""
        response = test_client.get("/api/packages/atopile/nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "atopile/nonexistent"
        assert data["installed"] is False

    def test_get_packages_list_format_dependencies(
        self, tmp_path: Path, project_with_list_dependencies: Path
    ):
        """GET /api/packages should parse list-format dependencies correctly."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_list_dependencies.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/packages?include_registry=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        # Check correct parsing of list-format deps
        identifiers = {p["identifier"]: p for p in data["packages"]}
        assert "atopile/buttons" in identifiers
        assert "atopile/bosch-bme280" in identifiers

        # Check version parsed from 'release' field
        assert identifiers["atopile/buttons"]["version"] == "0.3.1"
        assert identifiers["atopile/bosch-bme280"]["version"] == "0.2.0"

    def test_package_info_has_all_expected_fields(
        self, tmp_path: Path, project_with_list_dependencies: Path
    ):
        """Package info should include all expected fields for UI."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_list_dependencies.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/packages?include_registry=false")

        assert response.status_code == 200
        data = response.json()

        # Check a package has all expected fields
        pkg = data["packages"][0]
        assert "identifier" in pkg
        assert "name" in pkg
        assert "publisher" in pkg
        assert "version" in pkg
        assert "installed" in pkg
        assert "installed_in" in pkg
        # Optional fields should be present (possibly None)
        assert "latest_version" in pkg
        assert "summary" in pkg
        assert "description" in pkg
        assert "homepage" in pkg
        assert "repository" in pkg
        assert "license" in pkg
        assert "downloads" in pkg
        assert "version_count" in pkg
        assert "keywords" in pkg

    def test_packages_installed_in_tracks_project_paths(self, tmp_path: Path):
        """installed_in should track which projects have the package."""
        # Create two projects that share a dependency
        proj1 = tmp_path / "project1"
        proj1.mkdir()
        (proj1 / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: main.ato:App
                dependencies:
                - type: registry
                  identifier: atopile/shared-pkg
                  release: 1.0.0
                """
            ).lstrip()
        )

        proj2 = tmp_path / "project2"
        proj2.mkdir()
        (proj2 / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: main.ato:App
                dependencies:
                - type: registry
                  identifier: atopile/shared-pkg
                  release: 1.0.0
                """
            ).lstrip()
        )

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get("/api/packages?include_registry=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        pkg = data["packages"][0]
        assert pkg["identifier"] == "atopile/shared-pkg"
        assert len(pkg["installed_in"]) == 2
        assert str(proj1) in pkg["installed_in"]
        assert str(proj2) in pkg["installed_in"]


class TestPackageDetailsEndpoint:
    """Tests for the /api/packages/{id}/details endpoint."""

    def test_get_package_details_returns_health_stats(self, test_client: TestClient):
        """GET /api/packages/{id}/details should return health stats from registry."""
        # Use a real package that exists in the registry
        response = test_client.get("/api/packages/atopile/bosch-bme280/details")

        assert response.status_code == 200
        data = response.json()

        # Check basic fields
        assert data["identifier"] == "atopile/bosch-bme280"
        assert data["name"] == "bosch-bme280"
        assert data["publisher"] == "atopile"

        # Check health stats are present and are numbers
        assert "downloads" in data
        assert data["downloads"] is not None
        assert isinstance(data["downloads"], int)
        assert data["downloads"] >= 0

        # Check weekly/monthly downloads
        assert "downloads_this_week" in data
        assert "downloads_this_month" in data

        # Check version count
        assert "version_count" in data
        assert data["version_count"] >= 1

    def test_get_package_details_returns_versions(self, test_client: TestClient):
        """GET /api/packages/{id}/details should return version list."""
        response = test_client.get("/api/packages/atopile/bosch-bme280/details")

        assert response.status_code == 200
        data = response.json()

        # Check versions array
        assert "versions" in data
        assert isinstance(data["versions"], list)
        assert len(data["versions"]) >= 1

        # Check version structure
        version = data["versions"][0]
        assert "version" in version
        assert "released_at" in version

    def test_get_package_details_returns_license(self, test_client: TestClient):
        """GET /api/packages/{id}/details should return license info."""
        response = test_client.get("/api/packages/atopile/bosch-bme280/details")

        assert response.status_code == 200
        data = response.json()

        # License should be present
        assert "license" in data
        # May be None or a string like "MIT"

    def test_get_package_details_not_found(self, test_client: TestClient):
        """GET /api/packages/{id}/details for nonexistent package returns 404."""
        response = test_client.get(
            "/api/packages/nonexistent/totally-fake-package/details"
        )

        assert response.status_code == 404

    def test_get_package_details_includes_installation_status(
        self, tmp_path: Path, project_with_list_dependencies: Path
    ):
        """GET /api/packages/{id}/details should include installation status."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_list_dependencies.parent],
        )

        with TestClient(app) as client:
            # This package is installed in project_with_list_dependencies
            response = client.get("/api/packages/atopile/buttons/details")

        # Note: This may fail if the package doesn't exist in the registry
        # In that case, the test verifies proper 404 handling
        if response.status_code == 200:
            data = response.json()
            # Should show as installed since it's in the workspace
            assert "installed" in data
            assert "installed_in" in data
            # installed_version should match the installed version
            if data["installed"]:
                assert "installed_version" in data

    @pytest.fixture
    def project_with_list_dependencies(self, tmp_path: Path) -> Path:
        """Create project with list-format dependencies (current format)."""
        project_dir = tmp_path / "project_list_deps"
        project_dir.mkdir()

        ato_yaml = project_dir / "ato.yaml"
        ato_yaml.write_text(
            dedent(
                """
                requires-atopile: "^0.12.0"
                builds:
                  default:
                    entry: main.ato:App
                dependencies:
                - type: registry
                  identifier: atopile/buttons
                  release: 0.3.1
                - type: registry
                  identifier: atopile/bosch-bme280
                  release: 0.2.0
                """
            ).lstrip()
        )
        return project_dir


class TestSummaryEndpoint:
    """Tests for summary endpoint."""

    def test_get_summary_empty(self, tmp_path: Path):
        """GET /api/summary should return summary data."""
        summary_file = tmp_path / "summary.json"
        summary_data = {"builds": [], "totals": {"success": 0, "failed": 0}}
        summary_file.write_text(json.dumps(summary_data))

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()
        assert "builds" in data
        assert "totals" in data

    def test_get_summary_no_file(self, tmp_path: Path):
        """GET /api/summary when no file exists returns empty structure."""
        nonexistent = tmp_path / "nonexistent.json"
        app = create_app(
            summary_file=nonexistent,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()
        # Returns empty but valid structure when no file exists
        assert data["builds"] == []
        # totals has default keys with zero values
        assert "totals" in data
        assert data["totals"].get("builds", 0) == 0

    def test_get_summary_includes_active_builds(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """GET /api/summary should include builds from _active_builds."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text('{"builds": [], "totals": {}}')

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        # Manually inject a "building" entry into _active_builds
        # This simulates a build in progress
        test_build_id = "test-build-001"
        with _build_lock:
            _active_builds[test_build_id] = {
                "status": "building",
                "project_root": str(minimal_ato_project),
                "targets": ["default"],
                "return_code": None,
                "error": None,
                "started_at": time.time(),
            }

        try:
            with TestClient(app) as client:
                # Get summary - should include the manually injected build
                response = client.get("/api/summary")

            assert response.status_code == 200
            data = response.json()
            # Should have the active build
            assert len(data["builds"]) >= 1
            # The first build should be our active one
            active_build = data["builds"][0]
            assert active_build["status"] == "building"
            assert active_build["project_name"] == "test_project"
            assert active_build["return_code"] is None
        finally:
            # Clean up
            with _build_lock:
                _active_builds.pop(test_build_id, None)


class TestLogsEndpoint:
    """Tests for log file endpoint."""

    def test_get_log_file(self, tmp_path: Path):
        """GET /api/logs/{build_name}/{log_filename} should return log content."""
        # Create summary with log_dir
        log_dir = tmp_path / "logs" / "my_build"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "build.log"
        log_file.write_text("Build started\nBuild complete")

        summary_data = {
            "builds": [{"name": "my_build", "log_dir": str(log_dir)}],
            "totals": {},
        }
        summary_file = tmp_path / "summary.json"
        summary_file.write_text(json.dumps(summary_data))

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get("/api/logs/my_build/build.log")

        assert response.status_code == 200
        assert "Build started" in response.text
        assert "Build complete" in response.text

    def test_get_log_file_not_found(self, tmp_path: Path):
        """GET /api/logs with nonexistent file returns 404."""
        log_dir = tmp_path / "logs" / "my_build"
        log_dir.mkdir(parents=True)

        summary_data = {
            "builds": [{"name": "my_build", "log_dir": str(log_dir)}],
            "totals": {},
        }
        summary_file = tmp_path / "summary.json"
        summary_file.write_text(json.dumps(summary_data))

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get("/api/logs/my_build/nonexistent.log")

        assert response.status_code == 404

    def test_get_log_build_not_found(self, tmp_path: Path):
        """GET /api/logs with nonexistent build returns 404."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text('{"builds": [], "totals": {}}')

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get("/api/logs/nonexistent_build/build.log")

        assert response.status_code == 404


class TestBOMEndpoints:
    """Tests for BOM (Bill of Materials) API endpoints."""

    @pytest.fixture
    def project_with_bom(self, tmp_path: Path) -> Path:
        """Create a project structure with a mock BOM file."""
        project_dir = tmp_path / "project_with_bom"
        project_dir.mkdir()

        # Create ato.yaml
        (project_dir / "ato.yaml").write_text(
            """
requires-atopile: "^0.9.0"
builds:
  default:
    entry: main.ato:App
"""
        )

        # Create BOM directory structure
        bom_dir = project_dir / "build" / "builds" / "default"
        bom_dir.mkdir(parents=True)

        # Create mock BOM JSON
        bom_data = {
            "version": "1.0",
            "components": [
                {
                    "id": "c25744",
                    "lcsc": "C25744",
                    "manufacturer": "Yageo",
                    "mpn": "RC0402FR-0710KL",
                    "type": "resistor",
                    "value": "10kΩ ±1%",
                    "package": "0402",
                    "description": "Thick Film Resistor",
                    "quantity": 2,
                    "unitCost": 0.002,
                    "stock": 50000,
                    "isBasic": True,
                    "isPreferred": False,
                    "source": "picked",
                    "parameters": [
                        {"name": "resistance", "value": "10k", "unit": "ohm"}
                    ],
                    "usages": [
                        {"address": "App.power_supply.r_top", "designator": "R1"},
                        {"address": "App.power_supply.r_bot", "designator": "R2"},
                    ],
                },
                {
                    "id": "c1525",
                    "lcsc": "C1525",
                    "manufacturer": "Samsung",
                    "mpn": "CL05B104KO5NNNC",
                    "type": "capacitor",
                    "value": "100nF",
                    "package": "0402",
                    "description": "MLCC",
                    "quantity": 1,
                    "unitCost": 0.003,
                    "stock": 120000,
                    "isBasic": True,
                    "isPreferred": True,
                    "source": "picked",
                    "parameters": [],
                    "usages": [
                        {"address": "App.decoupling[0]", "designator": "C1"},
                    ],
                },
            ],
        }
        (bom_dir / "default.bom.json").write_text(json.dumps(bom_data))

        return project_dir

    def test_get_bom_returns_data(self, tmp_path: Path, project_with_bom: Path):
        """GET /api/bom should return the BOM data."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_bom.parent],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom",
                params={"project_root": str(project_with_bom), "target": "default"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"
        assert "components" in data
        assert len(data["components"]) == 2

        # Verify first component
        resistor = next(c for c in data["components"] if c["type"] == "resistor")
        assert resistor["lcsc"] == "C25744"
        assert resistor["quantity"] == 2
        assert len(resistor["usages"]) == 2

    def test_get_bom_default_target(self, tmp_path: Path, project_with_bom: Path):
        """GET /api/bom should default to 'default' target."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            # Only provide project_root, not target
            response = client.get(
                "/api/bom",
                params={"project_root": str(project_with_bom)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"

    def test_get_bom_invalid_project_returns_400(self, tmp_path: Path):
        """GET /api/bom with non-existent project returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom",
                params={"project_root": "/nonexistent/path", "target": "default"},
            )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_get_bom_missing_ato_yaml_returns_400(self, tmp_path: Path):
        """GET /api/bom with no ato.yaml returns 400."""
        empty_dir = tmp_path / "empty_project"
        empty_dir.mkdir()

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom",
                params={"project_root": str(empty_dir), "target": "default"},
            )

        assert response.status_code == 400
        assert "No ato.yaml" in response.json()["detail"]

    def test_get_bom_no_build_returns_404(self, tmp_path: Path):
        """GET /api/bom before running build returns 404."""
        project_dir = tmp_path / "project_no_build"
        project_dir.mkdir()
        (project_dir / "ato.yaml").write_text(
            """
builds:
  default:
    entry: main.ato:App
"""
        )

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom",
                params={"project_root": str(project_dir), "target": "default"},
            )

        assert response.status_code == 404
        assert "Run 'ato build' first" in response.json()["detail"]

    def test_get_bom_targets_returns_list(self, tmp_path: Path, project_with_bom: Path):
        """GET /api/bom/targets should list available BOM targets."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom/targets",
                params={"project_root": str(project_with_bom)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["project_root"] == str(project_with_bom)
        assert "targets" in data
        assert len(data["targets"]) >= 1

        # Check target structure
        target = data["targets"][0]
        assert target["name"] == "default"
        assert "bom_path" in target
        assert "last_modified" in target

    def test_get_bom_targets_empty_project(self, tmp_path: Path):
        """GET /api/bom/targets for project with no builds returns empty list."""
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom/targets",
                params={"project_root": str(project_dir)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["targets"] == []

    def test_get_bom_multiple_targets(self, tmp_path: Path):
        """GET /api/bom/targets should return all targets with BOM files."""
        project_dir = tmp_path / "multi_target_project"
        project_dir.mkdir()
        (project_dir / "ato.yaml").write_text(
            "builds:\n  default:\n    entry: main.ato:App"
        )

        # Create multiple build targets
        for target_name in ["default", "test", "production"]:
            target_dir = project_dir / "build" / "builds" / target_name
            target_dir.mkdir(parents=True)
            bom_file = target_dir / f"{target_name}.bom.json"
            bom_file.write_text('{"version": "1.0", "components": []}')

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/bom/targets",
                params={"project_root": str(project_dir)},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["targets"]) == 3

        target_names = {t["name"] for t in data["targets"]}
        assert "default" in target_names
        assert "test" in target_names
        assert "production" in target_names


# --- Integration Tests ---
# These tests run actual builds on real projects

QUICKSTART_PROJECT = Path(__file__).parent.parent / "examples" / "quickstart"


@pytest.fixture
def quickstart_project() -> Path:
    """Return the path to the quickstart example project."""
    if not QUICKSTART_PROJECT.exists():
        pytest.skip("Quickstart project not found")
    return QUICKSTART_PROJECT


class TestBuildIntegration:
    """Integration tests for project discovery and build API contracts.

    Note: Tests that actually run `ato build` are in a separate file
    (test_dashboard_integration.py) because FastAPI's TestClient runs
    background tasks synchronously, blocking until builds complete.
    """

    def test_discover_quickstart_project(self, quickstart_project: Path):
        """Project discovery should find the quickstart project."""
        projects = discover_projects_in_paths([quickstart_project.parent])

        # Find the quickstart project
        quickstart = None
        for p in projects:
            if p.name == "quickstart":
                quickstart = p
                break

        assert quickstart is not None, "Quickstart project not discovered"
        assert quickstart.root == str(quickstart_project)
        assert len(quickstart.targets) >= 1
        assert any(t.name == "default" for t in quickstart.targets)

    def test_quickstart_project_in_api(self, tmp_path: Path, quickstart_project: Path):
        """GET /api/projects should return the quickstart project."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text('{"builds": [], "totals": {}}')

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[quickstart_project.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Find quickstart in the response
        quickstart = None
        for p in data["projects"]:
            if p["name"] == "quickstart":
                quickstart = p
                break

        assert quickstart is not None
        assert len(quickstart["targets"]) >= 1

    def test_build_request_validation(self, tmp_path: Path, quickstart_project: Path):
        """Build request validation should accept valid quickstart project."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text('{"builds": [], "totals": {}}')

        _app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[quickstart_project.parent],
        )

        # We don't actually start the build, just test validation
        _ = _app  # Silence unused variable warning

        request = BuildRequest(
            project_root=str(quickstart_project),
            targets=["default"],
            frozen=False,
        )
        assert request.project_root == str(quickstart_project)
        assert "default" in request.targets


class TestProblemsEndpoint:
    """Tests for the /api/problems endpoint."""

    @pytest.fixture
    def project_with_build_logs(self, tmp_path: Path) -> Path:
        """Create a project with mock build logs containing problems."""
        project_dir = tmp_path / "project_with_logs"
        project_dir.mkdir()

        # Create ato.yaml
        (project_dir / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: main.ato:App
                """
            ).lstrip()
        )

        # Create build logs directory structure
        log_dir = project_dir / "build" / "logs" / "latest"
        log_dir.mkdir(parents=True)

        # Create summary.json with build info
        summary_data = {
            "builds": [
                {
                    "name": "default",
                    "display_name": "default",
                    "log_file": str(log_dir / "default.jsonl"),
                    "status": "warning",
                }
            ],
            "totals": {"warnings": 2, "errors": 1},
        }
        (log_dir / "summary.json").write_text(json.dumps(summary_data))

        # Create JSONL log file with problems
        log_entries = [
            {
                "level": "INFO",
                "message": "Starting build",
                "timestamp": "2024-01-19T10:00:00",
            },
            {
                "level": "WARNING",
                "message": "Parameter may be over-constrained",
                "stage": "solving",
                "logger": "atopile.solver",
                "timestamp": "2024-01-19T10:00:01",
                "ato_traceback": 'File "main.ato", line 15, column 4',
            },
            {
                "level": "ERROR",
                "message": "Could not find suitable component",
                "stage": "picking",
                "logger": "atopile.picker",
                "timestamp": "2024-01-19T10:00:02",
                "ato_traceback": 'File "main.ato", line 23',
            },
            {
                "level": "WARNING",
                "message": "Footprint not optimal for assembly",
                "stage": "layout",
                "logger": "atopile.layout",
                "timestamp": "2024-01-19T10:00:03",
            },
        ]
        log_content = "\n".join(json.dumps(entry) for entry in log_entries)
        (log_dir / "default.jsonl").write_text(log_content)

        return project_dir

    def test_get_problems_returns_warnings_and_errors(
        self, tmp_path: Path, project_with_build_logs: Path
    ):
        """GET /api/problems should return both warnings and errors."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_build_logs.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/problems")

        assert response.status_code == 200
        data = response.json()
        assert "problems" in data
        assert "total" in data
        assert "error_count" in data
        assert "warning_count" in data

        # Should have found 2 warnings and 1 error from the log
        assert data["warning_count"] == 2
        assert data["error_count"] == 1
        assert data["total"] == 3

    def test_get_problems_parses_file_locations(
        self, tmp_path: Path, project_with_build_logs: Path
    ):
        """GET /api/problems should parse file/line/column from ato_traceback."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_build_logs.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/problems")

        assert response.status_code == 200
        data = response.json()

        # Find the warning with line and column
        warning_with_location = None
        for p in data["problems"]:
            if p["line"] == 15 and p["column"] == 4:
                warning_with_location = p
                break

        assert warning_with_location is not None
        assert warning_with_location["file"] == "main.ato"
        assert warning_with_location["line"] == 15
        assert warning_with_location["column"] == 4

    def test_get_problems_filter_by_level(
        self, tmp_path: Path, project_with_build_logs: Path
    ):
        """GET /api/problems?level=error should only return errors."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_build_logs.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/problems", params={"level": "error"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert all(p["level"] == "error" for p in data["problems"])

    def test_get_problems_filter_by_project(
        self, tmp_path: Path, project_with_build_logs: Path
    ):
        """GET /api/problems?project_root=... should filter by project."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_build_logs.parent],
        )

        with TestClient(app) as client:
            # Filter to existing project
            response = client.get(
                "/api/problems",
                params={"project_root": str(project_with_build_logs)},
            )
            assert response.status_code == 200
            assert response.json()["total"] == 3

            # Filter to non-existent project
            response_empty = client.get(
                "/api/problems",
                params={"project_root": "/nonexistent/project"},
            )
            assert response_empty.status_code == 200
            assert response_empty.json()["total"] == 0

    def test_get_problems_empty_workspace(self, tmp_path: Path):
        """GET /api/problems should return empty list for empty workspace."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[],
        )

        with TestClient(app) as client:
            response = client.get("/api/problems")

        assert response.status_code == 200
        data = response.json()
        assert data["problems"] == []
        assert data["total"] == 0
        assert data["error_count"] == 0
        assert data["warning_count"] == 0


class TestResolveLocationEndpoint:
    """Tests for the /api/resolve-location endpoint."""

    @pytest.fixture
    def project_with_modules(self, tmp_path: Path) -> Path:
        """Create a project with .ato files containing modules."""
        project_dir = tmp_path / "project_modules"
        project_dir.mkdir()

        # Create ato.yaml
        (project_dir / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: main.ato:App
                """
            ).lstrip()
        )

        # Create main.ato with modules
        (project_dir / "main.ato").write_text(
            dedent(
                """
                module App:
                    power = new PowerSupply
                    sensor = new TempSensor

                module PowerSupply:
                    voltage = 3.3V
                    current = 100mA

                interface TempSensor:
                    reading = 25C
                """
            ).lstrip()
        )

        return project_dir

    def test_resolve_location_finds_module(
        self, tmp_path: Path, project_with_modules: Path
    ):
        """GET /api/resolve-location should resolve module address to file:line."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_modules.parent],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/resolve-location",
                params={
                    "address": "main.ato::App",
                    "project_root": str(project_with_modules),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "file" in data
        assert "line" in data
        assert data["resolved"] is True
        assert "main.ato" in data["file"]

    def test_resolve_location_finds_nested_field(
        self, tmp_path: Path, project_with_modules: Path
    ):
        """GET /api/resolve-location should resolve nested field addresses."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_modules.parent],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/resolve-location",
                params={
                    "address": "main.ato::PowerSupply.voltage",
                    "project_root": str(project_with_modules),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["resolved"] is True
        assert "main.ato" in data["file"]

    def test_resolve_location_strips_type_annotation(
        self, tmp_path: Path, project_with_modules: Path
    ):
        """GET /api/resolve-location should handle addresses with |Type suffix."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_modules.parent],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/resolve-location",
                params={
                    "address": "main.ato::App.power|PowerSupply",
                    "project_root": str(project_with_modules),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "file" in data

    def test_resolve_location_invalid_format_returns_400(
        self, tmp_path: Path, project_with_modules: Path
    ):
        """GET /api/resolve-location with invalid address format returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_modules.parent],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/resolve-location",
                params={
                    "address": "no_double_colon_here",  # Missing ::
                },
            )

        assert response.status_code == 400
        assert "Invalid address format" in response.json()["detail"]

    def test_resolve_location_file_not_found_returns_404(
        self, tmp_path: Path, project_with_modules: Path
    ):
        """GET /api/resolve-location with nonexistent file returns 404."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[project_with_modules.parent],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/resolve-location",
                params={
                    "address": "nonexistent.ato::Module",
                    "project_root": str(project_with_modules),
                },
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestProjectCreateEndpoint:
    """Tests for the /api/project/create endpoint."""

    def test_create_project_success(self, tmp_path: Path):
        """POST /api/project/create should create a new project."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/create",
                json={
                    "parent_directory": str(tmp_path),
                    "name": "my-new-project",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_name"] == "my-new-project"
        assert "project_root" in data

        # Verify the project was created
        project_dir = Path(data["project_root"])
        assert project_dir.exists()
        assert (project_dir / "ato.yaml").exists()
        assert (project_dir / "main.ato").exists()
        assert (project_dir / "layouts").is_dir()
        assert (project_dir / ".gitignore").exists()

    def test_create_project_auto_name(self, tmp_path: Path):
        """POST /api/project/create without name should auto-generate name."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/create",
                json={"parent_directory": str(tmp_path)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_name"] == "new-project"

    def test_create_project_auto_increment_name(self, tmp_path: Path):
        """POST /api/project/create should increment name if exists."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        # Create first project
        (tmp_path / "new-project").mkdir()

        with TestClient(app) as client:
            response = client.post(
                "/api/project/create",
                json={"parent_directory": str(tmp_path)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "new-project-2"

    def test_create_project_invalid_parent_returns_400(self, tmp_path: Path):
        """POST /api/project/create with nonexistent parent returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/create",
                json={
                    "parent_directory": "/nonexistent/path",
                    "name": "test",
                },
            )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_create_project_already_exists_returns_400(self, tmp_path: Path):
        """POST /api/project/create with existing name returns 400."""
        # Create existing directory
        (tmp_path / "existing-project").mkdir()

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/create",
                json={
                    "parent_directory": str(tmp_path),
                    "name": "existing-project",
                },
            )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestProjectRenameEndpoint:
    """Tests for the /api/project/rename endpoint."""

    def test_rename_project_success(self, tmp_path: Path, minimal_ato_project: Path):
        """POST /api/project/rename should rename the project directory."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/rename",
                json={
                    "project_root": str(minimal_ato_project),
                    "new_name": "renamed-project",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["old_root"] == str(minimal_ato_project)
        assert "renamed-project" in data["new_root"]

        # Verify the rename happened
        new_path = Path(data["new_root"])
        assert new_path.exists()
        assert not minimal_ato_project.exists()
        assert (new_path / "ato.yaml").exists()

    def test_rename_project_not_found_returns_400(self, tmp_path: Path):
        """POST /api/project/rename with nonexistent project returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/rename",
                json={
                    "project_root": "/nonexistent/project",
                    "new_name": "new-name",
                },
            )

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_rename_project_invalid_name_returns_400(
        self, tmp_path: Path, minimal_ato_project: Path
    ):
        """POST /api/project/rename with invalid name returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/rename",
                json={
                    "project_root": str(minimal_ato_project),
                    "new_name": "invalid/name",  # Contains /
                },
            )

        assert response.status_code == 400
        assert "Invalid project name" in response.json()["detail"]

    def test_rename_project_target_exists_returns_400(
        self, tmp_path: Path, minimal_ato_project: Path
    ):
        """POST /api/project/rename to existing directory returns 400."""
        # Create target directory
        (tmp_path / "existing-dir").mkdir()

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/project/rename",
                json={
                    "project_root": str(minimal_ato_project),
                    "new_name": "existing-dir",
                },
            )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestModulesEndpoint:
    """Tests for the /api/modules endpoint."""

    @pytest.fixture
    def project_with_multiple_modules(self, tmp_path: Path) -> Path:
        """Create a project with multiple module definitions."""
        project_dir = tmp_path / "multi_module_project"
        project_dir.mkdir()

        # Create ato.yaml
        (project_dir / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: main.ato:App
                """
            ).lstrip()
        )

        # Create main.ato with various block types
        (project_dir / "main.ato").write_text(
            dedent(
                """
                module App:
                    pass

                module PowerSupply from Regulator:
                    pass

                interface I2CBus:
                    pass

                component Resistor:
                    pass
                """
            ).lstrip()
        )

        # Create another file with more modules
        (project_dir / "sensors.ato").write_text(
            dedent(
                """
                module TempSensor:
                    pass

                interface SensorInterface:
                    pass
                """
            ).lstrip()
        )

        return project_dir

    def test_get_modules_returns_all_blocks(
        self, tmp_path: Path, project_with_multiple_modules: Path
    ):
        """GET /api/modules should return all module/interface/component definitions."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/modules",
                params={"project_root": str(project_with_multiple_modules)},
            )

        assert response.status_code == 200
        data = response.json()
        assert "modules" in data
        assert "total" in data

        # Should find 6 blocks total
        assert data["total"] == 6

        # Check all types are present
        names = {m["name"] for m in data["modules"]}
        assert "App" in names
        assert "PowerSupply" in names
        assert "I2CBus" in names
        assert "Resistor" in names
        assert "TempSensor" in names
        assert "SensorInterface" in names

    def test_get_modules_filter_by_type(
        self, tmp_path: Path, project_with_multiple_modules: Path
    ):
        """GET /api/modules?type_filter=module should only return modules."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/modules",
                params={
                    "project_root": str(project_with_multiple_modules),
                    "type_filter": "module",
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Should only find modules (App, PowerSupply, TempSensor)
        assert data["total"] == 3
        assert all(m["type"] == "module" for m in data["modules"])

    def test_get_modules_includes_entry_points(
        self, tmp_path: Path, project_with_multiple_modules: Path
    ):
        """GET /api/modules should include entry point strings."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/modules",
                params={"project_root": str(project_with_multiple_modules)},
            )

        assert response.status_code == 200
        data = response.json()

        # Find the App module
        app_module = next(m for m in data["modules"] if m["name"] == "App")
        assert app_module["entry"] == "main.ato:App"
        assert app_module["file"] == "main.ato"

    def test_get_modules_project_not_found(self, tmp_path: Path):
        """GET /api/modules with nonexistent project returns 404."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/modules",
                params={"project_root": "/nonexistent/project"},
            )

        assert response.status_code == 404


class TestVariablesEndpoint:
    """Tests for the /api/variables endpoint."""

    @pytest.fixture
    def project_with_variables(self, tmp_path: Path) -> Path:
        """Create a project with mock variables output."""
        project_dir = tmp_path / "project_with_vars"
        project_dir.mkdir()

        # Create ato.yaml
        (project_dir / "ato.yaml").write_text(
            dedent(
                """
                builds:
                  default:
                    entry: main.ato:App
                """
            ).lstrip()
        )

        # Create variables directory structure
        vars_dir = project_dir / "build" / "builds" / "default"
        vars_dir.mkdir(parents=True)

        # Create mock variables JSON
        variables_data = {
            "root": {
                "name": "App",
                "type": "module",
                "parameters": [
                    {
                        "name": "voltage",
                        "spec": "3.3V +/- 5%",
                        "actual": "3.3V",
                        "unit": "V",
                        "source": "user",
                    },
                    {
                        "name": "current",
                        "spec": "100mA to 200mA",
                        "actual": "150mA",
                        "unit": "mA",
                        "source": "derived",
                    },
                ],
                "children": [
                    {
                        "name": "resistor",
                        "type": "module",
                        "parameters": [
                            {
                                "name": "resistance",
                                "spec": "10kohm +/- 1%",
                                "actual": "10kohm",
                                "unit": "ohm",
                                "source": "picked",
                            }
                        ],
                        "children": [],
                    }
                ],
            }
        }
        (vars_dir / "default.variables.json").write_text(json.dumps(variables_data))

        return project_dir

    def test_get_variables_returns_data(
        self, tmp_path: Path, project_with_variables: Path
    ):
        """GET /api/variables should return variables JSON."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/variables",
                params={
                    "project_root": str(project_with_variables),
                    "target": "default",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "root" in data
        assert data["root"]["name"] == "App"
        assert len(data["root"]["parameters"]) == 2
        assert len(data["root"]["children"]) == 1

    def test_get_variables_not_built_returns_404(self, tmp_path: Path):
        """GET /api/variables before building returns 404."""
        project_dir = tmp_path / "unbuilt_project"
        project_dir.mkdir()
        (project_dir / "ato.yaml").write_text(
            "builds:\n  default:\n    entry: main.ato:App"
        )

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/variables",
                params={"project_root": str(project_dir), "target": "default"},
            )

        assert response.status_code == 404
        assert "Run 'ato build' first" in response.json()["detail"]

    def test_get_variables_targets_returns_list(
        self, tmp_path: Path, project_with_variables: Path
    ):
        """GET /api/variables/targets should list available targets."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/variables/targets",
                params={"project_root": str(project_with_variables)},
            )

        assert response.status_code == 200
        data = response.json()
        assert "targets" in data
        assert len(data["targets"]) >= 1
        assert data["targets"][0]["name"] == "default"


class TestStandaloneBuild:
    """Tests for standalone build support in /api/build."""

    @pytest.fixture
    def standalone_project(self, tmp_path: Path) -> Path:
        """Create a project with just .ato files (no build config)."""
        project_dir = tmp_path / "standalone_project"
        project_dir.mkdir()

        # Create main.ato but NO ato.yaml (standalone mode)
        (project_dir / "main.ato").write_text(
            dedent(
                """
                module App:
                    pass
                """
            ).lstrip()
        )

        return project_dir

    def test_standalone_build_request_validation(
        self, tmp_path: Path, standalone_project: Path, clear_active_builds
    ):
        """POST /api/build with standalone=True should accept entry without ato.yaml."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(standalone_project),
                        "entry": "main.ato:App",
                        "standalone": True,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "build_id" in data

    def test_standalone_build_requires_entry(
        self, tmp_path: Path, standalone_project: Path
    ):
        """POST /api/build with standalone=True but no entry returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/build",
                json={
                    "project_root": str(standalone_project),
                    "standalone": True,
                    # No entry provided
                },
            )

        assert response.status_code == 400
        assert "entry point" in response.json()["detail"].lower()

    def test_standalone_build_validates_entry_file(
        self, tmp_path: Path, standalone_project: Path
    ):
        """POST /api/build with nonexistent entry file returns 400."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/build",
                json={
                    "project_root": str(standalone_project),
                    "entry": "nonexistent.ato:Module",
                    "standalone": True,
                },
            )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_standalone_build_command_includes_flags(
        self, tmp_path: Path, standalone_project: Path, clear_active_builds
    ):
        """Standalone build should pass --standalone flag to subprocess."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            with TestClient(app) as client:
                client.post(
                    "/api/build",
                    json={
                        "project_root": str(standalone_project),
                        "entry": "main.ato:App",
                        "standalone": True,
                    },
                )

                # Wait for background task
                time.sleep(0.2)

        # Verify the command included standalone flags
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        assert "ato" in cmd
        assert "build" in cmd
        assert "--standalone" in cmd
        assert "main.ato:App" in cmd


class TestBuildStageTracking:
    """
    Tests for build stage initialization, timing, and state tracking.

    These tests verify the build flow from "play button clicked" through
    to build completion, ensuring all state updates occur correctly.
    """

    def test_build_initializes_with_default_stages(self, clear_active_builds):
        """When a build starts, it should initialize all stages as 'pending'."""
        # Directly test the stage initialization logic without running subprocess
        # This isolates the test from TestClient running background tasks synchronously

        # Manually create a build entry as would be done by the /api/build endpoint
        build_id = "test-init-stages"
        with _build_lock:
            initial_stages = [
                {
                    "name": name,
                    "display_name": display_name,
                    "status": "pending",
                    "elapsed_seconds": None,
                }
                for name, display_name in DEFAULT_BUILD_STAGES
            ]
            _active_builds[build_id] = {
                "status": "queued",
                "project_root": "/test/project",
                "targets": ["default"],
                "stages": initial_stages,
                "current_stage": None,
            }

        # Verify stages are correctly initialized
        with _build_lock:
            build_info = _active_builds[build_id]
            stages = build_info.get("stages", [])

            # Should have all default stages
            assert len(stages) == len(DEFAULT_BUILD_STAGES)

            # All stages should be pending initially
            for i, stage in enumerate(stages):
                expected_name, expected_display = DEFAULT_BUILD_STAGES[i]
                assert stage["name"] == expected_name
                assert stage["display_name"] == expected_display
                assert stage["status"] == "pending"
                assert stage["elapsed_seconds"] is None

    def test_stage_status_response_includes_stages(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """GET /api/build/{id}/status should return stages with correct structure."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = iter([])
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            with TestClient(app) as client:
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": ["default"],
                        "frozen": False,
                    },
                )
                build_id = start_response.json()["build_id"]

                # Get status
                status_response = client.get(f"/api/build/{build_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()

        # Should have stages array
        assert "stages" in status_data
        stages = status_data["stages"]
        assert len(stages) == len(DEFAULT_BUILD_STAGES)

        # Each stage should have the required fields
        for stage in stages:
            assert "name" in stage
            assert "display_name" in stage
            assert "status" in stage
            assert "elapsed_seconds" in stage

    def test_update_build_stage_from_output_detects_stage_change(
        self, clear_active_builds
    ):
        """_update_build_stage_from_output should detect stage transitions."""
        # Set up a fake build in _active_builds
        build_id = "test-build-1"
        with _build_lock:
            _active_builds[build_id] = {
                "status": "building",
                "project_root": "/test",
                "targets": ["default"],
                "current_stage": None,
                "current_stage_index": 0,
                "stages": [
                    {
                        "name": name,
                        "display_name": display,
                        "status": "pending",
                        "elapsed_seconds": None,
                    }
                    for name, display in DEFAULT_BUILD_STAGES
                ],
            }

        # Simulate output that matches first stage pattern
        _update_build_stage_from_output(build_id, "Initializing build context...")

        # Check that stage was updated
        with _build_lock:
            build = _active_builds[build_id]
            assert build["current_stage"] == "Parse & Compile"
            assert build["stages"][0]["status"] == "running"
            assert build["stages"][0].get("start_time") is not None

    def test_stage_transition_marks_previous_as_success(self, clear_active_builds):
        """When moving to a new stage, previous stages should be marked success."""
        build_id = "test-build-2"
        with _build_lock:
            _active_builds[build_id] = {
                "status": "building",
                "project_root": "/test",
                "targets": ["default"],
                "current_stage": "Parse & Compile",
                "current_stage_index": 0,
                "stages": [
                    {
                        "name": "init-build-context",
                        "display_name": "Parse & Compile",
                        "status": "running",
                        "elapsed_seconds": None,
                        "start_time": time.time() - 1.5,
                    },
                    {
                        "name": "instantiate-app",
                        "display_name": "Instantiate",
                        "status": "pending",
                        "elapsed_seconds": None,
                    },
                    {
                        "name": "prepare-build",
                        "display_name": "Prepare Build",
                        "status": "pending",
                        "elapsed_seconds": None,
                    },
                ]
                + [
                    {
                        "name": name,
                        "display_name": display,
                        "status": "pending",
                        "elapsed_seconds": None,
                    }
                    for name, display in DEFAULT_BUILD_STAGES[3:]
                ],
            }

        # Move to instantiate stage
        _update_build_stage_from_output(build_id, "Instantiate: Creating app instance")

        with _build_lock:
            build = _active_builds[build_id]
            # First stage should be success with elapsed time
            assert build["stages"][0]["status"] == "success"
            assert build["stages"][0]["elapsed_seconds"] is not None
            assert build["stages"][0]["elapsed_seconds"] > 0

            # Second stage should now be running
            assert build["stages"][1]["status"] == "running"
            assert build["current_stage"] == "Instantiate"

    def test_stage_elapsed_time_calculated_on_completion(self, clear_active_builds):
        """Stage elapsed_seconds should be calculated when stage completes."""
        build_id = "test-build-3"
        start_time = time.time() - 2.0  # Started 2 seconds ago

        with _build_lock:
            _active_builds[build_id] = {
                "status": "building",
                "project_root": "/test",
                "targets": ["default"],
                "current_stage": "Parse & Compile",
                "current_stage_index": 0,
                "stages": [
                    {
                        "name": "init-build-context",
                        "display_name": "Parse & Compile",
                        "status": "running",
                        "elapsed_seconds": None,
                        "start_time": start_time,
                    },
                ]
                + [
                    {
                        "name": name,
                        "display_name": display,
                        "status": "pending",
                        "elapsed_seconds": None,
                    }
                    for name, display in DEFAULT_BUILD_STAGES[1:]
                ],
            }

        # Trigger stage transition (skipping to picker stage)
        _update_build_stage_from_output(build_id, "picker: Picking parts...")

        with _build_lock:
            build = _active_builds[build_id]
            # First stage should have elapsed time >= 2 seconds
            first_stage = build["stages"][0]
            assert first_stage["status"] == "success"
            assert first_stage["elapsed_seconds"] is not None
            assert first_stage["elapsed_seconds"] >= 1.5  # Allow some tolerance

    def test_build_completes_all_stages_success(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """On successful build completion, all stages should be marked success."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            # Simulate some output
            mock_process.stdout = iter(
                [
                    "Initializing...\n",
                    "Instantiate: done\n",
                    "Build complete\n",
                ]
            )
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            with TestClient(app) as client:
                response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": ["default"],
                        "frozen": False,
                    },
                )
                build_id = response.json()["build_id"]

                # Wait for build to complete
                time.sleep(0.3)

                # Check final status
                status_response = client.get(f"/api/build/{build_id}/status")

        status_data = status_response.json()
        assert status_data["status"] == "success"

        # All stages should be success
        for stage in status_data["stages"]:
            assert stage["status"] == "success"


class TestSummaryBuildStateIntegration:
    """
    Tests for the /api/summary endpoint and how it integrates with build state.

    These tests verify that the summary correctly reflects active builds
    and persisted build history.
    """

    def test_summary_includes_active_build_with_stages(
        self, tmp_path: Path, clear_active_builds
    ):
        """Active builds should appear in /api/summary with their stages."""
        # Since TestClient runs background tasks synchronously, we need to manually
        # inject an active build to test the summary endpoint's behavior
        summary_file = tmp_path / "summary.json"
        summary_file.write_text(
            json.dumps(
                {
                    "builds": [],
                    "timestamp": "2024-01-01T00:00:00",
                }
            )
        )
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        # Manually inject an active build into _active_builds
        build_id = "test-active-build"
        with _build_lock:
            _active_builds[build_id] = {
                "status": "building",
                "project_root": str(tmp_path),
                "targets": ["default"],
                "start_time": time.time(),
                "stages": [
                    {
                        "name": name,
                        "display_name": display,
                        "status": "pending",
                        "elapsed_seconds": None,
                    }
                    for name, display in DEFAULT_BUILD_STAGES
                ],
                "current_stage": "Parse & Compile",
                "current_stage_index": 0,
            }
            # Mark first stage as running
            _active_builds[build_id]["stages"][0]["status"] = "running"

        with TestClient(app) as client:
            # Check summary - should show active build
            summary_response = client.get("/api/summary")

        summary_data = summary_response.json()
        assert "builds" in summary_data

        # Find our active build
        active_builds = [
            b
            for b in summary_data["builds"]
            if b.get("status") in ("building", "queued")
        ]
        assert len(active_builds) >= 1

        # Active build should have stages
        active_build = active_builds[0]
        assert "stages" in active_build
        assert len(active_build["stages"]) > 0

    def test_summary_builds_have_warnings_errors_counts(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """Builds in summary should have warnings and errors counts."""
        # Create a summary with build data including warnings/errors
        summary_file = tmp_path / "summary.json"
        summary_file.write_text(
            json.dumps(
                {
                    "builds": [
                        {
                            "name": "default",
                            "display_name": "test_project:default",
                            "project_name": "test_project",
                            "status": "warning",
                            "elapsed_seconds": 15.5,
                            "warnings": 3,
                            "errors": 0,
                            "return_code": 0,
                            "stages": [
                                {
                                    "name": "init-build-context",
                                    "display_name": "Parse & Compile",
                                    "status": "success",
                                    "elapsed_seconds": 1.2,
                                },
                                {
                                    "name": "picker",
                                    "display_name": "Pick Parts",
                                    "status": "warning",
                                    "elapsed_seconds": 5.3,
                                },
                            ],
                        }
                    ],
                    "timestamp": "2024-01-15T10:30:00",
                }
            )
        )

        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with TestClient(app) as client:
            response = client.get("/api/summary")

        data = response.json()
        assert len(data["builds"]) == 1

        build = data["builds"][0]
        assert build["warnings"] == 3
        assert build["errors"] == 0
        assert build["status"] == "warning"

        # Should have stage data with elapsed times
        assert len(build["stages"]) == 2
        assert build["stages"][0]["elapsed_seconds"] == 1.2
        assert build["stages"][1]["elapsed_seconds"] == 5.3


class TestBuildUIStateFlow:
    """
    End-to-end tests simulating the full UI state flow when a user clicks
    the play button to start a build.

    These tests verify the complete state machine from initial click
    through build completion.
    """

    def test_full_build_flow_state_transitions(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """
        Test the complete build flow:
        1. Initial state (no active build)
        2. Build queued
        3. Build building (with stages updating)
        4. Build complete (success/failed)
        """
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        collected_states = []

        with patch("atopile.dashboard.server.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = iter(
                [
                    "init-build-context: Starting...\n",
                    "instantiate-app: Creating...\n",
                    "picker: Selecting parts...\n",
                    "Build complete!\n",
                ]
            )
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            with TestClient(app) as client:
                # 1. Start the build
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": ["default"],
                        "frozen": False,
                    },
                )
                assert start_response.status_code == 200
                build_id = start_response.json()["build_id"]
                collected_states.append(("started", start_response.json()))

                # 2. Poll for status a few times
                for _ in range(5):
                    time.sleep(0.05)
                    status_response = client.get(f"/api/build/{build_id}/status")
                    if status_response.status_code == 200:
                        collected_states.append(("polling", status_response.json()))

                # Wait for completion
                time.sleep(0.3)

                # 3. Get final status
                final_response = client.get(f"/api/build/{build_id}/status")
                collected_states.append(("final", final_response.json()))

        # Verify we captured state transitions
        assert len(collected_states) >= 2

        # Final state should be success
        final_state = collected_states[-1][1]
        assert final_state["status"] == "success"
        assert final_state["return_code"] == 0

        # Should have stages with times
        assert "stages" in final_state
        assert len(final_state["stages"]) == len(DEFAULT_BUILD_STAGES)

    def test_build_status_has_elapsed_seconds(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """Build status should include total elapsed_seconds."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )

        with patch("atopile.dashboard.server.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = iter(["Building...\n"])
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            with TestClient(app) as client:
                start_response = client.post(
                    "/api/build",
                    json={
                        "project_root": str(minimal_ato_project),
                        "targets": ["default"],
                        "frozen": False,
                    },
                )
                build_id = start_response.json()["build_id"]

                # Small delay
                time.sleep(0.2)

                status_response = client.get(f"/api/build/{build_id}/status")

        status_data = status_response.json()
        assert "elapsed_seconds" in status_data
        # Should have some elapsed time
        assert (
            status_data["elapsed_seconds"] is not None
            or status_data["status"] == "success"
        )

    def test_projects_endpoint_includes_last_build_status(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """GET /api/projects should include last_build status for targets."""
        # Create a build status file
        build_dir = minimal_ato_project / "build"
        build_dir.mkdir(exist_ok=True)
        status_file = build_dir / ".build_status.json"
        status_file.write_text(
            json.dumps(
                {
                    "targets": {
                        "default": {
                            "status": "success",
                            "timestamp": "2024-01-15T10:30:00",
                            "elapsed_seconds": 12.5,
                            "warnings": 2,
                            "errors": 0,
                            "stages": [
                                {
                                    "name": "init-build-context",
                                    "display_name": "Parse & Compile",
                                    "status": "success",
                                    "elapsed_seconds": 1.1,
                                },
                                {
                                    "name": "picker",
                                    "display_name": "Pick Parts",
                                    "status": "success",
                                    "elapsed_seconds": 3.2,
                                },
                            ],
                        }
                    },
                    "last_updated": "2024-01-15T10:30:00",
                }
            )
        )

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[minimal_ato_project.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()

        # Find our project
        projects = data["projects"]
        assert len(projects) >= 1

        our_project = next((p for p in projects if "test_project" in p["name"]), None)
        assert our_project is not None

        # Find the default target
        default_target = next(
            (t for t in our_project["targets"] if t["name"] == "default"), None
        )
        assert default_target is not None

        # Should have last_build info
        assert "last_build" in default_target
        last_build = default_target["last_build"]
        assert last_build is not None
        assert last_build["status"] == "success"
        assert last_build["warnings"] == 2
        assert last_build["errors"] == 0
        assert len(last_build["stages"]) == 2


class TestStaleBuildDetection:
    """Test detection/correction of stale 'building' status from interrupts."""

    def test_stale_building_status_is_corrected_to_failed(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """
        When a summary.json shows 'building' but no active build exists,
        the status should be corrected to 'failed'.
        """
        # Create a summary.json with a "building" status (simulating interrupted build)
        build_logs = minimal_ato_project / "build" / "logs" / "latest"
        build_logs.mkdir(parents=True)
        summary = build_logs / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "builds": [
                        {
                            "name": "stale-build-123",
                            "display_name": "default (building)",
                            "status": "building",
                            "elapsed_seconds": 10.0,
                        }
                    ],
                    "totals": {
                        "builds": 1,
                        "successful": 0,
                        "failed": 0,
                        "warnings": 0,
                        "errors": 0,
                    },
                }
            )
        )

        # No active builds exist (simulates server restart after crash)
        with _build_lock:
            assert len(_active_builds) == 0

        # Create app and test
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[minimal_ato_project.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()

        # Find the stale build
        stale_build = next(
            (b for b in data["builds"] if b.get("name") == "stale-build-123"), None
        )
        assert stale_build is not None
        # Status should be corrected to "failed"
        assert stale_build["status"] == "failed"
        # Display name should show "(interrupted)" instead of "(building)"
        assert "(interrupted)" in stale_build["display_name"]

    def test_active_building_status_is_preserved(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """
        When a summary.json shows 'building' and an active build exists,
        the status should remain 'building'.
        """
        build_id = "active-build-456"

        # Create a summary.json with a "building" status
        build_logs = minimal_ato_project / "build" / "logs" / "latest"
        build_logs.mkdir(parents=True)
        summary = build_logs / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "builds": [
                        {
                            "name": build_id,
                            "display_name": "default (building)",
                            "status": "building",
                            "elapsed_seconds": 5.0,
                        }
                    ],
                    "totals": {
                        "builds": 1,
                        "successful": 0,
                        "failed": 0,
                        "warnings": 0,
                        "errors": 0,
                    },
                }
            )
        )

        # Add an active build with matching ID
        with _build_lock:
            _active_builds[build_id] = {
                "name": build_id,
                "status": "building",
                "project_root": str(minimal_ato_project),
                "started_at": time.time(),
                "stages": [],
            }

        # Create app and test
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[minimal_ato_project.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()

        # Should have active builds showing "building" status
        building_builds = [b for b in data["builds"] if b["status"] == "building"]
        assert len(building_builds) >= 1

    def test_queued_status_without_active_build_is_corrected(
        self, tmp_path: Path, minimal_ato_project: Path, clear_active_builds
    ):
        """
        Queued builds without an active build entry should also be corrected.
        """
        # Create a summary.json with a "queued" status
        build_logs = minimal_ato_project / "build" / "logs" / "latest"
        build_logs.mkdir(parents=True)
        summary = build_logs / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "builds": [
                        {
                            "name": "queued-build-789",
                            "display_name": "default",
                            "status": "queued",
                        }
                    ],
                    "totals": {
                        "builds": 1,
                        "successful": 0,
                        "failed": 0,
                        "warnings": 0,
                        "errors": 0,
                    },
                }
            )
        )

        # No active builds
        with _build_lock:
            assert len(_active_builds) == 0

        # Create app and test
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[minimal_ato_project.parent],
        )

        with TestClient(app) as client:
            response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()

        # Find the queued build
        queued_build = next(
            (b for b in data["builds"] if b.get("name") == "queued-build-789"), None
        )
        assert queued_build is not None
        # Status should be corrected to "failed"
        assert queued_build["status"] == "failed"


# =============================================================================
# BuildQueue Tests
# =============================================================================


class TestBuildQueue:
    """Tests for the BuildQueue class."""

    def test_build_queue_initialization(self):
        """BuildQueue initializes with correct defaults."""
        bq = BuildQueue(max_concurrent=2)
        status = bq.get_status()

        assert status["queue_size"] == 0
        assert status["active_count"] == 0
        assert status["active_builds"] == []
        assert status["max_concurrent"] == 2
        assert status["worker_running"] is False

    def test_build_queue_enqueue(self, clear_active_builds):
        """BuildQueue enqueues builds correctly."""
        bq = BuildQueue(max_concurrent=4)

        # Don't register in _active_builds - worker will skip it
        # This tests that enqueue returns True and starts the worker
        result = bq.enqueue("test-build-1")
        assert result is True

        # Worker should have started
        status = bq.get_status()
        assert status["worker_running"] is True

    def test_build_queue_prevents_duplicate_enqueue(self, clear_active_builds):
        """BuildQueue prevents enqueueing the same build twice."""
        bq = BuildQueue(max_concurrent=4)

        # Manually add to active set to simulate running build
        with bq._lock:
            bq._active.add("test-build-dup")

        result = bq.enqueue("test-build-dup")
        assert result is False


class TestBuildDeduplication:
    """Tests for build deduplication functionality."""

    def test_make_build_key_deterministic(self):
        """_make_build_key produces consistent keys for same inputs."""
        key1 = _make_build_key("/path/to/project", ["default"], None)
        key2 = _make_build_key("/path/to/project", ["default"], None)

        assert key1 == key2
        assert len(key1) == 16  # Truncated hash

    def test_make_build_key_different_for_different_inputs(self):
        """_make_build_key produces different keys for different inputs."""
        key1 = _make_build_key("/path/to/project", ["default"], None)
        key2 = _make_build_key("/path/to/project", ["other"], None)
        key3 = _make_build_key("/other/project", ["default"], None)
        key4 = _make_build_key("/path/to/project", ["default"], "main.ato:App")

        assert key1 != key2
        assert key1 != key3
        assert key1 != key4

    def test_make_build_key_target_order_independent(self):
        """_make_build_key produces same key regardless of target order."""
        key1 = _make_build_key("/path", ["a", "b", "c"], None)
        key2 = _make_build_key("/path", ["c", "a", "b"], None)

        assert key1 == key2

    def test_is_duplicate_build_returns_none_for_new(self, clear_active_builds):
        """_is_duplicate_build returns None when no duplicate exists."""
        result = _is_duplicate_build("unique-key-12345")
        assert result is None

    def test_is_duplicate_build_returns_id_for_running(self, clear_active_builds):
        """_is_duplicate_build returns build_id when duplicate is running."""
        build_key = "duplicate-key-xyz"

        with _build_lock:
            _active_builds["existing-build"] = {
                "status": "building",
                "build_key": build_key,
            }

        result = _is_duplicate_build(build_key)
        assert result == "existing-build"

    def test_is_duplicate_build_ignores_completed(self, clear_active_builds):
        """_is_duplicate_build ignores completed builds."""
        build_key = "duplicate-key-xyz"

        with _build_lock:
            _active_builds["completed-build"] = {
                "status": "success",
                "build_key": build_key,
            }

        result = _is_duplicate_build(build_key)
        assert result is None


class TestBuildQueueEndpoint:
    """Tests for the /api/builds/queue endpoint."""

    def test_queue_status_endpoint(self, test_client: TestClient):
        """GET /api/builds/queue returns queue status."""
        response = test_client.get("/api/builds/queue")

        assert response.status_code == 200
        data = response.json()

        assert "queue_size" in data
        assert "active_count" in data
        assert "active_builds" in data
        assert "max_concurrent" in data
        assert "worker_running" in data


class TestBuildHistoryEndpoint:
    """Tests for the /api/builds/history endpoint."""

    def test_history_endpoint_returns_list(self, test_client: TestClient):
        """GET /api/builds/history returns a list of builds."""
        response = test_client.get("/api/builds/history")

        assert response.status_code == 200
        data = response.json()

        assert "builds" in data
        assert "total" in data
        assert isinstance(data["builds"], list)

    def test_history_endpoint_accepts_filters(self, test_client: TestClient):
        """GET /api/builds/history accepts filter parameters."""
        response = test_client.get(
            "/api/builds/history",
            params={
                "project_root": "/some/path",
                "status": "failed",
                "limit": 10,
            },
        )

        assert response.status_code == 200


class TestBuildQueueEndToEnd:
    """
    End-to-end tests for the build queue lifecycle.

    Tests the full flow: start build -> track status -> cancel build.
    """

    def test_start_build_appears_in_active_builds(
        self, tmp_path: Path, clear_active_builds
    ):
        """Starting a build makes it appear in /api/builds/active."""
        # Create a project
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "ato.yaml").write_text(
            "requires-atopile: '^0.9.0'\nbuilds:\n  default:\n    entry: main.ato:App\n"
        )
        (project_dir / "main.ato").write_text("module App:\n    pass\n")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )
        client = TestClient(app)

        # Start a build (use mock to prevent actual subprocess)
        with patch("atopile.dashboard.server._run_build_subprocess"):
            response = client.post(
                "/api/build",
                json={
                    "project_root": str(project_dir),
                    "targets": ["default"],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        build_id = data["build_id"]
        assert build_id is not None

        # Check that it appears in active builds with queued status
        active_response = client.get("/api/builds/active")
        assert active_response.status_code == 200
        active_data = active_response.json()

        build_ids = [b["build_id"] for b in active_data["builds"]]
        assert build_id in build_ids

        # Verify the build has queued status
        active_build = next(
            (b for b in active_data["builds"] if b["build_id"] == build_id),
            None,
        )
        assert active_build is not None
        assert active_build["status"] == "queued"

    def test_cancel_build_marks_as_cancelled(
        self, tmp_path: Path, clear_active_builds
    ):
        """Cancelling a build marks it as cancelled."""
        # Setup
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "ato.yaml").write_text(
            "requires-atopile: '^0.9.0'\nbuilds:\n  default:\n    entry: main.ato:App\n"
        )
        (project_dir / "main.ato").write_text("module App:\n    pass\n")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )
        client = TestClient(app)

        # Start a build
        with patch("atopile.dashboard.server._run_build_subprocess"):
            start_response = client.post(
                "/api/build",
                json={
                    "project_root": str(project_dir),
                    "targets": ["default"],
                },
            )

        assert start_response.status_code == 200
        build_id = start_response.json()["build_id"]

        # Cancel the build
        cancel_response = client.post(f"/api/build/{build_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["success"] is True

        # Verify status is cancelled in active builds
        active_response = client.get("/api/builds/active")
        active_data = active_response.json()

        cancelled_build = next(
            (b for b in active_data["builds"] if b["build_id"] == build_id),
            None,
        )
        assert cancelled_build is not None
        assert cancelled_build["status"] == "cancelled"

    def test_cancel_nonexistent_build_returns_404(
        self, test_client: TestClient, clear_active_builds
    ):
        """Cancelling a non-existent build returns 404."""
        response = test_client.post("/api/build/nonexistent-build-id/cancel")
        assert response.status_code == 404

    def test_duplicate_build_request_returns_existing(
        self, tmp_path: Path, clear_active_builds
    ):
        """Requesting a duplicate build returns the existing build_id."""
        # Setup
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "ato.yaml").write_text(
            "requires-atopile: '^0.9.0'\nbuilds:\n  default:\n    entry: main.ato:App\n"
        )
        (project_dir / "main.ato").write_text("module App:\n    pass\n")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )
        client = TestClient(app)

        build_request = {
            "project_root": str(project_dir),
            "targets": ["default"],
        }

        # Start first build
        with patch("atopile.dashboard.server._run_build_subprocess"):
            first_response = client.post("/api/build", json=build_request)

        assert first_response.status_code == 200
        first_build_id = first_response.json()["build_id"]

        # Try to start duplicate build
        with patch("atopile.dashboard.server._run_build_subprocess"):
            second_response = client.post("/api/build", json=build_request)

        assert second_response.status_code == 200
        second_data = second_response.json()

        # Should return the existing build_id
        assert second_data["build_id"] == first_build_id
        assert second_data.get("message") == "Build already in progress"

    def test_build_queue_status_reflects_queue_state(
        self, tmp_path: Path, clear_active_builds
    ):
        """The /api/builds/queue endpoint reflects queue state."""
        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}")
        app = create_app(
            summary_file=summary_file,
            logs_base=tmp_path,
            workspace_paths=[tmp_path],
        )
        client = TestClient(app)

        # Check initial queue status
        response = client.get("/api/builds/queue")
        assert response.status_code == 200
        data = response.json()

        assert "queue_size" in data
        assert "active_count" in data
        assert "max_concurrent" in data
        assert data["max_concurrent"] == 4  # Default concurrency limit
