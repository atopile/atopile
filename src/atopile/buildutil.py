import logging
from typing import Callable, Optional

from atopile import layout
from atopile.config import BuildContext
from atopile.errors import ExceptionAccumulator
from faebryk.core.module import Module
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
)
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.app.pcb import apply_design
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.picker import pick_part_recursively

logger = logging.getLogger(__name__)


def build(build_ctx: BuildContext, app: Module) -> None:
    """Build the project."""

    # TODO: consider making each of these a configurable target
    logger.info("Filling unspecified parameters")
    replace_tbd_with_any(app, recursive=True)

    logger.info("Picking parts")
    modules = {
        n.get_most_special() for n in app.get_children(direct_only=False, types=Module)
    }
    for n in modules:
        # TODO: make configurable
        add_api_pickers(n, base_prio=10)
    pick_part_recursively(app)

    logger.info("Make graph")
    G = app.get_graph()

    logger.info("Running checks")
    run_checks(app, G)

    logger.info("Make netlist & pcb")
    apply_design(build_ctx.layout_path, build_ctx.netlist_path, G, app, transform=None)

    # Ensure the build directory exists
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
    with ExceptionAccumulator() as accumulator:
        for target_name in targets:
            logger.info(f"Building '{target_name}' for '{build_ctx.name}' config")
            with accumulator.collect():
                muster.targets[target_name](build_ctx, app)
            built_targets.append(target_name)

    logger.info(f"Built '{', '.join(built_targets)}' for '{build_ctx.name}' config")


TargetType = Callable[[BuildContext, Module], None]


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


@muster.register("bom")
def generate_bom(build_ctx: BuildContext, app: Module) -> None:
    """Generate a BOM for the project."""
    write_bom_jlcpcb(
        app.get_children_modules(types=Module),
        build_ctx.output_base.with_suffix(".bom.csv"),
    )


@muster.register("mfg-data", default=False)
def generate_manufacturing_data(build_ctx: BuildContext, app: Module) -> None:
    """Generate a designator map for the project."""
    export_step(
        build_ctx.layout_path, step_file=build_ctx.output_base.with_suffix(".pcba.step")
    )
    export_glb(
        build_ctx.layout_path, glb_file=build_ctx.output_base.with_suffix(".pcba.glb")
    )
    export_dxf(
        build_ctx.layout_path, dxf_file=build_ctx.output_base.with_suffix(".pcba.dxf")
    )

    export_gerber(
        build_ctx.layout_path,
        gerber_zip_file=build_ctx.output_base.with_suffix(".gerber.zip"),
    )

    pnp_file = build_ctx.output_base.with_suffix(".pick_and_place.csv")
    export_pick_and_place(build_ctx.layout_path, pick_and_place_file=pnp_file)
    convert_kicad_pick_and_place_to_jlcpcb(
        pnp_file,
        build_ctx.output_base.with_suffix(".jlcpcb_pick_and_place.csv"),
    )


@muster.register("layout-module-map", default=False)
def generate_module_map(build_ctx: BuildContext, app: Module) -> None:
    """Generate a designator map for the project."""
    layout.generate_module_map(build_ctx, app)


@muster.register("variable-report")
def generate_variable_report(build_ctx: BuildContext, app: Module) -> None:
    """Generate a report of all the variable values in the design."""
    export_parameters_to_file(app, build_ctx.output_base / "variables.md")
