"""CLI command definition for `ato build`."""
import json
import logging
import shutil
from functools import wraps
from typing import Callable, Optional

import click

import atopile.bom
import atopile.config
import atopile.front_end
import atopile.layout
import atopile.manufacturing_data
import atopile.netlist
import atopile.assertions
from atopile.cli.common import project_options
from atopile.components import configure_cache, download_footprint
from atopile.config import BuildContext
from atopile.errors import handle_ato_errors, iter_through_errors
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
    for err_cltr, build_ctx in iter_through_errors(build_ctxs):
        log.info("Building %s", build_ctx.name)
        with err_cltr():
            _do_build(build_ctx)

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


def _do_build(build_ctx: BuildContext) -> None:
    """Execute a specific build."""

    # Configure the cache for component data
    # TODO: flip this around so that the cache pulls what it needs from the
    # project context
    configure_cache(atopile.config.get_project_context().project_path)

    # Solve the unknown variables
    atopile.assertions.solve_assertions(build_ctx)

    # Ensure the build directory exists
    log.info("Writing outputs to %s", build_ctx.build_path)
    build_ctx.build_path.mkdir(parents=True, exist_ok=True)

    if build_ctx.targets == ["__default__"]:
        targets = muster.do_by_default
    elif build_ctx.targets == ["*"] or build_ctx.targets == ["all"]:
        targets = list(muster.targets.keys())
    else:
        targets = build_ctx.targets

    build_ctx.output_base.parent.mkdir(parents=True, exist_ok=True)

    for err_cltr, target_name in iter_through_errors(targets):
        log.info("Building %s", target_name)
        with err_cltr():
            muster.targets[target_name](build_ctx)


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
            @wraps(func)
            def wrapper(build_args: BuildContext):
                with handle_ato_errors():
                    return func(build_args)

            self.add_target(wrapper, name, default)
            return wrapper

        return decorator


muster = Muster()


@muster.register("copy-footprints")
def consolidate_footprints(build_args: BuildContext) -> None:
    """Consolidate all the project's footprints into a single directory."""
    fp_target = build_args.build_path / "footprints" / "footprints.pretty"
    fp_target.mkdir(exist_ok=True, parents=True)

    for fp in atopile.config.get_project_context().project_path.glob("**/*.kicad_mod"):
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
