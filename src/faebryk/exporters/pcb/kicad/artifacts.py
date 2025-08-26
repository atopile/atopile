# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import subprocess
import subprocess as sp
import tempfile
from pathlib import Path
from typing import Optional
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
