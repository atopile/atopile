# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F
# from faebryk.core.zig.gen.faebryk.interface import EdgeInterface

logger = logging.getLogger(__name__)


class CapacitorElectrolytic(fabll.Node):
    anode = F.Electrical.MakeChild()
    cathode = F.Electrical.MakeChild()

    power = F.ElectricPower.MakeChild()

    _can_bridge = F.can_bridge.MakeChild(in_=anode, out_=cathode)

    capacitance = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Farad)
    max_voltage = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Volt)
    # temperature_coefficient = fabll.Parameter.MakeChild_Enum(
    #     enum_t=TemperatureCoefficient
    # )

    S = F.has_simple_value_representation.Spec
    _simple_repr = F.has_simple_value_representation.MakeChild(
        S(capacitance, tolerance=True),
        S(max_voltage),
        # S(temperature_coefficient),
    )

    _pin_association_heuristic = F.has_pin_association_heuristic_lookup_table.MakeChild(
        mapping={
            anode: ["anode", "a"],
            cathode: ["cathode", "c"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    # anode_edge = fabll.EdgeField(
    #     [anode],
    #     [power, "hv"],
    #     edge=EdgePointer.build(
    #         identifier="anode", order=None
    #     ),  # TODO: Change to electrical connect
    # )
    # cathode_edge = fabll.EdgeField(
    #     [cathode],
    #     [power, "lv"],
    #     edge=EdgePointer.build(
    #         identifier="cathode", order=None
    #     ),  # TODO: Change to electrical connect
    # )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import CapacitorElectrolytic, ElectricPower

        electrolytic_cap = new CapacitorElectrolytic
        electrolytic_cap.capacitance = 1000uF +/- 20%
        electrolytic_cap.max_voltage = 25V
        electrolytic_cap.package = "radial_8x12"  # 8mm diameter, 12mm height

        # Connect to power supply for bulk filtering
        power_supply = new ElectricPower
        assert power_supply.voltage within 12V +/- 10%

        # CRITICAL: Observe polarity! Anode to positive, cathode to negative
        power_supply.hv ~ electrolytic_cap.anode    # Positive terminal
        power_supply.lv ~ electrolytic_cap.cathode  # Negative terminal

        # Alternative bridge syntax (maintains polarity)
        power_supply.hv ~> electrolytic_cap ~> power_supply.lv

        # Common values and applications:
        # - 10-100uF: Local power supply filtering
        # - 100-1000uF: Bulk power supply capacitance
        # - 1000-10000uF: Main power supply smoothing
        # - Audio coupling: 1-100uF (mind polarity!)

        # WARNING: Reverse voltage will damage electrolytic capacitors!
        # Use ceramic or film capacitors for AC coupling applications
        """,
        language=F.has_usage_example.Language.ato,
    )
