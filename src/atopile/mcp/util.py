import logging
from enum import StrEnum
from typing import Callable

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Language(StrEnum):
    FABLL = "fabll(python)"
    ATO = "ato"


class NodeType(StrEnum):
    MODULE = "Module"
    INTERFACE = "Interface"


class NodeInfo(BaseModel):
    name: str
    docstring: str
    locator: str
    language: Language
    code: str


class NodeInfoOverview(BaseModel):
    name: str
    docstring: str
    language: Language
    type: NodeType
    inherits: str | None = None


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
