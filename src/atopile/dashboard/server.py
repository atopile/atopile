"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import json
import logging
import socket
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

log = logging.getLogger(__name__)


def create_app(
    summary_file: Optional[Path] = None, logs_base: Optional[Path] = None
) -> FastAPI:
    """
    Create the FastAPI application with API routes for the dashboard.

    Args:
        summary_file: Path to summary.json file.
        logs_base: Base directory for logs.
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

    # Track the current summary file
    state = {"summary_file": summary_file, "logs_base": logs_base}

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

    @app.get("/api/logs/query")
    async def query_logs(
        build_id: Optional[str] = Query(None, description="Filter by build ID"),
        project_path: Optional[str] = Query(None, description="Filter by project path"),
        target: Optional[str] = Query(None, description="Filter by build target"),
        stage: Optional[str] = Query(None, description="Filter by build stage"),
        level: Optional[str] = Query(
            None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"
        ),
        audience: Optional[str] = Query(
            None, description="Filter by audience (user, developer, agent)"
        ),
        limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Result offset for pagination"),
    ):
        """
        Query logs from the central SQLite database with optional filters.

        Returns structured log entries from the central build_logs.db database.
        """
        from atopile.logging import get_central_log_db

        try:
            db_path = get_central_log_db()
            if not db_path.exists():
                return {"logs": [], "total": 0, "builds": []}

            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row

            # Build query with filters
            conditions = []
            params: list = []

            if build_id:
                conditions.append("l.build_id = ?")
                params.append(build_id)
            if project_path:
                conditions.append("b.project_path = ?")
                params.append(project_path)
            if target:
                conditions.append("b.target = ?")
                params.append(target)
            if stage:
                conditions.append("l.stage = ?")
                params.append(stage)
            if level:
                conditions.append("l.level = ?")
                params.append(level.upper())
            if audience:
                conditions.append("l.audience = ?")
                params.append(audience.lower())

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            # Query logs with build info joined
            query = f"""
                SELECT l.id, l.build_id, l.timestamp, l.stage, l.level, l.audience,
                       l.message, l.ato_traceback, l.python_traceback, l.objects,
                       b.project_path, b.target, b.timestamp as build_timestamp
                FROM logs l
                JOIN builds b ON l.build_id = b.build_id
                {where_clause}
                ORDER BY l.id DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            logs = []
            for row in rows:
                log_entry = {
                    "id": row["id"],
                    "build_id": row["build_id"],
                    "timestamp": row["timestamp"],
                    "stage": row["stage"],
                    "level": row["level"],
                    "audience": row["audience"],
                    "message": row["message"],
                    "ato_traceback": row["ato_traceback"],
                    "python_traceback": row["python_traceback"],
                    "objects": json.loads(row["objects"]) if row["objects"] else None,
                    "project_path": row["project_path"],
                    "target": row["target"],
                    "build_timestamp": row["build_timestamp"],
                }
                logs.append(log_entry)

            # Also get list of available builds
            builds_query = """
                SELECT build_id, project_path, target, timestamp, created_at
                FROM builds
                ORDER BY created_at DESC
                LIMIT 100
            """
            builds_cursor = conn.execute(builds_query)
            builds = [
                {
                    "build_id": row["build_id"],
                    "project_path": row["project_path"],
                    "target": row["target"],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"],
                }
                for row in builds_cursor.fetchall()
            ]

            conn.close()
            return {"logs": logs, "total": len(logs), "builds": builds}

        except sqlite3.Error as e:
            log.warning(f"Error reading logs from central database: {e}")
            return {"logs": [], "total": 0, "builds": [], "error": str(e)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/builds")
    async def list_builds(
        project_path: Optional[str] = Query(None, description="Filter by project path"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    ):
        """
        List all builds from the central database.

        Returns build metadata including project_path, target, and timestamps.
        """
        from atopile.logging import get_central_log_db

        try:
            db_path = get_central_log_db()
            if not db_path.exists():
                return {"builds": []}

            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row

            if project_path:
                query = """
                    SELECT build_id, project_path, target, timestamp, created_at
                    FROM builds
                    WHERE project_path = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                cursor = conn.execute(query, [project_path, limit])
            else:
                query = """
                    SELECT build_id, project_path, target, timestamp, created_at
                    FROM builds
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                cursor = conn.execute(query, [limit])

            builds = [
                {
                    "build_id": row["build_id"],
                    "project_path": row["project_path"],
                    "target": row["target"],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"],
                }
                for row in cursor.fetchall()
            ]

            conn.close()
            return {"builds": builds}

        except sqlite3.Error as e:
            log.warning(f"Error reading builds from central database: {e}")
            return {"builds": [], "error": str(e)}
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
