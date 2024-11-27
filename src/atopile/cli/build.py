"""CLI command definition for `ato build`."""

import json
import logging
from typing import Annotated

import typer

import atopile.config
from atopile import buildutil, errors, front_end
from atopile.cli.common import create_build_contexts
from atopile.config import BuildContext, BuildType
from atopile.datatypes import Ref
from atopile.errors import ExceptionAccumulator
from faebryk.core.module import Module
from faebryk.library import _F as F
from faebryk.libs.picker import lcsc
from faebryk.libs.util import import_from_path

log = logging.getLogger(__name__)


@errors.muffle_fatalities()
@errors.log_ato_errors()
def build(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    option: Annotated[
        list[str], typer.Option("--option", "-o", envvar="ATO_OPTION")
    ] = [],
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Optionally specify a different entrypoint with the argument ENTRY.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    build_ctxs = create_build_contexts(entry, build, target, option)

    with ExceptionAccumulator() as accumulator:
        for build_ctx in build_ctxs:
            log.info("Building %s", build_ctx.name)
            with accumulator.collect():
                match build_ctx.build_type:
                    case BuildType.ATO:
                        app = _init_ato_app(build_ctx)
                    case BuildType.PYTHON:
                        app = _init_python_app(build_ctx)
                    case _:
                        raise ValueError(f"Unknown build type: {build_ctx.build_type}")

                app.add(F.is_app_root())

                # TODO: these should be drawn from the buildcontext like everything else
                lcsc.BUILD_FOLDER = build_ctx.build_path
                lcsc.LIB_FOLDER = (
                    build_ctx.build_path / build_ctx.layout_path.parent / "lib"
                )  # TODO: move this to the buildcontext
                lcsc.LIB_FOLDER.mkdir(exist_ok=True, parents=True)
                # lcsc.MODEL_PATH = None  # TODO: assign to something to download the 3d models

                # TODO: add a mechanism to override the following with custom build machinery
                buildutil.build(build_ctx, app)

        with accumulator.collect():
            project_context = atopile.config.get_project_context()

            # FIXME: this should be done elsewhere, but there's no other "overview"
            # that can see all the builds simultaneously
            manifest = {}
            manifest["version"] = "2.0"
            for ctx in build_ctxs:
                if ctx.layout_path:
                    by_layout_manifest = manifest.setdefault(
                        "by-layout", {}
                    ).setdefault(str(ctx.layout_path), {})
                    by_layout_manifest["layouts"] = str(
                        ctx.output_base.with_suffix(".layouts.json")
                    )

            manifest_path = project_context.project_path / "build" / "manifest.json"
            manifest_path.parent.mkdir(exist_ok=True, parents=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)

    log.info("Build complete!")


def do_prebuild(build_ctx: BuildContext) -> None:
    with ExceptionAccumulator() as _:
        if not build_ctx.dont_solve_equations:
            raise errors.AtoNotImplementedError(
                "Equation solving is not implemented yet"
            )


def _init_python_app(build_ctx: BuildContext) -> Module:
    """Initialize a specific .py build."""

    try:
        app_class = import_from_path(
            build_ctx.entry.file_path, build_ctx.entry.entry_section
        )
    except (FileNotFoundError, ImportError) as e:
        raise errors.AtoPythonLoadError(
            f"Cannot import build entry {build_ctx.entry.file_path}"
        ) from e
    except AttributeError as e:
        raise errors.AtoPythonLoadError(
            f"Build entry {build_ctx.entry.file_path} has no module named {build_ctx.entry.entry_section}"
        ) from e

    if not isinstance(app_class, type):
        raise errors.AtoPythonLoadError(
            f"Build entry {build_ctx.entry.file_path} is not a module we can instantiate"
        )

    app = app_class()

    return app


def _init_ato_app(build_ctx: BuildContext) -> Module:
    """Initialize a specific .ato build."""
    return front_end.bob.build_file(
        build_ctx.entry.file_path, Ref(build_ctx.entry.entry_section.split("."))
    )
