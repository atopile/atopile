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
    print(pcb.kicad_pcb.layers)
    input()
    out = kicad.dumps(pcb)
    load = kicad.loads(kicad.pcb.PcbFile, out)
    out2 = kicad.dumps(load)

    for line in difflib.unified_diff(out, out2, lineterm=""):
        print(line)
    print("\n--- Print complete, exiting ---")

    # Test the __field_names__ method
    field_names = kicad.footprint.Footprint.__field_names__()
    print("Field names:", field_names)

    # Test that we can create and copy a simple footprint
    test_footprint = kicad.footprint.Footprint(name="test_footprint")
    copied = kicad.copy(test_footprint)
    print("Successfully copied footprint:", copied.name)


if __name__ == "__main__":
    test_pcb()
