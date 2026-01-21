"""
Model-layer interfaces for external data sources.

This package contains pure data access logic (no FastAPI or server state).
"""

from . import registry

__all__ = ["registry"]
