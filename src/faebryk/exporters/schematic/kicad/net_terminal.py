# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

from skidl import Part, Pin
from skidl.utilities import export_to_all
from .geometry import Point, Tx, Vector


"""
Net_Terminal class for handling net labels.
"""


@export_to_all
class NetTerminal(Part):
    def __init__(self, net, tool_module):
        """Specialized Part with a single pin attached to a net.

        This is intended for attaching to nets to label them, typically when
        the net spans across levels of hierarchical nodes.
        """

        # Create a Part.
        from skidl import SKIDL

        super().__init__(name="NT", ref_prefix="NT", tool=SKIDL)

        # Set a default transformation matrix for this part.
        self.tx = Tx()

        # Add a single pin to the part.
        pin = Pin(num="1", name="~")
        self.add_pins(pin)

        # Connect the pin to the net.
        pin += net

        # Set the pin at point (0,0) and pointing leftward toward the part body
        # (consisting of just the net label for this type of part) so any attached routing
        # will go to the right.
        pin.x, pin.y = 0, 0
        pin.pt = Point(pin.x, pin.y)
        pin.orientation = "L"

        # Calculate the bounding box, but as if the pin were pointed right so
        # the associated label text would go to the left.
        self.bbox = tool_module.calc_hier_label_bbox(net.name, "R")

        # Resize bbox so it's an integer number of GRIDs.
        self.bbox = self.bbox.snap_resize(tool_module.constants.GRID)

        # Extend the bounding box a bit so any attached routing will come straight in.
        self.bbox.max += Vector(tool_module.constants.GRID, 0)
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
