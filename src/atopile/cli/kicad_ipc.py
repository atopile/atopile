"""CLI command definition for `ato kicad-ipc`."""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file

kicad_ipc_app = typer.Typer(rich_markup_mode="rich")

logger = logging.getLogger(__name__)


def _setup_logger():
    from faebryk.libs.kicad.ipc import running_in_kicad
    from faebryk.libs.paths import get_log_file

    if not running_in_kicad():
        return
    formatter = logging.Formatter(
        "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler = logging.FileHandler(str(get_log_file("kicad_ipc")), "w", "utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


@kicad_ipc_app.command()
# TODO: had to disable because slow and blocking kicad
# @capture("cli:kicad_ipc_layout_sync_start", "cli:kicad_ipc_layout_sync_end")
def layout_sync(
    legacy: Annotated[
        bool,
        typer.Option("--legacy", help="Called from legacy plugin"),
    ] = False,
    board: Annotated[
        Optional[Path],
        typer.Option("--board", help="Legacy only: Path to the PCB file to sync"),
    ] = None,
    include_groups: Annotated[
        Optional[list[str]],
        typer.Option(
            "--include-group",
            help="Legacy only: Specific group(s) to sync. "
            "If not specified, just syncs groups.",
        ),
    ] = None,
    include_fp: Annotated[
        Optional[list[str]],
        typer.Option(
            "--include-fp",
            help="Legacy only: Specific footprint(s) to sync.",
        ),
    ] = None,
    sync_all: Annotated[
        bool,
        typer.Option("--all", help="Debug only: Sync all groups"),
    ] = False,
):
    """
    Synchronize PCB layout groups from their source layouts.

    This command pulls layout information from source PCB files and applies it to
    groups in the target PCB file, preserving relative positions and routing.
    """

    from atopile.config import config as gcfg
    from faebryk.libs.kicad.ipc import PCBnew, reload_pcb
    from faebryk.libs.util import find, not_none, root_by_file

    _setup_logger()
    logger.info("layout_sync")

    if not legacy and (include_groups or include_fp):
        raise typer.BadParameter(
            "setting --include-group or --include-fp is only supported with --legacy"
        )
    if legacy and not board:
        raise typer.BadParameter("must specify --board when using --legacy")

    from faebryk.exporters.pcb.layout.layout_sync import LayoutSync

    if legacy:
        pcb_path = Path(not_none(board))
        if not pcb_path.exists():
            raise FileNotFoundError(f"PCB file not found: {pcb_path}")
    else:
        raise NotImplementedError("KiCAD IPC is too broken to use/test")
        pcbnew = PCBnew.get_host()
        pcb_path = pcbnew.path
        pcbnew.board.save()
        # from kipy.proto.common import KiCadObjectType
        # include_groups = [
        #     g.GetName()
        #     for g in pcbnew.board.get_selection(KiCadObjectType.KOT_PCB_GROUP)
        # ]
        # include_fp = [
        #     fp.m_Uuid.AsString()
        #     for fp in pcbnew.board.get_selection(KiCadObjectType.KOT_PCB_FOOTPRINT)
        # ]

    pcb_path = pcb_path.expanduser().resolve().absolute()
    logger.info(f"pcb_path: {pcb_path}")

    prj_root = root_by_file("ato.yaml", pcb_path.parent)
    gcfg.apply_options(entry=None, working_dir=prj_root)
    build = find(gcfg.project.builds.values(), lambda b: b.paths.layout == pcb_path)
    gcfg.select_build(build.name)

    # Create layout sync instance
    pcb_file = C_kicad_pcb_file.loads(pcb_path)
    sync = LayoutSync(pcb_file.kicad_pcb)

    if not sync.groups:
        logger.warning("No sub layout groups found in pcb")
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

    if sync_all:
        group_names = set(sync.groups.keys())

    # Only sync specified groups
    for group_name in group_names:
        if group_name in sync.groups:
            logger.info(f"Pulling layout for group: {group_name}")
            sync.pull_group_layout(group_name)
        else:
            logger.warning(f"Group '{group_name}' not found in layout maps")

    # Save the PCB
    logger.info(f"Saving PCB to {pcb_path}")
    pcb_file.dumps(pcb_path)

    # Reload in KiCad if requested
    logger.info("Reloading PCB in KiCad...")
    if legacy:
        # needs hack because plugin blocks IPC calls
        subprocess.Popen(
            [sys.executable, "-m", "atopile", "kicad-ipc", "reload", pcb_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        reload_pcb(pcb_path, backup_path=None)

    logger.info("Layout sync completed successfully")


@kicad_ipc_app.command()
def reload(pcb_path: Path):
    """Reload the PCB in KiCad."""
    from faebryk.libs.kicad.ipc import reload_pcb

    _setup_logger()
    reload_pcb(pcb_path, backup_path=None)
