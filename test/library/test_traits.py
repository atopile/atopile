import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


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
