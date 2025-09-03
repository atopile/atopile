#!/usr/bin/env python3
from pathlib import Path

from faebryk.core.zig import pcb as C_pcb


def test_pcb():
    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb"
    )
    pcb = C_pcb.loads(path.read_text())
    print(pcb.kicad_pcb.setup)
    print("\n--- Print complete, exiting ---")


if __name__ == "__main__":
    test_pcb()
