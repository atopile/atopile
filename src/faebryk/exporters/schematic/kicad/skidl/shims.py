"""
Replace common skidl functions with our own

Design notes:
- Skidl's original code uses hasattr to check if an attribute is present.
    I don't want to refactor all this, so we're assigning attributes as Skidl does
- We're not using dataclasses because typing doesn't pass through InitVar properly
"""

import math
from itertools import chain
from typing import TYPE_CHECKING, Any, Iterator, TypedDict

from .constants import GRID
from .geometry import Point, Tx, Vector

import faebryk.library._F as F
from faebryk.exporters.schematic.kicad.skidl.geometry import BBox, Point, Tx, Vector

if TYPE_CHECKING:
    import pygame

    from faebryk.libs.kicad import fileformats_sch

    from .route import Face, GlobalTrack


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
    if math.isclose(angle, 0):
        return "R"
    elif math.isclose(angle, 90):
        return "U"
    elif math.isclose(angle, 180):
        return "L"
    elif math.isclose(angle, 270):
        return "D"
    else:
        raise ValueError(f"Invalid angle: {angle}")


def audit_has(obj, attrs: list[str]) -> None:
    """Ensure mandatory attributes are set"""
    missing = [attr for attr in attrs if not hasattr(obj, attr)]
    if missing:
        raise ValueError(f"Missing attributes: {missing}")


class Part:
    # We need to assign these
    hierarchy: str  # dot-separated string of part names
    pins: list["Pin"]
    ref: str
    # A string of H, V, L, R operations that are applied in sequence left-to-right.
    symtx: str
    unit: dict[str, "PartUnit"]  # units within the part, empty is this is all it is
    bare_bbox: BBox
    hints: F.has_schematic_hints

    # things we've added to make life easier
    sch_symbol: "fileformats_sch.C_kicad_sch_file.C_kicad_sch.C_symbol_instance"
    fab_symbol: F.Symbol | None
    _similarites: dict["Part", float]

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        audit_has(
            self,
            [
                "hierarchy",
                "pins",
                "ref",
                "symtx",
                "unit",
                "fab_symbol",
                "sch_symbol",
                "bare_bbox",
                "_similarites",
            ],
        )

        for pin in self.pins:
            pin.audit()

        for unit in self.unit.values():
            unit.audit()

    # internal use
    anchor_pins: dict[Any, list["Pin"]]
    bottom_track: "GlobalTrack"
    delta_cost_tx: Tx  # transformation matrix associated with delta_cost
    delta_cost: float  # the largest decrease in cost and the associated orientation.
    force: Vector  # used for debugging
    bbox: BBox
    lbl_bbox: BBox  # The bbox and lbl_bbox are tied together
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
    _tx: Tx  # transformation matrix of the part's position

    def __iter__(self) -> Iterator["Pin"]:
        yield from self.pins

    def __len__(self) -> int:
        return len(self.pins)

    def __hash__(self) -> int:
        """Make hashable for use in dicts"""
        return id(self)

    @property
    def draw(self):
        """This was used in SKiDL to capture all the drawn elements in a design."""
        raise NotImplementedError

    def grab_pins(self) -> None:
        """Grab pin from Part and assign to PartUnit."""

        for pin in self.pins:
            pin.part = self

    def similarity(self, part: "Part", **options) -> float:
        assert not options, "No options supported"
        return self._similarites[part]

    @property
    def tx(self) -> Tx:
        return self._tx

    @tx.setter
    def tx(self, tx: Tx) -> None:
        self._tx = tx


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

    # Pin rotation is confusing, because it has to do with the way to line coming
    # from the pin is facing, not the side of the part/package it's on.
    # Here's a diagram to help:
    #
    #          D
    #          o
    #          |
    #       +-----+
    #       |     |
    #  R o--|     |--o L
    #       |     |
    #       +-----+
    #          |
    #          o
    #          U
    #
    orientation: str  # "U"/"D"/"L"/"R" for the pin's rotation

    part: Part  # to which part does this pin belong?
    stub: bool  # whether to stub the pin or not
    # position of the pin
    # - relative to the part?
    x: float
    y: float

    # things we've added to make life easier
    sch_pin: "fileformats_sch.C_kicad_sch_file.C_kicad_sch.C_symbol_instance.C_pin"
    fab_pin: F.Symbol.Pin
    fab_is_gnd: bool
    fab_is_pwr: bool
    _is_connected: bool

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        audit_has(
            self,
            [
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
            ],
        )

    # internal use
    face: "Face"
    place_pt: Point
    pt: Point
    route_pt: Point
    routed: bool

    def is_connected(self) -> bool:
        """Whether the pin is connected to anything"""
        return getattr(self, "_is_connected", False)


class Net:
    # We need to assign these
    name: str
    netio: str  # whether input or output
    pins: list[Pin]
    stub: bool  # whether to stub the pin or not

    # added for our use
    _is_implicit: bool
    fab_is_gnd: bool
    fab_is_pwr: bool

    # internal use
    parts: set[Part]

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        audit_has(self, ["name", "netio", "pins", "stub"])

        for pin in self.pins:
            pin.audit()

    def __bool__(self) -> bool:
        """TODO: does this need to be false if no parts or pins?"""
        return bool(self.pins) or bool(self.parts)

    def __iter__(self) -> Iterator[Pin | Part]:
        raise NotImplementedError  # not sure what to output here
        yield from self.pins
        yield from self.parts

    def __hash__(self) -> int:
        """Nets are sometimes used as keys in dicts, so they must be hashable"""
        return id(self)

    def is_implicit(self) -> bool:
        """Whether the net has a user-assigned name"""
        return self._is_implicit

    @classmethod
    def null_net(cls) -> "Net":
        net = cls()
        net.name = ""
        net.netio = ""
        net.pins = []
        net.stub = False
        net._is_implicit = True
        net.fab_is_gnd = False
        net.fab_is_pwr = False
        return net


class Circuit:
    nets: list[Net]
    parts: list[Part]

    def audit(self) -> None:
        """Ensure mandatory attributes are set"""
        audit_has(self, ["nets", "parts"])

        for obj in chain(self.nets, self.parts):
            obj.audit()


class Options(TypedDict):
    allow_routing_failure: bool
    compress_before_place: bool
    dont_rotate_pin_count: int
    draw_assigned_terminals: bool
    draw_font: str
    draw_global_routing: bool
    draw_pin_names: bool
    draw_placement: bool
    draw_routing_channels: bool
    draw_routing: bool
    draw_scr: "pygame.Surface"
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


class NetTerminal(Part):
    pull_pins: dict[Net, list[Pin]]

    def __init__(self, net: Net, hierarchy: str):
        """Specialized Part with a single pin attached to a net.

        This is intended for attaching to nets to label them, typically when
        the net spans across levels of hierarchical nodes.
        """
        from .bboxes import calc_hier_label_bbox

        # Set a default transformation matrix for this part.
        self.tx = Tx()
        self.ref = net.name
        self.hierarchy = hierarchy
        self.symtx = ""
        self.unit = {}

        # Add a single pin to the part.
        pin = Pin()
        pin.part = self
        pin.num = "1"
        pin.name = "~"
        pin.stub = False
        pin.fab_pin = None
        pin.sch_pin = None
        pin.fab_is_gnd = False
        pin.fab_is_pwr = False
        pin.net = net
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

        pin.audit()
        self.audit()

    @property
    def sch_symbol(self) -> None:
        return None

    @property
    def fab_symbol(self) -> None:
        return None

    @property
    def bare_bbox(self) -> None:
        return None

    @property
    def _similarites(self) -> dict[Part, float]:
        return {}
