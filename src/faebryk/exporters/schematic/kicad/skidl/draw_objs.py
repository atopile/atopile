# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

"""
KiCad 5 drawing objects.
"""

from collections import namedtuple


DrawDef = namedtuple(
    "DrawDef",
    "name ref zero name_offset show_nums show_names num_units lock_units power_symbol",
)

DrawF0 = namedtuple("DrawF0", "ref x y size orientation visibility halign valign")

DrawF1 = namedtuple(
    "DrawF1", "name x y size orientation visibility halign valign fieldname"
)

DrawArc = namedtuple(
    "DrawArc",
    "cx cy radius start_angle end_angle unit dmg thickness fill startx starty endx endy",
)

DrawCircle = namedtuple("DrawCircle", "cx cy radius unit dmg thickness fill")

DrawPoly = namedtuple("DrawPoly", "point_count unit dmg thickness points fill")

DrawRect = namedtuple("DrawRect", "x1 y1 x2 y2 unit dmg thickness fill")

DrawText = namedtuple(
    "DrawText", "angle x y size hidden unit dmg text italic bold halign valign"
)

DrawPin = namedtuple(
    "DrawPin",
    "name num x y length orientation num_size name_size unit dmg electrical_type shape",
)
