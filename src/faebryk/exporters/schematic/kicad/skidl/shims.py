"""Replace common skidl functions with our own"""

from typing import TYPE_CHECKING, Any, Iterator, TypedDict

from faebryk.exporters.schematic.kicad.skidl.geometry import BBox, Point, Tx, Vector
from dataclasses import dataclass

if TYPE_CHECKING:
    from .route import Face, GlobalTrack


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
    ref: str
    hierarchy: str  # dot-separated string of part names
    unit: dict[str, "PartUnit"]  # units within the part, empty is this is all it is
    pins: list["Pin"]  # TODO: source

    # TODO: where are these expected to be assigned?
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
    left_track: "GlobalTrack"
    right_track: "GlobalTrack"
    top_track: "GlobalTrack"
    bottom_track: "GlobalTrack"

    def __iter__(self) -> Iterator["Pin"]:
        # TODO:
        raise NotImplementedError

    @property
    def draw(self):
        # TODO:
        raise NotImplementedError

    def grab_pins(self) -> None:
        """Grab pin from Part and assign to PartUnit."""

        for pin in self.pins:
            pin.part = self


class PartUnit(Part):
    # TODO: represent these in Faebryk

    parent: Part

    def grab_pins(self) -> None:
        """Grab pin from Part and assign to PartUnit."""

        for pin in self.pins:
            pin.part = self

    def release_pins(self) -> None:
        """Return PartUnit pins to parent Part."""

        for pin in self.pins:
            pin.part = self.parent


class Pin:
    # We need to assign these
    num: str
    name: str
    net: "Net"
    stub: bool  # whether to stub the pin or not

    # TODO: where are these expected to be assigned?
    part: Part  # TODO:
    place_pt: Point  # TODO:
    pt: Point  # TODO:
    orientation: str  # TODO:
    route_pt: Point  # TODO:
    place_pt: Point  # TODO:
    orientation: str  # TODO:
    bbox: BBox  # TODO:

    # Assigned in NetTerminal, but it's unclear
    # whether this is typically something that comes from the user
    x: float
    y: float

    # internal use
    routed: bool
    route_pt: Point
    face: "Face"

    def is_connected(self) -> bool:
        # TODO:
        raise NotImplementedError


class Net:
    # We need to assign these
    name: str
    netio: str  # whether input or output
    pins: list[Pin]
    parts: set[Part]
    stub: bool  # whether to stub the pin or not

    def __bool__(self) -> bool:
        """TODO: does this need to be false if no parts or pins?"""
        raise NotImplementedError

    def __iter__(self) -> Iterator[Pin | Part]:
        yield from self.pins
        yield from self.parts

    def is_implicit(self) -> bool:
        # TODO:
        # Hint; The net has a user-assigned name, so add a terminal to it below.
        raise NotImplementedError


class Circuit:
    parts: list[Part]
    nets: list[Net]


class Options(TypedDict):
    allow_routing_failure: bool
    compress_before_place: bool
    dont_rotate_pin_count: int
    draw_assigned_terminals: bool
    draw_font: str
    draw_global_routing: bool
    draw_placement: bool
    draw_routing_channels: bool
    draw_routing: bool
    draw_scr: bool
    draw_switchbox_boundary: bool
    draw_switchbox_routing: bool
    draw_tx: Tx
    expansion_factor: float
    graphics_only: bool
    net_normalize: bool
    pin_normalize: bool
    pt_to_pt_mult: float
    rotate_parts: bool
    seed: int
    show_capacities: bool
    terminal_evolution: str
    use_push_pull: bool
