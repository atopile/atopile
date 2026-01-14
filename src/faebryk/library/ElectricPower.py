# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.exceptions import DeprecatedException, downgrade

logger = logging.getLogger(__name__)


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
    # These are floating until POST_DESIGN_SETUP connects them to hv/lv if used.
    # This avoids creating connection edges for every ElectricPower instance
    # when vcc/gnd are not actually referenced.
    vcc = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

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

    # Design check to connect deprecated vcc/gnd aliases to hv/lv if used
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_design_setup_check
    def __check_post_design_setup__(self):
        """
        Connect deprecated vcc/gnd to hv/lv if they have connections.
        This allows support for legacy designs that use vcc/gnd.
        """
        vcc_node = self.vcc.get()
        gnd_node = self.gnd.get()

        # Efficiently check for direct interface edges (O(edges) not O(graph))
        vcc_connected = _has_interface_connections(vcc_node)
        gnd_connected = _has_interface_connections(gnd_node)

        aliases_used: list[str] = []
        if vcc_connected:
            aliases_used.append("vcc->hv")
            vcc_node._is_interface.get().connect_to(self.hv.get())
        if gnd_connected:
            aliases_used.append("gnd->lv")
            gnd_node._is_interface.get().connect_to(self.lv.get())

        if aliases_used:
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    f"Deprecated ElectricPower aliases used in {self.pretty_repr()}: "
                    f"{', '.join(aliases_used)}. Use hv/lv instead."
                )


def _has_interface_connections(node: fabll.Node) -> bool:
    """
    Efficiently check if a node has any direct interface connection edges.

    This is O(number of direct edges on node) instead of O(entire connected component)
    like get_connected() which does full BFS traversal.
    """
    # Use a mutable container to track if we found any edges
    found: list[bool] = [False]

    def mark_found(ctx, edge):
        ctx[0] = True

    node.instance.visit_edges_of_type(
        edge_type=fbrk.EdgeInterfaceConnection.get_tid(),
        ctx=found,
        f=mark_found,
    )
    return found[0]
