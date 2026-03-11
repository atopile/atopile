# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserBadParameterError, UserException
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer, get_all_geos
from faebryk.exporters.pcb.rectangular_board_shape import apply_rectangular_board_shape
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.test.fileformats import PCBFILE


class _TestBoardShapeApp(fabll.Node):
    board = F.RectangularBoardShape.MakeChild()


def _new_test_transformer(
    *,
    x_m: float,
    y_m: float,
    corner_radius_m: float = 0.0,
) -> tuple[PCB_Transformer, F.RectangularBoardShape]:
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = _TestBoardShapeApp.bind_typegraph(tg=tg).create_instance(g=g)

    board = app.board.get()
    board.x.get().set_superset(g=g, value=x_m)
    board.y.get().set_superset(g=g, value=y_m)
    board.corner_radius.get().set_superset(g=g, value=corner_radius_m)

    pcb = kicad.copy(kicad.loads(kicad.pcb.PcbFile, PCBFILE)).kicad_pcb
    return PCB_Transformer(pcb=pcb, app=app), board


def test_apply_rectangular_board_shape_creates_board_only_footprint() -> None:
    transformer, board = _new_test_transformer(
        x_m=0.020, y_m=0.045, corner_radius_m=0.002
    )

    apply_rectangular_board_shape(transformer, board)

    board_fp = next(
        fp
        for fp in transformer.pcb.footprints
        if Property.get_property(fp.propertys, "Reference") == "BS1"
    )
    edge_geos = [
        geo
        for geo in get_all_geos(board_fp)
        if "Edge.Cuts" in kicad.geo.get_layers(geo)
    ]
    edge_points = [
        point
        for geo in edge_geos
        for point in (
            [geo.start, geo.end]
            if isinstance(geo, kicad.pcb.Line)
            else [geo.start, geo.mid, geo.end]
        )
    ]

    assert "board_only" in board_fp.attr
    assert board_fp.at.x == 0
    assert board_fp.at.y == 0
    assert len([geo for geo in edge_geos if isinstance(geo, kicad.pcb.Line)]) == 4
    assert len([geo for geo in edge_geos if isinstance(geo, kicad.pcb.Arc)]) == 4
    assert min(point.x for point in edge_points) == pytest.approx(-10.0)
    assert max(point.x for point in edge_points) == pytest.approx(10.0)
    assert min(point.y for point in edge_points) == pytest.approx(-22.5)
    assert max(point.y for point in edge_points) == pytest.approx(22.5)


def test_apply_rectangular_board_shape_rejects_foreign_outline() -> None:
    transformer, board = _new_test_transformer(x_m=0.020, y_m=0.045)
    transformer.insert_geo(
        kicad.pcb.Line(
            start=kicad.pcb.Xy(x=0, y=0),
            end=kicad.pcb.Xy(x=10, y=0),
            stroke=kicad.pcb.Stroke(width=0.05, type=kicad.pcb.E_stroke_type.SOLID),
            layer="Edge.Cuts",
            uuid=transformer.gen_uuid(mark=True),
            solder_mask_margin=None,
            fill=None,
            locked=None,
            layers=[],
        )
    )

    with pytest.raises(UserException, match="already contains Edge.Cuts geometry"):
        apply_rectangular_board_shape(transformer, board)


def test_apply_rectangular_board_shape_rejects_invalid_corner_radius() -> None:
    transformer, board = _new_test_transformer(
        x_m=0.020,
        y_m=0.045,
        corner_radius_m=0.020,
    )

    with pytest.raises(UserBadParameterError, match="corner_radius"):
        apply_rectangular_board_shape(transformer, board)
