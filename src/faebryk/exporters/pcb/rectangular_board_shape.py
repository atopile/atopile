# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math
from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserBadParameterError, UserException
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer, get_all_geos
from faebryk.libs.kicad.fileformats import Property, kicad

_BOARD_SHAPE_FOOTPRINT_NAME = "atopile:RectangularBoardShape"
_BOARD_SHAPE_KIND_PROPERTY = "atopile_kind"
_BOARD_SHAPE_KIND_VALUE = "RectangularBoardShape"
_BOARD_SHAPE_REFERENCE = "BS1"
_BOARD_SHAPE_VALUE = "RectangularBoardShape"
_EDGE_CUTS_LAYER = "Edge.Cuts"
_EDGE_CUTS_STROKE_WIDTH = 0.05
_HALF_SQRT2 = math.sqrt(2.0) / 2.0


@dataclass(frozen=True, slots=True)
class _RectangularBoardShapeSpec:
    x_mm: float
    y_mm: float
    corner_radius_mm: float


def _extract_dimension_mm(
    shape: F.RectangularBoardShape,
    param_name: str,
    *,
    default_m: float | None = None,
) -> float:
    param = getattr(shape, param_name).get()

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
        x_mm=_extract_dimension_mm(shape, "x"),
        y_mm=_extract_dimension_mm(shape, "y"),
        corner_radius_mm=_extract_dimension_mm(shape, "corner_radius", default_m=0.0),
    )
    _validate_spec(spec)
    return spec


def _validate_spec(spec: _RectangularBoardShapeSpec) -> None:
    if spec.x_mm <= 0 or spec.y_mm <= 0:
        raise UserBadParameterError("Board x and y must be greater than 0.")
    if spec.corner_radius_mm < 0:
        raise UserBadParameterError("`corner_radius` must be >= 0.")

    max_corner_radius_mm = min(spec.x_mm, spec.y_mm) / 2.0
    if spec.corner_radius_mm > max_corner_radius_mm:
        raise UserBadParameterError(
            f"`corner_radius` ({spec.corner_radius_mm:.3f} mm) exceeds half of the "
            f"smallest board dimension ({max_corner_radius_mm:.3f} mm)."
        )


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


def _build_rectangular_outline(
    transformer: PCB_Transformer,
    *,
    width_mm: float,
    height_mm: float,
) -> list[kicad.pcb.Line]:
    return [
        _edge_cuts_line(transformer, (0.0, 0.0), (width_mm, 0.0)),
        _edge_cuts_line(transformer, (width_mm, 0.0), (width_mm, height_mm)),
        _edge_cuts_line(transformer, (width_mm, height_mm), (0.0, height_mm)),
        _edge_cuts_line(transformer, (0.0, height_mm), (0.0, 0.0)),
    ]


def _build_rounded_rectangular_outline(
    transformer: PCB_Transformer,
    *,
    width_mm: float,
    height_mm: float,
    corner_radius_mm: float,
) -> list[kicad.pcb.Line | kicad.pcb.Arc]:
    r = corner_radius_mm
    offset = r * _HALF_SQRT2

    return [
        _edge_cuts_line(transformer, (r, 0.0), (width_mm - r, 0.0)),
        _edge_cuts_arc(
            transformer,
            start=(width_mm - r, 0.0),
            mid=(width_mm - r + offset, r - offset),
            end=(width_mm, r),
        ),
        _edge_cuts_line(transformer, (width_mm, r), (width_mm, height_mm - r)),
        _edge_cuts_arc(
            transformer,
            start=(width_mm, height_mm - r),
            mid=(width_mm - r + offset, height_mm - r + offset),
            end=(width_mm - r, height_mm),
        ),
        _edge_cuts_line(transformer, (width_mm - r, height_mm), (r, height_mm)),
        _edge_cuts_arc(
            transformer,
            start=(r, height_mm),
            mid=(r - offset, height_mm - r + offset),
            end=(0.0, height_mm - r),
        ),
        _edge_cuts_line(transformer, (0.0, height_mm - r), (0.0, r)),
        _edge_cuts_arc(
            transformer,
            start=(0.0, r),
            mid=(r - offset, r - offset),
            end=(r, 0.0),
        ),
    ]


def _build_board_shape_footprint(
    shape: F.RectangularBoardShape,
    geometry: list[kicad.pcb.Line | kicad.pcb.Arc],
) -> kicad.pcb.Footprint:
    properties = [
        ("Reference", _BOARD_SHAPE_REFERENCE),
        ("Value", _BOARD_SHAPE_VALUE),
        ("atopile_address", shape.get_full_name(include_uuid=False)),
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
        fp_circles=[],
        fp_rects=[],
        fp_poly=[],
        fp_texts=[],
        pads=[],
        embedded_fonts=None,
        models=[],
    )


def _is_board_shape_footprint(fp: kicad.pcb.Footprint) -> bool:
    return (
        Property.try_get_property(fp.propertys, _BOARD_SHAPE_KIND_PROPERTY)
        == _BOARD_SHAPE_KIND_VALUE
    )


def _ensure_associated_footprint(
    shape: F.RectangularBoardShape,
) -> F.Footprints.has_associated_footprint:
    if associated := shape.try_get_trait(F.Footprints.has_associated_footprint):
        return associated

    fp_node = fabll.Node.bind_typegraph_from_instance(shape.instance).create_instance(
        g=shape.instance.g()
    )
    fp_trait = fabll.Traits.create_and_add_instance_to(
        node=fp_node, trait=F.Footprints.is_footprint
    )
    return fabll.Traits.create_and_add_instance_to(
        node=shape, trait=F.Footprints.has_associated_footprint
    ).setup(fp_trait)


def _footprint_has_edge_cuts(fp: kicad.pcb.Footprint) -> bool:
    return any(
        _EDGE_CUTS_LAYER in kicad.geo.get_layers(geo) for geo in get_all_geos(fp)
    )


def _check_for_foreign_outline(transformer: PCB_Transformer) -> None:
    existing_shape_fps = [
        fp for fp in transformer.pcb.footprints if _is_board_shape_footprint(fp)
    ]
    if existing_shape_fps:
        return

    board_edge_cuts = [
        geo
        for geo in get_all_geos(transformer.pcb)
        if _EDGE_CUTS_LAYER in kicad.geo.get_layers(geo)
    ]
    footprint_edge_cuts = [
        fp
        for fp in transformer.pcb.footprints
        if not _is_board_shape_footprint(fp) and _footprint_has_edge_cuts(fp)
    ]
    if board_edge_cuts or footprint_edge_cuts:
        raise UserException(
            "Refusing to add RectangularBoardShape because the PCB already contains "
            "Edge.Cuts geometry not owned by this module. Remove the existing outline "
            "or migrate it first."
        )


def _bind_inserted_footprint(
    transformer: PCB_Transformer,
    shape: F.RectangularBoardShape,
    pcb_fp: kicad.pcb.Footprint,
) -> None:
    graph_fp = _ensure_associated_footprint(shape).get_footprint()
    if existing := graph_fp.try_get_trait(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint
    ):
        existing.setup(pcb_fp, transformer)
    else:
        transformer.bind_footprint(pcb_fp, shape)


def apply_rectangular_board_shape(
    transformer: PCB_Transformer, shape: F.RectangularBoardShape
) -> None:
    spec = _read_shape_spec(shape)
    _check_for_foreign_outline(transformer)

    for existing in list(transformer.pcb.footprints):
        if _is_board_shape_footprint(existing):
            transformer.remove_footprint(existing)

    geometry = (
        _build_rounded_rectangular_outline(
            transformer,
            width_mm=spec.x_mm,
            height_mm=spec.y_mm,
            corner_radius_mm=spec.corner_radius_mm,
        )
        if spec.corner_radius_mm > 0
        else _build_rectangular_outline(
            transformer,
            width_mm=spec.x_mm,
            height_mm=spec.y_mm,
        )
    )
    pcb_fp = kicad.insert(
        transformer.pcb,
        "footprints",
        transformer.pcb.footprints,
        _build_board_shape_footprint(shape, list(geometry)),
    )
    _bind_inserted_footprint(transformer, shape, pcb_fp)


def apply_board_shapes(app: fabll.Node, transformer: PCB_Transformer) -> None:
    board_shapes = app.get_children(
        direct_only=False,
        include_root=True,
        types=F.RectangularBoardShape,
    )
    if len(board_shapes) > 1:
        raise UserBadParameterError(
            "Only one RectangularBoardShape is currently supported per design. Found: "
            + ", ".join(
                f"`{shape.get_full_name(include_uuid=False)}`" for shape in board_shapes
            )
        )
    if board_shapes:
        apply_rectangular_board_shape(transformer, board_shapes[0])
