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

    anode.add_dependant(fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [anode]))
    cathode.add_dependant(fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [cathode]))

    _can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeEdge(["anode"], ["cathode"]))

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

    _pin_association_heuristic = fabll.Traits.MakeEdge(
        F.has_pin_association_heuristic.MakeChild(
            mapping={
                anode: ["A", "Anode", "+"],
                cathode: ["K", "C", "Cathode", "-"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
    )

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.anode.get(), trait=F.has_net_name_suggestion
        ).setup(name="anode", level=F.has_net_name_suggestion.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.cathode.get(), trait=F.has_net_name_suggestion
        ).setup(name="cathode", level=F.has_net_name_suggestion.Level.SUGGESTED)

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
