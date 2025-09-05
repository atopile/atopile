#!/usr/bin/env python3
import difflib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_fp_lib():
    from faebryk.libs.kicad.fileformats import kicad

    path = Path(
        "/home/needspeed/workspace/atopile/test/common/resources/fileformats/kicad/v9/fp-lib-table/fp-lib-table"
    )
    fp_lib_table = kicad.loads(kicad.fp_lib_table.FpLibTableFile, path)

    # Test direct Python list manipulation
    print(f"Before append: {len(fp_lib_table.fp_lib_table.libs)} libs")

    new_entry = kicad.fp_lib_table.FpLibEntry(
        name="test",
        type="KiCad",
        uri="test",
        options="",
        descr="test",
    )

    kicad.set(fp_lib_table.fp_lib_table, "libs", new_entry)

    out = kicad.dumps(fp_lib_table)
    print(out)

    print("\n--- Print complete, exiting ---")


if __name__ == "__main__":
    test_fp_lib()
