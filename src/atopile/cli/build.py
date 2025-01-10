"""CLI command definition for `ato build`."""

import logging
from typing import TYPE_CHECKING, Annotated

import typer

from atopile import errors
from atopile.config import BuildContext

if TYPE_CHECKING:
    from faebryk.core.module import Module

logger = logging.getLogger(__name__)


def build(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
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
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Optionally specify a different entrypoint with the argument ENTRY.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    import json

    import atopile.config
    from atopile import buildutil
    from atopile.cli.common import create_build_contexts
    from atopile.config import BuildType
    from faebryk.library import _F as F
    from faebryk.libs.exceptions import accumulate, log_user_errors
    from faebryk.libs.picker import lcsc

    build_ctxs = create_build_contexts(entry, build, target, option, standalone)

    for build_ctx in build_ctxs:
        if keep_picked_parts is not None:
            build_ctx.keep_picked_parts = keep_picked_parts

        if keep_net_names is not None:
            build_ctx.keep_net_names = keep_net_names

        if frozen is not None:
            build_ctx.frozen = frozen
            if frozen:
                if keep_picked_parts is False:  # is, ignores None
                    raise errors.UserBadParameterError(
                        "`--keep-picked-parts` conflict with `--frozen`"
                    )

                build_ctx.keep_picked_parts = True

                if keep_net_names is False:  # is, ignores None
                    raise errors.UserBadParameterError(
                        "`--keep-net-names` conflict with `--frozen`"
                    )

                build_ctx.keep_net_names = True

    with accumulate() as accumulator:
        for build_ctx in build_ctxs:
            logger.info("Building '%s'", build_ctx.name)
            with accumulator.collect(), log_user_errors(logger):
                match build_ctx.build_type:
                    case BuildType.ATO:
                        app = _init_ato_app(build_ctx)
                    case BuildType.PYTHON:
                        app = _init_python_app(build_ctx)
                        app.add(F.is_app_root())
                    case _:
                        raise ValueError(f"Unknown build type: {build_ctx.build_type}")

                # TODO: these should be drawn from the buildcontext like everything else
                lcsc.BUILD_FOLDER = build_ctx.paths.build
                lcsc.LIB_FOLDER = build_ctx.paths.component_lib
                lcsc.LIB_FOLDER.mkdir(exist_ok=True, parents=True)
                lcsc.KICAD_PROJECT_PATH = build_ctx.paths.kicad_project.parent

                # TODO: add a mechanism to override the following with custom build machinery # noqa: E501  # pre-existing
                buildutil.build(build_ctx, app)

        with accumulator.collect():
            project_context = atopile.config.get_project_context()

            # FIXME: this should be done elsewhere, but there's no other "overview"
            # that can see all the builds simultaneously
            manifest = {}
            manifest["version"] = "2.0"
            for ctx in build_ctxs:
                if ctx.paths.layout:
                    by_layout_manifest = manifest.setdefault(
                        "by-layout", {}
                    ).setdefault(str(ctx.paths.layout), {})
                    by_layout_manifest["layouts"] = str(
                        ctx.paths.output_base.with_suffix(".layouts.json")
                    )

            manifest_path = project_context.project_path / "build" / "manifest.json"
            manifest_path.parent.mkdir(exist_ok=True, parents=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)

    logger.info("Build successful! 🚀")


def _init_python_app(build_ctx: BuildContext) -> "Module":
    """Initialize a specific .py build."""

    from atopile import errors
    from faebryk.libs.util import import_from_path

    try:
        app_class = import_from_path(
            build_ctx.entry.file_path, build_ctx.entry.entry_section
        )
    except FileNotFoundError as e:
        raise errors.UserFileNotFoundError(
            f"Cannot find build entry {build_ctx.entry.file_path}"
        ) from e
    except Exception as e:
        raise errors.UserPythonModuleError(
            f"Cannot import build entry {build_ctx.entry.file_path}"
        ) from e

    if not isinstance(app_class, type):
        raise errors.UserPythonLoadError(
            f"Build entry {build_ctx.entry.file_path} is not a module we can instantiate"  # noqa: E501  # pre-existing
        )

    try:
        app = app_class()
    except Exception as e:
        raise errors.UserPythonConstructionError(
            f"Cannot construct build entry {build_ctx.entry.file_path}"
        ) from e

    return app


def _init_ato_app(build_ctx: BuildContext) -> "Module":
    """Initialize a specific .ato build."""

    from atopile import front_end
    from atopile.datatypes import Ref
    from faebryk.libs.library import L

    node = front_end.bob.build_file(
        build_ctx.entry.file_path, Ref(build_ctx.entry.entry_section.split("."))
    )
    assert isinstance(node, L.Module)
    return node
