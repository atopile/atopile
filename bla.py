from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad


def main() -> None:
    inp = Path("panel.kicad_pcb")
    out = Path("/tmp/panel.roundtrip.kicad_pcb")

    pcb = kicad.loads(kicad.pcb.PcbFile, inp)
    kicad.dumps(pcb, out)
    print(f"wrote: {out}")


if __name__ == "__main__":
    main()
