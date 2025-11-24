import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.kicad.fileformats import kicad


def test_has_kicad_footprint():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    _ = F.Pad.bind_typegraph(tg=tg).get_or_create_type()
    pad1 = F.Pad.bind_typegraph(tg=tg).create_instance(g=g)
    pad2 = F.Pad.bind_typegraph(tg=tg).create_instance(g=g)

    kicad_footprint = (
        F.has_kicad_footprint.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(
            kicad_identifier="libR_0402_1005Metric2",
            pinmap={pad1: "P1", pad2: "P2"},
        )
    )

    assert kicad_footprint.get_kicad_footprint() == "libR_0402_1005Metric2"
    assert kicad_footprint.get_pin_names() == {pad1: "P1", pad2: "P2"}


def test_pcb_transformer_traits():
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from faebryk.libs.test.fileformats import PCBFILE

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE)
    app = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    kpcb = pcb.kicad_pcb

    transformer = PCB_Transformer(pcb=kpcb, app=app)

    # assert transformer.tg is app.get_graph()
    assert transformer.app is app
    assert transformer.pcb is kpcb


def test_trait_basic_operations():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    obj = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    # Test obj does not have trait
    assert not obj.has_trait(F.has_footprint)
    with pytest.raises(fabll.TraitNotFound):
        obj.get_trait(F.has_footprint)
