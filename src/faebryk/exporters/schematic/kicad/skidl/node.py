# ruff: noqa: E501  imported from another project
# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

import itertools
import re
from collections import defaultdict
from itertools import chain
from typing import Unpack

from .geometry import BBox, Point, Segment, Tx, Vector
from .place import Placer
from .route import Router
from .shims import Circuit, Net, Options, Part, Pin

"""
Node class for storing circuit hierarchy.
"""

HIER_SEP = "."


class SchNode(Placer, Router):
    """Data structure for holding information about a node in the circuit hierarchy."""

    filename_sz = 20
    name_sz = 40

    def __init__(
        self,
        circuit=None,
        filepath=".",
        top_name="",
        title="",
        flatness=0.0,
    ):
        self.parent = None
        self.children = defaultdict(
            lambda: SchNode(None, filepath, top_name, title, flatness)
        )
        self.filepath = filepath
        self.top_name = top_name
        self.sheet_name = None
        self.sheet_filename = None
        self.title = title
        self.flatness = flatness
        self.flattened = False
        self.flattened_children = []
        self.parts: list["Part"] = []
        self.wires: dict[Net, list[Segment]] = defaultdict(list)
        self.junctions: dict[Net, list[Point]] = defaultdict(list)
        self.tx = Tx()
        self.bbox = BBox()

        if circuit:
            self.add_circuit(circuit)

    def find_node_with_part(self, part: Part):
        """Find the node that contains the part based on its hierarchy.

        Args:
            part (Part): The part being searched for in the node hierarchy.

        Returns:
            Node: The Node object containing the part.
        """
        level_names = part.hierarchy.split(HIER_SEP)

        # descend based on the hierarchy name
        node = self
        for lvl_nm in level_names[1:]:
            # stop descending if we're trying to go into something flattened
            if lvl_nm in node.flattened_children:
                break
            node = node.children[lvl_nm]

        assert part in node.parts
        return node

    # TODO: what's a circuit to us?
    def add_circuit(self, circuit: Circuit):
        """Add parts in circuit to node and its children.

        Args:
            circuit (Circuit): Circuit object.
        """
        # Build the circuit node hierarchy by adding the parts.
        assert circuit.parts, "Circuit has no parts"
        for part in circuit.parts:
            self.add_part(part)

        # FIXME: SKiDL doesn't seem to need to clean these up. We shouldn't really either
        # The flattening and adding of terminals was the other way around in SKiDL.
        # Flatten the hierarchy as specified by the flatness parameter.
        self.flatten(self.flatness)

        # Add terminals to nodes in the hierarchy for nets that span across nodes.
        for net in circuit.nets:
            # Skip nets that are stubbed since there will be no wire to attach to the NetTerminal.
            if getattr(net, "stub", False):
                continue

            # Search for pins in different nodes.
            # NOTE: this was a zip in SKiDL
            for pin1, pin2 in itertools.combinations(net.pins, 2):
                # If two pins on a net are in different nodes, we should definitely add a terminal
                if self.find_node_with_part(pin1.part) is not self.find_node_with_part(
                    pin2.part
                ):
                    # Found pins in different nodes, so break and add terminals to nodes below.
                    break
            else:
                if len(net.pins) == 1:
                    # Single pin on net and not stubbed, so add a terminal to it below.
                    pass
                elif not net.is_implicit():
                    # The net has a user-assigned name, so add a terminal to it below.
                    pass
                else:
                    # No need for net terminal because there are multiple pins
                    # and they are all in the same node.
                    continue

            # Add a single terminal to each node that contains one or more pins of the net.
            visited = []
            for pin in net.pins:
                # A stubbed pin can't be used to add NetTerminal since there is no explicit wire.
                if pin.stub:
                    continue

                part = pin.part

                if part.hierarchy in visited:
                    # Already added a terminal to this node, so don't add another.
                    continue

                # Add NetTerminal to the node with this part/pin.
                self.find_node_with_part(part).add_terminal(net, part.hierarchy)

                # Record that this hierarchical node was visited.
                visited.append(part.hierarchy)

    def add_part(self, part: Part, level: int = 0):
        """Add a part to the node at the appropriate level of the hierarchy.

        Args:
            part (Part): Part to be added to this node or one of its children.
            level (int, optional): The current level (depth) of the node in the hierarchy. Defaults to 0.
        """
        # Get list of names of hierarchical levels (in order) leading to this part.
        level_names = part.hierarchy.split(HIER_SEP)

        # Get depth in hierarchy for this part.
        part_level = len(level_names) - 1
        assert part_level >= level

        # Node name is the name assigned to this level of the hierarchy.
        self.name = level_names[level]

        # File name for storing the schematic for this node.
        base_filename = "_".join([self.top_name] + level_names[0 : level + 1]) + ".sch"
        self.sheet_filename = base_filename

        if part_level == level:
            # Add part to node at this level in the hierarchy.
            if not part.unit:
                # Monolithic part so just add it to the node.
                self.parts.append(part)
            else:
                # Multi-unit part so add each unit to the node.
                # FIXME: Some part units might be split into other nodes.
                for p in part.unit.values():
                    self.parts.append(p)
        else:
            # Part is at a level below the current node. Get the child node using
            # the name of the next level in the hierarchy for this part.
            # This is a default dict, so it also creates new nodes as needed.
            child_node = self.children[level_names[level + 1]]

            # Attach the child node to this node. (It may have just been created.)
            child_node.parent = self

            # Add part to the child node (or one of its children).
            child_node.add_part(part, level + 1)

    def add_terminal(self, net: Net, hierarchy: str):
        """Add a terminal for this net to the node.

        Args:
            net (Net): The net to be added to this node.
        """
        from .net_terminal import NetTerminal

        nt = NetTerminal(net, hierarchy)
        self.parts.append(nt)

    def external_bbox(self) -> BBox:
        """Return the bounding box of a hierarchical sheet as seen by its parent node."""
        bbox = BBox(Point(0, 0), Point(500, 500))
        bbox.add(Point(len("File: " + self.sheet_filename) * self.filename_sz, 0))
        bbox.add(Point(len("Sheet: " + self.name) * self.name_sz, 0))

        # Pad the bounding box for extra spacing when placed.
        bbox = bbox.resize(Vector(100, 100))

        return bbox

    def internal_bbox(self) -> BBox:
        """Return the bounding box for the circuitry contained within this node."""

        # The bounding box is determined by the arrangement of the node's parts and child nodes.
        bbox = BBox()
        for obj in chain(self.parts, self.children.values()):
            tx_bbox = obj.bbox * obj.tx
            bbox.add(tx_bbox)

        # Pad the bounding box for extra spacing when placed.
        bbox = bbox.resize(Vector(100, 100))

        return bbox

    def calc_bbox(self) -> BBox:
        """Compute the bounding box for the node in the circuit hierarchy."""

        if self.flattened:
            self.bbox = self.internal_bbox()
        else:
            # Use hierarchical bounding box if node has not been flattened.
            self.bbox = self.external_bbox()

        return self.bbox

    def flatten(self, flatness: float = 0.0) -> None:
        """Flatten node hierarchy according to flatness parameter.

        Args:
            flatness (float, optional): Degree of hierarchical flattening (0=completely hierarchical, 1=totally flat). Defaults to 0.0.

        Create hierarchical sheets for the node and its child nodes. Complexity (or size) of a node
        and its children is the total number of part pins they contain. The sum of all the child sizes
        multiplied by the flatness is the number of part pins that can be shown on the schematic
        page before hierarchy is used. The instances of each type of child are flattened and placed
        directly in the sheet as long as the sum of their sizes is below the slack. Otherwise, the
        children are included using hierarchical sheets. The children are handled in order of
        increasing size so small children are more likely to be flattened while large, complicated
        children are included using hierarchical sheets.
        """

        # Create sheets and compute complexity for any circuitry in hierarchical child nodes.
        for child in self.children.values():
            child.flatten(flatness)

        # Complexity of the parts directly instantiated at this hierarchical level.
        self.complexity = sum((len(part) for part in self.parts))

        # Sum the child complexities and use it to compute the number of pins that can be
        # shown before hierarchical sheets are used.
        child_complexity = sum((child.complexity for child in self.children.values()))
        slack = child_complexity * flatness

        # Group the children according to what types of modules they are by removing trailing instance ids.
        child_types: dict[str, list[SchNode]] = defaultdict(list)
        for child_id, child in self.children.items():
            child_types[re.sub(r"\d+$", "", child_id)].append(child)

        # Compute the total size of each type of children.
        child_type_sizes: dict[str, int] = {}
        for child_type, children in child_types.items():
            child_type_sizes[child_type] = sum((child.complexity for child in children))

        # Sort the groups from smallest total size to largest.
        sorted_child_type_sizes: list[tuple[str, int]] = sorted(
            child_type_sizes.items(), key=lambda item: item[1]
        )

        # Flatten each instance in a group until the slack is used up.
        for child_type, child_type_size in sorted_child_type_sizes:
            if child_type_size <= slack:
                # Include the circuitry of each child instance directly in the sheet.
                for child in child_types[child_type]:
                    child.flattened = True
                # Reduce the slack by the sum of the child sizes.
                slack -= child_type_size
            else:
                # Not enough slack left. Add these children as hierarchical sheets.
                for child in child_types[child_type]:
                    child.flattened = False

        # Move all the flattened children's content into this node
        for child in self.children.values():
            if child.flattened:
                self.parts.extend(child.parts)
                self.flattened_children.append(child.name)
        for child in self.flattened_children:
            del self.children[child]

    def get_internal_nets(self) -> list[Net]:
        """Return a list of nets that have at least one pin on a part in this node."""

        processed_nets = []
        internal_nets = []
        for part in self.parts:
            for part_pin in part:
                # No explicit wire for pins connected to labeled stub nets.
                if part_pin.stub:
                    continue

                # No explicit wires if the pin is not connected to anything.
                if not part_pin.is_connected():
                    continue

                net = part_pin.net

                # Skip nets that have already been processed.
                if net in processed_nets:
                    continue

                processed_nets.append(net)

                # Skip stubbed nets.
                if getattr(net, "stub", False):
                    continue

                # Add net to collection if at least one pin is on one of the parts of the node.
                for net_pin in net.pins:
                    if net_pin.part in self.parts:
                        internal_nets.append(net)
                        break

        return internal_nets

    def get_internal_pins(self, net: Net) -> list[Pin]:
        """Return the pins on the net that are on parts in the node.

        Args:
            net (Net): The net whose pins are being examined.

        Returns:
            list: List of pins on the net that are on parts in this node.
        """

        # Skip pins on stubbed nets.
        if getattr(net, "stub", False) is True:
            return []

        return [pin for pin in net.pins if pin.stub is False and pin.part in self.parts]

    def collect_stats(self, **options: Unpack[Options]) -> str:
        """Return comma-separated string with place & route statistics of a schematic."""

        def get_wire_length(node: SchNode) -> int:
            """Return the sum of the wire segment lengths between parts in a routed node."""

            wire_length = 0

            # Sum wire lengths for child nodes.
            for child in node.children.values():
                wire_length += get_wire_length(child)

            # Add the wire lengths between parts in the top node.
            for wire_segs in node.wires.values():
                for seg in wire_segs:
                    len_x = abs(seg.p1.x - seg.p2.x)
                    len_y = abs(seg.p1.y - seg.p2.y)
                    wire_length += len_x + len_y

            return wire_length

        return "{}\n".format(get_wire_length(self))
