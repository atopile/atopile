import json
import logging
import shutil
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Callable, Optional

import faebryk.library._F as F
from atopile import layout
from atopile.cli.logging import LoggingStage
from atopile.config import config
from atopile.errors import UserException, UserPickError
from atopile.front_end import DeprecatedException
from faebryk.core.cpp import set_max_paths
from faebryk.core.module import Module
from faebryk.core.pathfinder import MAX_PATHS
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.nullsolver import NullSolver
from faebryk.core.solver.solver import Solver
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.documentation.i2c import export_i2c_tree
from faebryk.exporters.netlist.graph import (
    attach_net_names,
    attach_nets,
)
from faebryk.exporters.parameters.parameters_to_file import export_parameters_to_file
from faebryk.exporters.pcb.kicad.artifacts import (
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
    githash_layout,
)
from faebryk.exporters.pcb.kicad.pcb import LibNotInTable, get_footprint
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)
from faebryk.exporters.pcb.testpoints.testpoints import export_testpoints
from faebryk.libs.app.checks import check_design
from faebryk.libs.app.designators import (
    attach_random_designators,
    load_designators,
)
from faebryk.libs.app.erc import needs_erc_check
from faebryk.libs.app.pcb import (
    apply_layouts,
    apply_routing,
    check_net_names,
    create_footprint_library,
    ensure_footprint_lib,
    load_net_names,
)
from faebryk.libs.app.picking import load_descriptive_properties, save_parameters
from faebryk.libs.exceptions import (
    UserResourceException,
    accumulate,
    downgrade,
    iter_leaf_exceptions,
    iter_through_errors,
)
from faebryk.libs.kicad.fileformats_latest import C_kicad_fp_lib_table_file
from faebryk.libs.picker.picker import PickError, pick_part_recursively
from faebryk.libs.util import ConfigFlag, KeyErrorAmbiguous

logger = logging.getLogger(__name__)

SKIP_SOLVING = ConfigFlag("SKIP_SOLVING", default=False)


def _get_solver() -> Solver:
    if SKIP_SOLVING:
        logger.warning("Assertion checking is disabled")
        return NullSolver()
    else:
        return DefaultSolver()


def build(app: Module) -> None:
    """Build the project."""

    def G():
        return app.get_graph()

    solver = _get_solver()
    app.add(F.has_solver(solver))
    pcb = F.PCB()
    app.add(F.PCB.has_pcb(pcb))

    # TODO remove, once erc split up
    app.add(needs_erc_check())

    # TODO remove hack
    # Disables children pathfinding
    # ```
    # power1.lv ~ power2.lv
    # power1.hv ~ power2.hv
    # -> power1 is not connected power2
    # ```
    set_max_paths(int(MAX_PATHS), 0, 0)

    excluded_checks = tuple(set(config.build.exclude_checks))

    with LoggingStage("checks-post-design", "Running post-design checks"):
        if not SKIP_SOLVING:
            logger.info("Resolving bus parameters")
            try:
                F.is_bus_parameter.resolve_bus_parameters(G())
            # FIXME: this is a hack around a compiler bug
            except KeyErrorAmbiguous as ex:
                raise UserException(
                    "Unfortunately, there's a compiler bug at the moment that means "
                    "that this sometimes fails. Try again, and it'll probably work. "
                    "See https://github.com/atopile/atopile/issues/807"
                ) from ex
        else:
            logger.warning("Skipping bus parameter resolution")

        check_design(
            G(),
            stage=F.implements_design_check.CheckStage.POST_DESIGN,
            exclude=excluded_checks,
        )

        # Pre-pick project checks - things to look at before time is spend ---------
        # Make sure the footprint libraries we're looking for exist
        consolidate_footprints(app)

    with LoggingStage("load-pcb", "Loading PCB"):
        pcb.load_from_file(config.build.paths.layout)
        if config.build.keep_designators:
            load_designators(G(), attach=True)

    with LoggingStage("picker", "Picking components") as stage:
        if config.build.keep_picked_parts:
            load_descriptive_properties(G())
        try:
            pick_part_recursively(app, solver, progress=stage)
        except* PickError as ex:
            raise ExceptionGroup(
                "Failed to pick parts for some modules",
                [UserPickError(str(e)) for e in iter_leaf_exceptions(ex)],
            ) from ex
        save_parameters(G())

    with LoggingStage("footprints", "Handling footprints"):
        # Use standard footprints for known packages regardless of
        # what's otherwise been specified.
        # FIXME: this currently includes explicitly set footprints, but shouldn't
        F.has_package.standardize_footprints(app, solver)
        create_footprint_library(app)

    with LoggingStage("nets", "Preparing nets"):
        attach_random_designators(G())
        nets = attach_nets(G())
        # We have to re-attach the footprints, and subsequently nets, because the first
        # attachment is typically done before the footprints have been created
        # and therefore many nets won't be re-attached properly. Also, we just created
        # and attached them to the design above, so they weren't even there to attach
        pcb.transformer.attach()
        if config.build.keep_net_names:
            load_net_names(G())
        attach_net_names(nets)
        check_net_names(G())

    with LoggingStage("checks-post-solve", "Running post-solve checks"):
        logger.info("Running checks")
        check_design(
            G(),
            stage=F.implements_design_check.CheckStage.POST_SOLVE,
            exclude=excluded_checks,
        )

    with LoggingStage("update-pcb", "Updating PCB"):
        original_pcb = deepcopy(pcb.pcb_file)
        pcb.transformer.apply_design(config.build.paths.fp_lib_table)
        pcb.transformer.check_unattached_fps()

        if transform_trait := app.try_get_trait(F.has_layout_transform):
            logger.info("Transforming PCB")
            transform_trait.transform(pcb.transformer)

        # set layout
        apply_layouts(app)
        pcb.transformer.move_footprints()
        apply_routing(app, pcb.transformer)
        if config.build.hide_designators:
            pcb.transformer.hide_all_designators()

        if pcb.pcb_file == original_pcb:
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
            updated_path = config.build.paths.output_base.with_suffix(
                ".updated.kicad_pcb"
            )
            original_pcb.dumps(original_path)
            pcb.pcb_file.dumps(updated_path)

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
                f'`diff --color "{original_relative}" "{updated_relative}"`',
                title="Frozen failed",
                # No markdown=False here because we have both a command and paths
            )
        else:
            backup_file = config.build.paths.output_base.with_suffix(
                f".{time.strftime('%Y%m%d-%H%M%S')}.kicad_pcb"
            )
            logger.info(f"Backing up layout to {backup_file}")
            with config.build.paths.layout.open("rb") as f:
                backup_file.write_bytes(f.read())

            logger.info(f"Updating layout {config.build.paths.layout}")
            pcb.pcb_file.dumps(config.build.paths.layout)

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

    if generate_manufacturing_data.__muster_name__ in targets:  # type: ignore
        with LoggingStage("checks-post-pcb", "Running post-pcb checks"):
            try:
                check_design(
                    G(),
                    stage=F.implements_design_check.CheckStage.POST_PCB,
                    exclude=excluded_checks,
                )
            except F.PCB.requires_drc_check.DrcException as ex:
                raise UserException(f"Detected DRC violations: \n{ex.pretty()}") from ex

    # Make the noise
    built_targets = []
    with accumulate() as accumulator:
        for target_name in targets:
            with LoggingStage(
                f"target-{target_name}", f"Building [green]'{target_name}'[/green]"
            ):
                with accumulator.collect():
                    muster.targets[target_name](app, solver)
                built_targets.append(target_name)


TargetType = Callable[[Module, Solver], None]


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
            func.__muster_name__ = name or func.__name__  # type: ignore
            return func

        return decorator


muster = Muster()


@muster.register("bom")
def generate_bom(app: Module, solver: Solver) -> None:
    """Generate a BOM for the project."""
    write_bom_jlcpcb(
        app.get_children_modules(types=Module),
        config.build.paths.output_base.with_suffix(".bom.csv"),
    )


@muster.register("mfg-data", default=False)
def generate_manufacturing_data(app: Module, solver: Solver) -> None:
    """
    Generate manufacturing artifacts for the project.
    - STEP
    - GLB
    - DXF
    - Gerber zip
    - Pick and place (default and JLCPCB)
    - Testpoint-location
    """
    # Create temp copy of layout file with git hash substituted
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(
            config.build.paths.layout,
            Path(tmpdir) / config.build.paths.layout.name,
        )

        export_step(
            tmp_layout,
            step_file=config.build.paths.output_base.with_suffix(".pcba.step"),
        )
        export_glb(
            tmp_layout,
            glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
        )
        export_dxf(
            tmp_layout,
            dxf_file=config.build.paths.output_base.with_suffix(".pcba.dxf"),
        )

        export_gerber(
            tmp_layout,
            gerber_zip_file=config.build.paths.output_base.with_suffix(".gerber.zip"),
        )

        pnp_file = config.build.paths.output_base.with_suffix(".pick_and_place.csv")
        export_pick_and_place(tmp_layout, pick_and_place_file=pnp_file)
        convert_kicad_pick_and_place_to_jlcpcb(
            pnp_file,
            config.build.paths.output_base.with_suffix(".jlcpcb_pick_and_place.csv"),
        )

        export_testpoints(
            app,
            testpoints_file=config.build.paths.output_base.with_suffix(
                ".testpoints.json"
            ),
        )


@muster.register("manifest")
def generate_manifest(app: Module, solver: Solver) -> None:
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
                json.dump(manifest, f, indent=4)


@muster.register("layout-module-map")
def generate_module_map(app: Module, solver: Solver) -> None:
    """Generate a designator map for the project."""
    layout.generate_module_map(app)


@muster.register("variable-report")
def generate_variable_report(app: Module, solver: Solver) -> None:
    """Generate a report of all the variable values in the design."""
    # TODO: support other file formats
    export_parameters_to_file(
        app, solver, config.build.paths.output_base.with_suffix(".variables.md")
    )


@muster.register("i2c-tree")
def generate_i2c_tree(app: Module, solver: Solver) -> None:
    """Generate a Mermaid diagram of the I2C bus tree."""
    export_i2c_tree(
        app, solver, config.build.paths.output_base.with_suffix(".i2c_tree.md")
    )


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
            [_make_user_resource_exception(e) for e in iter_leaf_exceptions(ex)]
        ) from ex
