import logging

import typer

logger = logging.getLogger(__name__)


lsp_app = typer.Typer(rich_markup_mode="rich")


@lsp_app.command()
def start():
    from atopile.lsp import LSP_SERVER

    LSP_SERVER.start_io()
