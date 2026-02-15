# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserBadParameterError
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer, get_all_geos
from faebryk.libs.kicad.fileformats import Property, kicad

logger = logging.getLogger(__name__)

_BOARD_SHAPE_FOOTPRINT_NAME = "atopile:RectangularBoardShape"
_BOARD_SHAPE_KIND_PROPERTY = "atopile_kind"
_BOARD_SHAPE_KIND_VALUE = "RectangularBoardShape"

_EDGE_CUTS_LAYER = "Edge.Cuts"
_EDGE_CUTS_STROKE_WIDTH = 0.05
_HALF_SQRT2 = math.sqrt(2.0) / 2.0

EdgeCutGeometry = kicad.pcb.Line | kicad.pcb.Arc | kicad.pcb.Circle


@dataclass(frozen=True, slots=True)
class _RectangularBoardShapeSpec:
    width_mm: float
    height_mm: float
    corner_radius_mm: float
    hole_diameter_mm: float


def _extract_dimension_mm(
    shape: F.RectangularBoardShape,
    param_name: str,
    *,
    default_m: float | None = None,
) -> float:
    param = getattr(shape, param_name).get()

    # In ato, direct assignments usually constrain the superset literal.
    # Prefer reading the singleton from superset first, then subset.
    superset = param.try_extract_superset()
    if superset is not None and superset.is_singleton():
        value_m = superset.get_single()
    else:
        value_m = param.try_extract_singleton()

    if value_m is None:
        if default_m is None:
            raise UserBadParameterError(
                f"`{shape.get_full_name()}.{param_name}` must be set to a single value."
            )
        value_m = default_m

    return value_m * 1_000.0


def _read_shape_spec(shape: F.RectangularBoardShape) -> _RectangularBoardShapeSpec:
    spec = _RectangularBoardShapeSpec(
        width_mm=_extract_dimension_mm(shape, "width"),
        height_mm=_extract_dimension_mm(shape, "height"),
        corner_radius_mm=_extract_dimension_mm(shape, "corner_radius", default_m=0.0),
        hole_diameter_mm=_extract_dimension_mm(
            shape, "mounting_hole_diameter", default_m=0.0
        ),
    )
    _validate_shape(spec)
    return spec


def _validate_shape(spec: _RectangularBoardShapeSpec) -> None:
    if spec.width_mm <= 0 or spec.height_mm <= 0:
        raise UserBadParameterError("Board width and height must be greater than 0.")
    if spec.corner_radius_mm < 0:
        raise UserBadParameterError("`corner_radius` must be >= 0.")
    if spec.hole_diameter_mm < 0:
        raise UserBadParameterError("`mounting_hole_diameter` must be >= 0.")

    max_corner_radius_mm = min(spec.width_mm, spec.height_mm) / 2.0
    if spec.corner_radius_mm > max_corner_radius_mm:
        raise UserBadParameterError(
            f"`corner_radius` ({spec.corner_radius_mm:.3f} mm) exceeds half of the "
            f"smallest board dimension ({max_corner_radius_mm:.3f} mm)."
        )


def _edge_cuts_kwargs(transformer: PCB_Transformer) -> dict:
    return {
        "stroke": kicad.pcb.Stroke(
            width=_EDGE_CUTS_STROKE_WIDTH,
            type=kicad.pcb.E_stroke_type.SOLID,
        ),
        "layer": _EDGE_CUTS_LAYER,
        "uuid": transformer.gen_uuid(mark=True),
        "solder_mask_margin": None,
        "fill": None,
        "locked": None,
        "layers": [],
    }


def _edge_cuts_line(
    transformer: PCB_Transformer, start: tuple[float, float], end: tuple[float, float]
) -> kicad.pcb.Line:
    return kicad.pcb.Line(
        start=kicad.pcb.Xy(x=start[0], y=start[1]),
        end=kicad.pcb.Xy(x=end[0], y=end[1]),
        **_edge_cuts_kwargs(transformer),
    )


def _edge_cuts_arc(
    transformer: PCB_Transformer,
    *,
    start: tuple[float, float],
    mid: tuple[float, float],
    end: tuple[float, float],
) -> kicad.pcb.Arc:
    return kicad.pcb.Arc(
        start=kicad.pcb.Xy(x=start[0], y=start[1]),
        mid=kicad.pcb.Xy(x=mid[0], y=mid[1]),
        end=kicad.pcb.Xy(x=end[0], y=end[1]),
        **_edge_cuts_kwargs(transformer),
    )


def _edge_cuts_circle(
    transformer: PCB_Transformer, center: tuple[float, float], radius_mm: float
) -> kicad.pcb.Circle:
    cx, cy = center
    return kicad.pcb.Circle(
        center=kicad.pcb.Xy(x=cx, y=cy),
        end=kicad.pcb.Xy(x=cx + radius_mm, y=cy),
        **_edge_cuts_kwargs(transformer),
    )


def _build_rectangular_outline(
    transformer: PCB_Transformer, spec: _RectangularBoardShapeSpec
) -> list[kicad.pcb.Line]:
    w, h = spec.width_mm, spec.height_mm
    return [
        _edge_cuts_line(transformer, (0.0, 0.0), (w, 0.0)),
        _edge_cuts_line(transformer, (w, 0.0), (w, h)),
        _edge_cuts_line(transformer, (w, h), (0.0, h)),
        _edge_cuts_line(transformer, (0.0, h), (0.0, 0.0)),
    ]


def _build_rounded_rectangle_outline(
    transformer: PCB_Transformer, spec: _RectangularBoardShapeSpec
) -> list[kicad.pcb.Line | kicad.pcb.Arc]:
    w, h, r = spec.width_mm, spec.height_mm, spec.corner_radius_mm
    offset = r * _HALF_SQRT2

    return [
        _edge_cuts_line(transformer, (r, 0.0), (w - r, 0.0)),
        _edge_cuts_arc(
            transformer,
            start=(w - r, 0.0),
            mid=(w - r + offset, r - offset),
            end=(w, r),
        ),
        _edge_cuts_line(transformer, (w, r), (w, h - r)),
        _edge_cuts_arc(
            transformer,
            start=(w, h - r),
            mid=(w - r + offset, h - r + offset),
            end=(w - r, h),
        ),
        _edge_cuts_line(transformer, (w - r, h), (r, h)),
        _edge_cuts_arc(
            transformer,
            start=(r, h),
            mid=(r - offset, h - r + offset),
            end=(0.0, h - r),
        ),
        _edge_cuts_line(transformer, (0.0, h - r), (0.0, r)),
        _edge_cuts_arc(
            transformer,
            start=(0.0, r),
            mid=(r - offset, r - offset),
            end=(r, 0.0),
        ),
    ]


def _build_corner_mounting_holes(
    transformer: PCB_Transformer, spec: _RectangularBoardShapeSpec
) -> list[kicad.pcb.Circle]:
    # Place one hole per corner, inset by (corner_radius + hole_diameter).
    hole_radius_mm = spec.hole_diameter_mm / 2.0
    edge_offset_mm = spec.corner_radius_mm + spec.hole_diameter_mm

    if spec.width_mm <= (2.0 * edge_offset_mm) or spec.height_mm <= (
        2.0 * edge_offset_mm
    ):
        raise UserBadParameterError(
            "Board is too small for corner mounting holes with the configured "
            f"diameter ({spec.hole_diameter_mm:.3f} mm)."
        )

    centers = [
        (edge_offset_mm, edge_offset_mm),
        (spec.width_mm - edge_offset_mm, edge_offset_mm),
        (spec.width_mm - edge_offset_mm, spec.height_mm - edge_offset_mm),
        (edge_offset_mm, spec.height_mm - edge_offset_mm),
    ]

    return [
        _edge_cuts_circle(transformer, center=center, radius_mm=hole_radius_mm)
        for center in centers
    ]


def _clear_edge_cuts(transformer: PCB_Transformer) -> None:
    for geo in list(get_all_geos(transformer.pcb)):
        if _EDGE_CUTS_LAYER in kicad.geo.get_layers(geo):
            transformer.delete_geo(geo)


def _is_board_shape_footprint(fp: kicad.pcb.Footprint) -> bool:
    return (
        Property.try_get_property(fp.propertys, _BOARD_SHAPE_KIND_PROPERTY)
        == _BOARD_SHAPE_KIND_VALUE
    ) or fp.name == _BOARD_SHAPE_FOOTPRINT_NAME


def _clear_board_shape_footprints(transformer: PCB_Transformer) -> None:
    for fp in list(transformer.pcb.footprints):
        if _is_board_shape_footprint(fp):
            transformer.remove_footprint(fp)


def _clear_existing_board_shape_artifacts(transformer: PCB_Transformer) -> None:
    _clear_edge_cuts(transformer)
    _clear_board_shape_footprints(transformer)


def _make_property(name: str, value: str) -> kicad.pcb.Property:
    return kicad.pcb.Property(
        name=name,
        value=value,
        at=kicad.pcb.Xyr(x=0, y=0, r=0),
        layer="User.9",
        uuid=PCB_Transformer.gen_uuid(mark=True),
        unlocked=None,
        hide=True,
        effects=None,
    )


def _build_board_shape_footprint(
    shape: F.RectangularBoardShape,
    geometry: list[EdgeCutGeometry],
) -> kicad.pcb.Footprint:
    shape_address = shape.get_full_name(include_uuid=False)
    properties = [
        ("Reference", "BS1"),
        ("Value", _BOARD_SHAPE_KIND_VALUE),
        ("atopile_address", shape_address),
        (_BOARD_SHAPE_KIND_PROPERTY, _BOARD_SHAPE_KIND_VALUE),
    ]
    return kicad.pcb.Footprint(
        name=_BOARD_SHAPE_FOOTPRINT_NAME,
        layer="F.Cu",
        uuid=PCB_Transformer.gen_uuid(mark=True),
        at=kicad.pcb.Xyr(x=0, y=0, r=0),
        path=None,
        propertys=[_make_property(name, value) for name, value in properties],
        attr=["board_only", "exclude_from_pos_files", "exclude_from_bom"],
        fp_lines=[geo for geo in geometry if isinstance(geo, kicad.pcb.Line)],
        fp_arcs=[geo for geo in geometry if isinstance(geo, kicad.pcb.Arc)],
        fp_circles=[geo for geo in geometry if isinstance(geo, kicad.pcb.Circle)],
        fp_rects=[],
        fp_poly=[],
        fp_texts=[],
        pads=[],
        embedded_fonts=None,
        models=[],
    )


def _ensure_associated_footprint(
    shape: F.RectangularBoardShape,
) -> F.Footprints.has_associated_footprint:
    if associated := shape.try_get_trait(F.Footprints.has_associated_footprint):
        return associated

    if not shape.has_trait(F.Footprints.can_attach_to_footprint):
        raise UserBadParameterError(
            f"`{shape.get_full_name()}` must support attaching to a footprint."
        )

    fp_node = fabll.Node.bind_typegraph_from_instance(shape.instance).create_instance(
        g=shape.instance.g()
    )
    fp_trait = fabll.Traits.create_and_add_instance_to(
        node=fp_node, trait=F.Footprints.is_footprint
    )
    return fabll.Traits.create_and_add_instance_to(
        node=shape, trait=F.Footprints.has_associated_footprint
    ).setup(fp_trait)


def _insert_and_bind_board_shape_footprint(
    transformer: PCB_Transformer,
    shape: F.RectangularBoardShape,
    geometry: list[EdgeCutGeometry],
) -> None:
    footprint = _build_board_shape_footprint(shape, geometry)
    pcb_fp = kicad.insert(
        transformer.pcb,
        "footprints",
        transformer.pcb.footprints,
        footprint,
    )

    graph_fp = _ensure_associated_footprint(shape).get_footprint()
    if kicad_fp_trait := graph_fp.try_get_trait(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint
    ):
        kicad_fp_trait.setup(pcb_fp, transformer)
    else:
        transformer.bind_footprint(pcb_fp, shape)


def apply_rectangular_board_shape(
    transformer: PCB_Transformer,
    shape: F.RectangularBoardShape,
) -> None:
    spec = _read_shape_spec(shape)
    geometry: list[EdgeCutGeometry] = (
        _build_rounded_rectangle_outline(transformer, spec)
        if spec.corner_radius_mm > 0
        else _build_rectangular_outline(transformer, spec)
    )

    if spec.hole_diameter_mm > 0:
        geometry.extend(_build_corner_mounting_holes(transformer, spec))

    _clear_existing_board_shape_artifacts(transformer)
    _insert_and_bind_board_shape_footprint(transformer, shape, geometry)

    logger.info(
        "Applied RectangularBoardShape footprint: %.3fmm x %.3fmm, "
        "corner radius %.3fmm, mounting hole diameter %.3fmm",
        spec.width_mm,
        spec.height_mm,
        spec.corner_radius_mm,
        spec.hole_diameter_mm,
    )


# --------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------


class _TestBoardShapeApp(fabll.Node):
    board = F.RectangularBoardShape.MakeChild()


def _new_test_transformer(
    *,
    width_m: float,
    height_m: float,
    corner_radius_m: float = 0.0,
    mounting_hole_diameter_m: float | None = None,
) -> PCB_Transformer:
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph
    from faebryk.libs.test.fileformats import PCBFILE

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = _TestBoardShapeApp.bind_typegraph(tg=tg).create_instance(g=g)

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


def _get_board_shape_edge_geometries(
    transformer: PCB_Transformer,
) -> list[kicad.pcb.Line | kicad.pcb.Arc | kicad.pcb.Circle]:
    board_shape = transformer.app.board.get()
    board_shape_fp = (
        board_shape.get_trait(F.Footprints.has_associated_footprint)
        .get_footprint()
        .get_trait(F.KiCadFootprints.has_associated_kicad_pcb_footprint)
        .get_footprint()
    )
    return [
        geo
        for geo in get_all_geos(board_shape_fp)
        if _EDGE_CUTS_LAYER in kicad.geo.get_layers(geo)
    ]


def test_apply_rectangular_board_shape_creates_rectangular_outline() -> None:
    transformer = _new_test_transformer(width_m=0.020, height_m=0.030)
    apply_rectangular_board_shape(transformer, shape=transformer.app.board.get())

    edge_geos = _get_board_shape_edge_geometries(transformer)
    lines = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Line)]
    arcs = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Arc)]
    circles = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Circle)]

    assert len(lines) == 4
    assert not arcs
    assert not circles


def test_board_shape_trait_dispatch_applies_rounded_outline_and_holes() -> None:
    import pytest

    transformer = _new_test_transformer(
        width_m=0.020,
        height_m=0.030,
        corner_radius_m=0.003,
        mounting_hole_diameter_m=0.0033,
    )

    transformer.app.board.get().get_trait(F.implements_board_shape).apply(transformer)

    edge_geos = _get_board_shape_edge_geometries(transformer)
    arcs = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Arc)]
    circles = [geo for geo in edge_geos if isinstance(geo, kicad.pcb.Circle)]

    assert len(arcs) == 4
    assert len(circles) == 4
    assert circles[0].end.x - circles[0].center.x == pytest.approx(1.65, abs=1e-3)


def test_rejects_corner_radius_larger_than_half_dimension() -> None:
    import pytest

    transformer = _new_test_transformer(
        width_m=0.020,
        height_m=0.030,
        corner_radius_m=0.011,
    )

    with pytest.raises(UserBadParameterError, match="corner_radius"):
        apply_rectangular_board_shape(transformer, shape=transformer.app.board.get())
