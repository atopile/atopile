"""Replace common skidl functions with our own"""

from typing import Iterator
from faebryk.core.trait import Trait
from faebryk.exporters.pcb.kicad.transformer import Point
from faebryk.exporters.schematic.kicad.skidl.geometry import BBox, Tx


def get_script_name():
    # TODO:
    raise NotImplementedError

def rmv_attr():
    # TODO:
    raise NotImplementedError

class Part(Trait):
    pins: list["Pin"]  # TODO:
    place_bbox: BBox  # TODO:
    lbl_bbox: BBox  # TODO:
    tx: Tx  # transformation matrix of the part's position

    def __iter__(self) -> Iterator["Pin"]:
        # TODO:
        raise NotImplementedError

class Pin(Trait):
    part: Part  # TODO:
    place_pt: Point  # TODO:
    pt: Point  # TODO:
    stub: bool  # whether to stub the pin or not
    orientation: str  # TODO:

    def is_connected(self) -> bool:
        # TODO:
        raise NotImplementedError


