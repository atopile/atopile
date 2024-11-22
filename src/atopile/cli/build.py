"""CLI command definition for `ato build`."""

import importlib.util
import itertools
import json
import logging
import shutil
import sys
import uuid
from typing import Annotated, Callable, Optional

import typer

import atopile.config
from atopile import errors
from atopile.cli.common import create_build_contexts
from atopile.config import BuildContext, BuildType
from atopile.errors import ExceptionAccumulator
from faebryk.core.module import Module
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import export_svg
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.manufacturing import export_pcba_artifacts
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.app.pcb import apply_design
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.picker import pick_part_recursively

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
                    case BuildType.PYTHON:
                        _do_python_build(build_ctx)

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


def _do_python_build(build_ctx: BuildContext) -> None:
    """Execute a specific .py build."""

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

    # TODO: add a mechanism to override the following with custom build machinery

    try:
        log.info("Filling unspecified parameters")
        replace_tbd_with_any(app, recursive=True)

        log.info("Picking parts")
        modules = {
            n.get_most_special()
            for n in app.get_children(direct_only=False, types=Module)
        }
        for n in modules:
            # TODO: make configurable
            add_api_pickers(n, base_prio=10)
        pick_part_recursively(app)

        log.info("Make graph")
        G = app.get_graph()

        log.info("Running checks")
        run_checks(app, G)

        log.info("Make netlist & pcb")
        apply_design(
            build_ctx.layout_path, build_ctx.netlist_path, G, app, transform=None
        )
    except Exception as e:
        raise errors.AtoError(f"Error building {build_ctx.name}") from e

    if build_ctx.export_manufacturing_artifacts:
        export_pcba_artifacts(build_ctx.output_base, build_ctx.layout_path, app)

    if build_ctx.export_visuals:
        export_svg(build_ctx.layout_path, build_ctx.visuals_path)

    if build_ctx.export_parameters:
        export_parameters_to_file(app, build_ctx.parameters_path)


def _do_ato_build(build_ctx: BuildContext) -> None:
    """Execute a specific .ato build."""
    do_prebuild(build_ctx)

    with ExceptionAccumulator() as accumulator:
        # Ensure the build directory exists
        log.info("Writing outputs to %s", build_ctx.build_path)
        build_ctx.build_path.mkdir(parents=True, exist_ok=True)

        # Figure out what targets to build
        if build_ctx.targets == ["__default__"]:
            targets = muster.do_by_default
        elif build_ctx.targets == ["*"] or build_ctx.targets == ["all"]:
            targets = list(muster.targets.keys())
        else:
            targets = build_ctx.targets

        # Remove targets we don't know about, or are excluded
        excluded_targets = set(build_ctx.exclude_targets)
        known_targets = set(muster.targets.keys())
        targets = list(set(targets) - excluded_targets & known_targets)

        # Ensure the output directory exists
        build_ctx.output_base.parent.mkdir(parents=True, exist_ok=True)

        # Make the noise
        built_targets = []
        for target_name in targets:
            log.info(f"Building '{target_name}' for '{build_ctx.name}' config")
            with accumulator.collect():
                muster.targets[target_name](build_ctx)
            built_targets.append(target_name)

    log.info(
        f"Successfully built '{', '.join(built_targets)}' for '{build_ctx.name}' config"
    )


TargetType = Callable[[BuildContext], None]


class Muster:
    """A class to register targets to."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.targets: dict[str, TargetType] = {}
        self.do_by_default: list[str] = []
        self.log = logger or logging.getLogger(__name__)

    def add_target(
        self, func: TargetType, name: Optional[str] = None, default: bool = True
    ):
        """Register a function as a target."""
        name = name or func.__name__
        self.targets[name] = func
        if default:
            self.do_by_default.append(name)
        return func

    def register(self, name: Optional[str] = None, default: bool = True):
        """Register a target under a given name."""

        def decorator(func: TargetType):
            self.add_target(func, name, default)
            return func

        return decorator


muster = Muster()


@muster.register("copy-footprints")
def consolidate_footprints(build_args: BuildContext) -> None:
    """Consolidate all the project's footprints into a single directory."""
    fp_target = build_args.build_path / "footprints" / "footprints.pretty"
    fp_target_step = build_args.build_path / "footprints" / "footprints.3dshapes"
    fp_target.mkdir(exist_ok=True, parents=True)

    for fp in atopile.config.get_project_context().project_path.glob("**/*.kicad_mod"):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            log.debug("Footprint %s already exists in the target directory", fp)

    # Post-process all the footprints in the target directory
    for fp in fp_target.glob("**/*.kicad_mod"):
        with open(fp, "r+", encoding="utf-8") as file:
            content = file.read()
            content = content.replace("{build_dir}", str(fp_target_step))
            file.seek(0)
            file.write(content)
            file.truncate()


@muster.register("copy-3dmodels")
def consolidate_3dmodels(build_args: BuildContext) -> None:
    """Consolidate all the project's 3d models into a single directory."""
    fp_target = build_args.build_path / "footprints" / "footprints.3dshapes"
    fp_target.mkdir(exist_ok=True, parents=True)

    prj_path = atopile.config.get_project_context().project_path

    for fp in itertools.chain(prj_path.glob("**/*.step"), prj_path.glob("**/*.wrl")):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            log.debug("Footprint %s already exists in the target directory", fp)


@muster.register("netlist")
def generate_netlist(build_args: BuildContext) -> None:
    """Generate a netlist for the project."""
    raise errors.AtoNotImplementedError("Netlist generation is not implemented yet")


@muster.register("bom")
def generate_bom(build_args: BuildContext) -> None:
    """Generate a BOM for the project."""
    raise errors.AtoNotImplementedError("BOM generation is not implemented yet")


@muster.register("designator-map")
def generate_designator_map(build_args: BuildContext) -> None:
    """Generate a designator map for the project."""
    raise errors.AtoNotImplementedError(
        "Designator map generation is not implemented yet"
    )


@muster.register("mfg-data", default=False)
def generate_manufacturing_data(build_ctx: BuildContext) -> None:
    """Generate a designator map for the project."""
    raise errors.AtoNotImplementedError(
        "Manufacturing data generation is not implemented yet"
    )


@muster.register("drc", default=False)
def generate_drc_report(build_ctx: BuildContext) -> None:
    """Generate a designator map for the project."""
    raise errors.AtoNotImplementedError("DRC report generation is not implemented yet")


@muster.register("clone-footprints")
def clone_footprints(build_args: BuildContext) -> None:
    """Clone the footprints for the project."""
    raise errors.AtoNotImplementedError("Footprint cloning is not implemented yet")


@muster.register("layout-module-map")
def generate_module_map(build_args: BuildContext) -> None:
    """Generate a designator map for the project."""
    raise errors.AtoNotImplementedError("Module map generation is not implemented yet")


@muster.register("assertions-report")
def generate_assertion_report(build_ctx: BuildContext) -> None:
    """Generate a report based on assertions made in the source code."""
    raise errors.AtoNotImplementedError(
        "Assertion report generation is not implemented yet"
    )


@muster.register("variable-report")
def generate_variable_report(build_ctx: BuildContext) -> None:
    """Generate a report of all the variable values in the design."""
    raise errors.AtoNotImplementedError(
        "Variable report generation is not implemented yet"
    )
