"""
atopile core server.

This package provides:
- WebSocket endpoint for the core server
- Build queue management

Directory Structure:
- server.py: Server lifecycle (websockets.serve on a background thread)
- websocket.py: WebSocket connection management and action dispatch
"""

from .server import CoreServer

__all__ = [
    "CoreServer",
]
