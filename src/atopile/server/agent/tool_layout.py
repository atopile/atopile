"""Layout component lookup and placement helpers for agent tools."""

from __future__ import annotations

import difflib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atopile.config import ProjectConfig
from atopile.server.path_utils import resolve_layout_path


def _resolve_build_target(project_root: Path, build_target: str) -> Any:
    project_cfg = ProjectConfig.from_path(project_root)
    if project_cfg is None:
        raise ValueError(f"No ato.yaml found in: {project_root}")
    build_cfg = project_cfg.builds.get(build_target)
    if build_cfg is None:
        known = ", ".join(sorted(project_cfg.builds.keys()))
        raise ValueError(f"Unknown build target '{build_target}'. Available: {known}")
    return build_cfg

def _rotate_xy(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)


def _footprint_reference(footprint: Any) -> str:
    from faebryk.libs.kicad.fileformats import Property

    reference = Property.try_get_property(
        getattr(footprint, "propertys", None),
        "Reference",
    )
    if isinstance(reference, str) and reference.strip():
        return reference.strip()
    return ""


def _footprint_bbox_mm(footprint: Any) -> tuple[float, float, float, float] | None:
    fp_at = getattr(footprint, "at", None)
    pads = getattr(footprint, "pads", None)
    if fp_at is None or pads is None:
        return None

    fp_x = float(getattr(fp_at, "x", 0.0) or 0.0)
    fp_y = float(getattr(fp_at, "y", 0.0) or 0.0)
    fp_r = float(getattr(fp_at, "r", 0.0) or 0.0)

    points: list[tuple[float, float]] = []
    for pad in pads:
        pad_at = getattr(pad, "at", None)
        pad_size = getattr(pad, "size", None)
        if pad_at is None or pad_size is None:
            continue

        width = float(getattr(pad_size, "w", 0.0) or 0.0)
        height = float(getattr(pad_size, "h", width) or width)
        if width <= 0 or height <= 0:
            continue

        rel_x = float(getattr(pad_at, "x", 0.0) or 0.0)
        rel_y = float(getattr(pad_at, "y", 0.0) or 0.0)
        rel_r = float(getattr(pad_at, "r", 0.0) or 0.0)

        dx, dy = _rotate_xy(rel_x, rel_y, fp_r)
        center_x = fp_x + dx
        center_y = fp_y + dy
        absolute_rotation = fp_r + rel_r

        half_w = width / 2.0
        half_h = height / 2.0
        for offset_x, offset_y in (
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h),
        ):
            rx, ry = _rotate_xy(offset_x, offset_y, absolute_rotation)
            points.append((center_x + rx, center_y + ry))

    if not points:
        # Fallback when footprint has no pads in the layout object.
        return (fp_x - 0.1, fp_y - 0.1, fp_x + 0.1, fp_y + 0.1)

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_overlap_details(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> dict[str, float] | None:
    overlap_x = min(first[2], second[2]) - max(first[0], second[0])
    overlap_y = min(first[3], second[3]) - max(first[1], second[1])
    if overlap_x <= 0 or overlap_y <= 0:
        return None

    return {
        "overlap_dx_mm": overlap_x,
        "overlap_dy_mm": overlap_y,
        "overlap_area_mm2": overlap_x * overlap_y,
    }


def _extract_edge_cuts_points(kicad_pcb: Any) -> list[tuple[float, float]]:
    from faebryk.libs.kicad.fileformats import kicad

    points: list[tuple[float, float]] = []

    def is_edge_cuts(geo: Any) -> bool:
        layers = kicad.geo.get_layers(geo)
        return "Edge.Cuts" in layers

    def append_xy(coord: Any) -> None:
        points.append(
            (
                float(getattr(coord, "x", 0.0)),
                float(getattr(coord, "y", 0.0)),
            )
        )

    for line in getattr(kicad_pcb, "gr_lines", []) or []:
        if is_edge_cuts(line):
            append_xy(line.start)
            append_xy(line.end)
    for arc in getattr(kicad_pcb, "gr_arcs", []) or []:
        if is_edge_cuts(arc):
            append_xy(arc.start)
            append_xy(arc.mid)
            append_xy(arc.end)
    for rect in getattr(kicad_pcb, "gr_rects", []) or []:
        if is_edge_cuts(rect):
            append_xy(rect.start)
            append_xy(rect.end)
    for circle in getattr(kicad_pcb, "gr_circles", []) or []:
        if not is_edge_cuts(circle):
            continue
        cx = float(circle.center.x)
        cy = float(circle.center.y)
        radius = (
            (float(circle.end.x) - cx) ** 2 + (float(circle.end.y) - cy) ** 2
        ) ** 0.5
        points.extend(
            [
                (cx - radius, cy),
                (cx + radius, cy),
                (cx, cy - radius),
                (cx, cy + radius),
            ]
        )

    for footprint in getattr(kicad_pcb, "footprints", []) or []:
        fp_at = getattr(footprint, "at", None)
        fp_x = float(getattr(fp_at, "x", 0.0) or 0.0)
        fp_y = float(getattr(fp_at, "y", 0.0) or 0.0)
        fp_r = float(getattr(fp_at, "r", 0.0) or 0.0)

        def transform_local(coord: Any) -> tuple[float, float]:
            local_x = float(getattr(coord, "x", 0.0) or 0.0)
            local_y = float(getattr(coord, "y", 0.0) or 0.0)
            dx, dy = _rotate_xy(local_x, local_y, fp_r)
            return (fp_x + dx, fp_y + dy)

        for line in getattr(footprint, "fp_lines", []) or []:
            if is_edge_cuts(line):
                points.append(transform_local(line.start))
                points.append(transform_local(line.end))
        for arc in getattr(footprint, "fp_arcs", []) or []:
            if is_edge_cuts(arc):
                points.append(transform_local(arc.start))
                points.append(transform_local(arc.mid))
                points.append(transform_local(arc.end))

    return points


def _analyze_layout_component_placement(
    *,
    pcb_file: Any,
    moved_record: _LayoutComponentRecord,
    all_records: list[_LayoutComponentRecord],
) -> dict[str, Any]:
    moved_bbox = _footprint_bbox_mm(moved_record.footprint)
    result: dict[str, Any] = {
        "checked": moved_bbox is not None,
        "reference": moved_record.reference or None,
        "atopile_address": moved_record.atopile_address,
        "component_bbox_mm": None,
        "board_bbox_mm": None,
        "board_outline_available": False,
        "on_board": None,
        "outside_board_area_mm2": None,
        "collision_count": 0,
        "collisions": [],
    }
    if moved_bbox is None:
        return result

    result["component_bbox_mm"] = {
        "min_x": round(moved_bbox[0], 4),
        "min_y": round(moved_bbox[1], 4),
        "max_x": round(moved_bbox[2], 4),
        "max_y": round(moved_bbox[3], 4),
    }

    collisions: list[dict[str, Any]] = []
    for record in all_records:
        if record.footprint is moved_record.footprint:
            continue
        if (
            record.reference
            and moved_record.reference
            and record.reference == moved_record.reference
        ):
            continue

        other_bbox = _footprint_bbox_mm(record.footprint)
        if other_bbox is None:
            continue
        overlap = _bbox_overlap_details(moved_bbox, other_bbox)
        if overlap is None:
            continue

        collisions.append(
            {
                "reference": record.reference or None,
                "atopile_address": record.atopile_address,
                "overlap_dx_mm": round(overlap["overlap_dx_mm"], 4),
                "overlap_dy_mm": round(overlap["overlap_dy_mm"], 4),
                "overlap_area_mm2": round(overlap["overlap_area_mm2"], 4),
            }
        )

    collisions.sort(key=lambda item: item.get("overlap_area_mm2", 0.0), reverse=True)
    result["collisions"] = collisions
    result["collision_count"] = len(collisions)

    kicad_pcb = getattr(pcb_file, "kicad_pcb", None)
    if kicad_pcb is None:
        return result

    edge_points = _extract_edge_cuts_points(kicad_pcb)
    if not edge_points:
        return result

    min_x = min(point[0] for point in edge_points)
    min_y = min(point[1] for point in edge_points)
    max_x = max(point[0] for point in edge_points)
    max_y = max(point[1] for point in edge_points)
    result["board_outline_available"] = True
    result["board_bbox_mm"] = {
        "min_x": round(min_x, 4),
        "min_y": round(min_y, 4),
        "max_x": round(max_x, 4),
        "max_y": round(max_y, 4),
    }

    within_bbox = (
        moved_bbox[0] >= min_x
        and moved_bbox[1] >= min_y
        and moved_bbox[2] <= max_x
        and moved_bbox[3] <= max_y
    )

    outside_area_mm2: float | None = None
    try:
        from shapely.geometry import MultiPoint, box

        hull = MultiPoint(edge_points).convex_hull
        footprint_box = box(*moved_bbox)
        if not hull.is_empty and hull.geom_type in {"Polygon", "MultiPolygon"}:
            covered = bool(hull.buffer(1e-6).covers(footprint_box))
            outside_area_mm2 = float(footprint_box.difference(hull).area)
            result["on_board"] = covered
        else:
            result["on_board"] = within_bbox
    except Exception:
        result["on_board"] = within_bbox

    if outside_area_mm2 is None:
        footprint_area = max(
            0.0,
            (moved_bbox[2] - moved_bbox[0]) * (moved_bbox[3] - moved_bbox[1]),
        )
        if result["on_board"] is False:
            outside_area_mm2 = footprint_area
        else:
            outside_area_mm2 = 0.0

    result["outside_board_area_mm2"] = round(float(outside_area_mm2), 4)
    return result


def _resolve_highlight_components(
    *,
    layout_path: Path,
    queries: list[str],
    fuzzy_limit: int,
) -> tuple[list[_LayoutComponentRecord], list[dict[str, Any]]]:
    if not queries:
        return [], []

    _, records = _load_layout_component_index(layout_path)
    resolved: list[_LayoutComponentRecord] = []
    unresolved: list[dict[str, Any]] = []
    seen_refs: set[str] = set()

    for query in queries:
        lookup = _lookup_layout_component(
            records=records,
            query=query,
            fuzzy_limit=fuzzy_limit,
        )
        if not lookup.found or lookup.record is None:
            unresolved.append(
                {
                    "query": query,
                    "message": lookup.message,
                    "suggestions": lookup.suggestions,
                }
            )
            continue

        reference_key = lookup.record.reference_norm or lookup.record.address_norm
        if reference_key and reference_key in seen_refs:
            continue
        if reference_key:
            seen_refs.add(reference_key)
        resolved.append(lookup.record)

    return resolved, unresolved

@dataclass
class _LayoutComponentRecord:
    reference: str
    atopile_address: str | None
    layer: str
    x_mm: float
    y_mm: float
    rotation_deg: float
    footprint: Any

    @property
    def reference_norm(self) -> str:
        return _normalize_component_lookup_token(self.reference)

    @property
    def address_norm(self) -> str:
        return _normalize_component_lookup_token(self.atopile_address or "")

    @property
    def address_tail_norm(self) -> str:
        return _extract_component_address_tail(self.atopile_address or "")


@dataclass
class _LayoutComponentLookup:
    found: bool
    matched_by: str | None
    record: _LayoutComponentRecord | None
    message: str
    suggestions: list[dict[str, Any]]


def _normalize_component_lookup_token(value: str) -> str:
    return str(value or "").strip().lower()


def _extract_component_address_tail(value: str) -> str:
    token = str(value or "").strip().lower()
    for separator in (".", "/", ":"):
        if separator in token:
            token = token.split(separator)[-1]
    return token


def _normalize_layout_layer(layer: Any, *, fallback: str) -> str:
    if not isinstance(layer, str) or not layer.strip():
        return fallback
    normalized = layer.strip()
    lowered = normalized.lower()
    aliases = {
        "top": "F.Cu",
        "front": "F.Cu",
        "f.cu": "F.Cu",
        "bottom": "B.Cu",
        "back": "B.Cu",
        "b.cu": "B.Cu",
    }
    return aliases.get(lowered, normalized)


def _resolve_layout_file_for_tool(
    *,
    project_root: Path,
    target: str,
) -> Path:
    errors: list[str] = []
    try:
        build_cfg = _resolve_build_target(project_root, target)
        layout_path = build_cfg.paths.layout
        if layout_path.exists() and layout_path.suffix.lower() == ".kicad_pcb":
            return layout_path
        errors.append(f"build target layout missing at {layout_path}")
    except Exception as exc:
        errors.append(str(exc))

    fallback = resolve_layout_path(project_root, target)
    if isinstance(fallback, Path):
        if fallback.is_file() and fallback.suffix.lower() == ".kicad_pcb":
            return fallback.resolve()
        if fallback.is_dir():
            candidates = sorted(
                path
                for path in fallback.glob("*.kicad_pcb")
                if path.is_file()
                and not path.name.startswith("_autosave-")
                and not path.name.endswith("-save.kicad_pcb")
            )
            if len(candidates) == 1:
                return candidates[0].resolve()
            if len(candidates) > 1:
                raise ValueError(
                    f"Multiple layout files found under {fallback}; specify target."
                )

    detail = "; ".join(part for part in errors if part) or "no layout candidates found"
    raise ValueError(
        f"Layout file for target '{target}' was not found. Details: {detail}"
    )


def _layout_component_payload(record: _LayoutComponentRecord) -> dict[str, Any]:
    return {
        "reference": record.reference or None,
        "atopile_address": record.atopile_address,
        "x_mm": record.x_mm,
        "y_mm": record.y_mm,
        "rotation_deg": record.rotation_deg,
        "layer": record.layer,
    }


def _load_layout_component_index(
    layout_path: Path,
) -> tuple[Any, list[_LayoutComponentRecord]]:
    from faebryk.libs.kicad.fileformats import Property, kicad

    if hasattr(kicad.loads, "cache"):
        kicad.loads.cache.pop(layout_path, None)

    pcb_file = kicad.loads(kicad.pcb.PcbFile, layout_path)
    pcb = pcb_file.kicad_pcb

    records: list[_LayoutComponentRecord] = []
    for footprint in pcb.footprints:
        reference_raw = Property.try_get_property(footprint.propertys, "Reference")
        address_raw = Property.try_get_property(footprint.propertys, "atopile_address")

        reference = (
            str(reference_raw).strip()
            if isinstance(reference_raw, str) and reference_raw.strip()
            else ""
        )
        atopile_address = (
            str(address_raw).strip()
            if isinstance(address_raw, str) and address_raw.strip()
            else None
        )
        if not reference and not atopile_address:
            continue

        at = getattr(footprint, "at", None)
        if at is None:
            continue

        x_mm = float(getattr(at, "x", 0.0) or 0.0)
        y_mm = float(getattr(at, "y", 0.0) or 0.0)
        rotation_deg = float(getattr(at, "r", 0.0) or 0.0)
        layer = str(getattr(footprint, "layer", "") or "")

        records.append(
            _LayoutComponentRecord(
                reference=reference,
                atopile_address=atopile_address,
                layer=layer,
                x_mm=x_mm,
                y_mm=y_mm,
                rotation_deg=rotation_deg,
                footprint=footprint,
            )
        )

    return pcb_file, records


def _write_layout_component_file(layout_path: Path, pcb_file: Any) -> None:
    from faebryk.libs.kicad.fileformats import kicad

    kicad.dumps(pcb_file, layout_path)
    if hasattr(kicad.loads, "cache"):
        kicad.loads.cache.pop(layout_path, None)


def _build_layout_component_suggestions(
    *,
    records: list[_LayoutComponentRecord],
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    query_norm = _normalize_component_lookup_token(query)
    if not query_norm or not records or limit <= 0:
        return []

    scored: list[tuple[float, _LayoutComponentRecord]] = []
    for record in records:
        candidates = [
            record.reference_norm,
            record.address_norm,
            record.address_tail_norm,
        ]
        best_score = 0.0
        for candidate in candidates:
            if not candidate:
                continue
            if candidate == query_norm:
                score = 1.0
            elif candidate.startswith(query_norm):
                score = 0.95
            elif query_norm in candidate:
                score = 0.85
            else:
                score = difflib.SequenceMatcher(None, query_norm, candidate).ratio()
            if score > best_score:
                best_score = score
        if best_score >= 0.35:
            scored.append((best_score, record))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].reference_norm,
            item[1].address_norm,
        ),
        reverse=True,
    )

    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for score, record in scored:
        dedupe_key = (record.reference_norm, record.address_norm)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        suggestion = _layout_component_payload(record)
        suggestion["score"] = round(score, 3)
        suggestions.append(suggestion)
        if len(suggestions) >= limit:
            break
    return suggestions


def _lookup_layout_component(
    *,
    records: list[_LayoutComponentRecord],
    query: str,
    fuzzy_limit: int,
) -> _LayoutComponentLookup:
    query_clean = str(query or "").strip()
    query_norm = _normalize_component_lookup_token(query_clean)
    if not query_norm:
        raise ValueError("address is required")

    address_exact = [
        record
        for record in records
        if record.address_norm and record.address_norm == query_norm
    ]
    if len(address_exact) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="atopile_address_exact",
            record=address_exact[0],
            message="Matched exact atopile_address.",
            suggestions=[],
        )
    if len(address_exact) > 1:
        return _LayoutComponentLookup(
            found=False,
            matched_by=None,
            record=None,
            message="Multiple components matched this atopile_address query.",
            suggestions=[
                _layout_component_payload(record)
                for record in address_exact[: max(1, fuzzy_limit)]
            ],
        )

    reference_exact = [
        record
        for record in records
        if record.reference_norm and record.reference_norm == query_norm
    ]
    if len(reference_exact) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="reference_exact",
            record=reference_exact[0],
            message="Matched exact reference.",
            suggestions=[],
        )

    query_tail = _extract_component_address_tail(query_clean)
    tail_matches = [
        record
        for record in records
        if record.address_tail_norm and record.address_tail_norm == query_tail
    ]
    if len(tail_matches) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="atopile_address_tail",
            record=tail_matches[0],
            message="Matched atopile_address tail token.",
            suggestions=[],
        )

    suffix_matches = [
        record
        for record in records
        if record.address_norm and record.address_norm.endswith(query_norm)
    ]
    if len(suffix_matches) == 1:
        return _LayoutComponentLookup(
            found=True,
            matched_by="atopile_address_suffix",
            record=suffix_matches[0],
            message="Matched atopile_address suffix.",
            suggestions=[],
        )

    return _LayoutComponentLookup(
        found=False,
        matched_by=None,
        record=None,
        message=(
            "Component not found by atopile_address/reference. "
            "Use one of the suggested similar components."
        ),
        suggestions=_build_layout_component_suggestions(
            records=records,
            query=query_clean,
            limit=max(1, min(20, fuzzy_limit)),
        ),
    )


def _layout_get_component_position(
    *,
    project_root: Path,
    target: str,
    address: str,
    fuzzy_limit: int,
) -> dict[str, Any]:
    layout_path = _resolve_layout_file_for_tool(
        project_root=project_root, target=target
    )
    _, records = _load_layout_component_index(layout_path)
    lookup = _lookup_layout_component(
        records=records,
        query=address,
        fuzzy_limit=fuzzy_limit,
    )
    if not lookup.found or lookup.record is None:
        return {
            "found": False,
            "target": target,
            "layout_path": str(layout_path),
            "query": str(address),
            "message": lookup.message,
            "suggestions": lookup.suggestions,
        }

    return {
        "found": True,
        "target": target,
        "layout_path": str(layout_path),
        "query": str(address),
        "matched_by": lookup.matched_by,
        "component": _layout_component_payload(lookup.record),
    }


def _layout_set_component_position(
    *,
    project_root: Path,
    target: str,
    address: str,
    mode: str,
    x_mm: float | None,
    y_mm: float | None,
    rotation_deg: float | None,
    dx_mm: float | None,
    dy_mm: float | None,
    drotation_deg: float | None,
    layer: str | None,
    fuzzy_limit: int,
) -> dict[str, Any]:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from faebryk.libs.kicad.fileformats import kicad

    layout_path = _resolve_layout_file_for_tool(
        project_root=project_root, target=target
    )
    pcb_file, records = _load_layout_component_index(layout_path)
    lookup = _lookup_layout_component(
        records=records,
        query=address,
        fuzzy_limit=fuzzy_limit,
    )
    if not lookup.found or lookup.record is None:
        return {
            "found": False,
            "target": target,
            "layout_path": str(layout_path),
            "query": str(address),
            "message": lookup.message,
            "suggestions": lookup.suggestions,
        }

    record = lookup.record
    before = _layout_component_payload(record)

    mode_clean = str(mode or "absolute").strip().lower() or "absolute"
    if mode_clean not in {"absolute", "relative"}:
        raise ValueError("mode must be one of: absolute, relative")

    if mode_clean == "absolute":
        if x_mm is None or y_mm is None:
            raise ValueError("x_mm and y_mm are required in absolute mode")
        target_x = float(x_mm)
        target_y = float(y_mm)
        target_rotation = (
            float(rotation_deg) if rotation_deg is not None else record.rotation_deg
        )
    else:
        if rotation_deg is not None:
            raise ValueError(
                "rotation_deg is not used in relative mode. Use drotation_deg."
            )
        delta_x = float(dx_mm or 0.0)
        delta_y = float(dy_mm or 0.0)
        delta_rotation = float(drotation_deg or 0.0)
        target_x = record.x_mm + delta_x
        target_y = record.y_mm + delta_y
        target_rotation = record.rotation_deg + delta_rotation

    target_layer = _normalize_layout_layer(layer, fallback=record.layer)
    target_coord = kicad.pcb.Xyr(
        x=target_x,
        y=target_y,
        r=target_rotation,
    )
    PCB_Transformer.move_fp(record.footprint, target_coord, target_layer)
    _write_layout_component_file(layout_path, pcb_file)

    after_record = _LayoutComponentRecord(
        reference=record.reference,
        atopile_address=record.atopile_address,
        layer=str(getattr(record.footprint, "layer", target_layer) or target_layer),
        x_mm=float(getattr(record.footprint.at, "x", target_x) or target_x),
        y_mm=float(getattr(record.footprint.at, "y", target_y) or target_y),
        rotation_deg=float(
            getattr(record.footprint.at, "r", target_rotation) or target_rotation
        ),
        footprint=record.footprint,
    )
    after = _layout_component_payload(after_record)
    placement_check = _analyze_layout_component_placement(
        pcb_file=pcb_file,
        moved_record=after_record,
        all_records=records,
    )

    return {
        "found": True,
        "updated": True,
        "target": target,
        "layout_path": str(layout_path),
        "query": str(address),
        "matched_by": lookup.matched_by,
        "mode": mode_clean,
        "before": before,
        "after": after,
        "delta": {
            "dx_mm": after["x_mm"] - before["x_mm"],
            "dy_mm": after["y_mm"] - before["y_mm"],
            "drotation_deg": after["rotation_deg"] - before["rotation_deg"],
        },
        "placement_check": placement_check,
    }
