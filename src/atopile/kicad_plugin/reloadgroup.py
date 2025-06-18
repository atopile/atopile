import logging
from pathlib import Path

import pcbnew  # type: ignore

from .common import (
    footprints_by_addr,
    get_footprint_addr,
    get_layout_map,
    groups_by_name,
    log_exceptions,
)

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
        board_path = Path(board.GetFileName())

        groups = groups_by_name(board)
        log.debug(f"Named groups in boards: {groups}")

        # We can ignore the uuid map here because in the context of the parent module,
        # there will always be addresses with the v0.3 compiler
        footprints = footprints_by_addr(board, {})

        for group_name, group_data in get_layout_map(board_path).items():
            log.debug(f"Updating group {group_name}")

            # FIXME: we rely on the fact that this dict is topologically sorted
            # from the layout.py code to ensure that nested groups are created
            # prior to their parent groups

            # If the group doesn't yet exist in the layout
            # create it and add it to the board
            if group_name in groups:
                g = groups[group_name]
                log.debug(f"Group {group_name} already exists. Using it.")
            else:
                g = pcbnew.PCB_GROUP(board)
                g.SetName(group_name)
                board.Add(g)
                groups[group_name] = g
                log.debug(f"Group {group_name} created and added to board")

            # Make sure all the footprints in the group are up to date
            footprints_in_group = {
                addr
                for fp in g.GetItems()
                if isinstance(fp, pcbnew.FOOTPRINT)
                and (addr := get_footprint_addr(fp, {}))
                and addr in footprints
            }
            expected_footprints = set(group_data["group_components"])

            for fp_addr in footprints_in_group - expected_footprints:
                g.RemoveItem(footprints[fp_addr])
                log.debug(f"Removed footprint {fp_addr}")

            # Add all items to the group
            # Start with the footprints
            for fp_addr in expected_footprints - footprints_in_group:
                if fp_addr in footprints:
                    g.AddItem(footprints[fp_addr])

            # FIXME: nested groups are not yet supported
            if group_data["nested_groups"]:
                raise NotImplementedError("Nested groups are not yet supported")


with log_exceptions():
    ReloadGroup().register()
