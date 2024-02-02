import csv
import logging
from io import StringIO
from pathlib import Path
from typing import Optional

import pcbnew

from .common import get_layout_path, get_prj_dir, parse_hierarchy

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
        board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = board.GetFileName()
        prjpath = get_prj_dir(board_path)

        heir = parse_hierarchy(board_path)

        sel_gs = [g for g in board.Groups() if g.IsSelected()]  # Selected groups

        for sg in sel_gs:
            csv_table = StringIO()
            writer = csv.DictWriter(csv_table, fieldnames=["Name", "x", "y", "theta"])
            writer.writeheader()

            g_name = sg.GetName()
            offset_x: Optional[int] = None
            offset_y: Optional[int] = None
            for item in sg.GetItems():
                if "Footprint" not in item.GetFriendlyName():
                    continue

                x, y = item.GetPosition()
                if offset_x is None:
                    offset_x = x
                    offset_y = y

                item_ref = item.GetReference()
                name = heir[g_name].get(item_ref)
                if not name:
                    continue

                writer.writerow(
                    {
                        "Name": name,
                        "x": x - offset_x,
                        "y": y - offset_y,
                        "theta": item.GetOrientationDegrees(),
                    }
                )

            layout_path = get_layout_path(prjpath, heir[g_name]["_package"])
            with layout_path.open("w") as f:
                f.write(csv_table.getvalue())


PushGroup().register()
