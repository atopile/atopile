import logging
from pathlib import Path

import pcbnew

from .common import footprints_by_addr, get_layout_map, groups_by_name, log_exceptions

log = logging.getLogger(__name__)


class ReloadGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Reload Group"
        self.category = "Reload Group Layout Atopile"
        self.description = (
            "Layout components on PCB in same spatial"
            " relationships as components on schematic"
        )
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "reload.png")
        self.dark_icon_file_name = self.icon_file_name

    @log_exceptions()
    def Run(self):
        board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = board.GetFileName()

        groups = groups_by_name(board)
        # We can ignore the uuid map here because in the context of the parent module,
        # there will always be addresses with the v0.3 compiler
        footprints = footprints_by_addr(board, {})

        for group_name, group_data in get_layout_map(board_path).items():
            # FIXME: we rely on the fact that this dict is topologically sorted
            # from the layout.py code to ensure that nested groups are created
            # prior to their parent groups

            # If the group doesn't yet exist in the layout
            # create it and add it to the board
            if group_name in groups:
                g = groups[group_name]
            else:
                g = pcbnew.PCB_GROUP(board)
                g.SetName(group_name)
                board.Add(g)
                groups[group_name] = g

            # Empty the group of footprints to begin with
            for fp in g.GetItems():
                if isinstance(fp, pcbnew.FOOTPRINT):
                    g.RemoveItem(fp)

            # Add all items to the group
            # Start with the footprints
            for fp_addr in group_data["group_components"]:
                g.AddItem(footprints[fp_addr])

            # Then add the nested groups
            for nested_group_addr in group_data["nested_groups"]:
                g.AddItem(groups[nested_group_addr])


with log_exceptions():
    ReloadGroup().register()
