import contextlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Union

import pcbnew  # type: ignore

log = logging.getLogger(__name__)


# ATTENTION: RUNS IN PYTHON3.8


@contextlib.contextmanager
def log_exceptions():
    try:
        yield
    except Exception as e:
        log.exception(e)
        raise


# Copy of util.py:find
def _find(haystack: Iterable, needle: Optional[Callable] = None) -> Dict[Any, Any]:
    """Find a value in a dict by key."""
    if needle is None:
        needle = lambda x: x is not None  # noqa: E731
    results = [x for x in haystack if needle(x)]
    if len(results) > 1:
        raise KeyError("Ambiguous")
    if not results:
        raise KeyError("Not found")
    return results[0]


# needed for windows
def path_key(dict_: Dict[str, Any], path: Path) -> Any:
    """Return the value in dict_ for the key that matches path."""
    return _find(dict_.items(), lambda x: Path(x[0]) == path)[1]


def get_prj_dir(path: Union[Path, str]) -> Path:
    """Return the atopile project directory."""
    path = Path(path)
    if (path / "ato.yaml").exists():
        return path
    for p in path.parents:
        if (p / "ato.yaml").exists():
            return p
    raise FileNotFoundError("ato.yaml not found in any parent directory")


def get_board_artifact_manifest(board_path: Union[Path, str]) -> Dict[str, Any]:
    """Return a dict of the artifact manifest related to this board."""
    board_path = Path(board_path)
    manifest_path = get_prj_dir(board_path) / "build" / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    layouts = manifest.get("by-layout", {})
    return path_key(layouts, board_path)


def groups_by_name(board: pcbnew.BOARD) -> Dict[str, pcbnew.PCB_GROUP]:
    """Return a dict of groups by name."""
    return {g.GetName(): g for g in board.Groups()}


def get_footprint_uuid(fp: pcbnew.FOOTPRINT) -> str:
    """Return the UUID of a footprint."""
    path = fp.GetPath().AsString()
    return path.split("/")[-1]


def get_footprint_addr(fp: pcbnew.FOOTPRINT, uuid_map: Dict[str, str]) -> Optional[str]:
    """Return the property "atopile_address" of a footprint."""
    field: pcbnew.PCB_FIELD = fp.GetFieldByName("atopile_address")
    if field:
        return field.GetText()

    # This is a backup to support old layouts which
    # haven't yet got addresses in their properties
    uuid = get_footprint_uuid(fp)
    if uuid in uuid_map:
        return uuid_map[uuid]

    return None


def footprints_by_addr(
    board: pcbnew.BOARD, uuid_map: Dict[str, str]
) -> Dict[str, pcbnew.FOOTPRINT]:
    """Return a dict of footprints by "atopile_address"."""
    return {
        addr: fp
        for fp in board.GetFootprints()
        if (addr := get_footprint_addr(fp, uuid_map))
    }


def get_layout_map(board_path: Union[Path, str]) -> Dict[str, Any]:
    """Return the layout map for the board."""
    board_path = Path(board_path)
    manifest = get_board_artifact_manifest(board_path)
    with Path(manifest["layouts"]).open("r", encoding="utf-8") as f:
        return json.load(f)


def flip_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict with keys and values swapped."""
    return {v: k for k, v in d.items()}


def sync_track(
    source_board: pcbnew.BOARD,
    track: pcbnew.PCB_TRACK,
    target_board: pcbnew.BOARD,
    net_map: Dict[str, str],
) -> pcbnew.PCB_TRACK:
    """Sync a track to the target board and update its net from net_map."""
    new_track: pcbnew.PCB_TRACK = track.Duplicate().Cast()
    new_track.SetParent(target_board)
    new_track.SetStart(track.GetStart())
    new_track.SetEnd(track.GetEnd())
    new_track.SetLayer(track.GetLayer())

    # Update the net using net_map
    source_net = track.GetNetname()
    if source_net in net_map:
        target_net_name = net_map[source_net]
        # Find the actual NETINFO_ITEM for the target net
        target_net_info = target_board.FindNet(target_net_name)
        if target_net_info:
            new_track.SetNet(target_net_info)
        else:
            log.warning(f"Could not find net '{target_net_name}' in target board")
            new_track.SetNetCode(0)  # No net
    else:
        new_track.SetNetCode(0)  # No net

    target_board.Add(new_track)
    source_board.Remove(new_track)
    return new_track


def generate_net_map(
    source_board: pcbnew.BOARD,
    target_board: pcbnew.BOARD,
    addr_map: Dict[str, str],
    uuid_map: Dict[str, str],
):
    """Generates a mapping from source net names to target net names based on matching
    addresses.

    For each component in the source board, if its address exists in addr_map, the
    target footprint is looked up. For each pad index in the source footprint, a mapping
    is added from source pad net (e.g., 'VCC') to target pad net (e.g., 'VCC_3V3').
    """
    net_map: dict[str, str] = {}
    # Track how many times we've seen each mapping for confidence
    mapping_counts: dict[str, dict[str, int]] = {}

    # Obtain a dictionary of target footprints by their address
    target_fps = footprints_by_addr(target_board, uuid_map)

    # Iterate through each footprint in the source board
    for src_fp in source_board.GetFootprints():
        # Get the source footprint address
        src_addr = get_footprint_addr(src_fp, uuid_map)
        if not src_addr:
            continue

        # Check if there is a mapping for this source address
        if src_addr not in addr_map:
            continue
        target_addr = addr_map[src_addr]

        # Look up the corresponding target footprint
        target_fp = target_fps.get(target_addr)
        if not target_fp:
            continue

        # For each pad in the source footprint, map its net to the pad in the target
        source_pads = list(src_fp.Pads())
        target_pads = list(target_fp.Pads())

        # Match pads by pad number, handling duplicate pad numbers by comparing size
        for source_pad in source_pads:
            pad_number = source_pad.GetNumber()
            source_net = source_pad.GetNetname()

            # Find matching target pads with the same number
            matching_target_pads = [
                p for p in target_pads if p.GetNumber() == pad_number
            ]

            target_net = None

            if len(matching_target_pads) == 1:
                # Exact match by number
                target_pad = matching_target_pads[0]
                target_net = target_pad.GetNetname()
            elif len(matching_target_pads) > 1:
                # Multiple pads with same number, find best match by size and shape
                best_match = None
                min_diff = float("inf")

                for candidate in matching_target_pads:
                    # Calculate difference in size and shape
                    size_diff = abs(
                        candidate.GetSize().x - source_pad.GetSize().x
                    ) + abs(candidate.GetSize().y - source_pad.GetSize().y)
                    shape_diff = (
                        0 if candidate.GetShape() == source_pad.GetShape() else 10
                    )
                    total_diff = size_diff + shape_diff

                    if total_diff < min_diff:
                        min_diff = total_diff
                        best_match = candidate

                if best_match:
                    target_net = best_match.GetNetname()

            # If we found a target net, update the mapping
            if target_net and source_net:
                # Initialize count tracking for this source net if we haven't seen it
                if source_net not in mapping_counts:
                    mapping_counts[source_net] = {}

                # Increment the count for this specific mapping
                current_count = mapping_counts[source_net].get(target_net, 0)
                mapping_counts[source_net][target_net] = current_count + 1

                # If we've seen this source net before, verify the mapping
                if source_net in net_map:
                    # If the existing mapping doesn't match, log a warning
                    if net_map[source_net] != target_net:
                        log.warning(
                            f"Conflicting net mapping for '{source_net}': "
                            f"'{net_map[source_net]}' vs '{target_net}'. "
                            f"Using most frequently seen mapping."
                        )

                        # Use the most frequently seen mapping
                        most_frequent_target = max(
                            mapping_counts[source_net].items(), key=lambda x: x[1]
                        )[0]
                        net_map[source_net] = most_frequent_target
                else:
                    # First time seeing this source net
                    net_map[source_net] = target_net

    # Log mapping confidence statistics
    for source_net, counts in mapping_counts.items():
        if len(counts) > 1:
            log.info(
                f"Multiple mappings found for source net '{source_net}': {counts}"
                f" - Using: '{net_map[source_net]}'"
            )
        else:
            # Single mapping with count
            target_net, count = next(iter(counts.items()))
            log.debug(
                f"Net mapping '{source_net}' -> '{target_net}' confirmed {count} times"
            )

    return net_map


# also pull in any silkscreen items
def sync_drawing(
    source_board: pcbnew.BOARD, drawing: pcbnew.DRAWINGS, target_board: pcbnew.BOARD
) -> pcbnew.DRAWINGS:
    """Sync a drawing to the target board."""
    new_drawing: pcbnew.DRAWINGS = drawing.Duplicate().Cast()
    new_drawing.SetParent(target_board)
    new_drawing.SetLayer(drawing.GetLayer())
    target_board.Add(new_drawing)
    source_board.Remove(new_drawing)
    return new_drawing


def update_zone_net(
    source_zone: pcbnew.ZONE,
    target_zone: pcbnew.ZONE,
    net_map: dict[str, str],
):
    """Updates the target zone's net using net_map.

    If the source zone's netname exists in net_map, the target zone's net is set
    to the corresponding value. Otherwise, the net is set to no net (net code 0).
    """
    source_netname = source_zone.GetNetname()
    log.info(
        f"update_zone_net: source_zone net = {source_netname} "
        f"for target_zone {target_zone}"
    )
    if source_netname in net_map:
        target_net_name = net_map[source_netname]
        # We need to get the actual NETINFO_ITEM from the target board
        target_board = target_zone.GetBoard()
        target_net_info = target_board.FindNet(target_net_name)
        if target_net_info:
            target_zone.SetNet(target_net_info)
        else:
            log.warning(
                f"Could not find net '{target_net_name}' in target board for zone"
            )
            target_zone.SetNetCode(0)
    else:
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
    source: pcbnew.BOARD,
    target: pcbnew.BOARD,
    addr_map: dict[str, str],
    uuid_map: dict[str, str],
) -> list[str]:
    """Update the target board with the layout from the source board."""
    # Update the footprint position, orientation, and side to match the source
    source_addrs = footprints_by_addr(source, uuid_map)
    target_addrs = footprints_by_addr(target, uuid_map)
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
        source_pads = list(source_fp.Pads())
        target_pads = list(target_fp.Pads())

        # First try to match by pad number
        for target_pad in target_pads:
            pad_number = target_pad.GetNumber()
            matching_source_pads = [
                p for p in source_pads if p.GetNumber() == pad_number
            ]

            if len(matching_source_pads) == 1:
                # Exact match by number
                source_pad = matching_source_pads[0]
            elif len(matching_source_pads) > 1:
                # Multiple pads with same number, find best match by size and shape
                best_match = None
                min_diff = float("inf")

                for candidate in matching_source_pads:
                    # Calculate difference in size and shape
                    size_diff = abs(
                        candidate.GetSize().x - target_pad.GetSize().x
                    ) + abs(candidate.GetSize().y - target_pad.GetSize().y)
                    shape_diff = (
                        0 if candidate.GetShape() == target_pad.GetShape() else 10
                    )
                    total_diff = size_diff + shape_diff

                    if total_diff < min_diff:
                        min_diff = total_diff
                        best_match = candidate

                source_pad = best_match
            else:
                # No matching pad by number, try to find closest by size and position
                best_match = None
                min_diff = float("inf")

                for candidate in source_pads:
                    # Calculate difference in size
                    size_diff = abs(
                        candidate.GetSize().x - target_pad.GetSize().x
                    ) + abs(candidate.GetSize().y - target_pad.GetSize().y)

                    # Only consider pads with similar size (threshold can be adjusted)
                    if size_diff > 1.0:  # mm
                        continue

                    # If similar size, consider shape and layer
                    shape_diff = (
                        0 if candidate.GetShape() == target_pad.GetShape() else 10
                    )
                    layer_diff = (
                        0 if candidate.GetLayer() == target_pad.GetLayer() else 5
                    )

                    total_diff = size_diff + shape_diff + layer_diff

                    if total_diff < min_diff:
                        min_diff = total_diff
                        best_match = candidate

                if best_match is not None:
                    source_pad = best_match
                    log.warning(
                        f"Used fallback matching for pad {pad_number} in {t_addr}"
                    )
                else:
                    log.warning(
                        f"No suitable pad match found for {pad_number} in {s_addr}"
                    )
                    continue

            # Make sure we found a valid source pad before proceeding
            if source_pad is None:
                log.warning(
                    f"Failed to find suitable source pad match for target"
                    f" pad {pad_number} in {s_addr}"
                )
                continue

            # Apply the source pad's position and orientation to the target pad
            target_pad.SetPosition(source_pad.GetPosition())
            target_pad.SetOrientation(source_pad.GetOrientation())
            target_pad.SetLayer(source_pad.GetLayer())
            target_pad.SetLayerSet(source_pad.GetLayerSet())

    return missing_addrs


def find_anchor_footprint(fps: Iterable[pcbnew.FOOTPRINT]) -> pcbnew.FOOTPRINT:
    """
    Return anchor footprint with largest pin count in board or group: tiebreaker size
    """
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


def calculate_translation(
    source_fps: Iterable[pcbnew.FOOTPRINT], target_fps: Iterable[pcbnew.FOOTPRINT]
) -> pcbnew.VECTOR2I:
    """Calculate the translation vector between two groups of footprints."""
    source_anchor_fp = find_anchor_footprint(source_fps)
    source_offset = source_anchor_fp.GetPosition()
    target_anchor_fp = find_anchor_footprint(target_fps)
    target_offset = target_anchor_fp.GetPosition()
    total_offset = target_offset - source_offset
    return total_offset
