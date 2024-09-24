"""Replace common skidl functions with our own"""

from typing import Any, Iterator

from faebryk.core.trait import Trait
from faebryk.exporters.schematic.kicad.skidl.geometry import BBox, Point, Tx, Vector


def get_script_name():
    # TODO:
    raise NotImplementedError


def to_list(x):
    """
    Return x if it is already a list, or return a list containing x if x is a scalar.
    """
    if isinstance(x, (list, tuple, set)):
        return x  # Already a list, so just return it.
    return [x]  # Wasn't a list, so make it into one.


def rmv_attr(objs, attrs):
    """Remove a list of attributes from a list of objects."""
    for o in to_list(objs):
        for a in to_list(attrs):
            try:
                delattr(o, a)
            except AttributeError:
                pass


class Part:
    # We need to assign these

    # TODO: where are these expected to be assigned?
    pins: list["Pin"]  # TODO: source
    place_bbox: BBox  # TODO:
    lbl_bbox: BBox  # TODO:
    tx: Tx  # transformation matrix of the part's position
    prev_tx: Tx  # previous transformation matrix of the part's position
    anchor_pins: dict[Any, list["Pin"]]  # TODO: better types, what is this?
    pull_pins: dict[Any, list["Pin"]]  # TODO: better types, what is this?
    pin_ctrs: dict  # TODO: better types, what is this?
    saved_anchor_pins: dict[Any, list["Pin"]]  # copy of anchor_pins
    saved_pull_pins: dict[Any, list["Pin"]]  # copy of pull_pins
    delta_cost: float  # the largest decrease in cost and the associated orientation.
    delta_cost_tx: Tx  # transformation matrix associated with delta_cost
    orientation_locked: bool  # whether the part's orientation is locked

    # attr assigned, eg. I don't need to care about it
    original_tx: Tx  # internal use
    force: Vector  # used for debugging
    mv: Vector  # internal use

    def __iter__(self) -> Iterator["Pin"]:
        # TODO:
        raise NotImplementedError


class Pin:
    # We need to assign these
    num: str
    name: str

    # TODO: where are these expected to be assigned?
    part: Part  # TODO:
    place_pt: Point  # TODO:
    pt: Point  # TODO:
    stub: bool  # whether to stub the pin or not
    orientation: str  # TODO:
    route_pt: Point  # TODO:
    place_pt: Point  # TODO:
    orientation: str  # TODO:

    # Assigned in NetTerminal, but it's unclear
    # whether this is typically something that comes from the user
    x: float
    y: float

    def is_connected(self) -> bool:
        # TODO:
        raise NotImplementedError


class Net:
    # We need to assign these
    name: str
    netio: str  # whether input or output

    # TODO: where are these expected to be assigned?
    pins: list[Pin]  # TODO:
    parts: set[Part]  # TODO:

    def __iter__(self) -> Iterator[Pin]:
        yield from self.pins
