"""CLI command definition for `ato build`."""

import logging
from typing import TYPE_CHECKING, Annotated

import typer
from more_itertools import first

from atopile import errors
from atopile.config import config
from faebryk.libs.app.pcb import open_pcb

if TYPE_CHECKING:
    from faebryk.core.module import Module

logger = logging.getLogger(__name__)


def build(
    entry: Annotated[str | None, typer.Argument()] = None,
    selected_builds: Annotated[
        list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")
    ] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    option: Annotated[
        list[str], typer.Option("--option", "-o", envvar="ATO_OPTION")
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
    from atopile import buildutil
    from atopile.cli.install import check_missing_deps_or_offer_to_install
    from atopile.config import BuildType
    from faebryk.library import _F as F
    from faebryk.libs.exceptions import accumulate, log_user_errors

    config.apply_options(
        entry=entry,
        selected_builds=selected_builds,
        target=target,
        option=option,
        standalone=standalone,
    )

    check_missing_deps_or_offer_to_install()

    if open_layout is not None:
        config.project.pcbnew_auto = open_layout

    for build_cfg in config.project.builds.values():
        if keep_picked_parts is not None:
            build_cfg.keep_picked_parts = keep_picked_parts

        if keep_net_names is not None:
            build_cfg.keep_net_names = keep_net_names

        if frozen is not None:
            build_cfg.frozen = frozen
            if frozen:
                if keep_picked_parts is False:  # is, ignores None
                    raise errors.UserBadParameterError(
                        "`--keep-picked-parts` conflict with `--frozen`"
                    )

                build_cfg.keep_picked_parts = True

                if keep_net_names is False:  # is, ignores None
                    raise errors.UserBadParameterError(
                        "`--keep-net-names` conflict with `--frozen`"
                    )

                build_cfg.keep_net_names = True

    with accumulate() as accumulator:
        for build in config.builds:
            with accumulator.collect(), log_user_errors(logger), build:
                logger.info("Building '%s'", config.build.name)
                match config.build.build_type:
                    case BuildType.ATO:
                        app = _init_ato_app()
                    case BuildType.PYTHON:
                        app = _init_python_app()
                        app.add(F.is_app_root())
                    case _:
                        raise ValueError(
                            f"Unknown build type: {config.build.build_type}"
                        )

                # TODO: add a way to override the following with custom build machinery
                buildutil.build(app)

    logger.info("Build successful! 🚀")

    selected_build_names = list(config.selected_builds)
    # Default to opening the layout if we're only building a single target
    # and we're running interactively
    if (
        config.project.pcbnew_auto is None
        and len(selected_build_names) == 1
        and config.interactive
    ):
        config.project.pcbnew_auto = True

    if config.project.pcbnew_auto:
        if len(selected_build_names) == 1:
            build = config.project.builds[first(selected_build_names)]
            try:
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


def _init_python_app() -> "Module":
    """Initialize a specific .py build."""

    from atopile import errors
    from faebryk.libs.util import import_from_path

    try:
        app_class = import_from_path(
            config.build.entry_file_path, config.build.entry_section
        )
    except FileNotFoundError as e:
        raise errors.UserFileNotFoundError(
            f"Cannot find build entry {config.build.address}"
        ) from e
    except Exception as e:
        raise errors.UserPythonModuleError(
            f"Cannot import build entry {config.build.address}"
        ) from e

    if not isinstance(app_class, type):
        raise errors.UserPythonLoadError(
            f"Build entry {config.build.address} is not a module we can instantiate"
        )

    try:
        app = app_class()
    except Exception as e:
        raise errors.UserPythonConstructionError(
            f"Cannot construct build entry {config.build.address}"
        ) from e

    return app


def _init_ato_app() -> "Module":
    """Initialize a specific .ato build."""

    from atopile import front_end
    from atopile.datatypes import Ref
    from faebryk.libs.library import L

    node = front_end.bob.build_file(
        config.build.entry_file_path,
        Ref(config.build.entry_section.split(".")),
    )
    assert isinstance(node, L.Module)
    return node
