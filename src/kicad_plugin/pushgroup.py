import csv
import logging
from pathlib import Path

import pcbnew

from .common import get_layout_path, get_prj_dir, name2des, parse_hierarchy

log = logging.getLogger(__name__)


class PullGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Pull Group"
        self.category = "Pull Group Layout Atopile"
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = Path(__file__).parent / "download.png"
        self.dark_icon_file_name = self.icon_file_name

    def Run(self):
        board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = board.GetFileName()
        prjpath = get_prj_dir(board_path)

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


        # Pull Selected Groups
        for g in board.Groups():
            # Skip over unselected groups
            if not g.IsSelected():
                continue

            g_name = g.GetName()
            layout_path = get_layout_path(prjpath, heir[g_name]['_package'])
            with layout_path.open("r", newline="") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header row

                for name, x, y, theta in reader:
                    # Extract name and designator
                    des = name2des(name, heir[g_name])
                    if not des:
                        continue

                    fp: pcbnew.FOOTPRINT = board.FindFootprintByReference(des)
                    if not fp:
                        continue

                    fp.SetPosition(pcbnew.VECTOR2I(float(x), float(y)))
                    fp.SetOrientationDegrees(float(theta))
                    fp.SetDescription(name)

PullGroup().register()
