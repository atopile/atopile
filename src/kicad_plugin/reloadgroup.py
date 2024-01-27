import csv
import logging
from pathlib import Path

import pcbnew

from .common import get_prj_dir, parse_hierarchy

log = logging.getLogger(__name__)


class ReloadGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Reload Group"
        self.category = "Reload Group Layout Atopile"
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = str(Path(__file__).parent / "reload.png")
        self.dark_icon_file_name = self.icon_file_name

    def Run(self):
        board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = board.GetFileName()

        heir = parse_hierarchy(board_path)

        # Setup groups if first time opening
        existing_groups = {g.GetName(): g for g in board.Groups()}

        for known_group_name, known_group_refs in heir.items():
            # If the group doesn't yet exist in the layout
            # create it and add it to the board
            if known_group_name in existing_groups:
                g = existing_groups[known_group_name]
            else:
                g = pcbnew.PCB_GROUP(board)
                g.SetName(known_group_name)
                board.Add(g)

            # Populate group with footprints
            for ref in known_group_refs:
                if not ref:
                    continue

                fp = board.FindFootprintByReference(ref)
                if not fp:
                    continue

                g.AddItem(fp)

ReloadGroup().register()
