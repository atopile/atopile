# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.exceptions import DeprecatedException, downgrade

logger = logging.getLogger(__name__)


def _count_interface_connections(node: fabll.Node) -> int:
    """
    Efficiently count the number of direct interface connection edges on a node.

    This is O(number of direct edges on node) instead of O(entire connected component)
    like get_connected() which does full BFS traversal.
    """
    count: list[int] = [0]

    def increment(ctx, edge):
        ctx[0] += 1

    node.instance.visit_edges_of_type(
        edge_type=fbrk.EdgeInterfaceConnection.get_tid(),
        ctx=count,
        f=increment,
    )
    return count[0]


class ElectricPower(fabll.Node):
    """
    ElectricPower is a class that represents a power rail. Power rails have a
    higher potential (hv), and lower potential (lv) Electrical.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    hv = F.Electrical.MakeChild()
    lv = F.Electrical.MakeChild()

    # Deprecated aliases for backwards compatibility.
    # These are always connected to hv/lv via the edges below.
    # The post_design check warns if they are actually used.
    vcc = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

    # Always connect vcc->hv and gnd->lv for backwards compatibility
    _vcc_to_hv = fabll.MakeEdge(
        [vcc], [hv], edge=fbrk.EdgeInterfaceConnection.build(shallow=False)
    )
    _gnd_to_lv = fabll.MakeEdge(
        [gnd], [lv], edge=fbrk.EdgeInterfaceConnection.build(shallow=False)
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)

    can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeChild(in_=[""], out_=[""]))

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="hv", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[hv],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="lv", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[lv],
        ),
    ]

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import ElectricPower

        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        assert power_5v.max_current <= 1A

        # Connect 2 ElectricPowers together
        power_5v ~ ic.power_input

        # Connect an example bypass capacitor
        power_5v.hv ~> example_capacitor ~> power_5v.lv
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )

    def make_source(self):
        fabll.Traits.create_and_add_instance_to(node=self, trait=F.is_source).setup()

    def make_sink(self):
        fabll.Traits.create_and_add_instance_to(node=self, trait=F.is_sink).setup()

    # Design check to warn if deprecated vcc/gnd aliases are used
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        """
        Warn if deprecated vcc/gnd aliases are being used.

        vcc/gnd are always connected to hv/lv (1 connection each).
        If they have more than 1 connection, something external is using them.
        """
        vcc_node = self.vcc.get()
        gnd_node = self.gnd.get()

        # Count direct interface edges - 1 connection is the vcc~hv or gnd~lv edge
        vcc_connection_count = _count_interface_connections(vcc_node)
        gnd_connection_count = _count_interface_connections(gnd_node)

        aliases_used: list[str] = []
        if vcc_connection_count > 1:
            aliases_used.append("vcc")
        if gnd_connection_count > 1:
            aliases_used.append("gnd")

        if aliases_used:
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    f"Deprecated ElectricPower aliases used in {self.pretty_repr()}: "
                    f"{', '.join(aliases_used)}. Use hv/lv instead."
                )
