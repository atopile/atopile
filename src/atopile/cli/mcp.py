import logging

import typer

from atopile.mcp.mcp_server import run_mcp
from atopile.telemetry import capture

logger = logging.getLogger(__name__)


mcp_app = typer.Typer(rich_markup_mode="rich")


@mcp_app.command()
@capture("cli:mcp_start", "cli:mcp_end")
def start(http: bool = False):
    """Start the MCP server."""
    logger.info("Starting atopile MCP server...")
    run_mcp(http)
