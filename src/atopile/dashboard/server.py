"""
FastAPI server for the build dashboard.

Serves the React dashboard and provides API endpoints for build data.
"""

import json
import logging
import socket
import threading
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import WEB_DIST_PATH, is_dashboard_built

log = logging.getLogger(__name__)


def create_app(summary_file: Path, logs_base: Path) -> FastAPI:
    """Create the FastAPI application with routes for the dashboard."""
    app = FastAPI(title="atopile Build Dashboard")

    @app.get("/api/summary")
    async def get_summary():
        """Return the current build summary."""
        if not summary_file.exists():
            return {"error": "No summary file found", "builds": [], "totals": {}}
        try:
            return json.loads(summary_file.read_text())
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/logs/{build_name}/{log_filename}")
    async def get_log_file(build_name: str, log_filename: str):
        """Return a specific log file by filename."""
        try:
            if not summary_file.exists():
                raise HTTPException(status_code=404, detail="No summary file found")

            summary = json.loads(summary_file.read_text())

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

    # Serve static files from the dist directory
    if is_dashboard_built():
        # Mount assets directory
        assets_dir = WEB_DIST_PATH / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/")
        async def serve_index():
            """Serve the main dashboard page."""
            index_path = WEB_DIST_PATH / "index.html"
            if index_path.exists():
                return FileResponse(index_path, media_type="text/html")
            return HTMLResponse("<h1>Dashboard not built</h1>", status_code=503)

        @app.get("/{path:path}")
        async def serve_static(path: str):
            """Serve static files from dist directory."""
            file_path = WEB_DIST_PATH / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            # Fall back to index.html for SPA routing
            index_path = WEB_DIST_PATH / "index.html"
            if index_path.exists():
                return FileResponse(index_path, media_type="text/html")
            raise HTTPException(status_code=404, detail="File not found")

    else:

        @app.get("/")
        async def dashboard_not_built():
            """Return error when dashboard is not built."""
            return HTMLResponse(
                """
                <html>
                <head><title>Dashboard Not Built</title></head>
                <body style="font-family: sans-serif; padding: 2rem;">
                    <h1>Dashboard Not Built</h1>
                    <p>The dashboard web app has not been built.</p>
                    <p>Run <code>npm ci && npm run build</code> in the
                       <code>src/atopile/dashboard/web</code> directory.</p>
                    <hr>
                    <p>API endpoints are still available:</p>
                    <ul>
                        <li><a href="/api/summary">/api/summary</a> - Build summary JSON</li>
                    </ul>
                </body>
                </html>
                """,
                status_code=503,
            )

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
