# excepthook must be installed before typer is imported
import atopile.cli.excepthook  # noqa: F401, I001

import logging
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from atopile import telemetry
from atopile.cli import build, configure, create, inspect, install, view
from atopile.cli.logging import logger, handler
from atopile.version import check_for_update
from faebryk.libs.logging import FLOG_FMT

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=bool(FLOG_FMT),  # required to override the excepthook
)


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
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Wait to attach debugger on start"),
    ] = False,
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="Increase verbosity"),
    ] = 0,
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
    if debug:
        import debugpy  # pylint: disable=import-outside-toplevel

        debug_port = 5678
        debugpy.listen(("localhost", debug_port))
        logger.info("Starting debugpy on port %s", debug_port)
        debugpy.wait_for_client()

    # set the log level
    if verbose == 1:
        handler.hide_traceback_types = ()
        handler.tracebacks_show_locals = True
    elif verbose == 2:
        handler.tracebacks_suppress_map = {}  # Traceback through atopile infra
    elif verbose >= 3:
        logger.root.setLevel(logging.DEBUG)
        handler.traceback_level = logging.WARNING

    if ctx.invoked_subcommand:
        check_for_update()

        # Initialize telemetry
        telemetry.setup_telemetry_data(ctx.invoked_subcommand)

    if not non_interactive and ctx.invoked_subcommand != "configure":
        configure.do_configure_if_needed()


app.command()(build.build)
app.add_typer(create.create_app, name="create")
app.command()(install.install)
app.command()(configure.configure)
app.command()(inspect.inspect)
app.command()(view.view)


def main():
    app()


if __name__ == "__main__":
    main()
