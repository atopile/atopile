from itertools import pairwise

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


def bind_nets_from_kicad_pads(tg: fbrk.TypeGraph, g: fabll.graph.GraphView) -> set[F.Net]:
    """
    Runs during:
    - load-pcb
    - prepare-nets

    Pulls nets from kicad pads and maps them to fbrk nets.
    """

    fbrk_nets: set[F.Net] = set()

    # you're gonna want to look at the miro for this
    for is_pad in F.Footprints.is_pad.bind_typegraph(tg).get_instances():
        pad_node = is_pad.get_parent_force()[0]
        has_linked_kicad_pad = pad_node.get_trait(F.KiCadFootprints.has_linked_kicad_pad)
        is_kicad_pad = has_linked_kicad_pad.pad_ptr_.get().deref().cast(F.KiCadFootprints.is_kicad_pad)
        kicad_pad_node = is_kicad_pad.get_parent_force()[0]

        # TODO some logic to get the kicad_net_node from the kicad_pad_node
        kicad_net_node = F.KiCadFootprints.GenericKiCadNet()

        is_kicad_net = kicad_net_node.is_kicad_net_.get()
        kicad_net_name = kicad_net_node.get_name()

        fbrk_net = F.Net.bind_typegraph(tg).create_instance(g=g).setup(net_name=kicad_net_name)
        has_linked_kicad_net = fabll.Traits.create_and_add_instance_to(fbrk_net, F.KiCadFootprints.has_linked_kicad_net)
        has_linked_kicad_net.net_ptr_.get().point(is_kicad_net)

        fbrk_nets.add(fbrk_net)

    return fbrk_nets

def bind_kicad_nets_to_fbrk_nets(tg: fbrk.TypeGraph, g: fabll.graph.GraphView) -> set[F.Net]:
    """
    Runs during:
    - load-pcb
    - prepare-nets

    Gets fbrk nets and maps them to kicad nets.
    """

    # get named fbrk nets
    for fbrk_net in 

    # for electrical with lead connected to net, 

def bind_electricals_to_fbrk_nets(tg: fbrk.TypeGraph, g: fabll.graph.GraphView) -> set[F.Net]:
    """
    Runs during:
    - prepare-nets

    Groups electricals into buses, assigns net name, and returns nets

    TODO
    - there's probably a sorting step missing here
    - should consider naming and stuff
    """
    fbrk_nets: set[F.Net] = set()
    buses = fabll.is_interface.group_into_buses(F.Electrical.bind_typegraph(tg).get_instances(g=g))

    for bus, members in buses.items():
        fbrk_net = F.Net.bind_typegraph(tg).create_instance(g=g)
        for member in members:
            member.get_trait(fabll.is_interface).connect_to(fbrk_net.part_of.get())
        fbrk_nets.add(fbrk_net)

    return fbrk_nets





def test_bind_nets_from_electricals(capsys):
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    bus_1 = [F.Electrical.bind_typegraph(tg).create_instance(g=g) for _ in range(2)]
    for left, right in pairwise(bus_1):
        left._is_interface.get().connect_to(right)

    bus_2 = [F.Electrical.bind_typegraph(tg).create_instance(g=g) for _ in range(5)]
    for left, right in pairwise(bus_2):
        left._is_interface.get().connect_to(right)

    nets = bind_electricals_to_fbrk_nets(tg, g)

    with capsys.disabled():
        print("")
        print(nets)
