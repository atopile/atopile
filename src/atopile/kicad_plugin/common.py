import contextlib
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

import pcbnew

LOG_FILE = (Path(__file__).parent / "log.log").expanduser().absolute()
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler(str(LOG_FILE), "w", "utf-8"))
log.setLevel(logging.DEBUG)


@contextlib.contextmanager
def log_exceptions():
    try:
        yield
    except Exception as e:
        log.exception(e)
        raise


def get_prj_dir(path: Path) -> Path:
    """Return the atopile project directory."""
    path = Path(path)
    if (path / "ato.yaml").exists():
        return path
    for p in path.parents:
        if (p / "ato.yaml").exists():
            return p
    raise FileNotFoundError("ato.yaml not found in any parent directory")


def get_board_artifact_manifest(board_path: Path) -> dict:
    """Return a dict of the artifact manifest related to this board."""
    board_path = Path(board_path)
    manifest_path = get_prj_dir(board_path) / "build" / "manifest.json"
    with manifest_path.open("r") as f:
        manifest = json.load(f)
    return manifest.get("by-layout", {}).get(str(board_path), {})


def groups_by_name(board: pcbnew.BOARD) -> dict[str, pcbnew.PCB_GROUP]:
    """Return a dict of groups by name."""
    return {g.GetName(): g for g in board.Groups()}


def get_footprint_addr(fp: pcbnew.FOOTPRINT) -> Optional[str]:
    """Return the property "atopile_address" of a footprint."""
    field: pcbnew.PCB_FIELD = fp.GetFieldByName("atopile_address")
    if field:
        return field.GetText()
    return None


def footprints_by_addr(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    """Return a dict of footprints by "atopile_address"."""
    return {addr: fp for fp in board.GetFootprints() if (addr := get_footprint_addr(fp))}


def get_layout_map(board_path: Path) -> dict[str, Any]:
    """Return the layout map for the board."""
    board_path = Path(board_path)
    manifest = get_board_artifact_manifest(board_path)
    with Path(manifest["layouts"]).open("r", encoding="utf-8") as f:
        return json.load(f)


def flip_dict(d: dict) -> dict:
    """Return a dict with keys and values swapped."""
    return {v: k for k, v in d.items()}


def sync_track(
    source_board: pcbnew.BOARD,
    track: pcbnew.PCB_TRACK,
    target_board: pcbnew.BOARD
) -> pcbnew.PCB_TRACK:
    """Sync a track to the target board."""
    new_track: pcbnew.PCB_TRACK = track.Duplicate().Cast()
    new_track.SetParent(target_board)
    new_track.SetStart(track.GetStart())
    new_track.SetEnd(track.GetEnd())
    new_track.SetLayer(track.GetLayer())
    target_board.Add(new_track)
    source_board.Remove(new_track)
    return new_track

# also pull in any silkscreen items
def sync_drawing(
    source_board: pcbnew.BOARD,
    drawing: pcbnew.DRAWINGS,
    target_board: pcbnew.BOARD
) -> pcbnew.DRAWINGS:
    """Sync a drawing to the target board."""
    new_drawing: pcbnew.DRAWINGS = drawing.Duplicate().Cast()
    new_drawing.SetParent(target_board)
    new_drawing.SetLayer(drawing.GetLayer())
    target_board.Add(new_drawing)
    source_board.Remove(new_drawing)
    return new_drawing


# TODO: There must be a better way to update net of fill
def update_zone_net(
    source_zone: pcbnew.ZONE,
    source_board: pcbnew.BOARD,
    target_zone: pcbnew.ZONE,
    target_board: pcbnew.BOARD,
    addr_map: dict[str, str],
):
    """Finds a pin connected to original zone, pulls pin net name from new board net"""
    source_netname = source_zone.GetNetname()
    log.info(
        f"update_zone_net source_zone={source_zone} target_zone={target_zone} source_netname={source_netname}"
    )
    matched_fp = None
    matched_pad_index = None
    for fp in source_board.GetFootprints():
        for index, pad in enumerate(fp.Pads()):
            if pad.GetNetname() == source_netname:
                matched_fp = fp
                matched_pad_index = index
                break

        if matched_fp and matched_pad_index != None:
            break

    if matched_fp and matched_pad_index != None:
        if matched_fp_addr := get_footprint_addr(matched_fp):
            if target_fp_addr := addr_map.get(matched_fp_addr, None):
                target_fps = footprints_by_addr(target_board)
                target_fp = target_fps.get(target_fp_addr, None)
                if target_fp:
                    new_netinfo = target_fp.Pads()[matched_pad_index].GetNet()
                    target_zone.SetNet(new_netinfo)
                    return

    # TODO: Verify that this will always set net to no net
    target_zone.SetNetCode(0)


def sync_zone(zone: pcbnew.ZONE, target: pcbnew.BOARD) -> pcbnew.ZONE:
    """Sync a zone to the target board."""
    new_zone: pcbnew.ZONE = zone.Duplicate().Cast()
    new_zone.SetParent(target)
    layer = zone.GetLayer()
    new_zone.SetNet(target.FindNet(zone.GetNetname()))
    if layer != -1:
        new_zone.SetLayer(zone.GetLayer())
    target.Add(new_zone)
    return new_zone


def sync_footprints(
    source: pcbnew.BOARD, target: pcbnew.BOARD, addr_map: dict[str, str]
) -> list[str]:
    """Update the target board with the layout from the source board."""
    # Update the footprint position, orientation, and side to match the source
    source_addrs = footprints_by_addr(source)
    target_addrs = footprints_by_addr(target)
    missing_addrs = []
    for s_addr, t_addr in addr_map.items():
        try:
            target_fp = target_addrs[t_addr]
            source_fp = source_addrs[s_addr]
        except KeyError:
            missing_addrs.append(s_addr)
            continue
        target_fp.SetPosition(source_fp.GetPosition())
        target_fp.SetOrientation(source_fp.GetOrientation())
        target_fp.SetLayer(source_fp.GetLayer())
        target_fp.SetLayerSet(source_fp.GetLayerSet())
        # Ref Designators
        target_fp.Reference().SetAttributes(source_fp.Reference().GetAttributes())
        target_ref: pcbnew.FP_TEXT = target_fp.Reference()
        source_ref: pcbnew.FP_TEXT = source_fp.Reference()
        target_ref.SetPosition(source_ref.GetPosition())

        # Pads
        for target_pad in target_fp.Pads():
            source_pad = source_fp.FindPadByNumber(target_pad.GetNumber())
            target_pad.SetPosition(source_pad.GetPosition())
            target_pad.SetOrientation(source_pad.GetOrientation())
            target_pad.SetLayer(source_pad.GetLayer())
            target_pad.SetLayerSet(source_pad.GetLayerSet())

    return missing_addrs


def find_anchor_footprint(fps: Iterable[pcbnew.FOOTPRINT]) -> pcbnew.FOOTPRINT:
    """Return anchor footprint with largest pin count in board or group: tiebreaker size"""
    # fps = layout.GetFootprints()
    # fps = [item for item in layout.GetItems() if isinstance(item, pcbnew.FOOTPRINT)]
    max_padcount = 0
    max_area = 0
    anchor_fp = None
    for fp in fps:
        if fp.GetPadCount() > max_padcount or (
            fp.GetPadCount() == max_padcount and fp.GetArea() > max_area
        ):
            anchor_fp = fp
            max_padcount = fp.GetPadCount()
            max_area = fp.GetArea()
    return anchor_fp


def get_group_footprints(group: pcbnew.PCB_GROUP) -> list[pcbnew.FOOTPRINT]:
    """Return a list of footprints in a group."""
    return [item for item in group.GetItems() if isinstance(item, pcbnew.FOOTPRINT)]


def calculate_translation(source_fps: Iterable[pcbnew.FOOTPRINT], target_fps: Iterable[pcbnew.FOOTPRINT]) -> pcbnew.VECTOR2I:
    """Calculate the translation vector between two groups of footprints."""
    source_anchor_fp = find_anchor_footprint(source_fps)
    source_offset = source_anchor_fp.GetPosition()
    target_anchor_fp = find_anchor_footprint(target_fps)
    target_offset = target_anchor_fp.GetPosition()
    total_offset = target_offset - source_offset
    return total_offset
