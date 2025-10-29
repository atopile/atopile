# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class Diode(fabll.Node):
    forward_voltage = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Volt)
    # Current at which the design is functional
    current = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Ampere)
    reverse_working_voltage = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Volt)
    reverse_leakage_current = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Ampere)
    # Current at which the design may be damaged
    max_current = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Ampere)

    anode = F.Electrical.MakeChild()
    cathode = F.Electrical.MakeChild()

    _can_bridge = F.can_bridge.MakeChild(in_=anode, out_=cathode)

    _simple_repr = F.has_simple_value_representation_based_on_params_chain.MakeChild(
        params={"forward_voltage": forward_voltage},
    ).put_on_type()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.D
    ).put_on_type()

    _pin_association_heuristic = F.has_pin_association_heuristic_lookup_table.MakeChild(
        mapping={
            anode: ["A", "Anode", "+"],
            cathode: ["K", "C", "Cathode", "-"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    # anode.add_dependant(
    #     F.has_net_name.MakeChild(name="anode", level=F.has_net_name.Level.SUGGESTED)
    # )
    # cathode.add_dependant(
    #     F.has_net_name.MakeChild(name="cathode", level=F.has_net_name.Level.SUGGESTED)
    # )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Diode, Resistor, ElectricPower

        diode = new Diode
        diode.forward_voltage = 0.7V +/- 10%
        diode.current = 10mA +/- 5%
        diode.reverse_working_voltage = 50V
        diode.max_current = 100mA
        diode.package = "SOD-123"

        # Connect as rectifier
        ac_input ~ diode.anode
        diode.cathode ~ dc_output

        # With current limiting resistor
        power_supply.hv ~> current_limit_resistor ~> diode ~> power_supply.lv
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
