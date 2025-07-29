"""CLI command definition for `ato layout-sync`."""

import logging
from pathlib import Path
from typing import Annotated, Optional

import typer

from atopile.config import config as gcfg
from atopile.telemetry import capture
from faebryk.libs.kicad.ipc import reload_pcb
from faebryk.libs.util import not_none, root_by_file

logger = logging.getLogger(__name__)


@capture("cli:layout_sync_start", "cli:layout_sync_end")
def layout_sync(
    pcb_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the KiCad PCB file to sync",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    include_groups: Annotated[
        Optional[list[str]],
        typer.Option(
            "--include-group",
            help="Specific group(s) to sync. If not specified, just syncs groups.",
        ),
    ] = None,
    include_fp: Annotated[
        Optional[list[str]],
        typer.Option(
            "--include-fp",
            help="Specific footprint(s) to sync.",
        ),
    ] = None,
    sync_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Sync all groups",
        ),
    ] = False,
    no_backup_unsaved: Annotated[
        bool,
        typer.Option(
            "--no-backup-unsaved",
            "-b",
            help="Don't backup unsaved PCB changes before syncing",
        ),
    ] = False,
):
    """
    Synchronize PCB layout groups from their source layouts.

    This command pulls layout information from source PCB files and applies it to
    groups in the target PCB file, preserving relative positions and routing.
    """

    # TODO remove
    no_backup_unsaved = False
    sync_all = True
    include_groups = None
    include_fp = None
    logger.info(
        f"args: {no_backup_unsaved=} {sync_all=} {include_groups=} {include_fp=}"
    )

    if sync_all and (include_groups or include_fp):
        raise typer.BadParameter("Cannot use --all and --include together")

    from faebryk.exporters.pcb.layout.layout_sync import LayoutSync

    pcb_path = pcb_path.expanduser().resolve().absolute()
    prj_root = root_by_file("ato.yaml", pcb_path.parent)
    gcfg.apply_options(entry=None, working_dir=prj_root)

    # Create layout sync instance
    sync = LayoutSync(pcb_path)

    if not sync.layout_maps:
        logger.warning("No layout maps found in manifest")
        return

    # Sync groups
    logger.info("Synchronizing groups...")
    sync.sync_groups()

    group_names = set(include_groups or [])

    # determine groups from fps
    fp_uuids = set(include_fp or [])
    for group in sync.pcb.groups:
        if set(group.members).issubset(fp_uuids):
            group_names.add(not_none(group.name))

    # Pull layouts for specified groups or all groups
    if group_names:
        # Only sync specified groups
        for group_name in group_names:
            if group_name in sync.layout_maps:
                logger.info(f"Pulling layout for group: {group_name}")
                sync.pull_group_layout(group_name)
            else:
                logger.warning(f"Group '{group_name}' not found in layout maps")
    elif sync_all:
        # Sync all groups
        for group_name in sync.layout_maps:
            logger.info(f"Pulling layout for group: {group_name}")
            sync.pull_group_layout(group_name)

    # Save the PCB
    logger.info(f"Saving PCB to {pcb_path}")
    sync.save_pcb()

    # Reload in KiCad if requested
    logger.info("Reloading PCB in KiCad...")
    # TODO better backup path
    reload_pcb(pcb_path, backup_path=pcb_path if not no_backup_unsaved else None)

    logger.info("Layout sync completed successfully")
