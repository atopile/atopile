# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import subprocess as sp
import tempfile
from pathlib import Path
from zipfile import ZipFile

from kicadcliwrapper.generated.kicad_cli import kicad_cli as k

logger = logging.getLogger(__name__)


def _export(cmd):
    return k(k.pcb(k.pcb.export(cmd))).exec()


def export_step(pcb_file: Path, step_file: Path) -> None:
    """
    3D PCBA STEP file export using the kicad-cli
    """

    try:
        _export(
            k.pcb.export.step(
                INPUT_FILE=str(pcb_file),
                force=True,
                no_dnp=True,
                subst_models=True,
                output=str(step_file.absolute()),
            )
        )
    except sp.CalledProcessError as e:
        raise Exception("Failed to export step file") from e


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
        raise Exception("Failed to export dxf file") from e


def export_glb(pcb_file: Path, glb_file: Path) -> None:
    """
    3D PCBA GLB file export using the kicad-cli
    """

    try:
        _export(
            k.pcb.export.glb(
                INPUT_FILE=str(pcb_file),
                force=True,
                include_tracks=True,
                include_zones=True,
                grid_origin=True,
                subst_models=True,
                no_dnp=True,
                output=str(glb_file.absolute()),
            )
        )
    except sp.CalledProcessError as e:
        raise Exception("Failed to export glb file") from e


def export_svg(pcb_file: Path, svg_file: Path, flip_board: bool = False) -> None:
    """
    2D PCBA SVG file export using the kicad-cli
    """

    layers = "F.Cu,F.Paste,F.SilkS,F.Mask,Edge.Cuts"
    if flip_board:
        layers = layers.replace("F.", "B.")

    try:
        _export(
            k.pcb.export.svg(
                INPUT_FILE=str(pcb_file),
                layers=layers,
                page_size_mode="2",
                exclude_drawing_sheet=True,
                output=str(svg_file),
            )
        )
    except sp.CalledProcessError as e:
        raise Exception("Failed to export svg file") from e


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
                    layers="F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,F.CrtYd,B.CrtYd,F.Fab,B.Fab,Edge.Cuts",
                    output=out_dir,
                )
            )
        except sp.CalledProcessError as e:
            raise Exception("Failed to export gerber files") from e

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
            raise Exception("Failed to export drill files") from e

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
        raise Exception("Failed to export pick and place file") from e
