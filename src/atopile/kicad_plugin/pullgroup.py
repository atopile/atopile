import logging
from pathlib import Path

import pcbnew  # type: ignore

from .common import (
    calculate_translation,
    flip_dict,
    footprints_by_addr,
    generate_net_map,
    get_footprint_addr,
    get_group_footprints,
    get_layout_map,
    groups_by_name,
    log_exceptions,
    sync_drawing,
    sync_footprints,
    sync_track,
    sync_zone,
    update_zone_net,
)

log = logging.getLogger(__name__)


def sync():
    board: pcbnew.BOARD = pcbnew.GetBoard()
    board_path = Path(board.GetFileName())

    groups = groups_by_name(board)
    log.debug(f"Named groups in boards: {groups}")

    # We can ignore the uuid map here because in the context of the parent module,
    # there will always be addresses with the v0.3 compiler
    footprints = footprints_by_addr(board, {})

    for group_name, group_data in get_layout_map(board_path).items():
        log.debug(f"Updating group {group_name}")

        # FIXME: we rely on the fact that this dict is topologically sorted
        # from the layout.py code to ensure that nested groups are created
        # prior to their parent groups

        # If the group doesn't yet exist in the layout
        # create it and add it to the board
        if group_name in groups:
            g = groups[group_name]
            log.debug(f"Group {group_name} already exists. Using it.")
        else:
            g = pcbnew.PCB_GROUP(board)
            g.SetName(group_name)
            board.Add(g)
            groups[group_name] = g
            log.debug(f"Group {group_name} created and added to board")

        # Make sure all the footprints in the group are up to date
        footprints_in_group = {
            addr
            for fp in g.GetItems()
            if isinstance(fp, pcbnew.FOOTPRINT)
            and (addr := get_footprint_addr(fp, {}))
            and addr in footprints
        }
        expected_footprints = set(group_data["group_components"])

        for fp_addr in footprints_in_group - expected_footprints:
            g.RemoveItem(footprints[fp_addr])
            log.debug(f"Removed footprint {fp_addr}")

        # Add all items to the group
        # Start with the footprints
        for fp_addr in expected_footprints - footprints_in_group:
            if fp_addr in footprints:
                g.AddItem(footprints[fp_addr])

        # FIXME: nested groups are not yet supported
        if group_data["nested_groups"]:
            raise NotImplementedError("Nested groups are not yet supported")
    pcbnew.Refresh()


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

        sync()

        selected_groups = [
            g
            for g in target_board.Groups()
            if g.IsSelected()
            or
            # add all groups where all parts of the group are selected
            all(item.IsSelected() for item in g.GetItems())
        ]

        # Pull Selected Groups
        for g in selected_groups:
            assert isinstance(g, pcbnew.PCB_GROUP)

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
