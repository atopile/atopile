# ruff: noqa: E501  imported from another project
"""
Functions for generating a KiCad EESCHEMA schematic.
"""

# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

import datetime
import os.path
import re
import time
from collections import Counter, OrderedDict
from typing import Unpack

from .bboxes import calc_hier_label_bbox
from .constants import BLK_INT_PAD, BOX_LABEL_FONT_SIZE, GRID, PIN_LABEL_FONT_SIZE
from .geometry import BBox, Point, Tx, Vector
from .net_terminal import NetTerminal
from .node import HIER_SEP, SchNode
from .shims import Circuit, Options, Part, PartUnit, Pin, rmv_attr


def bbox_to_eeschema(bbox: BBox, tx: Tx, name=None):
    """Create a bounding box using EESCHEMA graphic lines."""

    # Make sure the box corners are integers.
    bbox = (bbox * tx).round()

    graphic_box = []

    if name:
        # Place name at the lower-left corner of the box.
        name_pt = bbox.ul
        graphic_box.append(
            "Text Notes {} {} 0    {}  ~ 20\n{}".format(
                name_pt.x, name_pt.y, BOX_LABEL_FONT_SIZE, name
            )
        )

    graphic_box.append("Wire Notes Line")
    graphic_box.append(
        "	{} {} {} {}".format(bbox.ll.x, bbox.ll.y, bbox.lr.x, bbox.lr.y)
    )
    graphic_box.append("Wire Notes Line")
    graphic_box.append(
        "	{} {} {} {}".format(bbox.lr.x, bbox.lr.y, bbox.ur.x, bbox.ur.y)
    )
    graphic_box.append("Wire Notes Line")
    graphic_box.append(
        "	{} {} {} {}".format(bbox.ur.x, bbox.ur.y, bbox.ul.x, bbox.ul.y)
    )
    graphic_box.append("Wire Notes Line")
    graphic_box.append(
        "	{} {} {} {}".format(bbox.ul.x, bbox.ul.y, bbox.ll.x, bbox.ll.y)
    )
    graphic_box.append("")  # For blank line at end.

    return "\n".join(graphic_box)


def net_to_eeschema(self, tx):
    """Generate the EESCHEMA code for the net terminal.

    Args:
        tx (Tx): Transformation matrix for the node containing this net terminal.

    Returns:
        str: EESCHEMA code string.
    """
    self.pins[0].stub = True
    self.pins[0].orientation = "R"
    return pin_label_to_eeschema(self.pins[0], tx)
    # return pin_label_to_eeschema(self.pins[0], tx) + bbox_to_eeschema(self.bbox, self.tx * tx)


def part_to_eeschema(part, tx):
    """Create EESCHEMA code for a part.

    Args:
        part (Part): SKiDL part.
        tx (Tx): Transformation matrix.

    Returns:
        string: EESCHEMA code for the part.

    Notes:
        https://en.wikibooks.org/wiki/Kicad/file_formats#Schematic_Files_Format
    """

    tx = part.tx * tx
    origin = tx.origin.round()
    time_hex = hex(int(time.time()))[2:]
    unit_num = getattr(part, "num", 1)

    eeschema = []
    eeschema.append("$Comp")
    lib = os.path.splitext(part.lib.filename)[0]
    eeschema.append("L {}:{} {}".format(lib, part.name, part.ref))
    eeschema.append("U {} 1 {}".format(unit_num, time_hex))
    eeschema.append("P {} {}".format(str(origin.x), str(origin.y)))

    # Add part symbols. For now we are only adding the designator
    n_F0 = 1
    for i in range(len(part.draw)):
        if re.search("^DrawF0", str(part.draw[i])):
            n_F0 = i
            break
    eeschema.append(
        'F 0 "{}" {} {} {} {} {} {} {}'.format(
            part.ref,
            part.draw[n_F0].orientation,
            str(origin.x + part.draw[n_F0].x),
            str(origin.y + part.draw[n_F0].y),
            part.draw[n_F0].size,
            "000",  # TODO: Refine this to match part def.
            part.draw[n_F0].halign,
            part.draw[n_F0].valign,
        )
    )

    # Part value.
    n_F1 = 1
    for i in range(len(part.draw)):
        if re.search("^DrawF1", str(part.draw[i])):
            n_F1 = i
            break
    eeschema.append(
        'F 1 "{}" {} {} {} {} {} {} {}'.format(
            str(part.value),
            part.draw[n_F1].orientation,
            str(origin.x + part.draw[n_F1].x),
            str(origin.y + part.draw[n_F1].y),
            part.draw[n_F1].size,
            "000",  # TODO: Refine this to match part def.
            part.draw[n_F1].halign,
            part.draw[n_F1].valign,
        )
    )

    # Part footprint.
    n_F2 = 2
    for i in range(len(part.draw)):
        if re.search("^DrawF2", str(part.draw[i])):
            n_F2 = i
            break
    eeschema.append(
        'F 2 "{}" {} {} {} {} {} {} {}'.format(
            part.footprint,
            part.draw[n_F2].orientation,
            str(origin.x + part.draw[n_F2].x),
            str(origin.y + part.draw[n_F2].y),
            part.draw[n_F2].size,
            "001",  # TODO: Refine this to match part def.
            part.draw[n_F2].halign,
            part.draw[n_F2].valign,
        )
    )
    eeschema.append("   1   {} {}".format(str(origin.x), str(origin.y)))
    eeschema.append("   {}  {}  {}  {}".format(tx.a, tx.b, tx.c, tx.d))
    eeschema.append("$EndComp")
    eeschema.append("")  # For blank line at end.

    # For debugging: draws a bounding box around a part.
    # eeschema.append(bbox_to_eeschema(part.bbox, tx))
    # eeschema.append(bbox_to_eeschema(part.place_bbox, tx))

    return "\n".join(eeschema)


def wire_to_eeschema(net, wire, tx):
    """Create EESCHEMA code for a multi-segment wire.

    Args:
        net (Net): Net associated with the wire.
        wire (list): List of Segments for a wire.
        tx (Tx): transformation matrix for each point in the wire.

    Returns:
        string: Text to be placed into EESCHEMA file.
    """

    eeschema = []
    for segment in wire:
        eeschema.append("Wire Wire Line")
        w = (segment * tx).round()
        eeschema.append("  {} {} {} {}".format(w.p1.x, w.p1.y, w.p2.x, w.p2.y))
    eeschema.append("")  # For blank line at end.
    return "\n".join(eeschema)


def junction_to_eeschema(net, junctions, tx):
    eeschema = []
    for junction in junctions:
        pt = (junction * tx).round()
        eeschema.append("Connection ~ {} {}".format(pt.x, pt.y))
    eeschema.append("")  # For blank line at end.
    return "\n".join(eeschema)


def power_part_to_eeschema(part, tx=Tx()):
    return ""  # REMOVE: Remove this.
    out = []
    for pin in part.pins:
        try:
            if not (pin.net is None):
                if pin.net.netclass == "Power":
                    # strip out the '_...' section from power nets
                    t = pin.net.name
                    u = t.split("_")
                    symbol_name = u[0]
                    # find the stub in the part
                    time_hex = hex(int(time.time()))[2:]
                    pin_pt = (part.origin + offset + Point(pin.x, pin.y)).round()
                    x, y = pin_pt.x, pin_pt.y
                    out.append("$Comp\n")
                    out.append("L power:{} #PWR?\n".format(symbol_name))
                    out.append("U 1 1 {}\n".format(time_hex))
                    out.append("P {} {}\n".format(str(x), str(y)))
                    # Add part symbols. For now we are only adding the designator
                    n_F0 = 1
                    for i in range(len(part.draw)):
                        if re.search("^DrawF0", str(part.draw[i])):
                            n_F0 = i
                            break
                    part_orientation = part.draw[n_F0].orientation
                    part_horizontal_align = part.draw[n_F0].halign
                    part_vertical_align = part.draw[n_F0].valign

                    # check if the pin orientation will clash with the power part
                    if "+" in symbol_name:
                        # voltage sources face up, so check if the pin is facing down (opposite logic y-axis)
                        if pin.orientation == "U":
                            orientation = [-1, 0, 0, 1]
                    elif "gnd" in symbol_name.lower():
                        # gnd points down so check if the pin is facing up (opposite logic y-axis)
                        if pin.orientation == "D":
                            orientation = [-1, 0, 0, 1]
                    out.append(
                        'F 0 "{}" {} {} {} {} {} {} {}\n'.format(
                            "#PWR?",
                            part_orientation,
                            str(x + 25),
                            str(y + 25),
                            str(40),
                            "001",
                            part_horizontal_align,
                            part_vertical_align,
                        )
                    )
                    out.append(
                        'F 1 "{}" {} {} {} {} {} {} {}\n'.format(
                            symbol_name,
                            part_orientation,
                            str(x + 25),
                            str(y + 25),
                            str(40),
                            "000",
                            part_horizontal_align,
                            part_vertical_align,
                        )
                    )
                    out.append("   1   {} {}\n".format(str(x), str(y)))
                    out.append(
                        "   {}   {}  {}  {}\n".format(
                            orientation[0],
                            orientation[1],
                            orientation[2],
                            orientation[3],
                        )
                    )
                    out.append("$EndComp\n")
        except Exception as inst:
            print(type(inst))
            print(inst.args)
            print(inst)
    return "\n" + "".join(out)


# Sizes of EESCHEMA schematic pages from smallest to largest. Dimensions in mils.
A_sizes_list = [
    ("A4", BBox(Point(0, 0), Point(11693, 8268))),
    ("A3", BBox(Point(0, 0), Point(16535, 11693))),
    ("A2", BBox(Point(0, 0), Point(23386, 16535))),
    ("A1", BBox(Point(0, 0), Point(33110, 23386))),
    ("A0", BBox(Point(0, 0), Point(46811, 33110))),
]

# Create bounding box for each A size sheet.
A_sizes = OrderedDict(A_sizes_list)


def get_A_size(bbox: BBox) -> str:
    """Return the A-size page needed to fit the given bounding box."""

    width = bbox.w
    height = bbox.h * 1.25  # HACK: why 1.25?
    for A_size, page in A_sizes.items():
        if width < page.w and height < page.h:
            return A_size
    return "A0"  # Nothing fits, so use the largest available.


def calc_sheet_tx(bbox):
    """Compute the page size and positioning for this sheet."""
    A_size = get_A_size(bbox)
    page_bbox = bbox * Tx(d=-1)
    move_to_ctr = A_sizes[A_size].ctr.snap(GRID) - page_bbox.ctr.snap(GRID)
    move_tx = Tx(d=-1).move(move_to_ctr)
    return move_tx


def calc_pin_dir(pin):
    """Calculate pin direction accounting for part transformation matrix."""

    # Copy the part trans. matrix, but remove the translation vector, leaving only scaling/rotation stuff.
    tx = pin.part.tx
    tx = Tx(a=tx.a, b=tx.b, c=tx.c, d=tx.d)

    # Use the pin orientation to compute the pin direction vector.
    pin_vector = {
        "U": Point(0, 1),
        "D": Point(0, -1),
        "L": Point(-1, 0),
        "R": Point(1, 0),
    }[pin.orientation]

    # Rotate the direction vector using the part rotation matrix.
    pin_vector = pin_vector * tx

    # Create an integer tuple from the rotated direction vector.
    pin_vector = (int(round(pin_vector.x)), int(round(pin_vector.y)))

    # Return the pin orientation based on its rotated direction vector.
    return {
        (0, 1): "U",
        (0, -1): "D",
        (-1, 0): "L",
        (1, 0): "R",
    }[pin_vector]


def pin_label_to_eeschema(pin, tx):
    """Create EESCHEMA text of net label attached to a pin."""

    if pin.stub is False or not pin.is_connected():
        # No label if pin is not connected or is connected to an explicit wire.
        return ""

    label_type = "HLabel"
    for pn in pin.net.pins:
        if pin.part.hierarchy.startswith(pn.part.hierarchy):
            continue
        if pn.part.hierarchy.startswith(pin.part.hierarchy):
            continue
        label_type = "GLabel"
        break

    part_tx = pin.part.tx * tx
    pt = pin.pt * part_tx

    pin_dir = calc_pin_dir(pin)
    orientation = {
        "R": 0,
        "D": 1,
        "L": 2,
        "U": 3,
    }[pin_dir]

    return "Text {} {} {} {}    {}   UnSpc ~ 0\n{}\n".format(
        label_type,
        int(round(pt.x)),
        int(round(pt.y)),
        orientation,
        PIN_LABEL_FONT_SIZE,
        pin.net.name,
    )


def create_eeschema_file(
    filename,
    contents,
    cur_sheet_num=1,
    total_sheet_num=1,
    title="Default",
    rev_major=0,
    rev_minor=1,
    year=datetime.date.today().year,
    month=datetime.date.today().month,
    day=datetime.date.today().day,
    A_size="A2",
):
    """Write EESCHEMA header, contents, and footer to a file."""

    with open(filename, "w") as f:
        f.write(
            "\n".join(
                (
                    "EESchema Schematic File Version 4",
                    "EELAYER 30 0",
                    "EELAYER END",
                    "$Descr {} {} {}".format(
                        A_size, A_sizes[A_size].max.x, A_sizes[A_size].max.y
                    ),
                    "encoding utf-8",
                    "Sheet {} {}".format(cur_sheet_num, total_sheet_num),
                    'Title "{}"'.format(title),
                    'Date "{}-{}-{}"'.format(year, month, day),
                    'Rev "v{}.{}"'.format(rev_major, rev_minor),
                    'Comp ""',
                    'Comment1 ""',
                    'Comment2 ""',
                    'Comment3 ""',
                    'Comment4 ""',
                    "$EndDescr",
                    "",
                    contents,
                    "$EndSCHEMATC",
                )
            )
        )


def node_to_eeschema(node: SchNode, sheet_tx: Tx = Tx()) -> str:
    """Convert node circuitry to an EESCHEMA sheet.

    Args:
        sheet_tx (Tx, optional): Scaling/translation matrix for sheet. Defaults to Tx().

    Returns:
        str: EESCHEMA text for the node circuitry.
    """
    # List to hold all the EESCHEMA code for this node.
    eeschema_code = []

    if node.flattened:
        # Create the transformation matrix for the placement of the parts in the node.
        tx = node.tx * sheet_tx
    else:
        # Unflattened nodes are placed in their own sheet, so compute
        # their bounding box as if they *were* flattened and use that to
        # find the transformation matrix for an appropriately-sized sheet.
        flattened_bbox = node.internal_bbox()
        tx = calc_sheet_tx(flattened_bbox)

    # Generate EESCHEMA code for each child of this node.
    for child in node.children.values():
        eeschema_code.append(node_to_eeschema(child, tx))

    # Generate EESCHEMA code for each part in the node.
    for part in node.parts:
        if isinstance(part, NetTerminal):
            eeschema_code.append(net_to_eeschema(part, tx=tx))
        else:
            eeschema_code.append(part_to_eeschema(part, tx=tx))

    # Generate EESCHEMA wiring code between the parts in the node.
    for net, wire in node.wires.items():
        wire_code = wire_to_eeschema(net, wire, tx=tx)
        eeschema_code.append(wire_code)
    for net, junctions in node.junctions.items():
        junction_code = junction_to_eeschema(net, junctions, tx=tx)
        eeschema_code.append(junction_code)

    # Generate power connections for the each part in the node.
    for part in node.parts:
        stub_code = power_part_to_eeschema(part, tx=tx)
        if len(stub_code) != 0:
            eeschema_code.append(stub_code)

    # Generate pin labels for stubbed nets on each part in the node.
    for part in node.parts:
        for pin in part:
            pin_label_code = pin_label_to_eeschema(pin, tx=tx)
            eeschema_code.append(pin_label_code)

    # Join EESCHEMA code into one big string.
    eeschema_code = "\n".join(eeschema_code)

    # If this node was flattened, then return the EESCHEMA code and surrounding box
    # for inclusion in the parent node.
    if node.flattened:
        # Generate the graphic box that surrounds the flattened hierarchical block of this node.
        block_name = node.name.split(HIER_SEP)[-1]
        pad = Vector(BLK_INT_PAD, BLK_INT_PAD)
        bbox_code = bbox_to_eeschema(node.bbox.resize(pad), tx, block_name)

        return "\n".join((eeschema_code, bbox_code))

    # Create a hierarchical sheet file for storing this unflattened node.
    A_size = get_A_size(flattened_bbox)
    filepath = os.path.join(node.filepath, node.sheet_filename)
    create_eeschema_file(filepath, eeschema_code, title=node.title, A_size=A_size)

    # Create the hierarchical sheet for insertion into the calling node sheet.
    bbox = (node.bbox * node.tx * sheet_tx).round()
    time_hex = hex(int(time.time()))[2:]
    return "\n".join(
        (
            "$Sheet",
            "S {} {} {} {}".format(bbox.ll.x, bbox.ll.y, bbox.w, bbox.h),
            "U {}".format(time_hex),
            'F0 "{}" {}'.format(node.name, node.name_sz),
            'F1 "{}" {}'.format(node.sheet_filename, node.filename_sz),
            "$EndSheet",
            "",
        )
    )


"""
Generate a KiCad EESCHEMA schematic from a Circuit object.
"""

# TODO: Handle symio attribute.

def _ideal_part_rotation(part: Part) -> tuple[float, float]:
    # Tally what rotation would make each pwr/gnd pin point up or down.
    def is_pwr(pin: Pin) -> bool:
        return pin.fab_is_pwr

    def is_gnd(pin: Pin) -> bool:
        return pin.fab_is_gnd

    def rotation_for(start: str, finish: str) -> float:
        seq = ["L", "U", "R", "D"] * 2
        start_idx = seq.index(start)
        finish_idx = seq.index(finish, start_idx)
        return (finish_idx - start_idx) * 90

    rotation_tally = Counter()
    for pin in part.pins:
        if is_pwr(pin):
            rotation_tally[rotation_for("D", pin.orientation)] += 1
        elif is_gnd(pin):
            rotation_tally[rotation_for("U", pin.orientation)] += 1
        # TODO: add support for IO pins left and right

    # Rotate the part unit in the direction with the most tallies.
    if most_common := rotation_tally.most_common(1):
        assert len(most_common) == 1
        return most_common[0][0], most_common[0][1] / rotation_tally.total()
    return 0, 0


def preprocess_circuit(circuit: Circuit, **options: Unpack[Options]):
    """Add stuff to parts & nets for doing placement and routing of schematics."""

    def units(part: Part) -> list[PartUnit | Part]:
        if len(part.unit) == 0:
            return [part]
        else:
            return part.unit.values()

    def initialize(part: Part):
        """Initialize part or its part units."""

        # Initialize the units of the part, or the part itself if it has no units.
        pin_limit = options.get("orientation_pin_limit", 44)
        for part_unit in units(part):
            # Initialize transform matrix.
            part_unit.tx = Tx.from_symtx(getattr(part_unit, "symtx", ""))

            # Lock part orientation if symtx was specified. Also lock parts with a lot of pins
            # since they're typically drawn the way they're supposed to be oriented.
            # And also lock single-pin parts because these are usually power/ground and
            # they shouldn't be flipped around.
            num_pins = len(part_unit.pins)
            part_unit.orientation_locked = getattr(part_unit, "symtx", False) or not (
                1 < num_pins <= pin_limit
            )

            # Assign pins from the parent part to the part unit.
            part_unit.grab_pins()

            # Initialize pin attributes used for generating schematics.
            for pin in part_unit:
                pin.pt = Point(pin.x, pin.y)
                pin.routed = False

    def rotate_power_pins(part: Part):
        """Rotate a part based on the direction of its power pins.

        This function is to make sure that voltage sources face up and gnd pins
        face down.
        """

        # Don't rotate parts that are already explicitly rotated/flipped.
        # FIXME: this was the inverted in SKiDL
        if getattr(part, "symtx", ""):
            return

        dont_rotate_pin_cnt = options.get("dont_rotate_pin_count", 10000)

        for part_unit in units(part):
            # Don't rotate parts with too many pins.
            if len(part_unit) > dont_rotate_pin_cnt:
                return

            rotation, certainty = _ideal_part_rotation(part_unit)
            if certainty:
                part_unit.tx = part_unit.tx.rot_ccw(rotation)

                if certainty >= part_unit.hints.lock_rotation_certainty:
                    part_unit.orientation_locked = True

    def calc_part_bbox(part: Part):
        """Calculate the labeled bounding boxes and store it in the part."""
        # Find part/unit bounding boxes excluding any net labels on pins.
        # TODO: part.lbl_bbox could be substituted for part.bbox.
        # TODO: Part ref and value should be updated before calculating bounding box.

        for part_unit in units(part):
            assert isinstance(part_unit, (PartUnit, Part))
            assert isinstance(part_unit.bare_bbox, BBox)

            # Expand the bounding box if it's too small in either dimension.
            resize_wh = Vector(0, 0)
            if part_unit.bare_bbox.w < 100:
                resize_wh.x = (100 - part_unit.bare_bbox.w) / 2
            if part_unit.bare_bbox.h < 100:
                resize_wh.y = (100 - part_unit.bare_bbox.h) / 2
            part_unit.bare_bbox = part_unit.bare_bbox.resize(resize_wh)

            # Find expanded bounding box that includes any hier labels attached to pins.
            part_unit.lbl_bbox = BBox()
            part_unit.lbl_bbox.add(part_unit.bare_bbox)
            for pin in part_unit:
                if pin.stub:
                    # Find bounding box for net stub label attached to pin.
                    hlbl_bbox = calc_hier_label_bbox(pin.net.name, pin.orientation)
                    # Move the label bbox to the pin location.
                    hlbl_bbox *= Tx().move(pin.pt)
                    # Update the bbox for the labelled part with this pin label.
                    part_unit.lbl_bbox.add(hlbl_bbox)

            # Set the active bounding box to the labeled version.
            part_unit.bbox = part_unit.lbl_bbox

    # Pre-process parts
    for part in circuit.parts:
        # Initialize part attributes used for generating schematics.
        initialize(part)

        # Rotate parts.  Power pins should face up. GND pins should face down.
        rotate_power_pins(part)

        # Compute bounding boxes around parts
        calc_part_bbox(part)


def finalize_parts_and_nets(circuit: Circuit, **options: Unpack[Options]):
    """Restore parts and nets after place & route is done."""

    # Remove any NetTerminals that were added.
    circuit.parts = [p for p in circuit.parts if not isinstance(p, NetTerminal)]

    # Return pins from the part units to their parent part.
    for part in circuit.parts:
        part.grab_pins()

    # Remove some stuff added to parts during schematic generation process.
    rmv_attr(circuit.parts, ("force", "bbox", "lbl_bbox", "tx"))


def gen_schematic(
    circuit: Circuit,
    filepath: str,
    top_name: str,
    title="SKiDL-Generated Schematic",
    flatness: float = 0.0,
    retries: int = 2,
    **options: Unpack[Options],
) -> SchNode:
    """Create a schematic file from a Circuit object.

    Args:
        circuit (Circuit): The Circuit object that will have a schematic generated for it.
        filepath (str, optional): The directory where the schematic files are placed. Defaults to ".".
        top_name (str, optional): The name for the top of the circuit hierarchy. Defaults to get_script_name().
        title (str, optional): The title of the schematic. Defaults to "SKiDL-Generated Schematic".
        flatness (float, optional): Determines how much the hierarchy is flattened in the schematic. Defaults to 0.0 (completely hierarchical).
        retries (int, optional): Number of times to re-try if routing fails. Defaults to 2.
        options (dict, optional): Dict of options and values, usually for drawing/debugging.
    """

    from .place import PlacementFailure
    from .route import RoutingFailure

    # Part placement options that should always be turned on.
    options["use_push_pull"] = True
    options["rotate_parts"] = True
    options["pt_to_pt_mult"] = 5  # HACK: Ad-hoc value.
    options["pin_normalize"] = True

    # Start with default routing area.
    expansion_factor = 1.0

    # Try to place & route one or more times.
    for _ in range(retries):
        preprocess_circuit(circuit, **options)

        node = SchNode(circuit, filepath, top_name, title, flatness)

        try:
            # Place parts.
            node.place(expansion_factor=expansion_factor, **options)

            # Route parts.
            node.route(**options)

        except PlacementFailure:
            # Placement failed, so try again.
            finalize_parts_and_nets(circuit, **options)
            continue

        except RoutingFailure:
            # Routing failed, so expand routing area ...
            expansion_factor *= 1.5  # HACK: Ad-hoc increase of expansion factor.
            # ... and try again.
            finalize_parts_and_nets(circuit, **options)
            continue

        # Place & route was successful if we got here, so exit.
        return node

    # Exited the loop without successful routing.
    raise (RoutingFailure)
