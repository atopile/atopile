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
    fp = pcb.kicad_pcb.footprints[0]
    prop = kicad.pcb.Property(
        name="Value",
        value="LED",
        at=kicad.pcb.Xyr(x=0, y=0, r=0),
        layer="F.SilkS",
        hide=False,
        uuid=kicad.gen_uuid(),
        effects=kicad.pcb.Effects(
            font=kicad.pcb.Font(size=kicad.pcb.Wh(w=1.524, h=1.524), thickness=0.3),
            hide=False,
            justifys=[],
        ),
    )
    print("prop:", prop.__zig_address__())
    prop = Property.set_property(fp, prop)
    print("post prop:", prop.__zig_address__())
    prop.value = "LED2"
    print("post prop.value:", prop.value)

    print(Property.get_property_obj(fp.propertys, "Value").__zig_address__())
    print(Property.get_property_obj(fp.propertys, "Value").value)

    for prop in fp.propertys:
        print(prop.__zig_address__(), prop.name, prop.value)

    # Property.get_property_obj(fp.propertys, "Value").value = "LED"
    # print("GET prop from fp")
    # print({p.name: Property.get_property(fp.propertys, p.name) for p in fp.propertys})
    # fp = pcb.kicad_pcb.footprints[0]
    # print(f"GET prop from refreshed fp: {fp.__zig_address__()}")
    # print({p.name: Property.get_property(fp.propertys, p.name) for p in fp.propertys})
    # out = kicad.dumps(pcb)
    # pcb2 = kicad.loads(kicad.pcb.PcbFile, out)
    # print(
    #    {
    #        p.name: Property.get_property(
    #            pcb2.kicad_pcb.footprints[0].propertys, p.name
    #        )
    #        for p in pcb2.kicad_pcb.footprints[0].propertys
    #    }
    # )


if __name__ == "__main__":
    test_pcb()
