import sys

# fast-path for self-check
# makes extension a lot faster
if __name__ in ("__main__", "atopile.cli.cli"):
    if len(sys.argv) == 2 and sys.argv[1] == "self-check":
        from importlib.metadata import version as get_package_version

        print(get_package_version("atopile"))
        sys.exit(0)


# excepthook must be installed before typer is imported
import atopile.cli.excepthook  # noqa: F401, I001

import json
import logging
from enum import Enum
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Annotated

import typer

from atopile import version
from atopile.cli import (
    build,
    configure,
    create,
    inspect_,
    install,
    kicad_ipc,
    package,
    view,
    lsp,
    mcp,
)
from atopile.cli.logging_ import handler, logger
from atopile.errors import UserException, UserNoProjectException
from atopile.version import check_for_update
from faebryk.libs.exceptions import (
    UserResourceException,
    iter_leaf_exceptions,
)
from faebryk.libs.logging import FLOG_FMT

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=bool(FLOG_FMT),  # required to override the excepthook
    rich_markup_mode="rich",
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
    """Output a version string meeting the pypa version spec."""
    if not value or ctx.resilient_parsing:
        return
    typer.echo(get_package_version("atopile"))
    raise typer.Exit()


def semver_callback(ctx: typer.Context, value: bool):
    """Output a version string meeting the semver.org spec."""
    if not value or ctx.resilient_parsing:
        return
    version_string = get_package_version("atopile")
    typer.echo(version.parse(version_string))
    raise typer.Exit()


@app.callback()
def cli(
    ctx: typer.Context,
    non_interactive: Annotated[
        bool | None,
        typer.Option(
            "--non-interactive", envvar=["ATO_NON_INTERACTIVE", "NONINTERACTIVE"]
        ),
    ] = None,
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
    semver: Annotated[
        bool | None,
        typer.Option("--semver", callback=semver_callback, is_eager=True),
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

    # FIXME: this won't work properly when configs
    # are reloaded from a pointed-to file (eg in `ato build path/to/file`)
    # from outside a project directory
    if non_interactive is not None:
        from atopile.config import config

        config.interactive = not non_interactive

    if ctx.invoked_subcommand:
        check_for_update()

    configure.setup()


app.command()(build.build)
app.add_typer(create.create_app, name="create")
app.command(deprecated=True, hidden=True)(install.install)
app.command(deprecated=True, hidden=True)(configure.configure)
app.command()(inspect_.inspect)
app.command()(view.view)
app.add_typer(package.package_app, name="package", hidden=True)
app.add_typer(install.dependencies_app, name="dependencies", help="Manage dependencies")
app.command(rich_help_panel="Shortcuts")(install.sync)
app.command(rich_help_panel="Shortcuts")(install.add)
app.command(rich_help_panel="Shortcuts")(install.remove)
app.add_typer(lsp.lsp_app, name="lsp", hidden=True)
app.add_typer(mcp.mcp_app, name="mcp", hidden=True)
app.add_typer(kicad_ipc.kicad_ipc_app, name="kicad-ipc", hidden=True)


@app.command(hidden=True)
def export_config_schema(pretty: bool = False):
    from atopile.config import ProjectConfig

    config_schema = ProjectConfig.model_json_schema()

    if pretty:
        print(json.dumps(config_schema, indent=4))
    else:
        print(json.dumps(config_schema))


class ConfigFormat(str, Enum):
    python = "python"
    json = "json"


@app.command(hidden=True)
def dump_config(format: ConfigFormat = ConfigFormat.python):
    from rich import print

    from atopile.config import config

    print(config.project.model_dump(mode=format))


@app.command(help="Check file for syntax errors and internal consistency")
def validate(
    path: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
):
    from atopile import front_end
    from atopile.config import config

    path = path.resolve().relative_to(Path.cwd())

    # pick up project config if we're in a project
    # required for package search path inclusion
    try:
        config.apply_options(entry=None)
    except UserNoProjectException:
        pass

    if path.suffix != ".ato":
        raise UserResourceException("Invalid file type")

    try:
        front_end.bob.try_build_all_from_file(path)
    except* UserException as e:
        for error in iter_leaf_exceptions(e):
            logger.error(error, exc_info=error)

    else:
        typer.echo(f"{path}: ok")


def main():
    app()


if __name__ == "__main__":
    main()
