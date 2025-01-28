import logging
from pathlib import Path

import pcbnew

from .common import (
    calculate_translation,
    get_group_footprints,
    get_layout_map,
    log_exceptions,
    sync_drawing,
    sync_footprints,
    sync_track,
)

log = logging.getLogger(__name__)


class PushGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Push Group"
        self.category = "Push Group Layout Atopile"
        self.description = (
            "Layout components on PCB in same spatial"
            " relationships as components on schematic"
        )
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "upload.png")
        self.dark_icon_file_name = self.icon_file_name

    @log_exceptions()
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

            log.debug(f"Loading layout {layout_path}")
            target_board: pcbnew.BOARD = pcbnew.LoadBoard(str(layout_path))

            # Remove everything but the footprints from the target board
            log.debug(f"Removing tracks from {layout_path}")
            for item in target_board.GetTracks():
                target_board.Remove(item)

            # Calculate offset before moving footprints
            offset = calculate_translation(
                source_fps=get_group_footprints(g),
                target_fps=source_board.GetFootprints(),
            )

            layout_maps = known_layouts[g_name]

            # Push the layout
            log.debug(f"Syncing footprints from {layout_path}")
            sync_footprints(
                source_board,
                target_board,
                layout_maps["addr_map"],
                layout_maps["uuid_to_addr_map"],
            )

            for i in g.GetItems():
                if isinstance(i, pcbnew.PCB_TRACK):
                    log.debug(f"Syncing track from {layout_path}")
                    sync_track(source_board, i, target_board)
                elif isinstance(i, pcbnew.DRAWINGS):
                    log.debug(f"Syncing drawing from {layout_path}")
                    sync_drawing(source_board, i, target_board)

            # Shift all objects of interest by offset
            for fp in target_board.GetFootprints():
                log.debug(f"Moving footprint {fp.GetReference()} from {layout_path}")
                fp.Move(offset)

            for track in target_board.GetTracks():
                log.debug(f"Moving track {track.GetClass()} from {layout_path}")
                track.Move(offset)

            # Save the target board
            log.debug(f"Saving {target_board.GetFileName()}")
            target_board.Save(target_board.GetFileName())


with log_exceptions():
    PushGroup().register()
