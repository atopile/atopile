#!/usr/bin/env python3
import difflib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_pcb():
    from faebryk.libs.kicad.fileformats import kicad

    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb"
    )
    pcb = kicad.loads(kicad.pcb.PcbFile, path)
    out = kicad.dumps(pcb)
    load = kicad.loads(kicad.pcb.PcbFile, out)
    out2 = kicad.dumps(load)

    for line in difflib.unified_diff(out, out2, lineterm=""):
        print(line)
    print("\n--- Print complete, exiting ---")


if __name__ == "__main__":
    test_pcb()
