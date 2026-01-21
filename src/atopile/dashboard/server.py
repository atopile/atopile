"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data and build execution.
Uses WebSockets for real-time push updates instead of polling.
"""

import asyncio
import json
import logging
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

log = logging.getLogger(__name__)

# Log level ordering for filtering
LOG_LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "ALERT": 4}


@dataclass
class LogSubscription:
    """Per-client log subscription settings."""

    project_path: str
    build_id: str  # Required - must filter by specific build
    target: Optional[str] = None  # For reference
    min_level: str = "INFO"  # Minimum level to include
    stages: list[str] = field(default_factory=list)  # Empty = all stages
    last_log_id: int = 0  # For incremental updates


@dataclass
class ClientState:
    """State for a single WebSocket client."""

    client_id: str
    websocket: WebSocket
    subscription: Optional[LogSubscription] = None
    streaming_task: Optional[asyncio.Task] = None


class ConnectionManager:
    """Manages WebSocket connections with per-client state and log subscriptions."""

    def __init__(self):
        self._clients: dict[str, ClientState] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a WebSocket connection and return a client ID."""
        await websocket.accept()
        client_id = str(uuid.uuid4())[:8]
        client = ClientState(client_id=client_id, websocket=websocket)
        async with self._lock:
            self._clients[client_id] = client
        log.info(f"WebSocket client connected: {client_id} (total: {len(self._clients)})")
        return client_id

    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection and cancel any streaming task."""
        async with self._lock:
            client = self._clients.pop(client_id, None)
            if client and client.streaming_task:
                client.streaming_task.cancel()
                try:
                    await client.streaming_task
                except asyncio.CancelledError:
                    pass
        log.info(f"WebSocket client disconnected: {client_id} (total: {len(self._clients)})")

    async def get_client(self, client_id: str) -> Optional[ClientState]:
        """Get client state by ID."""
        async with self._lock:
            return self._clients.get(client_id)

    async def set_subscription(
        self, client_id: str, subscription: Optional[LogSubscription]
    ) -> None:
        """Set the log subscription for a client."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client:
                # Cancel existing streaming task
                if client.streaming_task:
                    client.streaming_task.cancel()
                    try:
                        await client.streaming_task
                    except asyncio.CancelledError:
                        pass
                    client.streaming_task = None
                client.subscription = subscription

    async def set_streaming_task(self, client_id: str, task: asyncio.Task) -> None:
        """Set the streaming task for a client."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client:
                client.streaming_task = task

    async def send_to_client(self, client_id: str, message: dict) -> bool:
        """Send a message to a specific client. Returns False if client disconnected."""
        async with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return False
            try:
                await client.websocket.send_json(message)
                return True
            except Exception:
                return False

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        async with self._lock:
            if not self._clients:
                return
            log.info(
                f"WebSocket broadcast: {message.get('type')} to {len(self._clients)} clients"
            )
            dead_clients: list[str] = []
            for client_id, client in self._clients.items():
                try:
                    await client.websocket.send_json(message)
                except Exception:
                    dead_clients.append(client_id)
            for client_id in dead_clients:
                self._clients.pop(client_id, None)

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)


# Global WebSocket connection manager and event loop reference
_ws_manager = ConnectionManager()
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def _sync_broadcast(event_type: str, data: dict) -> None:
    """Thread-safe broadcast for use from sync context (e.g., monitor_build thread)."""
    global _event_loop
    if _event_loop is None:
        log.warning("Event loop not set, cannot broadcast")
        return
    message = {"type": event_type, "data": data}
    asyncio.run_coroutine_threadsafe(_ws_manager.broadcast(message), _event_loop)


def _get_project_summary(project_path: str) -> dict:
    """
    Get the build summary for a project.

    Returns a summary dict with builds, totals, and timestamp.
    This is the same data as the /api/summary endpoint but callable from sync context.
    """
    empty_response = {
        "timestamp": None,
        "totals": {
            "builds": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0,
            "errors": 0,
        },
        "builds": [],
        "project_path": project_path,
    }

    project_root = Path(project_path)
    if not project_root.exists():
        return empty_response

    builds_dir = project_root / "build" / "builds"
    if not builds_dir.exists():
        return empty_response

    builds = []
    for summary_file in builds_dir.glob("*/build_summary.json"):
        try:
            build_data = json.loads(summary_file.read_text())
            build_data["project_path"] = str(project_root)
            builds.append(build_data)
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Failed to read build summary {summary_file}: {e}")
            continue

    total = len(builds)
    success = sum(1 for b in builds if b.get("status") in ("success", "warning"))
    failed = sum(1 for b in builds if b.get("status") == "failed")
    warnings = sum(b.get("warnings", 0) for b in builds)
    errors = sum(b.get("errors", 0) for b in builds)

    timestamps = [b.get("timestamp") for b in builds if b.get("timestamp")]
    timestamp = max(timestamps) if timestamps else None

    return {
        "timestamp": timestamp,
        "totals": {
            "builds": total,
            "successful": success,
            "failed": failed,
            "warnings": warnings,
            "errors": errors,
        },
        "builds": builds,
        "project_path": project_path,
    }


def _get_latest_build_id(project_path: str, target: str) -> Optional[tuple[str, str]]:
    """
    Get the latest build_id and completion timestamp for a project/target.

    Returns (build_id, timestamp) or None if no builds found.
    """
    from atopile.logging import get_central_log_db

    try:
        db_path = get_central_log_db()
        if not db_path.exists():
            return None

        conn = sqlite3.connect(str(db_path), timeout=2.0)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT build_id, timestamp
            FROM builds
            WHERE project_path = ? AND target = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_path, target),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return (row["build_id"], row["timestamp"])
        return None

    except sqlite3.Error as e:
        log.warning(f"Error getting latest build_id: {e}")
        return None


def _query_filtered_logs(
    build_id: str,
    last_log_id: int,
    min_level: str = "INFO",
    stages: Optional[list[str]] = None,
    limit: int = 100,
) -> tuple[list[dict], int]:
    """
    Query logs from the database for a specific build_id with filters applied.

    Returns (list of log entries, new last_log_id).
    """
    from atopile.logging import get_central_log_db

    try:
        db_path = get_central_log_db()
        if not db_path.exists():
            return [], last_log_id

        conn = sqlite3.connect(str(db_path), timeout=2.0)
        conn.row_factory = sqlite3.Row

        # Build query with filters - always filter by build_id
        conditions = ["l.id > ?", "l.build_id = ?"]
        params: list = [last_log_id, build_id]

        # Filter by minimum log level
        min_level_order = LOG_LEVEL_ORDER.get(min_level.upper(), 1)
        level_placeholders = []
        for level, order in LOG_LEVEL_ORDER.items():
            if order >= min_level_order:
                level_placeholders.append("?")
                params.append(level)
        if level_placeholders:
            conditions.append(f"l.level IN ({','.join(level_placeholders)})")

        # Filter by stages if specified
        if stages:
            stage_placeholders = ",".join("?" * len(stages))
            conditions.append(f"l.stage IN ({stage_placeholders})")
            params.extend(stages)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT l.id, l.build_id, l.timestamp, l.stage, l.level, l.audience,
                   l.message, l.ato_traceback, l.python_traceback,
                   b.project_path, b.target, b.timestamp as build_timestamp
            FROM logs l
            JOIN builds b ON l.build_id = b.build_id
            WHERE {where_clause}
            ORDER BY l.id ASC
            LIMIT ?
        """
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        logs = []
        new_last_id = last_log_id
        for row in rows:
            new_last_id = max(new_last_id, row["id"])
            logs.append(
                {
                    "id": row["id"],
                    "build_id": row["build_id"],
                    "timestamp": row["timestamp"],
                    "stage": row["stage"],
                    "level": row["level"],
                    "message": row["message"],
                    "ato_traceback": row["ato_traceback"],
                    "python_traceback": row["python_traceback"],
                    "project_path": row["project_path"],
                    "target": row["target"],
                }
            )

        conn.close()
        return logs, new_last_id

    except sqlite3.Error as e:
        log.warning(f"Error querying logs: {e}")
        return [], last_log_id
    except Exception as e:
        log.warning(f"Unexpected error querying logs: {e}")
        return [], last_log_id


async def _stream_logs_to_client(client_id: str, subscription: LogSubscription) -> None:
    """
    Stream logs to a specific client based on their subscription.

    Uses fast polling (50ms) with smart batching:
    - Send when buffer has 500+ entries, OR
    - Send when 500ms elapsed since last send (if buffer non-empty)
    Whichever comes first.

    Filters by build_id (required), level, and stage.
    """
    log.info(
        f"Starting log stream for client {client_id}: "
        f"build_id={subscription.build_id}, target={subscription.target}, "
        f"min_level={subscription.min_level}, stages={subscription.stages}"
    )

    last_log_id = subscription.last_log_id
    poll_interval = 0.05  # 50ms - fast polling for push-like feel
    max_batch_interval = 0.5  # 500ms max time between sends
    max_batch_size = 500  # Send immediately if we have this many

    log_buffer: list[dict] = []
    last_send_time = time.time()

    try:
        while True:
            # Query for new logs filtered by build_id, level, and stage
            logs, new_last_id = _query_filtered_logs(
                build_id=subscription.build_id,
                last_log_id=last_log_id,
                min_level=subscription.min_level,
                stages=subscription.stages if subscription.stages else None,
                limit=100,  # Small batches for responsiveness
            )

            if logs:
                last_log_id = new_last_id
                log_buffer.extend(logs)

            # Determine if we should send
            time_since_send = time.time() - last_send_time
            should_send = (
                len(log_buffer) >= max_batch_size  # Buffer full
                or (log_buffer and time_since_send >= max_batch_interval)  # Time elapsed
            )

            if should_send and log_buffer:
                # Update subscription's last_log_id
                client = await _ws_manager.get_client(client_id)
                if client and client.subscription:
                    client.subscription.last_log_id = last_log_id

                # Send batch to client
                success = await _ws_manager.send_to_client(
                    client_id,
                    {
                        "type": "log_batch",
                        "data": {
                            "logs": log_buffer,
                            "last_id": last_log_id,
                            "count": len(log_buffer),
                        },
                    },
                )
                if not success:
                    log.info(f"Client {client_id} disconnected, stopping log stream")
                    break

                log.debug(f"Sent {len(log_buffer)} logs to client {client_id}")
                log_buffer = []
                last_send_time = time.time()

            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        log.info(f"Log stream cancelled for client {client_id}")
        raise
    except Exception as e:
        log.error(f"Error in log stream for client {client_id}: {e}")


class BuildRequest(BaseModel):
    """Request body for /build endpoint."""

    project_path: str
    targets: list[str]


class BuildProcess:
    """Tracks a running build subprocess."""

    def __init__(
        self,
        build_id: str,
        project_path: str,
        targets: list[str],
        process: subprocess.Popen,
    ):
        self.build_id = build_id
        self.project_path = project_path
        self.targets = targets
        self.process = process
        self.started_at = time.time()

    @property
    def is_running(self) -> bool:
        return self.process.poll() is None

    @property
    def return_code(self) -> Optional[int]:
        return self.process.poll()

    def terminate(self) -> None:
        if self.is_running:
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()


def _find_ato_binary() -> Optional[str]:
    """Find the ato binary in common locations."""
    # Try to find ato in PATH
    ato_path = shutil.which("ato")
    if ato_path:
        return ato_path

    # Try common locations
    common_paths = [
        Path.home() / ".local" / "bin" / "ato",
        Path("/usr/local/bin/ato"),
        Path("/opt/homebrew/bin/ato"),
    ]
    for p in common_paths:
        if p.exists():
            return str(p)

    return None


def create_app(
    project_root: Optional[Path] = None,
) -> FastAPI:
    """
    Create the FastAPI application with API routes for the dashboard.

    Args:
        project_root: Root directory of the project (where ato.yaml is located).
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

    # Server state
    state: dict = {
        "project_root": project_root,
        "build_processes": {},  # build_id -> BuildProcess
        "ato_binary": None,  # Path to ato binary (set via /config endpoint)
    }

    @app.get("/api/status")
    async def get_status():
        """Return server status and running builds."""
        running_builds = []
        completed_builds = []

        for build_id, bp in list(state["build_processes"].items()):
            build_info = {
                "build_id": build_id,
                "project_path": bp.project_path,
                "targets": bp.targets,
                "started_at": bp.started_at,
                "elapsed_seconds": time.time() - bp.started_at,
            }
            if bp.is_running:
                running_builds.append(build_info)
            else:
                build_info["return_code"] = bp.return_code
                completed_builds.append(build_info)
                # Clean up old completed builds (keep last 10)
                if len(completed_builds) > 10:
                    del state["build_processes"][build_id]

        return {
            "status": "running",
            "ato_binary": state["ato_binary"],
            "running_builds": running_builds,
            "completed_builds": completed_builds[-10:],
            "ws_clients": _ws_manager.client_count,
        }

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time updates.

        Clients can send messages to control log streaming:
        - subscribe_logs: Start streaming logs with filter settings
        - update_filters: Change filter settings (resets log stream)
        - unsubscribe_logs: Stop streaming logs

        Server sends:
        - connected: Initial connection confirmation with client_id
        - build_started: A build has started
        - build_completed: A build has finished
        - summary_updated: Build summary has changed
        - log_batch: Batch of log entries
        """
        global _event_loop
        _event_loop = asyncio.get_running_loop()

        client_id = await _ws_manager.connect(websocket)
        try:
            # Send initial connection confirmation
            await websocket.send_json(
                {"type": "connected", "data": {"client_id": client_id}}
            )

            # Handle incoming messages
            while True:
                try:
                    raw_message = await websocket.receive_text()
                    try:
                        message = json.loads(raw_message)
                        msg_type = message.get("type")
                        msg_data = message.get("data", {})

                        if msg_type == "subscribe_logs":
                            # Get build_id - either from client or look up latest
                            project_path = msg_data.get("project_path", "")
                            target = msg_data.get("target", "")
                            build_id = msg_data.get("build_id")
                            build_timestamp = None

                            if not build_id:
                                # Look up the latest build_id for this target
                                result = _get_latest_build_id(project_path, target)
                                if result:
                                    build_id, build_timestamp = result
                                else:
                                    # No builds found - send error
                                    await websocket.send_json(
                                        {
                                            "type": "subscription_error",
                                            "data": {
                                                "error": "no_builds",
                                                "message": f"No builds found for {target}",
                                            },
                                        }
                                    )
                                    log.warning(
                                        f"Client {client_id} subscribe failed: no builds for {target}"
                                    )
                                    continue

                            # Create subscription with build_id
                            subscription = LogSubscription(
                                project_path=project_path,
                                build_id=build_id,
                                target=target,
                                min_level=msg_data.get("min_level", "INFO"),
                                stages=msg_data.get("stages", []),
                                last_log_id=0,  # Always start from beginning for new subscription
                            )
                            await _ws_manager.set_subscription(client_id, subscription)

                            # Start streaming task
                            task = asyncio.create_task(
                                _stream_logs_to_client(client_id, subscription)
                            )
                            await _ws_manager.set_streaming_task(client_id, task)

                            # Send confirmation with build_id
                            await websocket.send_json(
                                {
                                    "type": "subscribed",
                                    "data": {
                                        "build_id": build_id,
                                        "build_timestamp": build_timestamp,
                                        "project_path": subscription.project_path,
                                        "target": subscription.target,
                                        "min_level": subscription.min_level,
                                        "stages": subscription.stages,
                                    },
                                }
                            )
                            log.info(
                                f"Client {client_id} subscribed to logs: "
                                f"build_id={build_id}, target={target}"
                            )

                        elif msg_type == "update_filters":
                            # Update filter settings - this resets the stream
                            client = await _ws_manager.get_client(client_id)
                            if client and client.subscription:
                                # Update filter settings
                                if "min_level" in msg_data:
                                    client.subscription.min_level = msg_data["min_level"]
                                if "stages" in msg_data:
                                    client.subscription.stages = msg_data["stages"]
                                if "target" in msg_data:
                                    client.subscription.target = msg_data["target"]

                                # Reset last_log_id to resend all matching logs
                                client.subscription.last_log_id = 0

                                # Cancel and restart streaming task
                                if client.streaming_task:
                                    client.streaming_task.cancel()
                                    try:
                                        await client.streaming_task
                                    except asyncio.CancelledError:
                                        pass

                                task = asyncio.create_task(
                                    _stream_logs_to_client(client_id, client.subscription)
                                )
                                await _ws_manager.set_streaming_task(client_id, task)

                                await websocket.send_json(
                                    {
                                        "type": "filters_updated",
                                        "data": {
                                            "min_level": client.subscription.min_level,
                                            "stages": client.subscription.stages,
                                            "target": client.subscription.target,
                                        },
                                    }
                                )
                                log.info(f"Client {client_id} updated filters")

                        elif msg_type == "unsubscribe_logs":
                            # Stop log streaming
                            await _ws_manager.set_subscription(client_id, None)
                            await websocket.send_json(
                                {"type": "unsubscribed", "data": {}}
                            )
                            log.info(f"Client {client_id} unsubscribed from logs")

                        elif msg_type == "request_summary":
                            # Client requests current summary for a project
                            project_path = msg_data.get("project_path", "")
                            if project_path:
                                summary = _get_project_summary(project_path)
                                await websocket.send_json(
                                    {"type": "summary_updated", "data": summary}
                                )
                                log.info(f"Client {client_id} requested summary for {project_path}")
                            else:
                                log.warning(f"Client {client_id} requested summary without project_path")

                        else:
                            log.debug(f"Unknown message type from {client_id}: {msg_type}")

                    except json.JSONDecodeError:
                        log.warning(f"Invalid JSON from client {client_id}")

                except WebSocketDisconnect:
                    break

        finally:
            await _ws_manager.disconnect(client_id)

    @app.post("/api/config")
    async def set_config(ato_binary: Optional[str] = None):
        """Configure server settings like the ato binary path."""
        if ato_binary:
            state["ato_binary"] = ato_binary
        return {"ato_binary": state["ato_binary"]}

    @app.post("/api/build")
    async def start_build(request: BuildRequest):
        """
        Start a build for the specified project and targets.

        Returns the build_id which can be used to track progress.
        """
        log.info(
            f"Build request: project={request.project_path}, targets={request.targets}"
        )

        # Validate project path
        project_path = Path(request.project_path)
        if not project_path.exists():
            log.error(f"Project path does not exist: {request.project_path}")
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {request.project_path}",
            )

        ato_yaml = project_path / "ato.yaml"
        if not ato_yaml.exists():
            log.error(f"No ato.yaml found in: {request.project_path}")
            raise HTTPException(
                status_code=400, detail=f"No ato.yaml found in: {request.project_path}"
            )

        # Find ato binary - try configured path first, then search
        ato_bin = state["ato_binary"]
        if not ato_bin:
            ato_bin = _find_ato_binary()
            log.info(f"Auto-detected ato binary: {ato_bin}")

        if not ato_bin:
            log.error("ato binary not found in PATH or common locations")
            raise HTTPException(
                status_code=500,
                detail="ato binary not found. Configure it via /api/config or ensure 'ato' is in PATH",
            )

        # Build command
        cmd = [ato_bin, "build"]
        for target in request.targets:
            cmd.extend(["--build", target])

        # Generate build ID
        build_id = str(uuid.uuid4())[:8]

        try:
            # Start build subprocess
            process = subprocess.Popen(
                cmd,
                cwd=str(project_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # Track the build
            bp = BuildProcess(
                build_id=build_id,
                project_path=str(project_path),
                targets=request.targets,
                process=process,
            )
            state["build_processes"][build_id] = bp

            log.info(
                f"Started build {build_id} for {request.targets} in {request.project_path}"
            )

            # Broadcast build started event
            _sync_broadcast(
                "build_started",
                {
                    "build_id": build_id,
                    "project_path": str(project_path),
                    "targets": request.targets,
                },
            )

            # Start background thread to monitor build completion
            def monitor_build():
                summary_interval = 0.5  # Send summary updates every 0.5 seconds for responsive UI
                last_summary_update = time.time()

                while process.poll() is None:
                    time.sleep(0.1)  # Short sleep for responsive completion detection
                    now = time.time()

                    # Send periodic summary updates with full summary data
                    if now - last_summary_update >= summary_interval:
                        last_summary_update = now
                        log.debug(
                            f"Build {build_id} still running, sending summary update"
                        )
                        summary = _get_project_summary(str(project_path))
                        _sync_broadcast("summary_updated", summary)

                return_code = process.returncode
                log.info(f"Build {build_id} completed with return code {return_code}")

                # Broadcast build completed event
                _sync_broadcast(
                    "build_completed",
                    {
                        "build_id": build_id,
                        "project_path": str(project_path),
                        "targets": request.targets,
                        "return_code": return_code,
                        "success": return_code == 0,
                    },
                )

                # Broadcast final summary with full data
                summary = _get_project_summary(str(project_path))
                _sync_broadcast("summary_updated", summary)

            monitor_thread = threading.Thread(target=monitor_build, daemon=True)
            monitor_thread.start()

            return {
                "build_id": build_id,
                "status": "started",
                "project_path": str(project_path),
                "targets": request.targets,
            }

        except Exception as e:
            log.error(f"Failed to start build: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/build/{build_id}")
    async def cancel_build(build_id: str):
        """Cancel a running build."""
        bp = state["build_processes"].get(build_id)
        if not bp:
            raise HTTPException(status_code=404, detail=f"Build not found: {build_id}")

        if bp.is_running:
            bp.terminate()
            return {"build_id": build_id, "status": "cancelled"}
        else:
            return {
                "build_id": build_id,
                "status": "already_completed",
                "return_code": bp.return_code,
            }

    @app.get("/api/summary")
    async def get_summary(
        project_path: Optional[str] = Query(
            None, description="Project path to get builds for"
        ),
    ):
        """
        Return the aggregated build summary for a project.

        IMPORTANT: project_path must be provided by the client. The server does not
        maintain project state - each request should specify which project to query.
        """
        # Empty response structure for consistency
        empty_response = {
            "timestamp": None,
            "totals": {
                "builds": 0,
                "successful": 0,
                "failed": 0,
                "warnings": 0,
                "errors": 0,
            },
            "builds": [],
        }

        # Require project_path from client
        if not project_path:
            log.debug("Summary requested without project_path")
            return empty_response

        project_root = Path(project_path)
        if not project_root.exists():
            log.warning(f"Project path does not exist: {project_path}")
            return empty_response

        # Scan for per-target build summaries
        builds_dir = project_root / "build" / "builds"
        if not builds_dir.exists():
            log.debug(f"No builds directory at {builds_dir}")
            return empty_response

        builds = []
        for summary_file in builds_dir.glob("*/build_summary.json"):
            try:
                build_data = json.loads(summary_file.read_text())
                # Add project_path to build data for client reference
                build_data["project_path"] = str(project_root)
                builds.append(build_data)
            except (json.JSONDecodeError, OSError) as e:
                log.warning(f"Failed to read build summary {summary_file}: {e}")
                continue

        # Aggregate stats
        total = len(builds)
        success = sum(1 for b in builds if b.get("status") in ("success", "warning"))
        failed = sum(1 for b in builds if b.get("status") == "failed")
        warnings = sum(b.get("warnings", 0) for b in builds)
        errors = sum(b.get("errors", 0) for b in builds)

        # Get timestamp from most recent build
        timestamps = [b.get("timestamp") for b in builds if b.get("timestamp")]
        timestamp = max(timestamps) if timestamps else None

        log.info(
            f"Summary for {project_path}: {total} builds ({success} ok, {failed} failed)"
        )

        return {
            "timestamp": timestamp,
            "totals": {
                "builds": total,
                "successful": success,
                "failed": failed,
                "warnings": warnings,
                "errors": errors,
            },
            "builds": builds,
        }

    @app.get("/api/logs/query")
    async def query_logs(
        build_id: str = Query(
            ..., description="Build ID to query logs for (required)"
        ),
        levels: Optional[str] = Query(
            None,
            description="Filter by log levels (comma-separated, e.g. 'INFO,WARNING,ERROR')",
        ),
        stages: Optional[str] = Query(
            None,
            description="Filter by stages (comma-separated, e.g. 'compile,Picking parts')",
        ),
        limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Result offset for pagination"),
    ):
        """
        Query logs from the central SQLite database.

        IMPORTANT: build_id is required to prevent accidentally returning all logs.
        Returns structured log entries filtered by build_id and optionally by log levels and stages.
        """
        from atopile.logging import get_central_log_db

        try:
            db_path = get_central_log_db()
            if not db_path.exists():
                return {"logs": [], "total": 0, "builds": [], "stages": []}

            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row

            # Build query with filters - build_id is now required
            conditions = ["l.build_id = ?"]
            params: list = [build_id]

            log.debug(f"Querying logs for build_id={build_id}")
            # Support multiple levels (comma-separated)
            if levels:
                level_list = [
                    lv.strip().upper() for lv in levels.split(",") if lv.strip()
                ]
                if level_list:
                    placeholders = ",".join("?" * len(level_list))
                    conditions.append(f"l.level IN ({placeholders})")
                    params.extend(level_list)
            # Support multiple stages (comma-separated)
            if stages:
                stage_list = [s.strip() for s in stages.split(",") if s.strip()]
                if stage_list:
                    placeholders = ",".join("?" * len(stage_list))
                    conditions.append(f"l.stage IN ({placeholders})")
                    params.extend(stage_list)

            where_clause = (
                "WHERE " + " AND ".join(conditions) if conditions else ""
            )

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

            # Get list of available stages for this build
            available_stages: list[str] = []
            if build_id:
                stages_query = """
                    SELECT DISTINCT stage FROM logs
                    WHERE build_id = ?
                    ORDER BY stage
                """
                stages_cursor = conn.execute(stages_query, [build_id])
                available_stages = [row["stage"] for row in stages_cursor.fetchall()]

            conn.close()
            return {
                "logs": logs,
                "total": len(logs),
                "builds": builds,
                "stages": available_stages,
            }

        except sqlite3.Error as e:
            log.warning(f"Error reading logs from central database: {e}")
            return {"logs": [], "total": 0, "builds": [], "stages": [], "error": str(e)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/builds")
    async def list_builds(
        project_path: Optional[str] = Query(
            None, description="Filter by project path"
        ),
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

    def __init__(
        self, port: Optional[int] = None, project_root: Optional[Path] = None
    ):
        self.port = port or find_free_port()
        self.app = create_app(project_root)
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
            log_level="info",
            access_log=True,
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


# Default port for the dashboard server
DEFAULT_PORT = 8501


def start_dashboard_server(
    port: Optional[int] = None,
    project_root: Optional[Path] = None,
) -> tuple[DashboardServer, str]:
    """
    Start the dashboard server.

    Args:
        port: Port to use (defaults to DEFAULT_PORT)
        project_root: Optional default project root

    Returns:
        Tuple of (DashboardServer, url)
    """
    server = DashboardServer(port=port or DEFAULT_PORT, project_root=project_root)
    server.start()
    return server, server.url
