"""
Build dashboard for atopile.

This package provides:
- server.py: FastAPI server to serve the dashboard and API endpoints
- web/: React-based interactive build dashboard
"""

from pathlib import Path

# Path to the web dashboard dist directory
WEB_DIST_PATH = Path(__file__).parent / "web" / "dist"


def is_dashboard_built() -> bool:
    """Check if the web dashboard has been built."""
    return (WEB_DIST_PATH / "index.html").exists()
