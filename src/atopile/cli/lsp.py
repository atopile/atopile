import logging

import typer

from atopile.telemetry import capture

logger = logging.getLogger(__name__)


lsp_app = typer.Typer(rich_markup_mode="rich")


@lsp_app.command()
@capture("cli:lsp_start", "cli:lsp_end")
def start():
    from atopile.lsp import LSP_SERVER

    LSP_SERVER.start_io()
