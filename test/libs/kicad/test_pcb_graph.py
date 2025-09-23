from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from atopile.pcb_transformer import dump_pcb_graph, load_pcb_graph
from faebryk.core.parameter import Parameter
from faebryk.core.pcbgraph import (
    FootprintNode,
    LineNode,
    PadNode,
    ViaNode,
    XYRNode,
    ZoneNode,
    get_net_id,
)


def _param(node, name: str):
    value = node.runtime.get(name)
    if isinstance(value, Parameter):
        return value.try_get_literal()
    return None


@pytest.mark.parametrize(
    "pcb_path",
    [Path("build/pcbgraph_poc.kicad_pcb")],
)
def test_pcb_graph_round_trip_small(pcb_path: Path) -> None:
    original = pcb_path.read_text()
    graph = load_pcb_graph(pcb_path)
    regenerated = dump_pcb_graph(graph)

    if regenerated != original:
        diff = "\n".join(
            difflib.unified_diff(
                original.splitlines(),
                regenerated.splitlines(),
                fromfile="original",
                tofile="roundtrip",
                lineterm="",
            )
        )
        pytest.fail(f"Round-trip serialization changed the pcb file:\n{diff}")

    pcb_node = graph.pcb_node

    copper_lines = [
        line
        for line in pcb_node.get_children(direct_only=True, types=LineNode)
        if _param(line, "kicad_kind") == "segment"
    ]
    assert copper_lines, "Segments should be present in the PCB graph"
    assert {get_net_id(line) for line in copper_lines} == {1}

    assert {_param(line, "layer_name") for line in copper_lines} == {"F.Cu", "B.Cu"}

    vias = [
        via
        for via in pcb_node.get_children(direct_only=True, types=ViaNode)
        if _param(via, "uuid") is not None
    ]
    assert vias and all(isinstance(v, ViaNode) for v in vias)
    assert get_net_id(vias[0]) == 1

    silkscreen = [
        line
        for line in pcb_node.get_children(direct_only=True, types=LineNode)
        if _param(line, "kicad_kind") == "gr_line"
        and _param(line, "layer_name") == "F.SilkS"
    ]
    assert silkscreen, "Expect front silkscreen graphics to be captured"


@pytest.mark.parametrize(
    "pcb_path",
    [Path("examples/esp32_minimal/layouts/esp32_minimal/esp32_minimal.kicad_pcb")],
)
def test_pcb_graph_round_trip_esp32(pcb_path: Path) -> None:
    original = pcb_path.read_text()
    graph = load_pcb_graph(pcb_path)
    regenerated = dump_pcb_graph(graph)

    if regenerated != original:
        diff = "\n".join(
            difflib.unified_diff(
                original.splitlines(),
                regenerated.splitlines(),
                fromfile="original",
                tofile="roundtrip",
                lineterm="",
            )
        )
        pytest.fail(f"Round-trip serialization changed the pcb file:\n{diff}")

    pcb_node = graph.pcb_node

    footprints = list(pcb_node.get_children(direct_only=True, types=FootprintNode))
    assert footprints, "Footprints should be captured"
    first_fp = footprints[0]
    assert first_fp.ref.try_get_literal() is not None
    pad_nodes = list(first_fp.get_children(direct_only=True, types=PadNode))
    assert pad_nodes, "Pads should be attached to footprint nodes"

    zones = list(pcb_node.get_children(direct_only=True, types=ZoneNode))
    assert zones, "Zones should be captured"
    outline_points = [
        point
        for point in zones[0].outline.get_children(direct_only=True, types=XYRNode)
        if _param(point, "index") is not None
    ]
    assert outline_points, "Zone outline should expose polygon points"

    from faebryk.core.pcbgraph import ArcNode

    outline_arcs = [
        arc
        for arc in zones[0].outline.get_children(direct_only=True, types=ArcNode)
        if _param(arc, "arc_order") is not None
    ]
    if outline_arcs:
        assert all(
            arc.start.x.try_get_literal() is not None
            and arc.end.x.try_get_literal() is not None
            for arc in outline_arcs
        ), "Polygon arcs should have start and end coordinates"

    via_nodes = list(pcb_node.get_children(direct_only=True, types=ViaNode))
    assert via_nodes, "Vias should still be present"
