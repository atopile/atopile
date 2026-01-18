"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)


class BuildRequest(BaseModel):
    """Request to start a new build."""

    project_root: str
    targets: list[str]


class BuildResponse(BaseModel):
    """Response after starting a build."""

    build_id: str
    status: str


class BuildManager:
    """Manages build processes started via the server API."""

    def __init__(self, project_root: Path, targets: list[str], build_id: str):
        self.project_root = project_root
        self.targets = targets
        self.build_id = build_id
        self.process: Optional[subprocess.Popen] = None
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.return_code: Optional[int] = None

    def start(self) -> None:
        """Start the build subprocess."""
        # Build the command - run ato build (without --ui since we use the extension's server)
        cmd = [
            sys.executable,
            "-m",
            "atopile",
            "build",
        ]

        # Add each target as a --build flag
        for target in self.targets:
            cmd.extend(["-b", target])

        # Copy environment
        env = os.environ.copy()

        self.start_time = time.time()
        self.process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def poll(self) -> Optional[int]:
        """Check if process has finished. Returns exit code or None if still running."""
        if self.process is None:
            return None

        ret = self.process.poll()
        if ret is not None and self.return_code is None:
            self.return_code = ret
            self.end_time = time.time()
        return ret

    @property
    def is_running(self) -> bool:
        """Check if build is still running."""
        return self.process is not None and self.return_code is None


# Global state for builds managed by the server
_active_builds: dict[str, BuildManager] = {}
_build_lock = threading.Lock()


def create_app(
    summary_file: Optional[Path] = None, logs_base: Optional[Path] = None
) -> FastAPI:
    """
    Create the FastAPI application with API routes for the dashboard.

    Args:
        summary_file: Path to summary.json file.
            If None, server runs in standalone mode.
        logs_base: Base directory for logs.
            If None, server runs in standalone mode.
    """
    app = FastAPI(title="atopile Build Server")

    # Add CORS middleware to allow requests from VS Code webview
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Webviews use vscode-webview:// origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Track the current summary file (can be updated by build endpoint)
    state = {"summary_file": summary_file, "logs_base": logs_base}

    @app.post("/api/build")
    async def start_build(request: BuildRequest) -> BuildResponse:
        """Start a new build with specified targets."""
        build_id = str(uuid.uuid4())[:8]

        project_root = Path(request.project_root)
        if not project_root.exists():
            raise HTTPException(
                status_code=400, detail=f"Project root not found: {project_root}"
            )

        # Update state to point to this project's summary file
        # The build will write to build/logs/latest/summary.json
        logs_base = project_root / "build" / "logs"
        latest_summary = logs_base / "latest" / "summary.json"
        state["summary_file"] = latest_summary
        state["logs_base"] = logs_base
        log.info("Updated summary_file to %s", latest_summary)

        # Create BuildManager
        manager = BuildManager(
            project_root=project_root,
            targets=request.targets,
            build_id=build_id,
        )

        with _build_lock:
            _active_builds[build_id] = manager

        # Start build in background thread
        def run_build():
            manager.start()
            # Wait for completion
            while manager.is_running:
                manager.poll()
                time.sleep(0.5)
            log.info(
                "Build %s completed with code %s", build_id, manager.return_code
            )

        thread = threading.Thread(target=run_build, daemon=True)
        thread.start()

        log.info(
            "Started build %s for targets %s in %s",
            build_id,
            request.targets,
            project_root,
        )

        return BuildResponse(build_id=build_id, status="started")

    @app.get("/api/builds")
    async def list_builds():
        """List all active and recent builds."""
        with _build_lock:
            builds = []
            for build_id, manager in _active_builds.items():
                manager.poll()  # Update status
                builds.append(
                    {
                        "build_id": build_id,
                        "project_root": str(manager.project_root),
                        "targets": manager.targets,
                        "is_running": manager.is_running,
                        "return_code": manager.return_code,
                        "start_time": manager.start_time,
                        "end_time": manager.end_time,
                    }
                )
            return {"builds": builds}

    @app.get("/api/summary")
    async def get_summary():
        """Return the current build summary."""
        summary_path = state["summary_file"]
        if summary_path is None or not summary_path.exists():
            return {"error": "No summary file found", "builds": [], "totals": {}}
        try:
            return json.loads(summary_path.read_text())
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/logs/{build_name}/{log_filename}")
    async def get_log_file(build_name: str, log_filename: str):
        """Return a specific log file by filename."""
        try:
            summary_path = state["summary_file"]
            if summary_path is None or not summary_path.exists():
                raise HTTPException(status_code=404, detail="No summary file found")

            summary = json.loads(summary_path.read_text())

            # Find the build and get its log_dir
            log_dir = None
            for build in summary.get("builds", []):
                if build.get("name") == build_name or build.get(
                    "display_name"
                ) == build_name:
                    log_dir = build.get("log_dir")
                    break

            if not log_dir:
                raise HTTPException(
                    status_code=404, detail=f"Build not found: {build_name}"
                )

            # Construct the log file path
            log_file = Path(log_dir) / log_filename

            if not log_file.exists():
                raise HTTPException(
                    status_code=404, detail=f"Log file not found: {log_filename}"
                )

            return PlainTextResponse(
                content=log_file.read_text(),
                media_type="text/plain",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


def find_free_port() -> int:
    """Find a free port to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class DashboardServer:
    """Manages the dashboard server lifecycle."""

    def __init__(self, summary_file: Path, logs_base: Path, port: Optional[int] = None):
        self.summary_file = summary_file
        self.logs_base = logs_base
        self.port = port or find_free_port()
        self.app = create_app(summary_file, logs_base)
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """Get the dashboard URL."""
        return f"http://localhost:{self.port}"

    def start(self) -> None:
        """Start the server in a background thread."""
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)

        def run():
            self._server.run()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

        # Wait for server to be ready
        import time

        for _ in range(50):  # Wait up to 5 seconds
            if self._server.started:
                break
            time.sleep(0.1)

    def shutdown(self) -> None:
        """Shutdown the server."""
        if self._server:
            self._server.should_exit = True
            if self._thread:
                self._thread.join(timeout=2.0)


def start_dashboard_server(
    summary_file: Path, logs_base: Optional[Path] = None, port: Optional[int] = None
) -> tuple[DashboardServer, str]:
    """
    Start the dashboard server.

    Args:
        summary_file: Path to the summary.json file
        logs_base: Base directory for logs (defaults to summary_file's parent)
        port: Port to use (defaults to a free port)

    Returns:
        Tuple of (DashboardServer, url)
    """
    if logs_base is None:
        logs_base = summary_file.parent

    server = DashboardServer(summary_file, logs_base, port)
    server.start()
    return server, server.url


def run_server(host: str = "127.0.0.1", port: int = 8501) -> None:
    """
    Run the ato server (blocking).

    This is the entry point for `ato server start`. The server provides:
    - POST /api/build: Start a new build
    - GET /api/builds: List active builds
    - GET /api/summary: Get build summary
    - GET /api/logs/{build}/{file}: Get log file content

    The React frontend is served by VS Code webview, not this server.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="warning")
