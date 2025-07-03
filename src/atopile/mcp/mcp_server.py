import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from atopile.mcp.util import mcp_decorate, register_tools
from faebryk.libs.util import ConfigFlag, root_by_file

mcp = FastMCP("atopile", stateless_http=True)


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

    register_tools(mcp)

    logger.info("Starting atopile MCP server...")
    mcp.run(transport="streamable-http" if http else "stdio")


@mcp_decorate()
def find_project_from_filepath(absolute_path_to_file: Path) -> Path:
    """
    Find the project root from an .ato file inside that project.
    """

    path = absolute_path_to_file
    logger.info(f"Finding project from filepath: {path}")
    if not path.is_absolute():
        raise ValueError("Path is not absolute")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist")
    if not path.is_file():
        raise ValueError(f"Path {path} is not a file")

    if path.suffix != ".ato":
        raise ValueError("Path is not an ato file")

    return root_by_file("ato.yaml", path.parent)
