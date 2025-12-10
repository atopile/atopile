from itertools import pairwise

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


def bind_fbrk_nets_to_kicad_nets(tg: fbrk.TypeGraph, g: fabll.graph.GraphView):
    """
    Gets named fbrk nets and attempts to map them to existing kicad nets
    """

    # get all nets
    for fbrk_net in F.Net.bind_typegraph(tg).get_instances(g):

        pad_count = 0
        kicad_net_name_counts: dict[str, int] = {}

        # filter out unnamed nets, we only want to match named nets
        if fbrk_net.get_name() is None:
            continue

        # filter out nets that already have a kicad net association
        if fbrk_net.has_trait(F.KiCadFootprints.has_associated_kicad_pcb_net):
            continue

        # for all the fbrk pads in the net, count and collect their kicad net names
        for pad in fbrk_net.get_connected_pads():
            pad_count += 1

            # if the fbrk pad has a kicad pad with a name...
            if has_associated_kicad_pcb_pad := pad.try_get_trait(F.KiCadFootprints.has_associated_kicad_pcb_pad):
                if kicad_net := has_associated_kicad_pcb_pad.get_pad().net:
                    if kicad_net_name := kicad_net.name:

                        # save that name and track it's count
                        kicad_net_name_counts[kicad_net_name] = kicad_net_name_counts.get(kicad_net_name, 0) + 1

        # skip if there's no named kicad nets
        if not kicad_net_name_counts:
            continue

        # pick the highest occuring kicad net name
        # + check at least 80% of fbrk pads have it
        best_kicad_net_name = max(kicad_net_name_counts, key=kicad_net_name_counts.get)
        best_count = kicad_net_name_counts[best_kicad_net_name]
        if best_count <= pad_count * 0.8:
            continue

        # bind the kicad net to the fabll net
        fabll.Traits.create_and_add_instance_to(fbrk_net, F.KiCadFootprints.has_associated_kicad_pcb_net)


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
