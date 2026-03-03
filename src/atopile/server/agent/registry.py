"""Tool registry — wraps existing tools.py with a clean interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from atopile.dataclasses import AppContext
from atopile.server.agent import tools as _legacy_tools


class ToolRegistry:
    """Adapter over the existing tools module."""

    def __init__(self) -> None:
        self._definitions: list[dict[str, Any]] | None = None

    def definitions(self) -> list[dict[str, Any]]:
        if self._definitions is None:
            self._definitions = _legacy_tools.get_tool_definitions()
        return self._definitions

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        project_root: Path,
        ctx: AppContext,
    ) -> dict[str, Any]:
        return await _legacy_tools.execute_tool(
            name=name,
            arguments=arguments,
            project_root=project_root,
            ctx=ctx,
        )
