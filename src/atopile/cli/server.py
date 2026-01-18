"""CLI command definition for `ato server`."""

import logging
from typing import Annotated

import typer

logger = logging.getLogger(__name__)

server_app = typer.Typer(rich_markup_mode="rich")


@server_app.command()
def start(
    port: Annotated[int, typer.Option(help="Port to listen on")] = 8501,
    host: Annotated[str, typer.Option(help="Host to bind to")] = "127.0.0.1",
):
    """Start the ato server for build management and dashboard UI."""
    from atopile.dashboard.server import run_server

    # Print ready message for clients to detect (before starting server)
    # This allows the extension to know when the server is ready
    print(f"ATO_SERVER_READY:{port}", flush=True)

    logger.info("Starting ato server on %s:%d", host, port)
    run_server(host=host, port=port)
