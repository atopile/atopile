import logging
from pathlib import Path

import pcbnew  # type: ignore

from .common import (
    calculate_translation,
    flip_dict,
    generate_net_map,
    get_group_footprints,
    get_layout_map,
    log_exceptions,
    sync_drawing,
    sync_footprints,
    sync_track,
    sync_zone,
    update_zone_net,
)

log = logging.getLogger(__name__)


class PullGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Pull Group"
        self.category = "Pull Group Layout Atopile"
        self.description = (
            "Layout components on PCB in same spatial"
            " relationships as components on schematic"
        )
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "download.png")
        self.dark_icon_file_name = self.icon_file_name

    @log_exceptions()
    def Run(self):
        target_board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = target_board.GetFileName()
        known_layouts = get_layout_map(board_path)

        combined_addr_map = {}
        combined_uuid_map = {}
        for group_key, group_val in known_layouts.items():
            # Expect each group value to be a dict with a 'layout_path' key
            if isinstance(group_val, dict) and "layout_path" in group_val:
                combined_addr_map.update(group_val.get("addr_map", {}))
                combined_uuid_map.update(group_val.get("uuid_to_addr_map", {}))

        log.info(f"Combined addr_map: {combined_addr_map}")
        log.info(f"Combined uuid_to_addr_map: {combined_uuid_map}")

        # Pull Selected Groups
        for g in target_board.Groups():
            assert isinstance(g, pcbnew.PCB_GROUP)

            # Skip over unselected groups
            if not g.IsSelected():
                continue

            g_name = g.GetName()
            if g_name not in known_layouts:
                continue

            layout_path = Path(known_layouts[g_name]["layout_path"])
            # Check what layouts exist
            if not layout_path.exists():
                raise FileNotFoundError(
                    f"Cannot load group. Layout file {layout_path} does not exist"
                )

            # Remove everything but the footprints from the target group
            for item in g.GetItems():
                if not isinstance(item, pcbnew.FOOTPRINT):
                    target_board.Remove(item)

            # Load the layout and sync
            source_board: pcbnew.BOARD = pcbnew.LoadBoard(str(layout_path))

            # Calculate offset before moving footprints
            offset = calculate_translation(
                source_fps=source_board.GetFootprints(),
                target_fps=get_group_footprints(g),
            )

            layout_maps = known_layouts[g_name]

            # Get addr_map and uuid_map for this specific layout
            layout_addr_map = layout_maps.get("addr_map", {})
            layout_uuid_map = layout_maps.get("uuid_to_addr_map", {})

            if "addr_map" not in layout_maps:
                log.error(
                    f"[DEBUG] layout_maps keys for group {g_name}: "
                    f"{list(layout_maps.keys())}"
                )
                log.warning(
                    f"'addr_map' key not found in layout_maps for group {g_name}; "
                    f"defaulting to empty mapping"
                )
            if "uuid_to_addr_map" not in layout_maps:
                log.error(
                    f"[DEBUG] layout_maps keys for group {g_name}: "
                    f"{list(layout_maps.keys())}"
                )
                log.warning(
                    f"'uuid_to_addr_map' key not found in layout_maps for"
                    f" group {g_name}; defaulting to empty mapping"
                )

            # Generate net_map specifically for this source layout and target board
            try:
                net_map = generate_net_map(
                    source_board=source_board,
                    target_board=target_board,
                    addr_map=flip_dict(layout_addr_map),
                    uuid_map=layout_uuid_map,
                )

                # Log some info about the nets for debugging
                # NetsByName() returns a dict where keys are the net names
                source_nets = list(source_board.GetNetInfo().NetsByName().keys())
                # Convert wxString to Python string for logging - used for display below
                source_nets_as_str = [str(net) for net in source_nets]
                log.info(f"Source board nets count: {len(source_nets)}")
                log.info(f"Net map entries count: {len(net_map)}")

                # Find unmapped nets that aren't empty
                unmapped_nets = [
                    net
                    for net in source_nets_as_str
                    if net not in net_map and net != ""
                ]
                log.info(f"Unmapped nets: {unmapped_nets}")

            except KeyError as e:
                log.error(
                    f"KeyError in generate_net_map for group {g_name}: {e}. "
                    f"Layout map keys: {list(layout_addr_map.keys())}"
                )
                raise

            sync_footprints(
                source_board,
                target_board,
                flip_dict(layout_maps.get("addr_map", {})),
                layout_maps.get("uuid_to_addr_map", {}),
            )

            for track in source_board.GetTracks():
                item = sync_track(source_board, track, target_board, net_map)
                g.AddItem(item)

            for drawing in source_board.GetDrawings():
                item = sync_drawing(source_board, drawing, target_board)
                g.AddItem(item)

            for zone in source_board.Zones():
                new_zone = sync_zone(zone, target_board)
                update_zone_net(
                    zone,
                    new_zone,
                    net_map,
                )
                g.AddItem(new_zone)

            # Shift entire target group by offset as last operation
            g.Move(offset)

        pcbnew.Refresh()


with log_exceptions():
    PullGroup().register()
