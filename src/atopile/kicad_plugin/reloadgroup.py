import logging
from pathlib import Path

import pcbnew

from .common import (
    get_layout_map,
    groups_by_name,
    get_footprint_addr,
    footprints_by_addr,
    log_exceptions
)

log = logging.getLogger(__name__)


class ReloadGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Reload Group"
        self.category = "Reload Group Layout Atopile"
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "reload.png")
        self.dark_icon_file_name = self.icon_file_name

    @log_exceptions()
    def Run(self):
        board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = board.GetFileName()

        existing_groups = groups_by_name(board)
        footprints = footprints_by_addr(board)

        for group_name, group_data in get_layout_map(board_path).items():
            # If the group doesn't yet exist in the layout
            # create it and add it to the board
            if group_name in existing_groups:
                g = existing_groups[group_name]
            else:
                g = pcbnew.PCB_GROUP(board)
                g.SetName(group_name)
                board.Add(g)

            # Make sure all the footprints in the group are up to date
            footprints_in_group = {
                addr
                for fp in g.GetItems()
                if isinstance(fp, pcbnew.FOOTPRINT)
                and (addr := get_footprint_addr(fp))
                and addr in footprints
            }
            expected_footprints = set(group_data["addr_map"].keys())
            for fp_addr in footprints_in_group - expected_footprints:
                g.RemoveItem(footprints[fp_addr])
            for fp_addr in expected_footprints - footprints_in_group:
                g.AddItem(footprints[fp_addr])

with log_exceptions():
    ReloadGroup().register()
