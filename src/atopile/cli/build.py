"""CLI command definition for `ato build`."""
import itertools
import json
import logging
import shutil
from typing import Callable, Optional

import click

import atopile.assertions
import atopile.bom
import atopile.config
import atopile.front_end
import atopile.layout
import atopile.manufacturing_data
import atopile.netlist
import atopile.variable_report
from atopile.cli.common import project_options
from atopile.components import download_footprint
from atopile.config import BuildContext
from atopile.errors import ExceptionAccumulator
from atopile.instance_methods import all_descendants, match_components
from atopile.netlist import get_netlist_as_str

log = logging.getLogger(__name__)


@click.command()
@project_options
def build(build_ctxs: list[BuildContext]):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Specify the root source file with the argument SOURCE.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    with ExceptionAccumulator() as err_cltr:
        for build_ctx in build_ctxs:
            log.info("Building %s", build_ctx.name)
            with err_cltr():
                _do_build(build_ctx)

        with err_cltr():
            project_context = atopile.config.get_project_context()

            # FIXME: this should be done elsewhere, but there's no other "overview"
            # that can see all the builds simultaneously
            manifest = {}
            manifest["version"] = "2.0"
            for ctx in build_ctxs:
                if ctx.layout_path:
                    by_layout_manifest = manifest.setdefault("by-layout", {}).setdefault(str(ctx.layout_path), {})
                    by_layout_manifest["layouts"] = str(ctx.output_base.with_suffix(".layouts.json"))

            manifest_path = project_context.project_path / "build" / "manifest.json"
            manifest_path.parent.mkdir(exist_ok=True, parents=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)

    log.info("Build complete!")


def do_prebuild(build_ctx: BuildContext) -> None:
    with ExceptionAccumulator() as err_cltr:
        # Solve the unknown variables
        if not build_ctx.dont_solve_equations:
            with err_cltr():
                atopile.assertions.simplify_expressions(build_ctx.entry)
                atopile.assertions.solve_assertions(build_ctx)
                atopile.assertions.simplify_expressions(build_ctx.entry)


def _do_build(build_ctx: BuildContext) -> None:
    """Execute a specific build."""
    do_prebuild(build_ctx)

    with ExceptionAccumulator() as err_cltr:
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
        targets = set(targets) - excluded_targets & known_targets

        # Ensure the output directory exists
        build_ctx.output_base.parent.mkdir(parents=True, exist_ok=True)

        # Make the noise
        built_targets = []
        for target_name in targets:
            log.info(f"Building '{target_name}' for '{build_ctx.name}' config")
            with err_cltr():
                muster.targets[target_name](build_ctx)
            built_targets.append(target_name)

    log.info(f"Successfully built '{', '.join(built_targets)}' for '{build_ctx.name}' config")


TargetType = Callable[[BuildContext], None]


class Muster:
    """A class to register targets to."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.targets = {}
        self.do_by_default = []
        self.log = logger or logging.getLogger(__name__)

    def add_target(self, func: TargetType, name: Optional[str] = None, default: bool = True):
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
    with open(build_args.output_base.with_suffix(".net"), "w", encoding="utf-8") as f:
        f.write(get_netlist_as_str(build_args.entry))


@muster.register("bom")
def generate_bom(build_args: BuildContext) -> None:
    """Generate a BOM for the project."""
    with open(build_args.output_base.with_suffix(".csv"), "w", encoding="utf-8") as f:
        f.write(atopile.bom.generate_bom(build_args.entry))


@muster.register("designator-map")
def generate_designator_map(build_args: BuildContext) -> None:
    """Generate a designator map for the project."""
    atopile.bom.generate_designator_map(build_args.entry)


@muster.register("mfg-data", default=False)
def generate_manufacturing_data(build_ctx: BuildContext) -> None:
    """Generate a designator map for the project."""
    atopile.manufacturing_data.generate_manufacturing_data(build_ctx)


@muster.register("drc", default=False)
def generate_drc_report(build_ctx: BuildContext) -> None:
    """Generate a designator map for the project."""
    atopile.manufacturing_data.generate_drc_report(build_ctx)


@muster.register("clone-footprints")
def clone_footprints(build_args: BuildContext) -> None:
    """Clone the footprints for the project."""
    all_components = filter(match_components, all_descendants(build_args.entry))

    for component in all_components:
        log.debug("Cloning footprint for %s", component)
        download_footprint(component, footprint_dir=build_args.build_path / "footprints/footprints.pretty")


@muster.register("layout-module-map")
def generate_module_map(build_args: BuildContext) -> None:
    """Generate a designator map for the project."""
    atopile.layout.generate_module_map(build_args)


@muster.register("assertions-report")
def generate_assertion_report(build_ctx: BuildContext) -> None:
    """Generate a report based on assertions made in the source code."""
    atopile.assertions.generate_assertion_report(build_ctx)


@muster.register("variable-report")
def generate_variable_report(build_ctx: BuildContext) -> None:
    """Generate a report of all the variable values in the design."""
    atopile.variable_report.generate(build_ctx)
