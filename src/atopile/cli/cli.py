import logging

import click
from rich.logging import RichHandler

from atopile import telemetry
from atopile.cli.rich_console import console

from . import build, configure, create, inspect, install

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
    ],
)


# cli root
@click.version_option()
@click.group()
@click.option("--non-interactive", is_flag=True, envvar="ATO_NON_INTERACTIVE")
@click.option("--debug", is_flag=True)
@click.option("-v", "--verbose", count=True)
@click.pass_context  # This decorator makes the context available to the command.
def cli(ctx, non_interactive: bool, debug: bool, verbose: int):
    """Base CLI group."""

    # Initialize telemetry
    telemetry.setup_telemetry_data(ctx.invoked_subcommand)

    if debug:
        import debugpy  # pylint: disable=import-outside-toplevel

        debug_port = 5678
        debugpy.listen(("localhost", debug_port))
        logging.info("Starting debugpy on port %s", debug_port)
        debugpy.wait_for_client()

    # set the log level
    if verbose == 1:
        logging.root.setLevel(logging.DEBUG)
    elif verbose > 1:
        logging.root.setLevel(logging.NOTSET)

    if not non_interactive:
        configure.do_configure_if_needed()


cli.add_command(build.build)
cli.add_command(create.create)
cli.add_command(install.install)
cli.add_command(configure.configure)
cli.add_command(inspect.inspect)


if __name__ == "__main__":
    cli()
