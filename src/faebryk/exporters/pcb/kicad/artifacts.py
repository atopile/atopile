# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
import subprocess
import subprocess as sp
import tempfile
from pathlib import Path
from typing import Any, Optional
from zipfile import ZipFile

from kicadcliwrapper.generated.kicad_cli import kicad_cli as k

logger = logging.getLogger(__name__)


class KicadCliExportError(Exception):
    pass


def _export(cmd):
    return k(k.pcb(k.pcb.export(cmd))).exec()


def githash_layout(layout: Path, out: Path) -> Path:
    # Get current git hash
    try:
        git_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=layout.parent
            )
            .decode("ascii")
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Could not get git hash, using 'unknown'")
        git_hash = "unknown"

    # Read and substitute git hash
    layout_text = layout.read_text(encoding="utf-8")
    layout_text = layout_text.replace("{{GITHASH}}", git_hash)

    # Write modified layout to temp file
    out.write_text(layout_text, encoding="utf-8")

    return out


def export_step(
    pcb_file: Path, step_file: Path, project_dir: Optional[Path] = None
) -> None:
    """
    3D PCBA STEP file export using the kicad-cli
    """

    # If project_dir is provided, set KIPRJMOD to ensure 3D model paths resolve
    cmd_args = {
        "INPUT_FILE": str(pcb_file),
        "force": True,
        "no_dnp": True,
        "subst_models": True,
        "output": str(step_file.absolute()),
    }

    if project_dir:
        cmd_args["define_var"] = f"KIPRJMOD={project_dir.absolute()}"

    try:
        _export(k.pcb.export.step(**cmd_args))
    except sp.CalledProcessError as e:
        raise KicadCliExportError("Failed to export step file") from e


def export_dxf(pcb_file: Path, dxf_file: Path) -> None:
    """
    PCB outline export using the kicad-cli
    """

    try:
        _export(
            k.pcb.export.dxf(
                INPUT_FILE=str(pcb_file),
                exclude_refdes=True,
                exclude_value=True,
                output_units="mm",
                layers="Edge.Cuts",
                output=str(dxf_file),
            )
        )
    except sp.CalledProcessError as e:
        raise KicadCliExportError("Failed to export dxf file") from e


def export_glb(
    pcb_file: Path, glb_file: Path, project_dir: Optional[Path] = None
) -> None:
    """
    3D PCBA GLB file export using the kicad-cli
    """

    # If project_dir is provided, set KIPRJMOD to ensure 3D model paths resolve
    cmd_args = {
        "INPUT_FILE": str(pcb_file),
        "force": True,
        "include_tracks": True,
        "include_zones": True,
        "grid_origin": True,
        "subst_models": True,
        "no_dnp": True,
        "cut_vias_in_body": True,
        "include_pads": True,
        "include_soldermask": True,
        "include_silkscreen": True,
        "output": str(glb_file.absolute()),
    }

    if project_dir:
        cmd_args["define_var"] = f"KIPRJMOD={project_dir.absolute()}"

    try:
        _export(k.pcb.export.glb(**cmd_args))
    except sp.CalledProcessError as e:
        raise KicadCliExportError("Failed to export glb file") from e


def export_svg(
    pcb_file: Path,
    svg_file: Path,
    flip_board: bool = False,
    project_dir: Optional[Path] = None,
) -> None:
    """
    2D PCBA SVG file export using the kicad-cli
    """

    layers = "F.Cu,F.Paste,F.SilkS,F.Mask,Edge.Cuts"
    if flip_board:
        layers = layers.replace("F.", "B.")

    cmd_vars = f"KIPRJMOD={project_dir.absolute()}" if project_dir else None

    try:
        _export(
            k.pcb.export.svg(
                INPUT_FILE=str(pcb_file),
                layers=layers,
                page_size_mode="2",
                exclude_drawing_sheet=True,
                output=str(svg_file),
                define_var=cmd_vars,
            )
        )
    except sp.CalledProcessError as e:
        raise KicadCliExportError("Failed to export svg file") from e


def export_3d_board_render(
    pcb_file: Path, image_file: Path, project_dir: Optional[Path] = None
) -> None:
    """
    Render a 3D PCBA image (png) using the kicad-cli
    """

    cmd_vars = f"KIPRJMOD={project_dir.absolute()}" if project_dir else None

    try:
        k(
            k.pcb(
                k.pcb.render(
                    INPUT_FILE=pcb_file.as_posix(),
                    output=image_file.as_posix(),
                    width="1000",
                    height="1000",
                    side="top",
                    background="opaque",
                    quality="high",
                    zoom="0.8",
                    rotate="335,0,-45",
                    define_var=cmd_vars,
                )
            )
        ).exec()
    except sp.CalledProcessError as e:
        raise KicadCliExportError("Failed to export 3d board render") from e


def export_gerber(pcb_file: Path, gerber_zip_file: Path) -> None:
    """
    Gerber export using the kicad-cli
    """

    logger.info(f"Exporting gerber files to {gerber_zip_file}")
    gerber_dir = gerber_zip_file.parent
    gerber_dir.mkdir(parents=True, exist_ok=True)

    # Create a temporary folder to export the gerber and drill files to
    with tempfile.TemporaryDirectory(dir=gerber_dir) as temp_dir:
        out_dir = temp_dir if temp_dir.endswith("/") else f"{temp_dir}/"

        try:
            _export(
                k.pcb.export.gerbers(
                    INPUT_FILE=str(pcb_file),
                    output=out_dir,
                )
            )
        except sp.CalledProcessError as e:
            raise KicadCliExportError("Failed to export gerber files") from e

        try:
            _export(
                k.pcb.export.drill(
                    INPUT_FILE=str(pcb_file),
                    format="excellon",
                    excellon_separate_th=True,
                    generate_map=True,
                    map_format="gerberx2",
                    output=out_dir,
                )
            )

        except sp.CalledProcessError as e:
            raise KicadCliExportError("Failed to export drill files") from e

        # Zip the gerber files
        with ZipFile(gerber_zip_file, "w") as zipf:
            for file in Path(temp_dir).iterdir():
                if file.is_file():
                    zipf.write(file, arcname=file.name)


def export_pick_and_place(pcb_file: Path, pick_and_place_file: Path) -> None:
    """
    Pick and place export using the kicad-cli
    """

    try:
        _export(
            k.pcb.export.pos(
                INPUT_FILE=str(pcb_file),
                side="both",
                format="csv",
                units="mm",
                exclude_dnp=True,
                output=str(pick_and_place_file),
            )
        )
    except sp.CalledProcessError as e:
        raise KicadCliExportError("Failed to export pick and place file") from e


def export_pcb_summary(pcb_file: Path, summary_file: Path) -> None:
    """
    Export PCB summary as JSON with board dimensions and stackup information.

    Extracts:
    - Board bounding dimensions from Edge.Cuts layer
    - Stackup information (layers, thicknesses, materials)
    - Layer count
    - Board area estimate
    """
    from faebryk.libs.kicad.fileformats import kicad

    logger.info(f"Exporting PCB summary to {summary_file}")

    # Load the PCB file
    pcb = kicad.loads(kicad.pcb.PcbFile, pcb_file)
    kicad_pcb = pcb.kicad_pcb

    summary: dict[str, Any] = {
        "version": kicad_pcb.version,
        "generator": kicad_pcb.generator,
    }

    # Extract board dimensions from Edge.Cuts layer
    edge_points = _extract_edge_cuts_points(kicad_pcb)
    if edge_points:
        xs = [p[0] for p in edge_points]
        ys = [p[1] for p in edge_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width_mm = max_x - min_x
        height_mm = max_y - min_y
        area_mm2 = width_mm * height_mm

        summary["dimensions"] = {
            "width_mm": round(width_mm, 3),
            "height_mm": round(height_mm, 3),
            "area_mm2": round(area_mm2, 3),
            "area_cm2": round(area_mm2 / 100, 3),
            "bounding_box": {
                "min_x": round(min_x, 3),
                "max_x": round(max_x, 3),
                "min_y": round(min_y, 3),
                "max_y": round(max_y, 3),
            },
        }
    else:
        summary["dimensions"] = None

    # Extract stackup information
    stackup = kicad_pcb.setup.stackup if kicad_pcb.setup else None
    if stackup:
        stackup_layers = []
        copper_layers = []

        for layer in stackup.layers:
            layer_info = {
                "name": layer.name,
                "type": layer.type,
                "thickness_mm": layer.thickness,
                "material": layer.material,
            }
            if layer.color:
                layer_info["color"] = layer.color
            if layer.epsilon_r is not None:
                layer_info["epsilon_r"] = layer.epsilon_r
            if layer.loss_tangent is not None:
                layer_info["loss_tangent"] = layer.loss_tangent

            stackup_layers.append(layer_info)

            # Track copper layers
            if layer.type == "copper":
                copper_layers.append(layer.name)

        # Calculate total board thickness
        total_thickness = sum(
            layer.thickness for layer in stackup.layers if layer.thickness is not None
        )

        summary["stackup"] = {
            "layers": stackup_layers,
            "layer_count": len(copper_layers),
            "copper_layers": copper_layers,
            "total_thickness_mm": round(total_thickness, 3)
            if total_thickness
            else None,
            "copper_finish": stackup.copper_finish,
            "edge_connector": stackup.edge_connector,
            "castellated_pads": stackup.castellated_pads,
            "edge_plating": stackup.edge_plating,
        }
    else:
        # Fallback: count copper layers from pcb layers definition
        copper_layer_count = sum(
            1
            for layer in (kicad_pcb.layers or [])
            if layer.type in ("signal", "power", "mixed")
        )
        summary["stackup"] = {
            "layer_count": copper_layer_count if copper_layer_count > 0 else None,
            "note": "Detailed stackup not defined in PCB file",
        }

    # Write JSON file
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)


def _extract_edge_cuts_points(kicad_pcb) -> list[tuple[float, float]]:
    """
    Extract all points from Edge.Cuts layer geometry.

    Returns a list of (x, y) coordinate tuples.
    """
    from faebryk.libs.kicad.fileformats import kicad

    points: list[tuple[float, float]] = []

    # Helper to check if geometry is on Edge.Cuts layer
    def is_edge_cuts(geo) -> bool:
        layers = kicad.geo.get_layers(geo)
        return "Edge.Cuts" in layers

    # Extract from graphic lines
    for line in kicad_pcb.gr_lines or []:
        if is_edge_cuts(line):
            points.append((line.start.x, line.start.y))
            points.append((line.end.x, line.end.y))

    # Extract from graphic arcs
    for arc in kicad_pcb.gr_arcs or []:
        if is_edge_cuts(arc):
            points.append((arc.start.x, arc.start.y))
            points.append((arc.mid.x, arc.mid.y))
            points.append((arc.end.x, arc.end.y))

    # Extract from graphic rectangles
    for rect in kicad_pcb.gr_rects or []:
        if is_edge_cuts(rect):
            points.append((rect.start.x, rect.start.y))
            points.append((rect.end.x, rect.end.y))

    # Extract from graphic circles
    for circle in kicad_pcb.gr_circles or []:
        if is_edge_cuts(circle):
            # For circles, add points at cardinal directions
            cx, cy = circle.center.x, circle.center.y
            # Calculate radius from center to end point
            r = ((circle.end.x - cx) ** 2 + (circle.end.y - cy) ** 2) ** 0.5
            points.extend(
                [
                    (cx - r, cy),
                    (cx + r, cy),
                    (cx, cy - r),
                    (cx, cy + r),
                ]
            )

    # Extract from footprint geometry on Edge.Cuts
    for fp in kicad_pcb.footprints or []:
        fp_x = fp.at.x if fp.at else 0
        fp_y = fp.at.y if fp.at else 0
        fp_angle = fp.at.r if fp.at and fp.at.r else 0

        import math

        def transform_point(x: float, y: float) -> tuple[float, float]:
            """Transform point from footprint-local to board coordinates."""
            if fp_angle:
                angle_rad = math.radians(fp_angle)
                cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
                rx = x * cos_a - y * sin_a
                ry = x * sin_a + y * cos_a
                return (fp_x + rx, fp_y + ry)
            return (fp_x + x, fp_y + y)

        for line in fp.fp_lines or []:
            if is_edge_cuts(line):
                points.append(transform_point(line.start.x, line.start.y))
                points.append(transform_point(line.end.x, line.end.y))

        for arc in fp.fp_arcs or []:
            if is_edge_cuts(arc):
                points.append(transform_point(arc.start.x, arc.start.y))
                points.append(transform_point(arc.mid.x, arc.mid.y))
                points.append(transform_point(arc.end.x, arc.end.y))

    return points
