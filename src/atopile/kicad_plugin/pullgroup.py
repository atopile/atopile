import logging
from pathlib import Path

import pcbnew

from .common import get_layout_map, sync_footprints, flip_dict, sync_track

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
            sync_footprints(
                source_board, target_board, flip_dict(known_layouts[g_name]["uuid_map"])
            )

            for track in source_board.GetTracks():
                item = sync_track(track, target_board)
                g.AddItem(item)

        pcbnew.Refresh()


PullGroup().register()
