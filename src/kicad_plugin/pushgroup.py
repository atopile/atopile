import logging
from pathlib import Path

import pcbnew

from .common import get_layout_map, sync_footprints, sync_track

log = logging.getLogger(__name__)


class PushGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Push Group"
        self.category = "Push Group Layout Atopile"
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "upload.png")
        self.dark_icon_file_name = self.icon_file_name

    def Run(self):
        source_board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = source_board.GetFileName()
        known_layouts = get_layout_map(board_path)

        # Push Selected Groups
        for g in source_board.Groups():
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

            target_board: pcbnew.BOARD = pcbnew.LoadBoard(str(layout_path))

            # Remove everything but the footprints from the target board
            for item in target_board.GetTracks():
                target_board.Remove(item)

            # Push the layout
            sync_footprints(
                source_board, target_board, known_layouts[g_name]["uuid_map"]
            )
            for track in g.GetItems():
                if isinstance(track, pcbnew.PCB_TRACK):
                    sync_track(track, target_board)

        # Save the target board
        target_board.Save(target_board.GetFileName())

PushGroup().register()
