"""
This is developer-targeted example for generating schematics.
Schematics are an alpha feature-in-progress, which means they're not bundled up nicely
with the rest of the exporter.
"""

import logging
from pathlib import Path

import iterative_design_nand
import minimal_led

from faebryk.exporters.schematic.kicad.transformer import Transformer
from faebryk.libs.examples.buildutil import apply_design_to_pcb
from faebryk.libs.kicad.fileformats_sch import C_kicad_sch_file
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import CouldntOSOpen, os_open

logger = logging.getLogger(__name__)


def build(module) -> Path:
    build_dir = Path(".") / "build"
    lib_path = build_dir / "kicad" / "libs"

    sch_file = C_kicad_sch_file.skeleton()

    logger.info("Building app")
    app = module.App()

    logger.info("Applying design to PCB")
    apply_design_to_pcb(app)

    logger.info("Generating schematic")
    full_transformer = Transformer(sch_file.kicad_sch, app.get_graph(), app)
    full_transformer.index_symbol_files(lib_path, load_globals=False)

    full_transformer.generate_schematic()

    output_path = build_dir / f"{module.__name__}.kicad_sch"
    sch_file.dumps(output_path)
    return output_path


if __name__ == "__main__":
    setup_basic_logging()

    for module in [minimal_led, iterative_design_nand]:
        logger.info(f"Building {module.__name__}")
        path = build(module)

        logger.info(f"Opening {path}")
        try:
            os_open(path)
        except CouldntOSOpen as ex:
            logger.error(f"Can't open {path}: {ex}")
