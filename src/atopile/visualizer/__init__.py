"""
Graph visualization tools for atopile/faebryk.

This package provides:
- explore_graphs.py: Script to explore graph structures
- web/: Three.js based interactive graph visualizer
"""

from pathlib import Path

# Path to the web visualizer dist directory
WEB_DIST_PATH = Path(__file__).parent / "web" / "dist"


def is_visualizer_built() -> bool:
    """Check if the web visualizer has been built."""
    return (WEB_DIST_PATH / "index.html").exists()
