import logging
import time

import click
from rich.logging import RichHandler

from atopile.cli.rich_console import console
from atopile import telemetry


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
    ctx.ensure_object(dict)
    ctx.obj['start_time'] = time.time()  # Store the start time in the context.
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

@cli.result_callback()
@click.pass_context  # To access the context in the result callback
def process_result(ctx, result, **kwargs):
    """Process the result of each CLI command to log telemetry."""
    start_time = ctx.obj['start_time']
    end_time = time.time()
    execution_time = end_time - start_time
    subcommand_name = ctx.invoked_subcommand  # Get the name of the invoked subcommand

    telemetry.log_telemetry(result, subcommand_name=subcommand_name, execution_time=execution_time, **kwargs)

cli.add_command(build.build)
cli.add_command(create.create)
cli.add_command(install.install)
cli.add_command(configure.configure)
cli.add_command(inspect.inspect)


if __name__ == "__main__":
    cli()
