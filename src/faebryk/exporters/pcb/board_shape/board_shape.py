# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserBadParameterError
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer, get_all_geos
from faebryk.libs.kicad.fileformats import kicad

logger = logging.getLogger(__name__)


def _get_rectangular_board_shapes(app: fabll.Node) -> list[F.RectangularBoardShape]:
    return list(
        app.get_children(
            types=F.RectangularBoardShape,
            direct_only=False,
            include_root=True,
        )
    )


def _extract_dimension_mm(
    shape: F.RectangularBoardShape,
    param_name: str,
    *,
    default_m: float | None = None,
) -> float:
    param = getattr(shape, param_name).get()
    value_m: float | None = None

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


def _build_corner_mounting_holes(
    transformer: PCB_Transformer,
    *,
    width_mm: float,
    height_mm: float,
    corner_radius_mm: float,
    hole_diameter_mm: float,
) -> list[kicad.pcb.Circle]:
    # Keep corner holes simple and deterministic:
    # place one hole per corner, inset by (corner_radius + hole_diameter).
    hole_radius_mm = hole_diameter_mm / 2.0
    edge_offset_mm = corner_radius_mm + hole_diameter_mm

    if width_mm <= (2.0 * edge_offset_mm) or height_mm <= (2.0 * edge_offset_mm):
        raise UserBadParameterError(
            "Board is too small for corner mounting holes with the configured "
            f"diameter ({hole_diameter_mm:.3f} mm)."
        )

    centers = [
        (edge_offset_mm, edge_offset_mm),
        (width_mm - edge_offset_mm, edge_offset_mm),
        (width_mm - edge_offset_mm, height_mm - edge_offset_mm),
        (edge_offset_mm, height_mm - edge_offset_mm),
    ]

    return [
        kicad.pcb.Circle(
            center=kicad.pcb.Xy(x=cx, y=cy),
            end=kicad.pcb.Xy(x=cx + hole_radius_mm, y=cy),
            stroke=kicad.pcb.Stroke(width=0.05, type=kicad.pcb.E_stroke_type.SOLID),
            layer="Edge.Cuts",
            uuid=transformer.gen_uuid(mark=True),
            solder_mask_margin=None,
            fill=None,
            locked=None,
            layers=[],
        )
        for cx, cy in centers
    ]


def _edge_cuts_line(
    transformer: PCB_Transformer, start: tuple[float, float], end: tuple[float, float]
) -> kicad.pcb.Line:
    return kicad.pcb.Line(
        start=kicad.pcb.Xy(x=start[0], y=start[1]),
        end=kicad.pcb.Xy(x=end[0], y=end[1]),
        stroke=kicad.pcb.Stroke(width=0.05, type=kicad.pcb.E_stroke_type.SOLID),
        layer="Edge.Cuts",
        uuid=transformer.gen_uuid(mark=True),
        solder_mask_margin=None,
        fill=None,
        locked=None,
        layers=[],
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
        stroke=kicad.pcb.Stroke(width=0.05, type=kicad.pcb.E_stroke_type.SOLID),
        layer="Edge.Cuts",
        uuid=transformer.gen_uuid(mark=True),
        solder_mask_margin=None,
        fill=None,
        locked=None,
        layers=[],
    )


def _build_rounded_rectangle_outline(
    transformer: PCB_Transformer,
    *,
    width_mm: float,
    height_mm: float,
    corner_radius_mm: float,
) -> list[kicad.pcb.Line | kicad.pcb.Arc]:
    r = corner_radius_mm
    half_sqrt2 = math.sqrt(2.0) / 2.0

    return [
        _edge_cuts_line(transformer, (r, 0.0), (width_mm - r, 0.0)),
        _edge_cuts_arc(
            transformer,
            start=(width_mm - r, 0.0),
            mid=(width_mm - r + (r * half_sqrt2), r - (r * half_sqrt2)),
            end=(width_mm, r),
        ),
        _edge_cuts_line(transformer, (width_mm, r), (width_mm, height_mm - r)),
        _edge_cuts_arc(
            transformer,
            start=(width_mm, height_mm - r),
            mid=(
                width_mm - r + (r * half_sqrt2),
                height_mm - r + (r * half_sqrt2),
            ),
            end=(width_mm - r, height_mm),
        ),
        _edge_cuts_line(transformer, (width_mm - r, height_mm), (r, height_mm)),
        _edge_cuts_arc(
            transformer,
            start=(r, height_mm),
            mid=(r - (r * half_sqrt2), height_mm - r + (r * half_sqrt2)),
            end=(0.0, height_mm - r),
        ),
        _edge_cuts_line(transformer, (0.0, height_mm - r), (0.0, r)),
        _edge_cuts_arc(
            transformer,
            start=(0.0, r),
            mid=(r - (r * half_sqrt2), r - (r * half_sqrt2)),
            end=(r, 0.0),
        ),
    ]


def _clear_edge_cuts(transformer: PCB_Transformer) -> None:
    for geo in list(get_all_geos(transformer.pcb)):
        if "Edge.Cuts" in kicad.geo.get_layers(geo):
            transformer.delete_geo(geo)


def apply_rectangular_board_shape(transformer: PCB_Transformer) -> None:
    shapes = _get_rectangular_board_shapes(transformer.app)
    if not shapes:
        return
    if len(shapes) > 1:
        raise UserBadParameterError(
            "Only one `RectangularBoardShape` is currently supported per design."
        )

    shape = shapes[0]
    width_mm = _extract_dimension_mm(shape, "width")
    height_mm = _extract_dimension_mm(shape, "height")
    corner_radius_mm = _extract_dimension_mm(shape, "corner_radius", default_m=0.0)
    hole_diameter_mm = _extract_dimension_mm(
        shape, "mounting_hole_diameter", default_m=0.0
    )

    if width_mm <= 0 or height_mm <= 0:
        raise UserBadParameterError("Board width and height must be greater than 0.")
    if corner_radius_mm < 0:
        raise UserBadParameterError("`corner_radius` must be >= 0.")
    if hole_diameter_mm < 0:
        raise UserBadParameterError("`mounting_hole_diameter` must be >= 0.")

    max_corner_radius_mm = min(width_mm, height_mm) / 2.0
    if corner_radius_mm > max_corner_radius_mm:
        raise UserBadParameterError(
            f"`corner_radius` ({corner_radius_mm:.3f} mm) exceeds half of the "
            f"smallest board dimension ({max_corner_radius_mm:.3f} mm)."
        )

    geometry = list(
        transformer.create_rectangular_edgecut(
            width_mm=width_mm,
            height_mm=height_mm,
            rounded_corners=False,
        )
    )
    if corner_radius_mm > 0:
        geometry = _build_rounded_rectangle_outline(
            transformer,
            width_mm=width_mm,
            height_mm=height_mm,
            corner_radius_mm=corner_radius_mm,
        )

    if hole_diameter_mm > 0:
        geometry.extend(
            _build_corner_mounting_holes(
                transformer,
                width_mm=width_mm,
                height_mm=height_mm,
                corner_radius_mm=corner_radius_mm,
                hole_diameter_mm=hole_diameter_mm,
            )
        )

    _clear_edge_cuts(transformer)
    for geo in geometry:
        transformer.insert_geo(geo)

    logger.info(
        "Applied RectangularBoardShape: %.3fmm x %.3fmm, corner radius %.3fmm, "
        "mounting hole diameter %.3fmm",
        width_mm,
        height_mm,
        corner_radius_mm,
        hole_diameter_mm,
    )
