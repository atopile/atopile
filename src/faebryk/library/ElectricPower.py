# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.exceptions import DeprecatedException, downgrade


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
    # The post_instantiation_design_check check warns if they are actually used.
    vcc = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

    # Always connect vcc->hv and gnd->lv for backwards compatibility
    _connections = [
        fabll.is_interface.MakeConnectionEdge([vcc], [hv]),
        fabll.is_interface.MakeConnectionEdge([gnd], [lv]),
    ]

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    # _is_source = fabll.Traits.MakeEdge(F.is_source.MakeChild())

    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    max_power = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Watt)

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

    bus_parameters = [
        fabll.Traits.MakeEdge(F.is_alias_bus_parameter.MakeChild(), owner=[voltage]),
        fabll.Traits.MakeEdge(F.is_sum_bus_parameter.MakeChild(), owner=[max_current]),
        fabll.Traits.MakeEdge(F.is_sum_bus_parameter.MakeChild(), owner=[max_power]),
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

    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        """
        Warn if deprecated vcc/gnd aliases are being used.

        vcc/gnd are always connected to hv/lv (1 connection each).
        If they have more than 1 connection, something external is using them.
        """

        def count_edges(count: list[int], edge: graph.BoundEdge):
            count[0] += 1

        vcc_node = self.vcc.get()
        gnd_node = self.gnd.get()

        count_vcc: list[int] = [0]
        count_gnd: list[int] = [0]

        fbrk.EdgeInterfaceConnection.visit_connected_edges(
            bound_node=vcc_node.instance, ctx=count_vcc, f=count_edges
        )
        fbrk.EdgeInterfaceConnection.visit_connected_edges(
            bound_node=gnd_node.instance, ctx=count_gnd, f=count_edges
        )

        aliases_used: list[str] = []

        if count_vcc[0] != 1:
            aliases_used.append("vcc")
        if count_gnd[0] != 1:
            aliases_used.append("gnd")

        if aliases_used:
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    f"Deprecated ElectricPower aliases used in {self.pretty_repr()}: "
                    f"{', '.join(aliases_used)}. Use hv/lv instead."
                )
