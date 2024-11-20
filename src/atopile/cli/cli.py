import logging
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

from atopile import telemetry
from atopile.cli.rich_console import console

from . import build, configure, create, inspect, install, view

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(
            console=console,
            tracebacks_suppress=[typer],
        )
    ],
)

app = typer.Typer(no_args_is_help=True)
state = {"non_interactive": False, "debug": False, "verbose": 0}


def python_interpreter_path(ctx: typer.Context, value: bool):
    """Print the current python interpreter path."""
    if not value or ctx.resilient_parsing:
        return
    typer.echo(sys.executable)
    raise typer.Exit()


def atopile_src_path(ctx: typer.Context, value: bool):
    """Print the current python interpreter path."""
    if not value or ctx.resilient_parsing:
        return
    typer.echo(Path(__file__).parent.parent)
    raise typer.Exit()


def version_callback(ctx: typer.Context, value: bool):
    if not value or ctx.resilient_parsing:
        return
    typer.echo(version("atopile"))
    raise typer.Exit()


@app.callback()
def cli(
    ctx: typer.Context,
    non_interactive: Annotated[
        bool, typer.Option("--non-interactive", envvar="ATO_NON_INTERACTIVE")
    ] = False,
    debug: Annotated[bool, typer.Option("--debug")] = False,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
    python_path: Annotated[
        bool, typer.Option(hidden=True, callback=python_interpreter_path)
    ] = False,
    atopile_path: Annotated[
        bool, typer.Option(hidden=True, callback=atopile_src_path)
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
):
    state["non_interactive"] = non_interactive
    state["debug"] = debug
    state["verbose"] = verbose

    if debug:
        import debugpy  # pylint: disable=import-outside-toplevel

        debug_port = 5678
        debugpy.listen(("localhost", debug_port))
        logging.info("Starting debugpy on port %s", debug_port)
        debugpy.wait_for_client()

    # Initialize telemetry
    if ctx.invoked_subcommand:
        telemetry.setup_telemetry_data(ctx.invoked_subcommand)

    # set the log level
    if verbose == 1:
        logging.root.setLevel(logging.DEBUG)
    elif verbose > 1:
        logging.root.setLevel(logging.NOTSET)

    if not non_interactive:
        configure.do_configure_if_needed()


app.command()(build.build)
app.command()(create.create)
app.command(no_args_is_help=True)(install.install)
app.command()(configure.configure)
app.command()(inspect.inspect)
app.command()(view.view)


def main():
    app()


if __name__ == "__main__":
    main()
