import logging
import shutil
from typing import Callable, Optional

from atopile import layout
from atopile.config import BuildContext
from atopile.front_end import DeprecatedException
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
)
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.library import _F as F
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.designators import (
    attach_designators,
    attach_random_designators,
    override_names_with_designators,
)
from faebryk.libs.app.parameters import resolve_dynamic_parameters
from faebryk.libs.app.pcb import (
    apply_layouts,
    apply_netlist,
    apply_routing,
)
from faebryk.libs.exceptions import (
    ExceptionAccumulator,
    UserResourceException,
    downgrade,
)
from faebryk.libs.kicad.fileformats import C_kicad_fp_lib_table_file, C_kicad_pcb_file
from faebryk.libs.picker.api.api import ApiNotConfiguredError
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.picker import pick_part_recursively

logger = logging.getLogger(__name__)


def build(build_ctx: BuildContext, app: Module) -> None:
    """Build the project."""
    G = app.get_graph()
    solver = DefaultSolver()
    build_ctx.ensure_paths()
    build_paths = build_ctx.paths

    logger.info("Resolving dynamic parameters")
    resolve_dynamic_parameters(G)

    logger.info("Running checks")
    run_checks(app, G)

    # Pickers ------------------------------------------------------------------
    logger.info("Picking parts")
    modules = app.get_children_modules(types=Module)
    # TODO currently slow
    # CachePicker.add_to_modules(modules, prio=-20)

    try:
        for n in modules:
            add_api_pickers(n)
    except ApiNotConfiguredError:
        logger.warning("API not configured. Skipping API pickers.")

    # Included here for use on the examples

    pick_part_recursively(app, solver)

    # Write Netlist ------------------------------------------------------------
    logger.info(f"Writing netlist to {build_paths.netlist}")

    netlist_path = build_paths.netlist

    pcb = C_kicad_pcb_file.loads(build_paths.layout)
    known_designators = PCB_Transformer.load_designators(G, pcb.kicad_pcb)
    attach_designators(known_designators)
    attach_random_designators(G)
    override_names_with_designators(G)

    logger.info("Creating Nets and attach kicad info")
    attach_nets_and_kicad_info(G)

    logger.info("Making faebryk netlist")
    t2 = make_t2_netlist_from_graph(G)
    logger.info("Making kicad netlist")
    netlist = from_faebryk_t2_netlist(t2).dumps()

    logger.info("Writing Experiment netlist to {}".format(netlist_path.resolve()))
    netlist_path.parent.mkdir(parents=True, exist_ok=True)
    netlist_path.write_text(netlist, encoding="utf-8")

    # Update PCB --------------------------------------------------------------
    logger.info("Updating PCB")

    consolidate_footprints(build_ctx)
    apply_netlist(build_paths, False)

    pcb = C_kicad_pcb_file.loads(build_paths.layout)

    transformer = PCB_Transformer(pcb.kicad_pcb, G, app)

    if transform_trait := app.try_get_trait(F.has_layout_transform):
        logger.info("Transforming PCB")
        transform_trait.transform(transformer)

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    logger.info(f"Writing pcbfile {build_paths.layout}")
    pcb.dumps(build_paths.layout)

    # Build targets -----------------------------------------------------------
    logger.info("Building targets")

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
        build_ctx.paths.output_base.with_suffix(".bom.csv"),
    )


@muster.register("mfg-data", default=False)
def generate_manufacturing_data(build_ctx: BuildContext, app: Module) -> None:
    """Generate a designator map for the project."""
    export_step(
        build_ctx.paths.layout,
        step_file=build_ctx.paths.output_base.with_suffix(".pcba.step"),
    )
    export_glb(
        build_ctx.paths.layout,
        glb_file=build_ctx.paths.output_base.with_suffix(".pcba.glb"),
    )
    export_dxf(
        build_ctx.paths.layout,
        dxf_file=build_ctx.paths.output_base.with_suffix(".pcba.dxf"),
    )

    export_gerber(
        build_ctx.paths.layout,
        gerber_zip_file=build_ctx.paths.output_base.with_suffix(".gerber.zip"),
    )

    pnp_file = build_ctx.paths.output_base.with_suffix(".pick_and_place.csv")
    export_pick_and_place(build_ctx.paths.layout, pick_and_place_file=pnp_file)
    convert_kicad_pick_and_place_to_jlcpcb(
        pnp_file,
        build_ctx.paths.output_base.with_suffix(".jlcpcb_pick_and_place.csv"),
    )


@muster.register("layout-module-map")
def generate_module_map(build_ctx: BuildContext, app: Module) -> None:
    """Generate a designator map for the project."""
    layout.generate_module_map(build_ctx, app)


@muster.register("variable-report")
def generate_variable_report(build_ctx: BuildContext, app: Module) -> None:
    """Generate a report of all the variable values in the design."""
    export_parameters_to_file(app, build_ctx.paths.output_base / "variables.md")


def consolidate_footprints(build_ctx: BuildContext) -> None:
    """
    Consolidate all the project's footprints into a single directory.

    TODO: @v0.4 remove this, it's a fallback for v0.2 designs
    If there's an entry named "lib" pointing at "build/footprints/footprints.pretty"
    then copy all footprints we can find there
    """
    if build_ctx.paths.fp_lib_table.exists():
        fptable = C_kicad_fp_lib_table_file.loads(build_ctx.paths.fp_lib_table)
    else:
        # no fp-lib-table, no worries
        return

    # TODO: @windows might need to check backslashes
    if not any(
        lib.name == "lib" and lib.uri.endswith("build/footprints/footprints.pretty")
        for lib in fptable.fp_lib_table.libs
    ):
        # no "lib" entry pointing to the footprints dir, this project isn't broken
        return

    fp_target = build_ctx.paths.build / "footprints" / "footprints.pretty"
    fp_target_step = build_ctx.paths.build / "footprints" / "footprints.3dshapes"
    fp_target.mkdir(exist_ok=True, parents=True)

    if not build_ctx.paths.root:
        with downgrade(UserResourceException):
            raise UserResourceException(
                "No project root directory found. Cannot consolidate footprints."
            )
        return

    for fp in build_ctx.paths.root.glob("**/*.kicad_mod"):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            logger.debug("Footprint %s already exists in the target directory", fp)

    # Post-process all the footprints in the target directory
    for fp in fp_target.glob("**/*.kicad_mod"):
        with open(fp, "r+", encoding="utf-8") as file:
            content = file.read()
            content = content.replace("{build_dir}", str(fp_target_step))
            file.seek(0)
            file.write(content)
            file.truncate()

    with downgrade(DeprecatedException):
        raise DeprecatedException(
            "This project uses a deprecated footprint consolidation mechanism."
        )
