"""
Shared application context for route handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppContext:
    summary_file: Optional[Path]
    logs_base: Optional[Path]
    workspace_paths: list[Path]
