#!/usr/bin/env python3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_pcb():
    from faebryk.libs.kicad.fileformats import kicad

    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/sch/test.kicad_sch"
    )
    sch = kicad.loads(kicad.schematic.SchematicFile, path)
    print(sch.__field_names__)
    # print(pcb.kicad_pcb.footprints[0])
    print("\n--- Print complete, exiting ---")


if __name__ == "__main__":
    test_pcb()
