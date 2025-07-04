"""CLI command definition for `ato build`."""

import logging
from typing import Annotated

import typer
from more_itertools import first

from atopile.cli.logging_ import NOW
from atopile.config import config
from atopile.telemetry import capture

logger = logging.getLogger(__name__)


@capture("cli:build_start", "cli:build_end")
def build(
    entry: Annotated[
        str | None,
        typer.Argument(
            help="Path to the project directory or build target address "
            '("path_to.ato:Module")'
        ),
    ] = None,
    selected_builds: Annotated[
        list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")
    ] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    frozen: Annotated[
        bool | None,
        typer.Option(
            help="PCB must be rebuilt without changes. Useful in CI",
            envvar="ATO_FROZEN",
        ),
    ] = None,
    keep_picked_parts: bool | None = None,
    keep_net_names: bool | None = None,
    keep_designators: bool | None = None,
    standalone: bool = False,
    open_layout: Annotated[
        bool | None, typer.Option("--open", envvar="ATO_OPEN_LAYOUT")
    ] = None,
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Optionally specify a different entrypoint with the argument ENTRY.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    from atopile import build as buildlib
    from atopile import buildutil
    from atopile.cli.install import check_missing_deps_or_offer_to_install
    from faebryk.libs.exceptions import accumulate, log_user_errors

    config.apply_options(
        entry=entry,
        selected_builds=selected_builds,
        target=target,
        standalone=standalone,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    check_missing_deps_or_offer_to_install()

    if open_layout is not None:
        config.project.open_layout_on_build = open_layout

    logger.info("Saving logs to %s", config.project.paths.logs / NOW)
    with accumulate() as accumulator:
        for build in config.builds:
            with accumulator.collect(), log_user_errors(logger), build:
                logger.info("Building '%s'", config.build.name)
                app = buildlib.init_app()

                # TODO: add a way to override the following with custom build machinery
                buildutil.build(app)

    logger.info("Build successful! 🚀")

    if config.should_open_layout_on_build():
        selected_build_names = list(config.selected_builds)
        if len(selected_build_names) == 1:
            build = config.project.builds[first(selected_build_names)]
            try:
                from faebryk.libs.app.pcb import open_pcb

                open_pcb(build.paths.layout)
            except FileNotFoundError:
                pass
            except RuntimeError as e:
                logger.info(
                    f"{e.args[0]}\nReload pcb manually by pressing Ctrl+O; Enter"
                )

        elif len(selected_build_names) > 1:
            logger.warning(
                "`--open` option is only supported when building "
                "a single build. It will be ignored."
            )
