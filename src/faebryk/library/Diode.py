# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class Diode(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    anode = F.Electrical.MakeChild()
    cathode = F.Electrical.MakeChild()

    forward_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    """Current at which the design is functional"""
    reverse_working_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    reverse_leakage_current = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ampere
    )
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    """Current at which the design may be damaged"""

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    anode_lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [anode])
    cathode_lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [cathode])

    anode_attatchable = fabll.Traits.MakeEdge(
        F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"a|anode|\+"), [anode_lead]
    )
    cathode_attatchable = fabll.Traits.MakeEdge(
        F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"k|c|cathode|-"),
        [cathode_lead],
    )

    can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeChild(["anode"], ["cathode"]))

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(forward_voltage, tolerance=True, prefix="Vf"),
            S(current, prefix="If"),
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.D)
    )

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="anode", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[anode],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="cathode", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[cathode],
        ),
    ]

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
