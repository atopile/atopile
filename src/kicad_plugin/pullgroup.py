import csv
import logging
from pathlib import Path
from typing import Optional

import pcbnew

from .common import get_layout_path, get_prj_dir, name2des, parse_hierarchy

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
        board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = board.GetFileName()
        prjpath = get_prj_dir(board_path)

        heir = parse_hierarchy(board_path)

        # Pull Selected Groups
        for g in board.Groups():
            # Skip over unselected groups
            if not g.IsSelected():
                continue

            g_name = g.GetName()
            if g_name not in heir:
                continue

            layout_path = get_layout_path(prjpath, heir[g_name]["_package"])
            # Check what layouts exist
            if not layout_path.exists():
                raise FileNotFoundError(
                    f"Cannot load group. Layout file {layout_path} does not exist"
                )

            with layout_path.open("r") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header row

                offset_x: Optional[int] = None
                offset_y: Optional[int] = None
                for name, x, y, theta in reader:
                    # Extract name and designator
                    des = name2des(name, heir[g_name])
                    if not des:
                        continue

                    fp: pcbnew.FOOTPRINT = board.FindFootprintByReference(des)
                    if not fp:
                        continue

                    if offset_x is None:
                        offset_x, offset_y = fp.GetPosition()

                    fp.SetPosition(pcbnew.VECTOR2I(
                        int(int(x) + offset_x),
                        int(int(y) + offset_y)
                    ))
                    fp.SetOrientationDegrees(float(theta))
                    fp.SetDescription(name)


PullGroup().register()
