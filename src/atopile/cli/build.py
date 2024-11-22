"""CLI command definition for `ato build`."""

import importlib.util
import json
import logging
import sys
import uuid
from typing import Annotated

import typer

import atopile.config
from atopile import buildutil, errors
from atopile.cli.common import create_build_contexts
from atopile.config import BuildContext, BuildType
from atopile.errors import ExceptionAccumulator
from faebryk.core.module import Module

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
                        log.error("Building .ato modules is not currently supported")
                        continue
                    case BuildType.PYTHON:
                        app = _init_python_app(build_ctx)
                    case _:
                        raise ValueError(f"Unknown build type: {build_ctx.build_type}")

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


def import_from_path(file_path):
    # setting to a sequence (and not None) indicates that the module is a package, which lets us use relative imports for submodules
    submodule_search_locations = []

    # custom unique name to avoid collisions
    module_name = str(uuid.uuid4())

    spec = importlib.util.spec_from_file_location(
        module_name, file_path, submodule_search_locations=submodule_search_locations
    )
    if spec is None:
        raise errors.AtoPythonLoadError(f"Failed to load {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    assert spec.loader is not None

    spec.loader.exec_module(module)
    return module


def _init_python_app(build_ctx: BuildContext) -> Module:
    """Initialize a specific .py build."""

    try:
        build_module = import_from_path(build_ctx.entry.file_path)
    except ImportError as e:
        raise errors.AtoPythonLoadError(
            f"Cannot import build entry {build_ctx.entry.file_path}"
        ) from e

    try:
        app_class = getattr(build_module, build_ctx.entry.entry_section)
    except AttributeError as e:
        raise errors.AtoPythonLoadError(
            f"Build entry {build_ctx.entry.file_path} has no module named {build_ctx.entry.entry_section}"
        ) from e

    app = app_class()

    return app


def _init_ato_app(build_ctx: BuildContext) -> Module:
    """Initialize a specific .ato build."""
    raise errors.AtoNotImplementedError("ato builds are not implemented yet")
    do_prebuild(build_ctx)
