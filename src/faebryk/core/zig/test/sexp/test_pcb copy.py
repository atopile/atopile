#!/usr/bin/env python3
from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad


def test_pcb_():
    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb"
    )
    pcb = kicad.loads(kicad.pcb.PcbFile, path)
    print(kicad.dumps(pcb))
    print("\n--- Print complete, exiting ---")


if __name__ == "__main__":
    test_pcb_()
