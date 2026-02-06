"""
Tree visualization tools for atopile/faebryk.

Provides power tree and I2C tree visualizers using Three.js.
"""

from pathlib import Path

WEB_DIST_PATH = Path(__file__).parent / "web" / "dist"


def is_tree_viewer_built() -> bool:
    """Check if the tree viewer web app has been built."""
    return (WEB_DIST_PATH / "index.html").exists()
