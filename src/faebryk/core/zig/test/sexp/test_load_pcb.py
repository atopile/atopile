from pathlib import Path
from time import time

import typer

from faebryk.libs.kicad.fileformats import kicad


def build_pcb(mb: int):
    base_path = Path(__file__).parent / "resources" / "v9" / "pcb" / "modular"
    header = (base_path / "header").read_text(encoding="utf-8")
    footer = (base_path / "footer").read_text(encoding="utf-8")
    block = (base_path / "block").read_text(encoding="utf-8")

    count = (mb * 1024 * 1024 - len(header) - len(footer)) // len(block)

    return header + block * count + footer


def main(mb: int = 10):
    now = time()
    pcb_raw = build_pcb(mb)
    # pcb_raw = path.read_text(encoding="utf-8")
    mb_raw = len(pcb_raw) / 1000 / 1000
    time_s = time() - now
    print(
        f"Raw PCB: {mb_raw:.2f} mb, took {time_s:.2f} seconds"
        f" ({mb_raw / time_s:.2f} mb/s)"
    )

    now = time()
    pcb = kicad.loads(kicad.pcb.PcbFile, pcb_raw)
    time_s = time() - now
    print(f"Loaded PCB: {time_s:.2f} seconds ({mb_raw / time_s:.2f} mb/s)")

    now = time()
    pcb_dumped = kicad.dumps(pcb)
    mb_dumped = len(pcb_dumped) / 1000 / 1000
    time_s = time() - now
    print(
        f"Dumped PCB: {mb_dumped:.2f} mb, took {time_s:.2f} seconds "
        f"({mb_dumped / time_s:.2f} mb/s)"
    )

    print(f"Footprints: {len(pcb.kicad_pcb.footprints)}")


if __name__ == "__main__":
    typer.run(main)
