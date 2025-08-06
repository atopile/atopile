"""CLI command definition for `ato build`."""

import logging
from typing import Annotated

import typer

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
    exclude_target: Annotated[
        list[str], typer.Option("--exclude-target", "-x", envvar="ATO_EXCLUDE_TARGET")
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
    from atopile.cli.logging_ import NOW
    from atopile.config import config
    from faebryk.libs.app.pcb import open_pcb
    from faebryk.libs.exceptions import accumulate, log_user_errors
    from faebryk.libs.kicad.ipc import reload_pcb
    from faebryk.libs.project.dependencies import ProjectDependencies

    config.apply_options(
        entry=entry,
        selected_builds=selected_builds,
        include_targets=target,
        exclude_targets=exclude_target,
        standalone=standalone,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    deps = ProjectDependencies(sync_versions=False)
    if deps.not_installed_dependencies:
        logger.info("Installing missing dependencies")
        deps.install_missing_dependencies()

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

    selected_build_names = list(config.selected_builds)
    for build_name in selected_build_names:
        build = config.project.builds[build_name]

        opened = False
        if config.should_open_layout_on_build():
            try:
                open_pcb(build.paths.layout)
            # No PCBnew
            except FileNotFoundError:
                continue
            # Already open, reload
            except RuntimeError:
                pass

        if not opened:
            try:
                reload_pcb(build.paths.layout, backup_path=build.paths.output_base)
            except Exception as e:
                logger.warning(f"{e}\nReload pcb manually in KiCAD")
