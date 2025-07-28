"""CLI command definition for `ato layout-sync`."""

import logging
from pathlib import Path
from typing import Annotated, Optional

import typer

from atopile.config import config as gcfg
from atopile.telemetry import capture
from faebryk.libs.kicad.ipc import reload_pcb
from faebryk.libs.util import root_by_file

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
    include: Annotated[
        Optional[list[str]],
        typer.Option(
            "--include",
            "-i",
            help="Specific group(s) or footprints to sync."
            " If not specified, just syncs groups.",
        ),
    ] = None,
    backup_unsaved: Annotated[
        bool,
        typer.Option(
            "--backup-unsaved",
            "-b",
            help="Backup unsaved PCB changes before syncing",
        ),
    ] = True,
):
    """
    Synchronize PCB layout groups from their source layouts.

    This command pulls layout information from source PCB files and applies it to
    groups in the target PCB file, preserving relative positions and routing.
    """
    # TODO remove
    print("Running layout sync")

    from faebryk.exporters.pcb.layout.layout_sync import LayoutSync

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

    # Pull layouts for specified groups or all groups
    if include:
        # Only sync specified groups
        for group_name in include:
            if group_name in sync.layout_maps:
                logger.info(f"Pulling layout for group: {group_name}")
                sync.pull_group_layout(group_name)
            else:
                logger.warning(f"Group '{group_name}' not found in layout maps")
    else:
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
    reload_pcb(pcb_path, backup_path=pcb_path if backup_unsaved else None)

    logger.info("Layout sync completed successfully")


def register(app: typer.Typer):
    """Register the layout-sync command with the main app."""
    app.command(name="layout-sync")(layout_sync)
