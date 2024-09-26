"""
Replace common skidl functions with our own

Design notes:
- Skidl's original code uses hasattr to check if an attribute is present.
    I don't want to refactor all this, so we're assigning attributes as Skidl does
- We're not using dataclasses because typing doesn't pass through InitVar properly
"""

from itertools import chain
from typing import TYPE_CHECKING, Any, Iterator, TypedDict

import faebryk.library._F as F
from faebryk.exporters.schematic.kicad.skidl.geometry import BBox, Point, Tx, Vector

if TYPE_CHECKING:
    from faebryk.libs.kicad import fileformats_sch

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



def angle_to_orientation(angle: float) -> str:
    """Convert an angle to an orientation"""
    if angle == 0:
        return "U"
    elif angle == 90:
        return "R"
    elif angle == 180:
        return "D"
    elif angle == 270:
        return "L"
    else:
        raise ValueError(f"Invalid angle: {angle}")


class Part:
    # We need to assign these
    hierarchy: str  # dot-separated string of part names
    pins: list["Pin"]
    ref: str
    # A string of H, V, L, R operations that are applied in sequence left-to-right.
    symtx: str
    unit: dict[str, "PartUnit"]  # units within the part, empty is this is all it is

    # things we've added to make life easier
    sch_symbol: fileformats_sch.C_kicad_sch_file.C_kicad_sch.C_symbol_instance
    fab_symbol: F.Symbol | None
    bare_bbox: BBox

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        for attr in [
            "hierarchy",
            "pins",
            "ref",
            "symtx",
            "unit",
            "fab_symbol",
            "bare_bbox",
        ]:
            if not hasattr(self, attr):
                raise ValueError(f"Missing attribute: {attr}")

        # don't audit pins, they're handled through nets instead
        for unit in self.unit.values():
            unit.audit()

    # internal use
    anchor_pins: dict[Any, list["Pin"]]
    bottom_track: "GlobalTrack"
    delta_cost_tx: Tx  # transformation matrix associated with delta_cost
    delta_cost: float  # the largest decrease in cost and the associated orientation.
    force: Vector  # used for debugging
    lbl_bbox: BBox
    left_track: "GlobalTrack"
    mv: Vector  # internal use
    # whether the part's orientation is locked, based on symtx or pin count
    orientation_locked: bool
    original_tx: Tx  # internal use
    pin_ctrs: dict["Net", Point]
    place_bbox: BBox
    prev_tx: Tx  # previous transformation matrix of the part's position
    pull_pins: dict[Any, list["Pin"]]
    right_track: "GlobalTrack"
    saved_anchor_pins: dict[Any, list["Pin"]]  # copy of anchor_pins
    saved_pull_pins: dict[Any, list["Pin"]]  # copy of pull_pins
    top_track: "GlobalTrack"
    tx: Tx  # transformation matrix of the part's position

    def __iter__(self) -> Iterator["Pin"]:
        yield from self.pins

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

    num: int  # which unit does this represent
    parent: Part

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        super().audit()
        for attr in ["num", "parent"]:
            if not hasattr(self, attr):
                raise ValueError(f"Missing attribute: {attr}")

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
    net: "Net"
    name: str
    num: str
    orientation: str  # "U"/"D"/"L"/"R" for the pin's location
    part: Part  # to which part does this pin belong?
    stub: bool  # whether to stub the pin or not
    # position of the pin
    # - relative to the part?
    x: float
    y: float

    # things we've added to make life easier
    sch_pin: fileformats_sch.C_kicad_sch_file.C_kicad_sch.C_symbol_instance.C_pin
    fab_pin: F.Symbol.Pin
    fab_is_gnd: bool
    fab_is_pwr: bool

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        for attr in [
            "name",
            "net",
            "num",
            "orientation",
            "part",
            "stub",
            "x",
            "y",
            "fab_pin",
            "fab_is_gnd",
            "fab_is_pwr",
        ]:
            if not hasattr(self, attr):
                raise ValueError(f"Missing attribute: {attr}")

    # internal use
    bbox: BBox
    face: "Face"
    place_pt: Point
    pt: Point
    route_pt: Point
    routed: bool

    def is_connected(self) -> bool:
        """Whether the pin is connected to anything"""
        raise NotImplementedError


class Net:
    # We need to assign these
    name: str
    netio: str  # whether input or output
    pins: list[Pin]
    stub: bool  # whether to stub the pin or not

    # internal use
    parts: set[Part]

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        for attr in ["name", "netio", "pins", "stub"]:
            if not hasattr(self, attr):
                raise ValueError(f"Missing attribute: {attr}")

        for pin in self.pins:
            pin.audit()

    def __bool__(self) -> bool:
        """TODO: does this need to be false if no parts or pins?"""
        raise NotImplementedError

    def __iter__(self) -> Iterator[Pin | Part]:
        raise NotImplementedError  # not sure what to output here
        yield from self.pins
        yield from self.parts

    def __hash__(self) -> int:
        """Nets are sometimes used as keys in dicts, so they must be hashable"""
        return id(self)

    def is_implicit(self) -> bool:
        """Whether the net has a user-assigned name"""
        raise NotImplementedError


class Circuit:
    nets: list[Net]
    parts: list[Part]

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        for attr in ["nets", "parts"]:
            if not hasattr(self, attr):
                raise ValueError(f"Missing attribute: {attr}")

        for obj in chain(self.nets, self.parts):
            obj.audit()


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
