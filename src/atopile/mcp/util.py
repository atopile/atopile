import logging
from typing import Callable

from mcp.server.fastmcp import FastMCP

from atopile.dataclasses import (
    Language,
    NodeInfo,
    NodeInfoOverview,
    NodeType,
)

logger = logging.getLogger(__name__)


MCP_DECORATOR = Callable[[FastMCP], Callable]


class MCPTools:
    def __init__(self):
        self._tools: dict[Callable, MCP_DECORATOR] = {}

    def register(self, decorator: MCP_DECORATOR = lambda mcp: mcp.tool()):
        def decorator_wrapper(func: Callable):
            self._tools[func] = decorator

            return func

        return decorator_wrapper

    def install(self, mcp: FastMCP):
        for func, decorator in self._tools.items():
            d = decorator(mcp)
            d(func)
