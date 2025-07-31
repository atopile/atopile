import logging
from pathlib import Path

from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

DEBUG = ConfigFlag("MCP_DEBUG", default=False)


def _setup_debug(enable: bool = False):
    """
    Setup debug logging to file
    """
    if not enable:
        return

    handler = logging.FileHandler(Path(__file__).parent / "mcp.log")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def run_mcp(http: bool = False, debug: bool = False):
    _setup_debug(enable=bool(DEBUG) or debug)

    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("atopile", stateless_http=True)

    from atopile.mcp.tools import (
        cli_tools,
        library_tools,
        packages_tools,
        project_tools,
    )

    cli_tools.install(mcp)
    library_tools.install(mcp)
    packages_tools.install(mcp)
    project_tools.install(mcp)

    logger.info("Starting atopile MCP server...")
    mcp.run(transport="streamable-http" if http else "stdio")
