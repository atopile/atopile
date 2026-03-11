# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math
from dataclasses import dataclass

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserBadParameterError, UserException
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer, get_all_geos
from faebryk.libs.kicad.fileformats import kicad

_BOARD_SHAPE_FOOTPRINT_NAME = "atopile:RectangularBoardShape"
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
    half_width = width_mm / 2.0
    half_height = height_mm / 2.0

    return [
        _edge_cuts_line(
            transformer, (-half_width, -half_height), (half_width, -half_height)
        ),
        _edge_cuts_line(
            transformer, (half_width, -half_height), (half_width, half_height)
        ),
        _edge_cuts_line(
            transformer, (half_width, half_height), (-half_width, half_height)
        ),
        _edge_cuts_line(
            transformer, (-half_width, half_height), (-half_width, -half_height)
        ),
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
    half_width = width_mm / 2.0
    half_height = height_mm / 2.0

    return [
        _edge_cuts_line(
            transformer,
            (-half_width + r, -half_height),
            (half_width - r, -half_height),
        ),
        _edge_cuts_arc(
            transformer,
            start=(half_width - r, -half_height),
            mid=(half_width - r + offset, -half_height + r - offset),
            end=(half_width, -half_height + r),
        ),
        _edge_cuts_line(
            transformer,
            (half_width, -half_height + r),
            (half_width, half_height - r),
        ),
        _edge_cuts_arc(
            transformer,
            start=(half_width, half_height - r),
            mid=(half_width - r + offset, half_height - r + offset),
            end=(half_width - r, half_height),
        ),
        _edge_cuts_line(
            transformer,
            (half_width - r, half_height),
            (-half_width + r, half_height),
        ),
        _edge_cuts_arc(
            transformer,
            start=(-half_width + r, half_height),
            mid=(-half_width + r - offset, half_height - r + offset),
            end=(-half_width, half_height - r),
        ),
        _edge_cuts_line(
            transformer,
            (-half_width, half_height - r),
            (-half_width, -half_height + r),
        ),
        _edge_cuts_arc(
            transformer,
            start=(-half_width, -half_height + r),
            mid=(-half_width + r - offset, -half_height + r - offset),
            end=(-half_width + r, -half_height),
        ),
    ]


def _build_board_shape_footprint(
    geometry: list[kicad.pcb.Line | kicad.pcb.Arc],
    transformer: PCB_Transformer,
) -> kicad.footprint.Footprint:
    return kicad.footprint.Footprint(
        name=_BOARD_SHAPE_FOOTPRINT_NAME,
        layer="F.Cu",
        uuid=transformer.gen_uuid(mark=True),
        path=None,
        propertys=[],
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


def _ensure_associated_footprint(
    shape: F.RectangularBoardShape,
) -> F.Footprints.has_associated_footprint:
    if associated := shape.try_get_trait(F.Footprints.has_associated_footprint):
        return associated

    return fabll.Traits.create_and_add_instance_to(
        node=shape, trait=F.Footprints.has_associated_footprint
    ).setup_from_pads_and_leads(component_node=shape, pads=[], leads=[])


def _footprint_has_edge_cuts(fp: kicad.pcb.Footprint) -> bool:
    return any(
        _EDGE_CUTS_LAYER in kicad.geo.get_layers(geo) for geo in get_all_geos(fp)
    )


def _check_for_foreign_outline(
    transformer: PCB_Transformer,
    owned_fp: kicad.pcb.Footprint | None,
) -> None:
    board_edge_cuts = [
        geo
        for geo in get_all_geos(transformer.pcb)
        if _EDGE_CUTS_LAYER in kicad.geo.get_layers(geo)
    ]
    footprint_edge_cuts = [
        fp
        for fp in transformer.pcb.footprints
        if (owned_fp is None or fp.uuid != owned_fp.uuid)
        and _footprint_has_edge_cuts(fp)
    ]
    if board_edge_cuts or footprint_edge_cuts:
        raise UserException(
            "Refusing to add RectangularBoardShape because the PCB already contains "
            "Edge.Cuts geometry not owned by this module. Remove the existing outline "
            "or migrate it first."
        )


def register_rectangular_board_shape_footprint(shape: F.RectangularBoardShape) -> None:
    board_shapes = F.RectangularBoardShape.bind_typegraph(shape.tg).get_instances(
        shape.g
    )
    if len(board_shapes) > 1:
        first_shape = min(
            board_shapes,
            key=lambda candidate: candidate.get_full_name(include_uuid=False),
        )
        if not shape.is_same(first_shape):
            return
        raise UserBadParameterError(
            "Only one RectangularBoardShape is currently supported per design. Found: "
            + ", ".join(
                f"`{candidate.get_full_name(include_uuid=False)}`"
                for candidate in board_shapes
            )
        )

    associated_fp = _ensure_associated_footprint(shape)
    footprint = associated_fp.get_footprint()
    synthetic_trait = footprint.try_get_trait(
        F.KiCadFootprints.can_generate_kicad_footprint
    )
    if synthetic_trait is not None:
        synthetic_trait.setup(
            generate_rectangular_board_shape_footprint,
            _BOARD_SHAPE_FOOTPRINT_NAME,
            reference=_BOARD_SHAPE_REFERENCE,
            value=_BOARD_SHAPE_VALUE,
            at=kicad.pcb.Xyr(x=0, y=0, r=0),
        )
    else:
        fabll.Traits.create_and_add_instance_to(
            node=footprint,
            trait=F.KiCadFootprints.can_generate_kicad_footprint,
        ).setup(
            generate_rectangular_board_shape_footprint,
            _BOARD_SHAPE_FOOTPRINT_NAME,
            reference=_BOARD_SHAPE_REFERENCE,
            value=_BOARD_SHAPE_VALUE,
            at=kicad.pcb.Xyr(x=0, y=0, r=0),
        )


def generate_rectangular_board_shape_footprint(
    component: fabll.Node, transformer: PCB_Transformer
) -> kicad.footprint.Footprint:
    shape = F.RectangularBoardShape.bind_instance(component.instance)
    spec = _read_shape_spec(shape)

    owned_fp = None
    if shape.has_trait(F.Footprints.has_associated_footprint):
        fp = shape.get_trait(F.Footprints.has_associated_footprint).get_footprint()
        if existing := fp.try_get_trait(
            F.KiCadFootprints.has_associated_kicad_pcb_footprint
        ):
            owned_fp = existing.get_footprint()

    _check_for_foreign_outline(transformer, owned_fp)

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
    return _build_board_shape_footprint(list(geometry), transformer)
