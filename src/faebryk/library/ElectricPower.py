# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


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
    vcc = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

    # Connect deprecated aliases to the actual rails
    # @raytallen: bug, we seem to be filtering out siblings
    _vcc_to_hv = fabll.MakeEdge(
        [vcc],
        [hv],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )
    _gnd_to_lv = fabll.MakeEdge(
        [gnd],
        [lv],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)

    can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeEdge(in_=[""], out_=[""]))

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
