#!/usr/bin/env python3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_pcb():
    from faebryk.core.zig import pcb as C_pcb

    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb"
    )
    pcb = C_pcb.loads(path.read_text())
    print(pcb.field_names)
    # print(pcb.kicad_pcb.footprints[0])
    print("\n--- Print complete, exiting ---")


if __name__ == "__main__":
    test_pcb()
