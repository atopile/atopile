import contextlib
import itertools
import logging
import time
from copy import deepcopy
from pathlib import Path
from textwrap import dedent

import faebryk.library._F as F
from atopile import layout
from atopile.cli.logging_ import LoggingStage
from atopile.config import config
from atopile.errors import UserException, UserPickError, UserToolNotAvailableError
from atopile.targets import generate_manufacturing_data, muster
from faebryk.core.cpp import set_max_paths
from faebryk.core.module import Module
from faebryk.core.pathfinder import MAX_PATHS
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.nullsolver import NullSolver
from faebryk.core.solver.solver import Solver
from faebryk.exporters.netlist.graph import attach_net_names, attach_nets
from faebryk.exporters.pcb.layout.layout_sync import LayoutSync
from faebryk.libs.app.checks import check_design
from faebryk.libs.app.designators import attach_random_designators, load_designators
from faebryk.libs.app.erc import needs_erc_check
from faebryk.libs.app.pcb import (
    apply_layouts,
    apply_routing,
    check_net_names,
    load_net_names,
)
from faebryk.libs.app.picking import load_part_info_from_pcb, save_part_info_to_pcb
from faebryk.libs.exceptions import accumulate, iter_leaf_exceptions
from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file
from faebryk.libs.picker.picker import PickError, pick_part_recursively
from faebryk.libs.util import (
    ConfigFlag,
    KeyErrorAmbiguous,
    compare_dataclasses,
    md_table,
    once,
    round_dataclass,
    sort_dataclass,
)

logger = logging.getLogger(__name__)

SKIP_SOLVING = ConfigFlag("SKIP_SOLVING", default=False)

MAX_PCB_DIFF_LENGTH = 100


def _get_solver() -> Solver:
    if SKIP_SOLVING:
        logger.warning("Assertion checking is disabled")
        return NullSolver()
    else:
        return DefaultSolver()


def _update_layout(
    pcb_file: C_kicad_pcb_file, original_pcb_file: C_kicad_pcb_file
) -> None:
    pcb_original_normalized = round_dataclass(
        sort_dataclass(original_pcb_file, sort_key=str, inplace=False), precision=2
    )
    pcb_normalized = round_dataclass(
        sort_dataclass(pcb_file, sort_key=str, inplace=False), precision=2
    )

    pcb_diff = compare_dataclasses(
        before=pcb_original_normalized,
        after=pcb_normalized,
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
            pcb_normalized.dumps(updated_path)

            # TODO: make this a real util
            def _try_relative(path: Path) -> Path:
                try:
                    return path.relative_to(Path.cwd(), walk_up=True)
                except ValueError:
                    return path

            original_relative = _try_relative(original_path)
            updated_relative = _try_relative(updated_path)

            diff_length = len(pcb_diff)
            truncated = diff_length > MAX_PCB_DIFF_LENGTH
            pcb_diff_items = (
                itertools.islice(pcb_diff.items(), MAX_PCB_DIFF_LENGTH)
                if truncated
                else pcb_diff.items()
            )

            raise UserException(
                dedent(
                    """
                    Built as frozen, but layout changed.

                    Original layout: **{original_relative}**

                    Updated layout: **{updated_relative}**

                    Diff:
                    {diff}{truncated_msg}
                    """
                ).format(
                    original_relative=original_relative,
                    updated_relative=updated_relative,
                    diff=md_table(
                        [
                            [f"**{path}**", diff["before"], diff["after"]]
                            for path, diff in pcb_diff_items
                        ],
                        headers=["Path", "Before", "After"],
                    ),
                    truncated_msg=f"\n... ({diff_length - MAX_PCB_DIFF_LENGTH} more)"
                    if truncated
                    else "",
                ),
                title="Frozen failed",
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

    targets = muster.select(
        set(config.build.targets) - set(config.build.exclude_targets)
    )

    if any(t.name == generate_manufacturing_data.name for t in targets):
        # TODO: model this better
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
            if target.virtual:
                continue

            if target.name in config.build.exclude_targets:
                logger.warning(f"Skipping excluded target '{target.name}'")
                continue

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
