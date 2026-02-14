# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.pcb.board_shape.board_shape import apply_rectangular_board_shape
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer, get_all_geos
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.test.fileformats import PCBFILE


class _TestApp(fabll.Node):
    board = F.RectangularBoardShape.MakeChild()


def _new_transformer(
    *,
    width_m: float,
    height_m: float,
    corner_radius_m: float = 0.0,
    mounting_hole_diameter_m: float | None = None,
) -> PCB_Transformer:
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = _TestApp.bind_typegraph(tg=tg).create_instance(g=g)

    board = app.board.get()
    board.width.get().set_superset(g=g, value=width_m)
    board.height.get().set_superset(g=g, value=height_m)
    board.corner_radius.get().set_superset(g=g, value=corner_radius_m)
    if mounting_hole_diameter_m is not None:
        board.mounting_hole_diameter.get().set_superset(
            g=g, value=mounting_hole_diameter_m
        )

    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
    return PCB_Transformer(pcb=pcb, app=app)


class TestBoardShapeExporter(unittest.TestCase):
    def test_generates_rectangular_outline(self):
        transformer = _new_transformer(width_m=0.020, height_m=0.030)
        apply_rectangular_board_shape(transformer)

        edge_geos = [
            geo
            for geo in get_all_geos(transformer.pcb)
            if "Edge.Cuts" in kicad.geo.get_layers(geo)
        ]
        lines = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Line)]
        arcs = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Arc)]
        circles = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Circle)]

        self.assertEqual(len(lines), 4)
        self.assertEqual(len(arcs), 0)
        self.assertEqual(len(circles), 0)

    def test_generates_rounded_outline_and_corner_holes(self):
        transformer = _new_transformer(
            width_m=0.020,
            height_m=0.030,
            corner_radius_m=0.003,
            mounting_hole_diameter_m=0.0033,
        )
        apply_rectangular_board_shape(transformer)

        edge_geos = [
            geo
            for geo in get_all_geos(transformer.pcb)
            if "Edge.Cuts" in kicad.geo.get_layers(geo)
        ]
        arcs = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Arc)]
        circles = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Circle)]

        self.assertEqual(len(arcs), 4)
        self.assertEqual(len(circles), 4)

        # 3.3mm diameter -> 1.65mm radius for each corner hole
        radius_mm = circles[0].end.x - circles[0].center.x
        self.assertAlmostEqual(radius_mm, 1.65, places=3)
