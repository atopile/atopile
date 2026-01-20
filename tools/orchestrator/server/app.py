"""FastAPI application for the orchestrator server."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..agents import get_available_backends
from ..exceptions import (
    AgentNotFoundError,
    AgentNotRunningError,
    BackendNotAvailableError,
    OrchestratorError,
    SessionNotFoundError,
)
from .dependencies import ConnectionManager, get_orchestrator_state
from .routes import agents_router, bridge_router, pipelines_router, sessions_router, websocket_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    import asyncio

    # Startup
    logger.info("Starting orchestrator server...")

    state = get_orchestrator_state()

    # Set up WebSocket manager
    ws_manager = ConnectionManager()
    state.set_ws_manager(ws_manager)

    # Store the event loop for thread-safe async operations
    state.set_event_loop(asyncio.get_running_loop())

    # Start process monitor
    state.start_monitor()

    logger.info("Orchestrator server started")

    yield

    # Shutdown
    logger.info("Shutting down orchestrator server...")
    state.shutdown()
    logger.info("Orchestrator server stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Agent Orchestrator",
        description="REST API for spawning and managing AI coding agents",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware for web clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(agents_router)
    app.include_router(bridge_router)
    app.include_router(sessions_router)
    app.include_router(pipelines_router)
    app.include_router(websocket_router)

    # Exception handlers
    @app.exception_handler(AgentNotFoundError)
    async def agent_not_found_handler(request: Request, exc: AgentNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc), "agent_id": exc.agent_id},
        )

    @app.exception_handler(SessionNotFoundError)
    async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc), "session_id": exc.session_id},
        )

    @app.exception_handler(AgentNotRunningError)
    async def agent_not_running_handler(request: Request, exc: AgentNotRunningError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "agent_id": exc.agent_id},
        )

    @app.exception_handler(BackendNotAvailableError)
    async def backend_not_available_handler(
        request: Request, exc: BackendNotAvailableError
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "backend": exc.backend},
        )

    @app.exception_handler(OrchestratorError)
    async def orchestrator_error_handler(request: Request, exc: OrchestratorError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    # Health and info endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "Agent Orchestrator",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
            "stats": "/stats",
        }

    @app.get("/stats")
    async def get_stats():
        """Get server statistics."""
        state = get_orchestrator_state()

        agents = state.agent_store.values()
        running = sum(1 for a in agents if a.is_running())
        completed = sum(1 for a in agents if a.status.value == "completed")
        failed = sum(1 for a in agents if a.status.value == "failed")

        pipelines = state.pipeline_store.values()
        pipelines_running = sum(1 for p in pipelines if p.status.value == "running")

        return {
            "agents": {
                "total": len(agents),
                "running": running,
                "completed": completed,
                "failed": failed,
            },
            "sessions": {
                "total": state.session_manager.count(),
            },
            "pipelines": {
                "total": len(pipelines),
                "running": pipelines_running,
            },
            "backends": {
                "available": [str(b.backend_type) for b in get_available_backends()],
            },
            "websockets": {
                "connections": (
                    state._ws_manager.get_connection_count()
                    if state._ws_manager
                    else 0
                ),
            },
        }

    @app.get("/backends")
    async def list_backends():
        """List available agent backends."""
        backends = get_available_backends()
        return {
            "backends": [
                {
                    "type": str(b.backend_type),
                    "binary": b.binary_name,
                    "path": str(b.get_binary_path()),
                    "capabilities": b.get_capabilities().model_dump(),
                }
                for b in backends
            ]
        }

    @app.post("/dev/restart")
    async def restart_servers():
        """Restart the backend and frontend dev servers.

        This endpoint spawns a background process that:
        1. Waits 1 second for this response to be sent
        2. Kills the current uvicorn and vite processes
        3. Restarts both servers

        Only for development use.
        """
        import os
        import subprocess
        import sys

        # Get the orchestrator directory
        orchestrator_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        web_dir = os.path.join(orchestrator_dir, "web")

        # Create a restart script that runs in the background
        restart_script = f"""
sleep 1
# Kill existing servers
pkill -f "uvicorn orchestrator" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true
sleep 1
# Restart backend
cd "{os.path.dirname(orchestrator_dir)}" && uv run uvicorn orchestrator.server.app:app --host 0.0.0.0 --port 8765 &
# Restart frontend
cd "{web_dir}" && npm run dev &
"""
        # Run the restart script in background
        subprocess.Popen(
            ["bash", "-c", restart_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return {"status": "restarting", "message": "Servers will restart in ~2 seconds"}

    @app.post("/screenshot")
    async def take_screenshot_endpoint(
        screenshot_type: str = "main",
        agent_name: str | None = None,
    ):
        """Take a screenshot of the orchestrator web UI.

        Args:
            screenshot_type: Type of screenshot:
                - "main": Dashboard view
                - "agent": Agent detail (clicks first/named agent)
                - "agent-top": Agent detail scrolled to top
                - "agent-scroll": Agent detail scrolled to bottom
            agent_name: Optional agent name to click on

        Returns:
            Path to the saved screenshot
        """
        import asyncio
        from pathlib import Path

        from ..screenshot import take_screenshot

        # Run in thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: take_screenshot(screenshot_type, agent_name),  # type: ignore
        )

        if result is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to take screenshot"},
            )

        return {
            "path": str(result),
            "filename": result.name,
            "type": screenshot_type,
        }

    @app.get("/screenshot/latest")
    async def get_latest_screenshot_endpoint():
        """Get information about the latest screenshot."""
        from ..screenshot import get_latest_screenshot, list_screenshots

        latest = get_latest_screenshot()
        if latest is None:
            return JSONResponse(
                status_code=404,
                content={"error": "No screenshots found"},
            )

        screenshots = list_screenshots()
        return {
            "latest": str(latest),
            "filename": latest.name,
            "count": len(screenshots),
            "all": [str(p) for p in screenshots[:10]],  # Last 10
        }

    return app


# Create the app instance for uvicorn
app = create_app()
