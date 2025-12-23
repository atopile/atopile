import logging
from itertools import pairwise
from typing import TYPE_CHECKING

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import KeyErrorAmbiguous

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer


def bind_fbrk_nets_to_kicad_nets(
    tg: fbrk.TypeGraph, g: fabll.graph.GraphView, transformer: "PCB_Transformer"
):
    """
    Gets fbrk nets and attempts to map them to existing kicad nets
    """

    # get all nets
    for fbrk_net in F.Net.bind_typegraph(tg).get_instances(g):
        pad_count = 0
        kicad_net_name_counts: dict[str, int] = {}

        # filter out nets that already have a kicad net association
        if fbrk_net.has_trait(F.KiCadFootprints.has_associated_kicad_pcb_net):
            continue

        # for all the fbrk pads in the net, count and collect their kicad net names
        for pad in fbrk_net.get_connected_pads():
            pad_count += 1

            # if the fbrk pad has a kicad pad with a name...
            if has_associated_kicad_pcb_pad := pad.try_get_trait(
                F.KiCadFootprints.has_associated_kicad_pcb_pad
            ):
                if kicad_net := has_associated_kicad_pcb_pad.get_pad().net:
                    if kicad_net_name := kicad_net.name:
                        # save that name and track it's count
                        kicad_net_name_counts[kicad_net_name] = (
                            kicad_net_name_counts.get(kicad_net_name, 0) + 1
                        )

        # skip if there's no named kicad nets
        if not kicad_net_name_counts:
            continue

        # pick the highest occuring kicad net name (highest count)
        # + check at least 80% of fbrk pads have it
        best_kicad_net_name = max(
            kicad_net_name_counts, key=lambda x: kicad_net_name_counts[x]
        )
        best_count = kicad_net_name_counts[best_kicad_net_name]
        if best_count <= pad_count * 0.8:
            continue

        # bind the kicad net to the fabll net
        trait_instance = fabll.Traits.create_and_add_instance_to(
            fbrk_net, F.KiCadFootprints.has_associated_kicad_pcb_net
        )

        # TODO for now since the transformer and kicadpcbnet are not in the graph yet
        nets_by_name = {}
        for pcb_net in transformer.pcb.nets:
            if pcb_net.name:
                nets_by_name[pcb_net.name] = pcb_net
        trait_instance.setup(nets_by_name[best_kicad_net_name], transformer)


def bind_electricals_to_fbrk_nets(
    tg: fbrk.TypeGraph, g: fabll.graph.GraphView
) -> set["F.Net"]:
    """
    Groups electricals into buses, get or create a net, and return all the nets
    """
    fbrk_nets: set[F.Net] = set()
    electricals_filtered: set[fabll.Node] = set()

    for is_lead_trait in fabll.Traits.get_implementors(
        F.Lead.is_lead.bind_typegraph(tg), g=g
    ):
        interface_node = fabll.Traits.bind(is_lead_trait).get_obj_raw()

        if not interface_node.has_trait(fabll.is_interface):
            continue

        if is_lead_trait.has_trait(F.Lead.has_associated_pads):
            electricals_filtered.add(interface_node)
        else:
            logger.warning(
                f"Lead of {interface_node.get_name()} has no associated pads"
            )

    # collect buses in a sorted manner
    buses = sorted(
        fabll.is_interface.group_into_buses(electricals_filtered),
        key=lambda node: node.get_full_name(include_uuid=False),
    )

    # find or generate nets
    for bus in buses:
        if fbrk_net := get_named_net(bus):
            fbrk_nets.add(fbrk_net)
        else:
            fbrk_net = F.Net.bind_typegraph(tg).create_instance(g=g)
            fbrk_net.part_of.get()._is_interface.get().connect_to(bus)
            fbrk_nets.add(fbrk_net)

    return fbrk_nets


def get_named_net(electrical: "F.Electrical") -> "F.Net | None":
    """
    Returnes exactly one named net that this electrical is part of.
    Will raise an error if there's somehow more than one net connected.
    """
    # Use trait API to get is_interface, works for both F.Electrical and pins
    is_interface = electrical.get_trait(fabll.is_interface)
    bus_members = is_interface.get_connected(include_self=True)
    named_nets_on_bus: set[F.has_net_name] = set()

    for bus_member in bus_members:
        # check if the parent of an electrical has the has_net_name trait
        if member_parent := bus_member.get_parent():
            if has_net_name := member_parent[0].try_get_trait(F.has_net_name):
                named_nets_on_bus.add(has_net_name)

    # if there's one net, let's return that
    if len(named_nets_on_bus) == 1:
        (named_net,) = named_nets_on_bus
        return fabll.Traits.bind(named_net).get_obj_raw().cast(F.Net)

    elif not named_nets_on_bus:
        return None

    else:
        raise KeyErrorAmbiguous(
            list(named_nets_on_bus), "Multiple named nets interconnected"
        )


def test_bind_nets_from_electricals():
    from faebryk.libs.net_naming import attach_net_names

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestPad(fabll.Node):
        is_pad = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="TST_PAD", pad_number="1")
        )

    class TestModule(fabll.Node):
        elec = F.Electrical.MakeChild()
        lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [elec])
        elec.add_dependant(lead)
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    bus_1 = [TestModule.bind_typegraph(tg).create_instance(g=g) for _ in range(2)]
    for module in bus_1:
        pad = TestPad.bind_typegraph(tg).create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(
            node=module.elec.get().get_trait(F.Lead.is_lead),
            trait=F.Lead.has_associated_pads,
        ).setup(pad.is_pad.get())
    for left, right in pairwise(bus_1):
        left.elec.get()._is_interface.get().connect_to(right.elec.get())

    bus_2 = [TestModule.bind_typegraph(tg).create_instance(g=g) for _ in range(3)]
    for module in bus_2:
        pad = TestPad.bind_typegraph(tg).create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(
            node=module.elec.get().get_trait(F.Lead.is_lead),
            trait=F.Lead.has_associated_pads,
        ).setup(pad.is_pad.get())
    for left, right in pairwise(bus_2):
        left.elec.get()._is_interface.get().connect_to(right.elec.get())

    nets = bind_electricals_to_fbrk_nets(tg, g)
    attach_net_names(nets)

    # sort nets by name to ensure deterministic ordering
    nets_sorted = sorted(nets, key=lambda net: net.get_name())

    assert len(nets_sorted) == 2
    print(nets_sorted)
    for i, net in enumerate(nets_sorted):
        assert net.get_name() == f"elec-{i}"
        assert len(net.get_connected_interfaces()) == 2 + i
        assert len(net.get_connected_pads()) == 2 + i
        assert len(net.part_of.get()._is_interface.get().get_connected()) == 2 + i
