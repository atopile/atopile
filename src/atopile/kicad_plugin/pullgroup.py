import logging
from pathlib import Path

import pcbnew

from .common import (
    calculate_translation,
    flip_dict,
    get_group_footprints,
    get_layout_map,
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
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "download.png")
        self.dark_icon_file_name = self.icon_file_name

    def Run(self):
        target_board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = target_board.GetFileName()
        known_layouts = get_layout_map(board_path)

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
            offset = calculate_translation(source_fps=source_board.GetFootprints(), target_fps=get_group_footprints(g))

            sync_footprints(
                source_board, target_board, flip_dict(known_layouts[g_name]["uuid_map"])
            )

            for track in source_board.GetTracks():
                item = sync_track(source_board, track, target_board)
                g.AddItem(item)

            for zone in source_board.Zones():
                new_zone = sync_zone(zone,target_board)
                update_zone_net(zone, source_board, new_zone, target_board, flip_dict(known_layouts[g_name]["uuid_map"]))
                g.AddItem(new_zone)

            # Shift entire target group by offset as last operation
            g.Move(offset)

        pcbnew.Refresh()


PullGroup().register()
