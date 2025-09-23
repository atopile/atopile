"""Bridge KiCad PCB files into Faebryk's PCB graph nodes."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from typing import Any

from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.core.pcbgraph import (
    ArcNode,
    CircleNode,
    FootprintNode,
    FootprintPropertyNode,
    KicadLayerNode,
    LayerNode,
    LineNode,
    NetNode,
    PadNode,
    PCBNode,
    PolygonNode,
    RectangleNode,
    TextNode,
    ViaNode,
    XYRNode,
    ZoneNode,
    get_net_id,
)
from faebryk.libs.kicad.fileformats_common import C_pts, C_stroke, C_xy, gen_uuid
from faebryk.libs.kicad.fileformats_latest import (
    C_arc,
    C_circle,
    C_kicad_pcb_file,
    C_line,
    C_net,
    C_polygon,
    C_rect,
)

Segment = C_kicad_pcb_file.C_kicad_pcb.C_segment
Via = C_kicad_pcb_file.C_kicad_pcb.C_via
LayerRecord = C_kicad_pcb_file.C_kicad_pcb.C_layer
FootprintRecord = C_kicad_pcb_file.C_kicad_pcb.C_pcb_footprint
ZoneRecord = C_kicad_pcb_file.C_kicad_pcb.C_zone


@dataclass
class PcbGraphData:
    """placeholder, will be removed as we integrated with the reset of the codebase"""

    pcb_node: PCBNode
    kicad_file: C_kicad_pcb_file


def _parameter_value(param: Parameter, default: Any = None) -> Any:
    literal = param.try_get_literal()
    if literal is None:
        return default
    if hasattr(literal, "value"):
        try:
            return literal.value
        except AttributeError:
            pass
    if hasattr(literal, "magnitude"):
        return float(literal.magnitude)
    return literal


def _set_param(node: Node, name: str, value: Any) -> Parameter:
    param = Parameter()
    node.add(param, name=name)
    if value is not None:
        param.alias_is(value)
    return param


def _get_param(node: Node, name: str, default: Any = None) -> Any:
    maybe = node.runtime.get(name)
    if isinstance(maybe, Parameter):
        literal = maybe.try_get_literal()
        if literal is None:
            return default
        if hasattr(literal, "value"):
            try:
                return literal.value
            except AttributeError:
                pass
        if hasattr(literal, "magnitude"):
            return float(literal.magnitude)
        return literal
    return default


def _parameter_float(param: Parameter, default: float | None = None) -> float:
    value = _parameter_value(param, default)
    if value is None:
        raise ValueError("missing literal value for parameter")
    return float(value)


def _set_xy_from_cxy(xyr, coord: C_xy) -> None:
    xyr.x.alias_is(coord.x)
    xyr.y.alias_is(coord.y)


def _parameter_int(param: Parameter, default: int | None = None) -> int:
    value = _parameter_value(param, default)
    if value is None:
        if default is None:
            raise ValueError("missing literal value for parameter")
        return int(default)
    return int(value)


def _populate_polygon_node(
    polygon_node: PolygonNode,
    polygon: C_polygon,
    role: str | None = None,
) -> None:
    if role is not None:
        _set_param(polygon_node, "polygon_role", role)
    if polygon.layer is not None:
        _set_param(polygon_node, "layer_name", polygon.layer)
    if hasattr(polygon, "layers") and polygon.layers is not None:
        _set_param(polygon_node, "layer_names", tuple(polygon.layers))

    uuid_value = getattr(polygon, "uuid", None)
    if uuid_value is not None:
        polygon_node.uuid.alias_is(uuid_value)

    # Add XYRNode children for each point
    point_nodes: list[XYRNode] = []
    for idx, xy in enumerate(getattr(polygon.pts, "xys", []) or []):
        point_node = XYRNode()
        point_node.x.alias_is(xy.x)
        point_node.y.alias_is(xy.y)
        _set_param(point_node, "index", idx)
        polygon_node.add(point_node)
        point_nodes.append(point_node)

    # Connect adjacent points to form the polygon ring
    if point_nodes:
        for idx, point_node in enumerate(point_nodes):
            next_point = point_nodes[(idx + 1) % len(point_nodes)]
            point_node.connect(next_point)

    # Add ArcNode children for arc segments
    coord_to_index = {
        (xy.x, xy.y): idx
        for idx, xy in enumerate(getattr(polygon.pts, "xys", []) or [])
    }
    for arc_idx, arc in enumerate(getattr(polygon.pts, "arcs", []) or []):
        arc_node = ArcNode()
        arc_node.start.x.alias_is(arc.start.x)
        arc_node.start.y.alias_is(arc.start.y)
        arc_node.center.x.alias_is(arc.mid.x)
        arc_node.center.y.alias_is(arc.mid.y)
        arc_node.end.x.alias_is(arc.end.x)
        arc_node.end.y.alias_is(arc.end.y)
        arc_node.width.alias_is(0.0)  # Polygon arcs don't have stroke width
        _set_param(arc_node, "arc_order", arc_idx)
        polygon_node.add(arc_node)

        # Connect arc to relevant points
        start_idx = coord_to_index.get((arc.start.x, arc.start.y))
        end_idx = coord_to_index.get((arc.end.x, arc.end.y))
        if start_idx is not None and start_idx < len(point_nodes):
            arc_node.connect(point_nodes[start_idx])
        if end_idx is not None and end_idx < len(point_nodes):
            arc_node.connect(point_nodes[end_idx])


def _polygon_node_to_polygon(
    polygon_node: PolygonNode,
    template: C_polygon | None = None,
    polygon_cls: type[C_polygon] = C_polygon,
) -> C_polygon:
    # Get XYRNode children (points) and sort by index
    point_nodes = list(polygon_node.get_children(direct_only=True, types=XYRNode))
    point_nodes.sort(key=lambda node: _get_param(node, "index", 0))

    points = []
    for point_node in point_nodes:
        x = _parameter_float(point_node.x)
        y = _parameter_float(point_node.y)
        points.append(C_xy(x, y))

    # Get ArcNode children and sort by arc_order
    arcs: list[C_pts.C_arc] = []
    arc_nodes = list(polygon_node.get_children(direct_only=True, types=ArcNode))
    arc_nodes.sort(key=lambda node: _get_param(node, "arc_order", 0))
    for arc_node in arc_nodes:
        start_x = _parameter_float(arc_node.start.x)
        start_y = _parameter_float(arc_node.start.y)
        mid_x = _parameter_float(arc_node.center.x)
        mid_y = _parameter_float(arc_node.center.y)
        end_x = _parameter_float(arc_node.end.x)
        end_y = _parameter_float(arc_node.end.y)

        arcs.append(
            C_pts.C_arc(
                start=C_xy(start_x, start_y),
                mid=C_xy(mid_x, mid_y),
                end=C_xy(end_x, end_y),
            )
        )

    layer_name_param = _get_param(polygon_node, "layer_name", None)
    layer_names_param = _get_param(polygon_node, "layer_names", None)

    if template is not None:
        polygon = copy.deepcopy(template)
        polygon.pts = C_pts(xys=points, arcs=[])
    else:
        if not points and not arcs:
            raise ValueError("Polygon requires at least one point or arc")
        kwargs: dict[str, Any] = {
            "layer": layer_name_param,
            "pts": C_pts(xys=points, arcs=[]),
        }
        if layer_names_param is not None and "layers" in polygon_cls.__annotations__:
            kwargs["layers"] = list(layer_names_param)
        polygon = polygon_cls(**kwargs)

    polygon.pts.arcs = arcs

    uuid_value = polygon_node.uuid.try_get_literal()
    if uuid_value is not None:
        polygon.uuid = uuid_value

    if layer_name_param is not None:
        polygon.layer = layer_name_param

    if layer_names_param is not None and hasattr(polygon, "layers"):
        polygon.layers = list(layer_names_param)

    return polygon


def load_pcb_graph(path: Path) -> PcbGraphData:
    kicad_file = C_kicad_pcb_file.loads(path)
    pcb = kicad_file.kicad_pcb
    pcb_node = PCBNode()

    _set_param(pcb_node, "kicad_version", pcb.version)
    if pcb.generator is not None:
        _set_param(pcb_node, "kicad_generator", pcb.generator)
    if pcb.generator_version is not None:
        _set_param(pcb_node, "kicad_generator_version", pcb.generator_version)
    if pcb.paper is not None:
        _set_param(pcb_node, "kicad_paper", pcb.paper)
    if pcb.general is not None:
        _set_param(pcb_node, "kicad_general", pcb.general)
    if pcb.setup is not None:
        _set_param(pcb_node, "kicad_setup", pcb.setup)

    layer_nodes: dict[str, LayerNode] = {}
    for order, layer in enumerate(pcb.layers):
        layer_node = LayerNode()
        kicad_layer = KicadLayerNode()
        layer_node.add(kicad_layer, name="kicad")
        kicad_layer.name.value.alias_is(layer.name)
        _set_param(layer_node, "kicad_number", layer.number)
        _set_param(layer_node, "kicad_name", layer.name)
        _set_param(
            layer_node, "kicad_type", getattr(layer.type, "value", str(layer.type))
        )
        if layer.alias is not None:
            _set_param(layer_node, "kicad_alias", layer.alias)
        if layer.unknown is not None:
            _set_param(layer_node, "kicad_unknown", layer.unknown)
        _set_param(layer_node, "kicad_order", order)
        pcb_node.add(layer_node, name=f"layer_{layer.number}")
        layer_nodes[layer.name] = layer_node

    nets_by_number: dict[int, NetNode] = {}
    for order, net in enumerate(pcb.nets):
        net_node = NetNode()
        if net.name:
            net_node.name.value.alias_is(net.name)
        net_node.net_id.alias_is(net.number)
        _set_param(net_node, "kicad_order", order)
        pcb_node.add(net_node, name=f"net_{net.number}")
        nets_by_number[net.number] = net_node

    for order, seg in enumerate(pcb.segments):
        line_node = LineNode()
        _set_xy_from_cxy(line_node.start, seg.start)
        _set_xy_from_cxy(line_node.end, seg.end)
        line_node.width.alias_is(seg.width)
        _set_param(line_node, "kicad_kind", "segment")
        _set_param(line_node, "kicad_order", order)
        _set_param(line_node, "uuid", seg.uuid)
        _set_param(line_node, "layer_name", seg.layer)
        if seg.solder_mask_margin is not None:
            _set_param(line_node, "solder_mask_margin", seg.solder_mask_margin)
        if seg.locked is not None:
            _set_param(line_node, "locked", seg.locked)
        if seg.layers:
            _set_param(line_node, "layers", tuple(seg.layers))
        if seg.layer in layer_nodes:
            line_node.layer.connect(layer_nodes[seg.layer])
        pcb_node.add(line_node)
        if net := nets_by_number.get(seg.net):
            net.connect(line_node)

    for order, gr in enumerate(pcb.gr_lines):
        line_node = LineNode()
        _set_xy_from_cxy(line_node.start, gr.start)
        _set_xy_from_cxy(line_node.end, gr.end)
        line_node.width.alias_is(gr.stroke.width)
        _set_param(line_node, "kicad_kind", "gr_line")
        _set_param(line_node, "kicad_order", order)
        _set_param(line_node, "uuid", gr.uuid)
        _set_param(line_node, "layer_name", gr.layer)
        _set_param(
            line_node,
            "stroke_type",
            getattr(gr.stroke.type, "value", str(gr.stroke.type)),
        )
        if gr.solder_mask_margin is not None:
            _set_param(line_node, "solder_mask_margin", gr.solder_mask_margin)
        if gr.locked is not None:
            _set_param(line_node, "locked", gr.locked)
        if gr.layers:
            _set_param(line_node, "layers", tuple(gr.layers))
        if gr.fill is not None:
            _set_param(line_node, "fill", gr.fill)
        if gr.layer in layer_nodes:
            line_node.layer.connect(layer_nodes[gr.layer])
        pcb_node.add(line_node)

    for order, arc in enumerate(pcb.gr_arcs):
        arc_node = ArcNode()
        _set_xy_from_cxy(arc_node.start, arc.start)
        _set_xy_from_cxy(arc_node.end, arc.end)
        arc_node.center.x.alias_is(arc.mid.x)
        arc_node.center.y.alias_is(arc.mid.y)
        arc_node.width.alias_is(arc.stroke.width)
        _set_param(arc_node, "kicad_kind", "gr_arc")
        _set_param(arc_node, "kicad_order", order)
        _set_param(arc_node, "uuid", arc.uuid)
        _set_param(arc_node, "layer_name", arc.layer)
        _set_param(
            arc_node,
            "stroke_type",
            getattr(arc.stroke.type, "value", str(arc.stroke.type)),
        )
        if arc.solder_mask_margin is not None:
            _set_param(arc_node, "solder_mask_margin", arc.solder_mask_margin)
        if arc.locked is not None:
            _set_param(arc_node, "locked", arc.locked)
        if arc.layers:
            _set_param(arc_node, "layers", tuple(arc.layers))
        if arc.fill is not None:
            _set_param(arc_node, "fill", arc.fill)
        if arc.layer in layer_nodes:
            arc_node.layer.connect(layer_nodes[arc.layer])
        pcb_node.add(arc_node)

    for order, circle in enumerate(pcb.gr_circles):
        circle_node = CircleNode()
        _set_xy_from_cxy(circle_node.center, circle.center)
        offset = (circle.end.x - circle.center.x, circle.end.y - circle.center.y)
        radius = hypot(*offset)
        circle_node.radius.alias_is(radius)
        _set_param(circle_node, "kicad_kind", "gr_circle")
        _set_param(circle_node, "kicad_order", order)
        _set_param(circle_node, "uuid", circle.uuid)
        _set_param(circle_node, "layer_name", circle.layer)
        _set_param(circle_node, "stroke_width", circle.stroke.width)
        _set_param(
            circle_node,
            "stroke_type",
            getattr(circle.stroke.type, "value", str(circle.stroke.type)),
        )
        _set_param(circle_node, "end_offset", offset)
        if circle.solder_mask_margin is not None:
            _set_param(circle_node, "solder_mask_margin", circle.solder_mask_margin)
        if circle.locked is not None:
            _set_param(circle_node, "locked", circle.locked)
        if circle.layers:
            _set_param(circle_node, "layers", tuple(circle.layers))
        if circle.fill is not None:
            _set_param(circle_node, "fill", circle.fill)
        if circle.layer in layer_nodes:
            circle_node.layer.connect(layer_nodes[circle.layer])
        pcb_node.add(circle_node)

    for order, rect in enumerate(pcb.gr_rects):
        rect_node = RectangleNode()
        _set_xy_from_cxy(rect_node.start, rect.start)
        _set_xy_from_cxy(rect_node.end, rect.end)
        _set_param(rect_node, "kicad_kind", "gr_rect")
        _set_param(rect_node, "kicad_order", order)
        _set_param(rect_node, "uuid", rect.uuid)
        _set_param(rect_node, "layer_name", rect.layer)
        _set_param(rect_node, "stroke_width", rect.stroke.width)
        _set_param(
            rect_node,
            "stroke_type",
            getattr(rect.stroke.type, "value", str(rect.stroke.type)),
        )
        if rect.solder_mask_margin is not None:
            _set_param(rect_node, "solder_mask_margin", rect.solder_mask_margin)
        if rect.locked is not None:
            _set_param(rect_node, "locked", rect.locked)
        if rect.layers:
            _set_param(rect_node, "layers", tuple(rect.layers))
        if rect.fill is not None:
            _set_param(rect_node, "fill", rect.fill)
        if rect.layer in layer_nodes:
            rect_node.layer.connect(layer_nodes[rect.layer])
        pcb_node.add(rect_node)

    for order, via in enumerate(pcb.vias):
        via_node = ViaNode()
        via_node.center.x.alias_is(via.at.x)
        via_node.center.y.alias_is(via.at.y)
        via_node.hole_size.alias_is(via.drill)
        via_node.pad_diameter.alias_is(via.size)
        _set_param(via_node, "kicad_order", order)
        _set_param(via_node, "uuid", via.uuid)
        _set_param(via_node, "layers", tuple(via.layers))
        if via.remove_unused_layers is not None:
            _set_param(via_node, "remove_unused_layers", via.remove_unused_layers)
        if via.keep_end_layers is not None:
            _set_param(via_node, "keep_end_layers", via.keep_end_layers)
        if via.zone_layer_connections is not None:
            _set_param(via_node, "zone_layer_connections", via.zone_layer_connections)
        if via.padstack is not None:
            _set_param(via_node, "padstack", via.padstack)
        if via.teardrops is not None:
            _set_param(via_node, "teardrops", via.teardrops)
        if via.tenting is not None:
            _set_param(via_node, "tenting", via.tenting)
        if via.free is not None:
            _set_param(via_node, "free", via.free)
        if via.locked is not None:
            _set_param(via_node, "locked", via.locked)
        if via.unknown is not None:
            _set_param(via_node, "unknown", via.unknown)
        # Note: Via pad layers are handled by the via layers parameter
        pcb_node.add(via_node)
        if net := nets_by_number.get(via.net):
            net.connect(via_node)

    footprint_nodes: list[FootprintNode] = []
    for order, footprint in enumerate(pcb.footprints):
        fp_node = FootprintNode()
        _set_param(fp_node, "kicad_order", order)
        _set_param(fp_node, "layer_name", footprint.layer)
        _set_param(fp_node, "raw_footprint", footprint)
        if footprint.name:
            fp_node.library_id.alias_is(footprint.name)
        if footprint.uuid is not None:
            fp_node.uuid.alias_is(footprint.uuid)
        if hasattr(footprint, "attr") and footprint.attr is not None:
            _set_param(fp_node, "attributes", footprint.attr)
        if footprint.at is not None:
            fp_node.pose.origin.x.alias_is(footprint.at.x)
            fp_node.pose.origin.y.alias_is(footprint.at.y)
            fp_node.pose.rotation.alias_is(footprint.at.r)
        props = footprint.propertys if isinstance(footprint.propertys, dict) else {}
        reference = props.get("Reference")
        value_prop = props.get("Value")
        if reference is not None:
            fp_node.ref.alias_is(reference.value)
        if value_prop is not None:
            fp_node.value.alias_is(value_prop.value)

        for prop in props.values():
            prop_node = FootprintPropertyNode()
            prop_node.key.alias_is(prop.name)
            prop_node.value.alias_is(prop.value)
            prop_node.shown.alias_is(not getattr(prop, "hide", False))
            _set_param(prop_node, "layer_name", getattr(prop.layer, "layer", None))
            _set_param(prop_node, "pose", getattr(prop, "at", None))
            _set_param(prop_node, "uuid", getattr(prop, "uuid", None))
            fp_node.add(prop_node)

        for idx, txt in enumerate(getattr(footprint, "fp_texts", [])):
            text_node = TextNode()
            text_node.content.alias_is(txt.text)
            if txt.at is not None:
                text_node.pose.origin.x.alias_is(txt.at.x)
                text_node.pose.origin.y.alias_is(txt.at.y)
                text_node.pose.rotation.alias_is(txt.at.r)
            if txt.effects and txt.effects.font and txt.effects.font.size:
                text_node.size.x.alias_is(txt.effects.font.size.w)
                text_node.size.y.alias_is(txt.effects.font.size.h)
                if txt.effects.font.thickness is not None:
                    text_node.thickness.alias_is(txt.effects.font.thickness)
            text_node.visible.alias_is(not getattr(txt, "hide", False))
            if txt.uuid is not None:
                text_node.uuid.alias_is(txt.uuid)
            layer_name = getattr(getattr(txt, "layer", None), "layer", None)
            if layer_name is not None:
                _set_param(text_node, "layer_name", layer_name)
                if layer_name in layer_nodes:
                    text_node.layer.connect(layer_nodes[layer_name])
            fp_node.add(text_node)

        for pad in getattr(footprint, "pads", []):
            pad_node = PadNode()
            if pad.name is not None:
                pad_node.number.alias_is(pad.name)
            if pad.type is not None:
                pad_node.pad_type.alias_is(pad.type)
            if pad.shape is not None:
                pad_node.shape.alias_is(pad.shape)
            if pad.at is not None:
                pad_node.pose.origin.x.alias_is(pad.at.x)
                pad_node.pose.origin.y.alias_is(pad.at.y)
                pad_node.pose.rotation.alias_is(pad.at.r)
            if pad.size is not None:
                if hasattr(pad.size, "x") and hasattr(pad.size, "y"):
                    pad_node.size.x.alias_is(pad.size.x)
                    pad_node.size.y.alias_is(pad.size.y)
                elif hasattr(pad.size, "w") and hasattr(pad.size, "h"):
                    pad_node.size.x.alias_is(pad.size.w)
                    pad_node.size.y.alias_is(pad.size.h)
            if pad.drill is not None:
                drill = pad.drill
                if hasattr(drill, "x") and hasattr(drill, "y"):
                    pad_node.drill.x.alias_is(drill.x)
                    pad_node.drill.y.alias_is(drill.y)
                elif hasattr(drill, "size") and drill.size is not None:
                    size = drill.size
                    if hasattr(size, "x") and hasattr(size, "y"):
                        pad_node.drill.x.alias_is(size.x)
                        pad_node.drill.y.alias_is(size.y)
                    else:
                        pad_node.drill.x.alias_is(size)
                        pad_node.drill.y.alias_is(size)
                elif isinstance(drill, (int, float)):
                    pad_node.drill.x.alias_is(float(drill))
                    pad_node.drill.y.alias_is(float(drill))
            layer_list = list(getattr(pad, "layers", []) or [])
            copper_layers = tuple(
                layer for layer in layer_list if layer.endswith(".Cu")
            )
            paste_layers = tuple(
                layer for layer in layer_list if layer.endswith(".Paste")
            )
            mask_layers = tuple(
                layer for layer in layer_list if layer.endswith(".Mask")
            )
            if copper_layers:
                pad_node.layers.copper_layers.alias_is(copper_layers)
            if paste_layers:
                pad_node.layers.paste_layers.alias_is(paste_layers)
            if mask_layers:
                pad_node.layers.mask_layers.alias_is(mask_layers)
            if getattr(pad, "uuid", None) is not None:
                pad_node.uuid.alias_is(pad.uuid)
            if getattr(pad, "clearance", None) is not None:
                pad_node.clearance.alias_is(pad.clearance)
            fp_node.add(pad_node)
            net_number = getattr(pad, "net", None)
            if isinstance(net_number, int) and net_number in nets_by_number:
                nets_by_number[net_number].connect(pad_node)

        for line in getattr(footprint, "fp_lines", []):
            line_node = LineNode()
            _set_xy_from_cxy(line_node.start, line.start)
            _set_xy_from_cxy(line_node.end, line.end)
            line_node.width.alias_is(line.stroke.width)
            _set_param(line_node, "kicad_kind", "fp_line")
            _set_param(line_node, "layer_name", line.layer)
            if line.layer in layer_nodes:
                line_node.layer.connect(layer_nodes[line.layer])
            fp_node.add(line_node)

        pcb_node.add(fp_node)
        footprint_nodes.append(fp_node)

    zone_nodes: list[ZoneNode] = []
    for order, zone in enumerate(pcb.zones):
        zone_node = ZoneNode()
        _set_param(zone_node, "kicad_order", order)
        if zone.uuid is not None:
            zone_node.uuid.alias_is(zone.uuid)
        if zone.net is not None:
            zone_node.net_number.alias_is(zone.net)
            if zone.net in nets_by_number:
                nets_by_number[zone.net].connect(zone_node)
        if zone.net_name is not None:
            zone_node.net_name.alias_is(zone.net_name)
        if zone.name is not None:
            _set_param(zone_node, "zone_name", zone.name)
        if zone.priority is not None:
            _set_param(zone_node, "priority", zone.priority)
        layers_tuple = tuple(zone.layers or [])
        if layers_tuple:
            _set_param(zone_node, "layer_names", layers_tuple)
            first_layer = layers_tuple[0]
            if first_layer in layer_nodes:
                zone_node.layer.connect(layer_nodes[first_layer])
        if zone.hatch is not None:
            _set_param(zone_node, "hatch", zone.hatch)
        if zone.fill is not None:
            _set_param(zone_node, "fill", zone.fill)
            if getattr(zone.fill, "thermal_gap", None) is not None:
                zone_node.settings.thermal_gap.alias_is(zone.fill.thermal_gap)
            if getattr(zone.fill, "thermal_bridge_width", None) is not None:
                zone_node.settings.thermal_width.alias_is(
                    zone.fill.thermal_bridge_width
                )
            if getattr(zone.fill, "mode", None) is not None:
                _set_param(zone_node, "fill_mode", zone.fill.mode)
            if getattr(zone.fill, "enable", None) is not None:
                _set_param(zone_node, "fill_enable", zone.fill.enable)
        if zone.connect_pads is not None:
            if getattr(zone.connect_pads, "clearance", None) is not None:
                zone_node.settings.clearance.alias_is(zone.connect_pads.clearance)
            if getattr(zone.connect_pads, "mode", None) is not None:
                _set_param(zone_node, "connect_mode", zone.connect_pads.mode)
            if getattr(zone.connect_pads, "unknown", None) is not None:
                _set_param(zone_node, "connect_unknown", zone.connect_pads.unknown)
        if getattr(zone, "min_thickness", None) is not None:
            zone_node.settings.min_thickness.alias_is(zone.min_thickness)
        if getattr(zone, "filled_areas_thickness", None) is not None:
            _set_param(zone_node, "filled_areas_thickness", zone.filled_areas_thickness)
        if getattr(zone, "keepout", None) is not None:
            _set_param(zone_node, "keepout", zone.keepout)
        if getattr(zone, "attr", None) is not None:
            _set_param(zone_node, "attr", zone.attr)
        if getattr(zone, "placement", None) is not None:
            _set_param(zone_node, "placement", zone.placement)
        if getattr(zone, "unknown", None) is not None:
            _set_param(zone_node, "unknown", zone.unknown)

        outline = getattr(zone, "polygon", None)
        if outline is not None and getattr(outline, "pts", None) is not None:
            _populate_polygon_node(zone_node.outline, outline, role="outline")

        for idx, polygon in enumerate(getattr(zone, "filled_polygon", []) or []):
            filled_node = PolygonNode()
            _populate_polygon_node(filled_node, polygon, role="filled")
            zone_node.add(filled_node, name=f"filled_{idx}")

        pcb_node.add(zone_node)
        zone_nodes.append(zone_node)

    return PcbGraphData(pcb_node=pcb_node, kicad_file=kicad_file)


def dump_pcb_graph(graph: PcbGraphData, path: Path | None = None) -> str:
    kicad_file = copy.deepcopy(graph.kicad_file)
    pcb = kicad_file.kicad_pcb

    version = _get_param(graph.pcb_node, "kicad_version", pcb.version)
    if version is not None:
        pcb.version = int(version)
    generator = _get_param(graph.pcb_node, "kicad_generator", pcb.generator)
    if generator is not None:
        pcb.generator = generator
    generator_version = _get_param(
        graph.pcb_node, "kicad_generator_version", pcb.generator_version
    )
    if generator_version is not None:
        pcb.generator_version = generator_version
    paper = _get_param(graph.pcb_node, "kicad_paper", pcb.paper)
    if paper is not None:
        pcb.paper = paper
    general = _get_param(graph.pcb_node, "kicad_general", pcb.general)
    if general is not None:
        pcb.general = copy.deepcopy(general)
    setup = _get_param(graph.pcb_node, "kicad_setup", pcb.setup)
    if setup is not None:
        pcb.setup = copy.deepcopy(setup)

    layer_defs = list(graph.pcb_node.get_children(direct_only=True, types=LayerNode))
    layer_defs.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.layers = [
        LayerRecord(
            number=int(_get_param(layer_node, "kicad_number", idx)),
            name=str(_get_param(layer_node, "kicad_name", f"layer_{idx}")),
            type=LayerRecord.E_type(_get_param(layer_node, "kicad_type", "user")),
            alias=_get_param(layer_node, "kicad_alias", None),
            unknown=_get_param(layer_node, "kicad_unknown", None),
        )
        for idx, layer_node in enumerate(layer_defs)
    ]

    net_nodes = list(graph.pcb_node.get_children(direct_only=True, types=NetNode))
    net_nodes.sort(
        key=lambda node: _get_param(node, "kicad_order", get_net_id(node) or 0)
    )
    pcb.nets = [
        C_net(
            number=int(_parameter_value(net_node.net_id, 0)),
            name=str(_parameter_value(net_node.name.value, "")),
        )
        for net_node in net_nodes
    ]

    line_nodes = list(graph.pcb_node.get_children(direct_only=True, types=LineNode))

    segments = [
        node for node in line_nodes if _get_param(node, "kicad_kind") == "segment"
    ]
    segments.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.segments = [
        Segment(
            layer=str(_get_param(node, "layer_name", "F.Cu")),
            layers=list(_get_param(node, "layers", [])) or None,
            start=C_xy(
                _parameter_float(node.start.x),
                _parameter_float(node.start.y),
            ),
            end=C_xy(
                _parameter_float(node.end.x),
                _parameter_float(node.end.y),
            ),
            width=_parameter_float(node.width),
            net=get_net_id(node) or 0,
            uuid=_get_param(node, "uuid", None),
            solder_mask_margin=_get_param(node, "solder_mask_margin", None),
            locked=_get_param(node, "locked", None),
        )
        for node in segments
    ]

    gr_lines = [
        node for node in line_nodes if _get_param(node, "kicad_kind") == "gr_line"
    ]
    gr_lines.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.gr_lines = [
        C_line(
            layer=str(_get_param(node, "layer_name", "F.SilkS")),
            layers=list(_get_param(node, "layers", [])) or None,
            solder_mask_margin=_get_param(node, "solder_mask_margin", None),
            stroke=C_stroke(
                width=_parameter_float(node.width),
                type=C_stroke.E_type(_get_param(node, "stroke_type", "solid")),
            ),
            fill=_get_param(node, "fill", None),
            locked=_get_param(node, "locked", None),
            uuid=_get_param(node, "uuid", None),
            start=C_xy(
                _parameter_float(node.start.x),
                _parameter_float(node.start.y),
            ),
            end=C_xy(
                _parameter_float(node.end.x),
                _parameter_float(node.end.y),
            ),
        )
        for node in gr_lines
    ]

    arc_nodes = list(graph.pcb_node.get_children(direct_only=True, types=ArcNode))
    arcs = [node for node in arc_nodes if _get_param(node, "kicad_kind") == "gr_arc"]
    arcs.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.gr_arcs = [
        C_arc(
            layer=str(_get_param(node, "layer_name", "F.SilkS")),
            layers=list(_get_param(node, "layers", [])) or None,
            solder_mask_margin=_get_param(node, "solder_mask_margin", None),
            stroke=C_stroke(
                width=_parameter_float(node.width),
                type=C_stroke.E_type(_get_param(node, "stroke_type", "solid")),
            ),
            fill=_get_param(node, "fill", None),
            locked=_get_param(node, "locked", None),
            uuid=_get_param(node, "uuid", None),
            start=C_xy(
                _parameter_float(node.start.x),
                _parameter_float(node.start.y),
            ),
            mid=C_xy(
                _parameter_float(node.center.x),
                _parameter_float(node.center.y),
            ),
            end=C_xy(
                _parameter_float(node.end.x),
                _parameter_float(node.end.y),
            ),
        )
        for node in arcs
    ]

    circle_nodes = list(graph.pcb_node.get_children(direct_only=True, types=CircleNode))
    circles = [
        node for node in circle_nodes if _get_param(node, "kicad_kind") == "gr_circle"
    ]
    circles.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.gr_circles = []
    for node in circles:
        cx = _parameter_float(node.center.x)
        cy = _parameter_float(node.center.y)
        radius = _parameter_float(node.radius)
        offset = _get_param(node, "end_offset", (radius, 0.0))
        dx, dy = offset
        if dx == 0 and dy == 0:
            dx, dy = radius, 0.0
        else:
            scale = radius / hypot(dx, dy)
            dx *= scale
            dy *= scale
        pcb.gr_circles.append(
            C_circle(
                layer=str(_get_param(node, "layer_name", "F.SilkS")),
                layers=list(_get_param(node, "layers", [])) or None,
                solder_mask_margin=_get_param(node, "solder_mask_margin", None),
                stroke=C_stroke(
                    width=float(_get_param(node, "stroke_width", 0.15)),
                    type=C_stroke.E_type(_get_param(node, "stroke_type", "solid")),
                ),
                fill=_get_param(node, "fill", None),
                locked=_get_param(node, "locked", None),
                uuid=_get_param(node, "uuid", None),
                center=C_xy(cx, cy),
                end=C_xy(cx + dx, cy + dy),
            )
        )

    rect_nodes = list(
        graph.pcb_node.get_children(direct_only=True, types=RectangleNode)
    )
    rects = [node for node in rect_nodes if _get_param(node, "kicad_kind") == "gr_rect"]
    rects.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.gr_rects = [
        C_rect(
            layer=str(_get_param(node, "layer_name", "F.SilkS")),
            layers=list(_get_param(node, "layers", [])) or None,
            solder_mask_margin=_get_param(node, "solder_mask_margin", None),
            stroke=C_stroke(
                width=float(_get_param(node, "stroke_width", 0.15)),
                type=C_stroke.E_type(_get_param(node, "stroke_type", "solid")),
            ),
            fill=_get_param(node, "fill", None),
            locked=_get_param(node, "locked", None),
            uuid=_get_param(node, "uuid", None),
            start=C_xy(
                _parameter_float(node.start.x),
                _parameter_float(node.start.y),
            ),
            end=C_xy(
                _parameter_float(node.end.x),
                _parameter_float(node.end.y),
            ),
        )
        for node in rects
    ]

    via_nodes = list(graph.pcb_node.get_children(direct_only=True, types=ViaNode))
    via_nodes.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.vias = [
        Via(
            at=C_xy(
                _parameter_float(node.center.x),
                _parameter_float(node.center.y),
            ),
            size=_parameter_float(node.pad_diameter),
            drill=_parameter_float(node.hole_size),
            layers=list(_get_param(node, "layers", [])) or ["F.Cu", "B.Cu"],
            net=get_net_id(node) or 0,
            remove_unused_layers=_get_param(node, "remove_unused_layers", None),
            keep_end_layers=_get_param(node, "keep_end_layers", None),
            zone_layer_connections=_get_param(node, "zone_layer_connections", None),
            padstack=_get_param(node, "padstack", None),
            teardrops=_get_param(node, "teardrops", None),
            tenting=_get_param(node, "tenting", None),
            free=_get_param(node, "free", None),
            locked=_get_param(node, "locked", None),
            uuid=_get_param(node, "uuid", None),
            unknown=_get_param(node, "unknown", None),
        )
        for node in via_nodes
    ]

    footprint_nodes = list(
        graph.pcb_node.get_children(direct_only=True, types=FootprintNode)
    )
    footprint_nodes.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    pcb.footprints = [
        copy.deepcopy(_get_param(node, "raw_footprint"))
        for node in footprint_nodes
        if _get_param(node, "raw_footprint") is not None
    ]

    zone_nodes = list(graph.pcb_node.get_children(direct_only=True, types=ZoneNode))
    zone_nodes.sort(key=lambda node: _get_param(node, "kicad_order", 0))
    zone_records: list[ZoneRecord] = []
    for zone_node in zone_nodes:
        net_number = _parameter_int(zone_node.net_number, 0)
        net_name = zone_node.net_name.try_get_literal() or ""
        uuid_value = zone_node.uuid.try_get_literal() or gen_uuid()

        layers_literal = _get_param(zone_node, "layer_names", None)
        layers_list = list(layers_literal) if layers_literal is not None else None

        hatch_data = _get_param(zone_node, "hatch", None)
        hatch = (
            copy.deepcopy(hatch_data)
            if hatch_data is not None
            else ZoneRecord.C_hatch(mode=ZoneRecord.C_hatch.E_mode.full, pitch=0.5)
        )

        clearance_literal = zone_node.settings.clearance.try_get_literal()
        clearance = float(clearance_literal) if clearance_literal is not None else 0.0
        connect_mode = _get_param(zone_node, "connect_mode", None)
        connect_unknown = _get_param(zone_node, "connect_unknown", None)
        connect_pads = ZoneRecord.C_connect_pads(
            mode=connect_mode,
            clearance=clearance,
            unknown=copy.deepcopy(connect_unknown),
        )

        min_thickness = _parameter_float(zone_node.settings.min_thickness, 0.0)
        filled_areas_thickness = bool(
            _get_param(zone_node, "filled_areas_thickness", False)
        )

        fill_data = _get_param(zone_node, "fill", None)
        if fill_data is not None:
            fill = copy.deepcopy(fill_data)
        else:
            thermal_gap_literal = zone_node.settings.thermal_gap.try_get_literal()
            thermal_width_literal = zone_node.settings.thermal_width.try_get_literal()
            fill = ZoneRecord.C_fill(
                enable=_get_param(zone_node, "fill_enable", None),
                mode=_get_param(zone_node, "fill_mode", None),
                thermal_gap=float(thermal_gap_literal or 0.0),
                thermal_bridge_width=float(thermal_width_literal or 0.0),
            )
        thermal_gap_literal = zone_node.settings.thermal_gap.try_get_literal()
        if thermal_gap_literal is not None:
            fill.thermal_gap = float(thermal_gap_literal)
        thermal_width_literal = zone_node.settings.thermal_width.try_get_literal()
        if thermal_width_literal is not None:
            fill.thermal_bridge_width = float(thermal_width_literal)

        polygon = _polygon_node_to_polygon(zone_node.outline)

        filled_polygons: list[C_polygon] = []
        for polygon_node in zone_node.get_children(direct_only=True, types=PolygonNode):
            if polygon_node is zone_node.outline:
                continue
            if _get_param(polygon_node, "polygon_role", "") == "filled":
                filled_polygons.append(
                    _polygon_node_to_polygon(
                        polygon_node, polygon_cls=ZoneRecord.C_filled_polygon
                    )
                )

        zone_records.append(
            ZoneRecord(
                net=net_number,
                net_name=net_name,
                layers=layers_list,
                uuid=uuid_value,
                name=_get_param(zone_node, "zone_name", None),
                hatch=hatch,
                priority=_get_param(zone_node, "priority", None),
                attr=copy.deepcopy(_get_param(zone_node, "attr", None)),
                connect_pads=connect_pads,
                min_thickness=min_thickness,
                filled_areas_thickness=filled_areas_thickness,
                fill=fill,
                keepout=copy.deepcopy(_get_param(zone_node, "keepout", None)),
                polygon=polygon,
                filled_polygon=filled_polygons,
                placement=copy.deepcopy(_get_param(zone_node, "placement", None)),
                unknown=copy.deepcopy(_get_param(zone_node, "unknown", None)),
            )
        )

    pcb.zones = zone_records

    return kicad_file.dumps(path)
