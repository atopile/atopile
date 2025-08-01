import contextlib
import json
import logging
import tempfile
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable

import faebryk.library._F as F
from atopile import layout
from atopile.cli.logging_ import LoggingStage
from atopile.config import config
from atopile.errors import (
    UserException,
    UserExportError,
    UserPickError,
    UserToolNotAvailableError,
)
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
    KicadCliExportError,
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
    githash_layout,
)
from faebryk.exporters.pcb.layout.layout_sync import LayoutSync
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
    load_net_names,
)
from faebryk.libs.app.picking import load_part_info_from_pcb, save_part_info_to_pcb
from faebryk.libs.exceptions import (
    accumulate,
    iter_leaf_exceptions,
)
from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file
from faebryk.libs.picker.picker import PickError, pick_part_recursively
from faebryk.libs.util import (
    ConfigFlag,
    KeyErrorAmbiguous,
    compare_dataclasses,
    md_table,
    once,
    sort_dataclass,
)

logger = logging.getLogger(__name__)

SKIP_SOLVING = ConfigFlag("SKIP_SOLVING", default=False)


def _get_solver() -> Solver:
    if SKIP_SOLVING:
        logger.warning("Assertion checking is disabled")
        return NullSolver()
    else:
        return DefaultSolver()


def _update_layout(
    pcb_file: C_kicad_pcb_file, original_pcb_file: C_kicad_pcb_file
) -> None:
    pcb_diff = compare_dataclasses(
        sort_dataclass(original_pcb_file, sort_key=lambda x: str(x)),
        sort_dataclass(pcb_file, sort_key=lambda x: str(x)),
        skip_keys=("uuid", "__atopile_lib_fp_hash__"),
        require_dataclass_type_match=False,
    )

    if config.build.frozen:
        if pcb_diff:
            original_path = config.build.paths.output_base.with_suffix(
                ".original.kicad_pcb"
            )
            updated_path = config.build.paths.output_base.with_suffix(
                ".updated.kicad_pcb"
            )
            original_pcb_file.dumps(original_path)
            pcb_file.dumps(updated_path)

            # TODO: make this a real util
            def _try_relative(path: Path) -> Path:
                try:
                    return path.relative_to(Path.cwd(), walk_up=True)
                except ValueError:
                    return path

            original_relative = _try_relative(original_path)
            updated_relative = _try_relative(updated_path)

            raise UserException(
                dedent(
                    """
                    Built as frozen, but layout changed.

                    Original layout: **{original_relative}**

                    Updated layout: **{updated_relative}**

                    Diff:
                    {diff}
                    """
                ).format(
                    original_relative=original_relative,
                    updated_relative=updated_relative,
                    diff=md_table(
                        [
                            [f"**{path}**", diff["before"], diff["after"]]
                            for path, diff in pcb_diff.items()
                        ],
                        headers=["Path", "Before", "After"],
                    ),
                ),
                title="Frozen failed",
                # No markdown=False here because we have both a command and paths
            )
        else:
            logger.info("No changes to layout. Passed --frozen check.")
    elif original_pcb_file == pcb_file:
        logger.info("No changes to layout. Not writing %s", config.build.paths.layout)
    else:
        logger.info(f"Updating layout {config.build.paths.layout}")
        sync = LayoutSync(pcb_file.kicad_pcb)
        original_fps = {
            addr: fp
            for fp in original_pcb_file.kicad_pcb.footprints
            if (addr := fp.try_get_property("atopile_address"))
        }
        current_fps = {
            addr: fp
            for fp in pcb_file.kicad_pcb.footprints
            if (addr := fp.try_get_property("atopile_address"))
        }
        new_fps = {k: v for k, v in current_fps.items() if k not in original_fps}
        sync.sync_groups()
        groups_to_update = {
            gname
            for gname, fps in sync.groups.items()
            if {
                addr
                for fp, _ in fps
                if (addr := fp.try_get_property("atopile_address"))
            }.issubset(new_fps)
        }

        for group_name in groups_to_update:
            sync.pull_group_layout(group_name)

        pcb_file.dumps(config.build.paths.layout)


def build(app: Module) -> None:
    """Build the project."""

    def G():
        return app.get_graph()

    solver = _get_solver()
    app.add(F.has_solver(solver))

    # Attach PCBs to entry points
    pcb = F.PCB(config.build.paths.layout)
    app.add(F.PCB.has_pcb(pcb))
    layout.attach_sub_pcbs_to_entry_points(app)

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

    with LoggingStage("load-pcb", "Loading PCB"):
        pcb.load()
        if config.build.keep_designators:
            load_designators(G(), attach=True)

    with LoggingStage("picker", "Picking components") as stage:
        if config.build.keep_picked_parts:
            load_part_info_from_pcb(G())
            solver.simplify(G())
        try:
            pick_part_recursively(app, solver, progress=stage)
        except* PickError as ex:
            raise ExceptionGroup(
                "Failed to pick parts for some modules",
                [UserPickError(str(e)) for e in iter_leaf_exceptions(ex)],
            ) from ex
        save_part_info_to_pcb(G())

    with LoggingStage("nets", "Preparing nets"):
        attach_random_designators(G())
        nets = attach_nets(G())
        # We have to re-attach the footprints, and subsequently nets, because the first
        # attachment is typically done before the footprints have been created
        # and therefore many nets won't be re-attached properly. Also, we just created
        # and attached them to the design above, so they weren't even there to attach
        pcb.transformer.attach()
        if config.build.keep_net_names:
            loaded_nets = load_net_names(G())
            nets |= loaded_nets

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
        # attach subaddresses for lifecycle manager to use
        layout.attach_subaddresses_to_modules(app)

        original_pcb = deepcopy(pcb.pcb_file)
        pcb.transformer.apply_design()
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

        # Backup layout
        backup_file = config.build.paths.output_base.with_suffix(
            f".{time.strftime('%Y%m%d-%H%M%S')}.kicad_pcb"
        )
        logger.info(f"Backing up layout to {backup_file}")
        backup_file.write_bytes(config.build.paths.layout.read_bytes())
        _update_layout(pcb.pcb_file, original_pcb)

    # Figure out what targets to build
    if config.build.targets == ["__default__"]:
        targets = [t for t in muster.targets.values() if t.default]
    elif config.build.targets == ["*"] or config.build.targets == ["all"]:
        targets = [t for t in muster.targets.values()]
    else:
        targets = [muster.targets[t] for t in config.build.targets]
        for target in targets:
            target.implicit = False

    # Remove excluded targets
    targets = [t for t in targets if t.name not in config.build.exclude_targets]

    if any(t.name == generate_manufacturing_data.name for t in targets):
        with LoggingStage("checks-post-pcb", "Running post-pcb checks"):
            pcb.add(F.PCB.requires_drc_check())
            try:
                check_design(
                    G(),
                    stage=F.implements_design_check.CheckStage.POST_PCB,
                    exclude=excluded_checks,
                )
            except F.PCB.requires_drc_check.DrcException as ex:
                raise UserException(f"Detected DRC violations: \n{ex.pretty()}") from ex

    @once
    def _check_kicad_cli() -> bool:
        with contextlib.suppress(Exception):
            from kicadcliwrapper.generated.kicad_cli import kicad_cli

            kicad_cli(kicad_cli.version()).exec()
            return True

        return False

    # Make the noise
    with accumulate() as accumulator:
        for target in targets:
            with LoggingStage(
                f"target-{target.name}", f"Building [green]'{target.name}'[/green]"
            ):
                if target.requires_kicad and not _check_kicad_cli():
                    if target.implicit:
                        logger.warning(
                            f"Skipping target '{target.name}' because kicad-cli was not"
                            " found",
                        )
                        continue
                    else:
                        raise UserToolNotAvailableError("kicad-cli not found")

                with accumulator.collect():
                    target(app, solver)


@dataclass
class MusterTarget:
    name: str
    default: bool
    requires_kicad: bool
    func: Callable[[Module, Solver], None]
    implicit: bool = True

    def __call__(self, app: Module, solver: Solver) -> None:
        return self.func(app, solver)


class Muster:
    """A class to register targets to."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.targets: dict[str, MusterTarget] = {}
        self.log = logger or logging.getLogger(__name__)

    def add_target(self, target: MusterTarget) -> MusterTarget:
        """Register a function as a target."""
        self.targets[target.name] = target
        return target

    def register(
        self,
        name: str | None = None,
        default: bool = True,
        requires_kicad: bool = False,
    ) -> Callable[[Callable[[Module, Solver], None]], MusterTarget]:
        """Register a target under a given name."""

        def decorator(func: Callable[[Module, Solver], None]) -> MusterTarget:
            target_name = name or func.__name__
            target = MusterTarget(
                name=target_name,
                default=default,
                requires_kicad=requires_kicad,
                func=func,
            )
            self.add_target(target)
            return target

        return decorator


muster = Muster()


@muster.register("bom")
def generate_bom(app: Module, solver: Solver) -> None:
    """Generate a BOM for the project."""
    write_bom_jlcpcb(
        app.get_children_modules(types=Module),
        config.build.paths.output_base.with_suffix(".bom.csv"),
    )


@muster.register("3d-model", default=False, requires_kicad=True)
def generate_3d_model(app: Module, solver: Solver) -> None:
    """Generate PCBA 3D model as GLB. Used for 3D preview in extension."""

    try:
        export_glb(
            config.build.paths.layout,
            glb_file=config.build.paths.output_base.with_suffix(".pcba.glb"),
            project_dir=config.build.paths.layout.parent,
        )
    except KicadCliExportError as e:
        raise UserExportError(f"Failed to generate 3D model: {e}") from e


@muster.register("mfg-data", default=False, requires_kicad=True)
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

        try:
            export_step(
                tmp_layout,
                step_file=config.build.paths.output_base.with_suffix(".pcba.step"),
                project_dir=config.build.paths.layout.parent,
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate STEP file: {e}") from e

        try:
            export_dxf(
                tmp_layout,
                dxf_file=config.build.paths.output_base.with_suffix(".pcba.dxf"),
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate DXF file: {e}") from e

        try:
            export_gerber(
                tmp_layout,
                gerber_zip_file=config.build.paths.output_base.with_suffix(
                    ".gerber.zip"
                ),
            )
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate Gerber file: {e}") from e

        pnp_file = config.build.paths.output_base.with_suffix(".pick_and_place.csv")
        try:
            export_pick_and_place(tmp_layout, pick_and_place_file=pnp_file)
        except KicadCliExportError as e:
            raise UserExportError(f"Failed to generate Pick and Place file: {e}") from e

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
