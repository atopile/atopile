#!/usr/bin/env python3
import logging
from pathlib import Path

from faebryk.libs.kicad.fileformats import Property

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_pcb():
    from faebryk.libs.kicad.fileformats import kicad

    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb"
    )
    pcb = kicad.loads(kicad.pcb.PcbFile, path)

    print(pcb.kicad_pcb.title_block)

    obj = kicad.pcb.TitleBlock(
        title="Test",
        date="2025-01-01",
        revision="1.0",
        company="Test",
        comment=[kicad.pcb.Comment(number=1, text="Test")],
    )
    print(obj.__zig_address__())
    obj.title = "Test2"
    pcb.kicad_pcb.title_block = obj
    print(pcb.kicad_pcb.title_block.__zig_address__())
    pcb.kicad_pcb.title_block.date = "2025-01-02"

    print(pcb.kicad_pcb.title_block)


if __name__ == "__main__":
    test_pcb()
