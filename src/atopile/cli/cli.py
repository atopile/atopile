import logging

import click
from rich.logging import RichHandler

from atopile.cli.rich_console import console

from . import build, create, install

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(
            console=console,
            tracebacks_suppress=[click],
        )
    ]
)


# cli root
@click.version_option()
@click.group()
@click.option("--debugpy", is_flag=True)
def cli(debugpy: bool):
    """Base CLI group."""
    # we process debugpy first, so we can attach the debugger ASAP into the process
    if debugpy:
        import debugpy as debugpy_mod  # pylint: disable=import-outside-toplevel
        debug_port = 5678
        debugpy_mod.listen(("localhost", debug_port))
        logging.info("Starting debugpy on port %s", debug_port)
        debugpy_mod.wait_for_client()


cli.add_command(build.build)
cli.add_command(create.create)
cli.add_command(install.install)


if __name__ == "__main__":
    cli()
