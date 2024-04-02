import logging
import json
from pathlib import Path
from typing import Any
import pcbnew
from typing import Union

LOG_FILE = Path("~/.atopile/kicad-plugin.log").expanduser().absolute()
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler(str(LOG_FILE), "w", "utf-8"))
log.setLevel(logging.DEBUG)


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


def get_footprint_uuid(fp: pcbnew.FOOTPRINT) -> str:
    """Return the UUID of a footprint."""
    path = fp.GetPath().AsString()
    return path.split("/")[-1]


def footprints_by_uuid(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    """Return a dict of footprints by UUID."""
    return {get_footprint_uuid(fp): fp for fp in board.GetFootprints()}


def get_layout_map(board_path: Path) -> dict[str, Any]:
    """Return the layout map for the board."""
    board_path = Path(board_path)
    manifest = get_board_artifact_manifest(board_path)
    with Path(manifest["layouts"]).open("r", encoding="utf-8") as f:
        return json.load(f)


def flip_dict(d: dict) -> dict:
    """Return a dict with keys and values swapped."""
    return {v: k for k, v in d.items()}


def sync_track(source_board: pcbnew.BOARD, track: pcbnew.PCB_TRACK, target: pcbnew.BOARD) -> pcbnew.PCB_TRACK:
    """Sync a track to the target board."""
    new_track: pcbnew.PCB_TRACK = track.Duplicate().Cast()
    new_track.SetParent(target)
    new_track.SetStart(track.GetStart())
    new_track.SetEnd(track.GetEnd())
    new_track.SetLayer(track.GetLayer())
    target.Add(new_track)
    source_board.Remove(new_track)
    return new_track


def sync_footprints(
    source: pcbnew.BOARD, target: pcbnew.BOARD, uuid_map: dict[str, str]
) -> list[str]:
    """Update the target board with the layout from the source board."""
    # Update the footprint position, orientation, and side to match the source
    source_uuids = footprints_by_uuid(source)
    target_uuids = footprints_by_uuid(target)
    missing_uuids = []
    for s_uuid, t_uuid in uuid_map.items():
        try:
            target_fp = target_uuids[t_uuid]
            source_fp = source_uuids[s_uuid]
        except KeyError:
            missing_uuids.append(s_uuid)
            continue
        target_fp.SetPosition(source_fp.GetPosition())
        target_fp.SetOrientation(source_fp.GetOrientation())
        target_fp.SetLayer(source_fp.GetLayer())
    return missing_uuids


def find_anchor_footprint(layout: Union[pcbnew.BOARD,pcbnew.PCB_GROUP]) -> pcbnew.FOOTPRINT:
    """Return anchor footprint with largest pin count in board or group: tiebreaker size"""
    if isinstance(layout,pcbnew.PCB_GROUP):
        max_padcount = 0
        max_area = 0
        anchor_fp = None
        items = layout.GetItems()
        fps = [item for item in items if isinstance(item, pcbnew.FOOTPRINT)]
        for fp in fps:
            if fp.GetPadCount() > max_padcount or (fp.GetPadCount()==max_padcount and fp.GetArea()>max_area):
                anchor_fp = fp
                max_padcount = fp.GetPadCount()
                max_area = fp.GetArea()
        return anchor_fp
    elif isinstance(layout,pcbnew.BOARD):
        max_padcount = 0
        max_area = 0
        anchor_fp = None
        fps = layout.GetFootprints()
        for fp in fps:
            if fp.GetPadCount() > max_padcount or (fp.GetPadCount()==max_padcount and fp.GetArea()>max_area):
                anchor_fp = fp
                max_padcount = fp.GetPadCount()
                max_area = fp.GetArea()
        return anchor_fp
    return None


def calculate_translation(source: Union[pcbnew.BOARD,pcbnew.PCB_GROUP], target: Union[pcbnew.BOARD,pcbnew.PCB_GROUP]) -> pcbnew.VECTOR2I:
    source_anchor_fp = find_anchor_footprint(source)
    source_offset = source_anchor_fp.GetPosition()
    target_anchor_fp = find_anchor_footprint(target)
    target_offset = target_anchor_fp.GetPosition()
    total_offset = target_offset-source_offset
    return total_offset