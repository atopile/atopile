# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

from .constants import GRID
from .geometry import Point, Tx, Vector
from .shims import Net, Part, Pin

"""
Net_Terminal class for handling net labels.
"""


class NetTerminal(Part):
    pull_pins: dict[Net, list[Pin]]

    def __init__(self, net: Net, tool_module):
        """Specialized Part with a single pin attached to a net.

        This is intended for attaching to nets to label them, typically when
        the net spans across levels of hierarchical nodes.
        """
        from .bboxes import calc_hier_label_bbox
        # Set a default transformation matrix for this part.
        self.tx = Tx()

        # Add a single pin to the part.
        pin = Pin()
        pin.part = self
        pin.num = "1"
        pin.name = "~"
        self.pins = [pin]

        # Connect the pin to the net.
        net.pins.append(pin)

        # Set the pin at point (0,0) and pointing leftward toward the part body
        # (consisting of just the net label for this type of part) so any attached routing
        # will go to the right.
        pin.x, pin.y = 0, 0
        pin.pt = Point(pin.x, pin.y)
        pin.orientation = "L"

        # Calculate the bounding box, but as if the pin were pointed right so
        # the associated label text would go to the left.
        self.bbox = calc_hier_label_bbox(net.name, "R")

        # Resize bbox so it's an integer number of GRIDs.
        self.bbox = self.bbox.snap_resize(GRID)

        # Extend the bounding box a bit so any attached routing will come straight in.
        self.bbox.max += Vector(GRID, 0)
        self.lbl_bbox = self.bbox

        # Flip the NetTerminal horizontally if it is an output net (label on the right).
        netio = getattr(net, "netio", "").lower()
        self.orientation_locked = bool(netio in ("i", "o"))
        if getattr(net, "netio", "").lower() == "o":
            origin = Point(0, 0)
            term_origin = self.tx.origin
            self.tx = (
                self.tx.move(origin - term_origin).flip_x().move(term_origin - origin)
            )
