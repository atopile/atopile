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

TOOLS: dict[Callable, MCP_DECORATOR] = {}


def mcp_decorate(decorator: MCP_DECORATOR = lambda mcp: mcp.tool()):
    def decorator_wrapper(func):
        TOOLS[func] = decorator

        return func

    return decorator_wrapper


def register_tools(mcp: FastMCP):
    # import all files in this directory except self and mcp_server.py
    import importlib
    import os

    current_dir = os.path.dirname(os.path.abspath(__file__))
    for file in os.listdir(current_dir):
        if file == __file__:
            continue
        if not file.endswith(".py"):
            continue
        module_name = f"atopile.mcp.{file.replace('.py', '')}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            logger.warning(f"Error importing module {module_name}: {e}")

    # Run mcp decorators
    for func, decorator in TOOLS.items():
        d = decorator(mcp)
        d(func)
