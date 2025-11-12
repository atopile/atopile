# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class DifferentialPair(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    p = F.ElectricSignal.MakeChild()
    n = F.ElectricSignal.MakeChild()
    reference = F.ElectricPower.MakeChild()

    impedance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.ChildField(fabll.is_interface)
    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    def terminated(self) -> "DifferentialPair":
        terminated_bus = DifferentialPair.bind_typegraph(self.tg).create_instance(
            g=self.tg.get_graph_view()
        )
        rs = [
            F.Resistor.bind_typegraph(self.tg).create_instance(
                g=self.tg.get_graph_view()
            )
            for _ in range(2)
        ]

        for r in rs:
            r.resistance.get().constrain_to_literal(
                g=self.tg.get_graph_view(),
                value=self.impedance.get().force_extract_literal(),
            )

        rs[0].get_trait(F.can_bridge).bridge(terminated_bus.p.get(), self.p.get())
        rs[1].get_trait(F.can_bridge).bridge(terminated_bus.n.get(), self.n.get())
        self.get_trait(fabll.is_interface).connect_shallow_to(terminated_bus)

        return terminated_bus

        # """Attach required net name suffixes for KiCad differential pair detection.

        # Ensures nets associated with the positive and negative lines end with
        # `_p` and `_n` respectively. The naming algorithm will append these
        # required affixes while still deconflicting names globally.
        # """
        # self.p.line.add(F.has_net_name_affix.setup(suffix="_P"))
        # self.n.line.add(F.has_net_name_affix.setup(suffix="_N"))

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import DifferentialPair, ElectricPower

        diff_pair = new DifferentialPair
        diff_pair.impedance = 100ohm +/- 10%  # Common for high-speed signals

        # Connect power reference for signal levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        diff_pair.p.reference ~ power_3v3
        diff_pair.n.reference ~ power_3v3

        # Connect between transmitter and receiver
        transmitter.diff_out ~ diff_pair
        diff_pair ~ receiver.diff_in

        # For terminated transmission line
        terminated_pair = diff_pair.terminated()
        transmitter.diff_out ~ terminated_pair

        # Common applications: USB, Ethernet, PCIe, HDMI
        usb_dp_dn = new DifferentialPair
        usb_dp_dn.impedance = 90ohm +/- 10%
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
