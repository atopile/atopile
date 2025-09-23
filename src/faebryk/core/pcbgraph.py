from enum import Enum
from typing import Optional, cast

from faebryk.core.link import Link, LinkDirect
from faebryk.core.node import GraphInterface, Node, NodeException, d_field
from faebryk.core.parameter import Parameter


class KicadLayer(Enum):
    F_Cu = "F.Cu"
    B_Cu = "B.Cu"
    F_Mask = "F.Mask"
    B_Mask = "B.Mask"
    F_SilkS = "F.SilkS"
    B_SilkS = "B.SilkS"


class NetName(Enum):
    """Enum to represent net names in the PCB graph"""

    NET_A = "net_a"
    NET_B = "net_b"
    NET_C = "net_c"
    GND = "GND"
    VCC = "VCC"


class BaseNode(Node):
    type: GraphInterface = d_field(GraphInterface)
    connected: GraphInterface = d_field(GraphInterface)

    def connect(self, *other: "BaseNode", link: Link | None = None) -> "BaseNode":
        """Connect this node to one or more other PCB graph nodes."""

        if not other:
            return self

        mismatched = [o for o in other if not isinstance(o, BaseNode)]
        if mismatched:
            mismatch_str = ", ".join(
                f"{o} (type {type(o).__name__})" for o in mismatched
            )
            raise NodeException(
                self,
                (
                    "Cannot connect PCB nodes; all counterparts must inherit "
                    f"BaseNode. Offending nodes: {mismatch_str}."
                ),
            )

        if link is None:
            link = LinkDirect()

        new_links = [
            o.connected
            for o in other
            if o is not self
            and (
                (existing_link := self.connected.is_connected_to(o.connected)) is None
                or existing_link != link
            )
        ]

        if new_links:
            self.connected.connect(new_links, link=link)

        return other[-1]


class AttributeNode(BaseNode):
    value: Parameter = d_field(Parameter)


class XYRNode(BaseNode):
    x: Parameter = d_field(Parameter)
    y: Parameter = d_field(Parameter)
    r: Parameter = d_field(Parameter)


class LayerNode(BaseNode):
    above: GraphInterface
    below: GraphInterface
    thickness: Parameter = d_field(Parameter)
    material: Parameter = d_field(Parameter)


class KicadLayerNode(BaseNode):
    name: AttributeNode = d_field(AttributeNode)


class NetNode(BaseNode):
    name: AttributeNode = d_field(AttributeNode)
    net_id: Parameter = d_field(Parameter)


class LineNode(BaseNode):
    start: XYRNode = d_field(XYRNode)
    end: XYRNode = d_field(XYRNode)
    width: Parameter = d_field(Parameter)
    layer: LayerNode = d_field(LayerNode)


class CircleNode(BaseNode):
    """Circle primitive corresponding to KiCad `(gr_circle ...)`/pad shapes."""

    center: XYRNode = d_field(XYRNode)
    radius: Parameter = d_field(Parameter)
    layer: LayerNode = d_field(LayerNode)


class ViaNode(BaseNode):
    center: XYRNode = d_field(XYRNode)
    hole_size: Parameter = d_field(Parameter)
    pad_diameter: Parameter = d_field(Parameter)


class ArcNode(BaseNode):
    start: XYRNode = d_field(XYRNode)
    end: XYRNode = d_field(XYRNode)
    center: XYRNode = d_field(XYRNode)
    width: Parameter = d_field(Parameter)
    layer: LayerNode = d_field(LayerNode)


class RectangleNode(BaseNode):
    start: XYRNode = d_field(XYRNode)
    end: XYRNode = d_field(XYRNode)
    corner_radius: Parameter = d_field(Parameter)
    layer: LayerNode = d_field(LayerNode)


class BoardSetupNode(BaseNode):
    """KiCad `(setup ...)` block.

    Example:
        (setup
            (pad_to_mask_clearance 0)
            (tenting front back)
        )
    """

    thickness: Parameter = d_field(Parameter)
    dielectric_constant: Parameter = d_field(Parameter)
    copper_weight: Parameter = d_field(Parameter)
    notes: Parameter = d_field(Parameter)


class StackupLayerNode(BaseNode):
    """Represents entries from the KiCad `(layers ...)` table.

    Example:
        (0 "F.Cu" signal)
        (31 "F.CrtYd" user "F.Courtyard")
    """

    name: Parameter = d_field(Parameter)
    material: Parameter = d_field(Parameter)
    thickness: Parameter = d_field(Parameter)
    order: Parameter = d_field(Parameter)
    kicad: KicadLayerNode = d_field(KicadLayerNode)
    uuid: Parameter = d_field(Parameter)


class StackupNode(BaseNode):
    """Container linking board setup and ordered stackup layers."""

    board_setup: BoardSetupNode


class FootprintPropertyNode(BaseNode):
    """KiCad footprint property stanza.

    Example:
        (property "Reference" "C3" (at 0 -4 0) (layer "F.SilkS"))
    """

    key: Parameter = d_field(Parameter)
    value: Parameter = d_field(Parameter)
    shown: Parameter = d_field(Parameter)


class PoseNode(BaseNode):
    """Shared helper for `(at x y rot)` coordinate tuples."""

    origin: XYRNode
    rotation: Parameter = d_field(Parameter)


class PadLayerOptionsNode(BaseNode):
    """Captures pad layer masks.

    Example:
        (layers "F.Cu" "F.Paste" "F.Mask")
    """

    copper_layers: Parameter = d_field(Parameter)
    paste_layers: Parameter = d_field(Parameter)
    mask_layers: Parameter = d_field(Parameter)


class PadNode(BaseNode):
    """Represents a KiCad pad.

    Example:
        (pad "1" smd roundrect (at 137 126.25 -90)
            (size 0.7 0.8) (drill (offset 0 0))
            (layers "F.Cu" "F.Paste" "F.Mask"))
    """

    number: Parameter = d_field(Parameter)
    pad_type: Parameter = d_field(Parameter)
    shape: Parameter = d_field(Parameter)
    pose: PoseNode = d_field(PoseNode)
    size: XYRNode = d_field(XYRNode)
    drill: XYRNode = d_field(XYRNode)
    layers: PadLayerOptionsNode = d_field(PadLayerOptionsNode)
    uuid: Parameter = d_field(Parameter)
    clearance: Parameter = d_field(Parameter)


class TextNode(BaseNode):
    """Covers KiCad text records.

    Example:
        (fp_text reference "C3" (at 0 -4 0) (layer "F.SilkS"))
    """

    content: Parameter = d_field(Parameter)
    pose: PoseNode = d_field(PoseNode)
    layer: LayerNode = d_field(LayerNode)
    size: XYRNode = d_field(XYRNode)
    thickness: Parameter = d_field(Parameter)
    italic: Parameter = d_field(Parameter)
    bold: Parameter = d_field(Parameter)
    justify: Parameter = d_field(Parameter)
    visible: Parameter = d_field(Parameter)
    uuid: Parameter = d_field(Parameter)


class FootprintNode(BaseNode):
    """Wraps a KiCad `(footprint ...)` block.

    Example:
        (footprint "Samsung_Electro_Mechanics_CL05B104KO5NNNC:C0402"
            (layer "F.Cu")
            ...)
    """

    ref: Parameter = d_field(Parameter)
    value: Parameter = d_field(Parameter)
    library_id: Parameter = d_field(Parameter)
    pose: PoseNode = d_field(PoseNode)
    uuid: Parameter = d_field(Parameter)
    attributes: Parameter = d_field(Parameter)


class KicadOrderNode(BaseNode):
    """Marks the starting point for KiCad export ordering.

    This node is connected to:
    - The parent polygon (to indicate which polygon it orders)
    - The first element in the KiCad export sequence

    This allows fast O(1) lookup of the export starting point without
    needing numbered element names or sorting.
    """

    uuid: Parameter


class PolygonNode(BaseNode):
    """Represents `(polygon (pts ...))` definitions.

    Example:
        (polygon (pts (xy 141.71 118.70) (xy 142.96 118.70)))
        (polygon (pts
            (arc (start x y) (mid mx my) (end ex ey))
            (xy x2 y2)
        ))

    Contains XYRNode children for points and ArcNode children for arc segments.
    The polygon outline is formed by connecting these elements in sequence.
    Geometry children are added to runtime containers rather than explicit fields.
    """

    uuid: Parameter = d_field(Parameter)
    # Geometry children (XYRNode and ArcNode) are added via .add() to runtime containers


class ZoneSettingsNode(BaseNode):
    """Encodes `(zone ...)` settings like clearance, thermal gaps, hatch spacing.

    Example:
        (connect_pads (clearance 0.2))
        (min_thickness 0.15)
    """

    clearance: Parameter = d_field(Parameter)
    min_thickness: Parameter = d_field(Parameter)
    thermal_gap: Parameter = d_field(Parameter)
    thermal_width: Parameter = d_field(Parameter)
    hatch_spacing: Parameter = d_field(Parameter)
    fill_mode: Parameter = d_field(Parameter)


class ZoneNode(BaseNode):
    """Models `(zone ...)` blocks.

    Example:
        (zone (net 43) (layer "F.Cu")
            (polygon (pts ...))
            (filled_polygon (pts ...)))

    Extra `(polygon ...)` sections become additional `PolygonNode` children and
    represent holes/keep-outs.
    """

    outline: PolygonNode = d_field(PolygonNode)
    settings: ZoneSettingsNode = d_field(ZoneSettingsNode)
    layer: LayerNode = d_field(LayerNode)
    net_number: Parameter = d_field(Parameter)
    net_name: Parameter = d_field(Parameter)
    uuid: Parameter = d_field(Parameter)


class GroupNode(BaseNode):
    """Represents `(group (uuid ...) (members ...))` declarations.

    Example:
        (group (uuid "...") (members "pad-uuid" "text-uuid"))
    """

    name: Parameter = d_field(Parameter)
    uuid: Parameter = d_field(Parameter)


class RuleNode(BaseNode):
    """Generic rule tuple such as `(clearance 0.2)` or `(via_drill 0.3)`.

    Example from `net_class`:
        (trace_width 0.2)
    """

    key: Parameter = d_field(Parameter)
    value: Parameter = d_field(Parameter)
    scope: Parameter = d_field(Parameter)
    uuid: Parameter = d_field(Parameter)


class NetClassNode(BaseNode):
    """Wraps KiCad `(net_class "Name" "Desc" ...)` definitions.

    Example:
        (net_class "Default" ""
            (clearance 0.2)
            (trace_width 0.2)
            (via_dia 0.8))
    """

    name: Parameter = d_field(Parameter)
    description: Parameter = d_field(Parameter)
    uuid: Parameter = d_field(Parameter)


def get_net(node: Node) -> Optional[NetNode]:
    nets = node.get_children(direct_only=True, types=NetNode)
    if nets:
        return nets[0]

    if isinstance(node, BaseNode):
        connected_nets = node.connected.get_connected_nodes([NetNode])
        if connected_nets:
            return cast(NetNode, next(iter(connected_nets)))

    return None


def get_net_id(node: Node) -> Optional[int]:
    net = get_net(node)
    if net is None:
        return None

    net_lit = net.net_id.try_get_literal()
    if net_lit is not None:
        lit_value = getattr(net_lit, "magnitude", net_lit)
        if lit_value is not None:
            return int(lit_value)

    return None


class PCBNode(BaseNode):
    """Board-level container node."""


def new_line(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    width: float,
    layer: KicadLayer,
) -> LineNode:
    line = LineNode()
    line.start.x.alias_is(x0)
    line.start.y.alias_is(y0)
    line.end.x.alias_is(x1)
    line.end.y.alias_is(y1)
    line.width.alias_is(width)
    # Attach KiCad layer info and set layer (defaults to F.Cu)
    kicad = KicadLayerNode()
    line.layer.add(kicad, name="kicad")
    kicad.name.value.alias_is(layer)
    return line


def new_arc(
    x0: float,
    y0: float,
    mx: float,
    my: float,
    x1: float,
    y1: float,
    width: float,
    layer: KicadLayer,
) -> ArcNode:
    arc = ArcNode()
    arc.start.x.alias_is(x0)
    arc.start.y.alias_is(y0)
    arc.center.x.alias_is(mx)
    arc.center.y.alias_is(my)
    arc.end.x.alias_is(x1)
    arc.end.y.alias_is(y1)
    arc.width.alias_is(width)
    kicad = KicadLayerNode()
    arc.layer.add(kicad, name="kicad")
    kicad.name.value.alias_is(layer)
    return arc


def new_rectangle(
    sx: float,
    sy: float,
    ex: float,
    ey: float,
    layer: KicadLayer,
) -> RectangleNode:
    rect = RectangleNode()
    rect.start.x.alias_is(sx)
    rect.start.y.alias_is(sy)
    rect.end.x.alias_is(ex)
    rect.end.y.alias_is(ey)
    kicad = KicadLayerNode()
    rect.layer.add(kicad, name="kicad")
    kicad.name.value.alias_is(layer)
    return rect


def new_via(cx: float, cy: float, hole_size: float, pad_diameter: float) -> ViaNode:
    via = ViaNode()
    via.center.x.alias_is(cx)
    via.center.y.alias_is(cy)
    via.hole_size.alias_is(hole_size)
    via.pad_diameter.alias_is(pad_diameter)
    return via


def new_circle(cx: float, cy: float, r: float, layer: KicadLayer) -> CircleNode:
    circ = CircleNode()
    circ.center.x.alias_is(cx)
    circ.center.y.alias_is(cy)
    circ.radius.alias_is(r)
    kicad = KicadLayerNode()
    circ.layer.add(kicad, name="kicad")
    kicad.name.value.alias_is(layer)
    return circ


def create_demo_pcb() -> tuple[PCBNode, NetNode]:
    """Create a simple demo PCB with various primitives for testing/examples."""
    pcb_node = PCBNode()

    # Create a net
    net = NetNode()
    net.name.value.alias_is(NetName.NET_A)
    net.net_id.alias_is(1)
    pcb_node.add(net)

    # Create some basic primitives using helper functions
    line = new_line(0.0, 0.0, 10.0, 0.0, 0.2, KicadLayer.F_Cu)
    arc = new_arc(10.0, 0.0, 15.0, 5.0, 20.0, 0.0, 0.2, KicadLayer.F_Cu)
    via = new_via(20.0, 0.0, 0.3, 0.6)
    circle = new_circle(25.0, 0.0, 1.0, KicadLayer.F_SilkS)

    # Add primitives to PCB
    pcb_node.add(line)
    pcb_node.add(arc)
    pcb_node.add(via)
    pcb_node.add(circle)

    # Connect primitives to the net
    net.connect(line, arc, via)

    # Create a simple polygon with the new structure
    polygon = PolygonNode()
    polygon.uuid.alias_is("demo-polygon-uuid")

    # Define polygon points
    points = [(30.0, -5.0), (35.0, -5.0), (35.0, 5.0), (30.0, 5.0)]

    # Create XYRNode children for each point
    point_nodes = []
    for x, y in points:
        point_node = XYRNode()
        point_node.x.alias_is(x)
        point_node.y.alias_is(y)
        polygon.add(point_node)
        point_nodes.append(point_node)

    # Connect adjacent points to form the polygon ring
    for idx, point_node in enumerate(point_nodes):
        next_point = point_nodes[(idx + 1) % len(point_nodes)]
        point_node.connect(next_point)

    pcb_node.add(polygon)

    return pcb_node, net
