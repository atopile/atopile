import json
import logging
import shutil
import time
from copy import deepcopy
from pathlib import Path
from typing import Callable, Optional

from more_itertools import first

from atopile import layout
from atopile.config import config
from atopile.errors import UserException, UserPickError
from atopile.front_end import DeprecatedException
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.solver import Solver
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.netlist.graph import attach_net_names, attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import faebryk_netlist_to_kicad
from faebryk.exporters.netlist.netlist import make_fbrk_netlist_from_graph
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
)
from faebryk.exporters.pcb.kicad.pcb import LibNotInTable, get_footprint
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.library import _F as F
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.designators import (
    attach_random_designators,
    load_designators,
)
from faebryk.libs.app.pcb import (
    apply_layouts,
    apply_netlist,
    apply_routing,
    create_footprint_library,
    ensure_footprint_lib,
    load_net_names,
    open_pcb,
)
from faebryk.libs.app.picking import load_descriptive_properties
from faebryk.libs.exceptions import (
    UserResourceException,
    accumulate,
    downgrade,
    iter_through_errors,
)
from faebryk.libs.kicad.fileformats import (
    C_kicad_footprint_file,
    C_kicad_fp_lib_table_file,
    C_kicad_pcb_file,
)
from faebryk.libs.picker.picker import PickError, pick_part_recursively
from faebryk.libs.util import KeyErrorAmbiguous, cast_assert, once

logger = logging.getLogger(__name__)


def build(app: Module) -> None:
    """Build the project."""
    G = app.get_graph()
    solver = DefaultSolver()

    logger.info("Resolving bus parameters")
    try:
        F.is_bus_parameter.resolve_bus_parameters(G)
    # FIXME: this is a hack around a compiler bug
    except KeyErrorAmbiguous as ex:
        raise UserException(
            "Unfortunately, there's a compiler bug at the moment that means that "
            "this sometimes fails. Try again, and it'll probably work. "
            "See https://github.com/atopile/atopile/issues/807"
        ) from ex

    logger.info("Running checks")
    run_checks(app, G)

    # Pre-pick project checks - things to look at before time is spend ---------
    # Make sure the footprint libraries we're looking for exist
    consolidate_footprints(app)

    # Load PCB / cached --------------------------------------------------------
    pcb = C_kicad_pcb_file.loads(config.build.paths.layout)
    transformer = PCB_Transformer(pcb.kicad_pcb, G, app, cleanup=False)
    load_designators(G, attach=True)

    # Pre-run solver -----------------------------------------------------------
    parameters = app.get_children(False, types=Parameter)
    if parameters:
        logger.info("Simplifying parameter graph")
        solver.inspect_get_known_supersets(first(parameters), force_update=True)

    # Pickers ------------------------------------------------------------------
    if config.build.keep_picked_parts:
        load_descriptive_properties(G)
    try:
        pick_part_recursively(app, solver)
    except PickError as ex:
        raise UserPickError.from_pick_error(ex) from ex

    # Footprints ----------------------------------------------------------------
    # Use standard footprints for known packages regardless of
    # what's otherwise been specified.
    # FIXME: this currently includes explicitly set footprints, but shouldn't
    standardize_footprints(app, solver)
    create_footprint_library(app)

    # Write Netlist ------------------------------------------------------------
    attach_random_designators(G)
    nets = attach_nets_and_kicad_info(G)
    if config.build.keep_net_names:
        load_net_names(G)
    attach_net_names(nets)
    netlist = faebryk_netlist_to_kicad(make_fbrk_netlist_from_graph(G))

    # Update PCB --------------------------------------------------------------
    logger.info("Updating PCB")
    original_pcb = deepcopy(pcb)
    apply_netlist(files=(pcb, netlist))

    # Re-attach now that any new footprints have been created / standardised
    transformer.attach(check_unattached=True)
    transformer.cleanup()

    if transform_trait := app.try_get_trait(F.has_layout_transform):
        logger.info("Transforming PCB")
        transform_trait.transform(transformer)

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    if pcb == original_pcb:
        if config.build.frozen:
            logger.info("No changes to layout. Passed --frozen check.")
        else:
            logger.info(
                f"No changes to layout. Not writing {config.build.paths.layout}"
            )
    elif config.build.frozen:
        original_path = config.build.paths.output_base.with_suffix(
            ".original.kicad_pcb"
        )
        updated_path = config.build.paths.output_base.with_suffix(".updated.kicad_pcb")
        original_pcb.dumps(original_path)
        pcb.dumps(updated_path)

        # TODO: make this a real util
        def _try_relative(path: Path) -> Path:
            try:
                return path.relative_to(Path.cwd(), walk_up=True)
            except ValueError:
                return path

        original_relative = _try_relative(original_path)
        updated_relative = _try_relative(updated_path)

        raise UserException(
            "Built as frozen, but layout changed. \n"
            f"Original layout: {original_relative}\n"
            f"Updated layout: {updated_relative}\n"
            "You can see the changes by running:\n"
            f'diff --color "{original_relative}" "{updated_relative}"',
            title="Frozen failed",
        )
    else:
        backup_file = config.build.paths.output_base.with_suffix(
            f".{time.strftime('%Y%m%d-%H%M%S')}.kicad_pcb"
        )
        logger.info(f"Backing up layout to {backup_file}")
        with config.build.paths.layout.open("rb") as f:
            backup_file.write_bytes(f.read())

        logger.info(f"Updating layout {config.build.paths.layout}")
        pcb.dumps(config.build.paths.layout)
        if config.project.pcbnew_auto:
            try:
                open_pcb(config.build.paths.layout)
            except FileNotFoundError:
                pass
            except RuntimeError as e:
                logger.info(
                    f"{e.args[0]}\nReload pcb manually by pressing Ctrl+O; Enter"
                )

    # Build targets -----------------------------------------------------------
    logger.info("Building targets")

    # Figure out what targets to build
    if config.build.targets == ["__default__"]:
        targets = muster.do_by_default
    elif config.build.targets == ["*"] or config.build.targets == ["all"]:
        targets = list(muster.targets.keys())
    else:
        targets = config.build.targets

    # Remove targets we don't know about, or are excluded
    excluded_targets = set(config.build.exclude_targets)
    known_targets = set(muster.targets.keys())
    targets = list(set(targets) - excluded_targets & known_targets)

    # Make the noise
    built_targets = []
    with accumulate() as accumulator:
        for target_name in targets:
            logger.info(f"Building '{target_name}' for '{config.build.name}' config")
            with accumulator.collect():
                muster.targets[target_name](app)
            built_targets.append(target_name)

    logger.info(
        f"Built {', '.join(f'\'{target}\'' for target in built_targets)} "
        f"for '{config.build.name}' config"
    )


TargetType = Callable[[Module], None]


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
def generate_bom(app: Module) -> None:
    """Generate a BOM for the project."""
    write_bom_jlcpcb(
        app.get_children_modules(types=Module),
        config.build.paths.output_base.with_suffix(".bom.csv"),
    )


@muster.register("mfg-data", default=False)
def generate_manufacturing_data(app: Module) -> None:
    """Generate a designator map for the project."""
    export_step(
        config.build.paths.layout,
        step_file=config.build.paths.output_base.with_suffix(".pcba.step"),
    )
    export_glb(
        config.build.paths.layout,
        glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
    )
    export_dxf(
        config.build.paths.layout,
        dxf_file=config.build.paths.output_base.with_suffix(".pcba.dxf"),
    )

    export_gerber(
        config.build.paths.layout,
        gerber_zip_file=config.build.paths.output_base.with_suffix(".gerber.zip"),
    )

    pnp_file = config.build.paths.output_base.with_suffix(".pick_and_place.csv")
    export_pick_and_place(config.build.paths.layout, pick_and_place_file=pnp_file)
    convert_kicad_pick_and_place_to_jlcpcb(
        pnp_file,
        config.build.paths.output_base.with_suffix(".jlcpcb_pick_and_place.csv"),
    )


@muster.register("manifest")
def generate_manifest(app: Module) -> None:
    """Generate a manifest for the project."""
    with accumulate() as accumulator:
        with accumulator.collect():
            manifest = {}
            manifest["version"] = "2.0"
            for build in config.builds:
                with build:
                    if config.build.paths.layout:
                        by_layout_manifest = manifest.setdefault(
                            "by-layout", {}
                        ).setdefault(str(config.build.paths.layout), {})
                        by_layout_manifest["layouts"] = str(
                            config.build.paths.output_base.with_suffix(".layouts.json")
                        )

            manifest_path = config.project.paths.manifest
            manifest_path.parent.mkdir(exist_ok=True, parents=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)


@muster.register("layout-module-map")
def generate_module_map(app: Module) -> None:
    """Generate a designator map for the project."""
    layout.generate_module_map(app)


@muster.register("variable-report")
def generate_variable_report(app: Module) -> None:
    """Generate a report of all the variable values in the design."""
    export_parameters_to_file(
        app, config.build.paths.output_base.with_suffix(".variables.md")
    )


def standardize_footprints(app: Module, solver: Solver) -> None:
    """
    Attach standard footprints for known packages

    This must be done before the create_footprint_library is run
    """
    from atopile.packages import KNOWN_PACKAGES_TO_FOOTPRINT

    gf = GraphFunctions(app.get_graph())

    # TODO: make this caching global. Shit takes time
    @once
    def _get_footprint(fp_path: Path) -> C_kicad_footprint_file:
        return C_kicad_footprint_file.loads(fp_path)

    for node, pkg_t in gf.nodes_with_trait(F.has_package):
        package_superset = solver.inspect_get_known_supersets(pkg_t.package)
        if package_superset.is_empty():
            logger.warning("%s has a package requirement but no candidates", node)
            continue
        elif not package_superset.is_single_element():
            logger.warning("%s has multiple package candidates", node)
            continue

        # Skip nodes with footprints already
        if node.has_trait(F.has_footprint):
            continue

        # We have guaranteed `.any()` returns only one thing
        package = cast_assert(F.has_package.Package, package_superset.any())

        if fp_path := KNOWN_PACKAGES_TO_FOOTPRINT.get(package):
            if can_attach_t := node.try_get_trait(F.can_attach_to_footprint):
                fp = _get_footprint(fp_path)
                kicad_fp = F.KicadFootprint.from_file(fp)
                kicad_fp.add(F.KicadFootprint.has_file(fp_path))
                can_attach_t.attach(kicad_fp)


def consolidate_footprints(app: Module) -> None:
    """
    Consolidate all the project's footprints into a single directory.

    TODO: @v0.4 remove this, it's a fallback for v0.2 designs
    If there's an entry named "lib" pointing at "build/footprints/footprints.pretty"
    then copy all footprints we can find there
    """
    fp_ids_to_check = []
    for fp_t in app.get_children(False, types=(F.has_footprint)):
        fp = fp_t.get_footprint()
        if has_identifier_t := fp.try_get_trait(F.KicadFootprint.has_kicad_identifier):
            fp_ids_to_check.append(has_identifier_t.kicad_identifier)

    try:
        fptable = C_kicad_fp_lib_table_file.loads(config.build.paths.fp_lib_table)
    except FileNotFoundError:
        fptable = C_kicad_fp_lib_table_file.skeleton()

    # TODO: @windows might need to check backslashes
    lib_in_fptable = any(
        lib.name == "lib" and lib.uri.endswith("build/footprints/footprints.pretty")
        for lib in fptable.fp_lib_table.libs
    )
    lib_prefix_on_ids = any(fp_id.startswith("lib:") for fp_id in fp_ids_to_check)
    if not lib_in_fptable and not lib_prefix_on_ids:
        # no "lib" entry pointing to the footprints dir, this project isn't broken
        return
    elif lib_prefix_on_ids and not lib_in_fptable:
        # we need to add a lib entry pointing to the footprints dir
        ensure_footprint_lib(
            "lib",
            config.project.paths.build / "footprints" / "footprints.pretty",
            fptable,
        )
    elif lib_in_fptable and not lib_prefix_on_ids:
        # We could probably just remove the lib entry
        # but let's be conservative for now
        logger.info(
            "It seems like this project is using a legacy footprint consolidation "
            "unnecessarily. You can likely remove the 'lib' entry from the "
            "'fp-lib-table' file."
        )

    fp_target = config.project.paths.build / "footprints" / "footprints.pretty"
    fp_target_step = config.project.paths.build / "footprints" / "footprints.3dshapes"
    fp_target.mkdir(exist_ok=True, parents=True)

    if not config.project.paths.root:
        with downgrade(UserResourceException):
            raise UserResourceException(
                "No project root directory found. Cannot consolidate footprints."
            )
        return

    for fp in config.project.paths.root.glob("**/*.kicad_mod"):
        try:
            shutil.copy(fp, fp_target)
        except shutil.SameFileError:
            logger.debug("Footprint '%s' already exists in the target directory", fp)

    # Post-process all the footprints in the target directory
    for fp in fp_target.glob("**/*.kicad_mod"):
        with open(fp, "r+", encoding="utf-8") as file:
            content = file.read()
            content = content.replace("{build_dir}", str(fp_target_step))
            file.seek(0)
            file.write(content)
            file.truncate()

    # TODO: @v0.4 increase the level of this to WARNING
    # when there's an alternative
    with downgrade(DeprecatedException, to_level=logging.DEBUG):
        raise DeprecatedException(
            "This project uses a deprecated footprint consolidation mechanism."
        )

    # Finally, check that we have all the footprints we know we will need
    try:
        for err_collector, fp_id in iter_through_errors(fp_ids_to_check):
            with err_collector():
                get_footprint(fp_id, config.build.paths.fp_lib_table)
    except* (FileNotFoundError, LibNotInTable) as ex:

        def _make_user_resource_exception(e: Exception) -> UserResourceException:
            if isinstance(e, FileNotFoundError):
                return UserResourceException(
                    f"Footprint library {e.filename} doesn't exist"
                )
            elif isinstance(e, LibNotInTable):
                return UserResourceException(
                    f"Footprint library {e.lib_id} not found in {e.lib_table_path}"
                )
            assert False, "How'd we get here?"

        raise ex.derive(
            [
                _make_user_resource_exception(e)
                for e in ex.exceptions
                if isinstance(e, (FileNotFoundError, LibNotInTable))
            ]
        ) from ex
