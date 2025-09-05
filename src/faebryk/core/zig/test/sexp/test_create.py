from faebryk.libs.kicad.fileformats import kicad

pcb = kicad.pcb.PcbFile(
    kicad_pcb=kicad.pcb.KicadPcb(
        generator="faebryk",
        generator_version="latest",
        gr_lines=[
            kicad.pcb.Line(
                start=kicad.pcb.Xy(x=0, y=0),
                end=kicad.pcb.Xy(x=10, y=10),
                stroke=kicad.pcb.Stroke(width=0.1, type="solid"),
                layer="F.Cu",
            )
        ],
    ),
)

print(kicad.dumps(pcb))
print(pcb.kicad_pcb.gr_lines[0])
