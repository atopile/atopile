# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class CapacitorPolarized(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    anode = F.Electrical.MakeChild()
    cathode = F.Electrical.MakeChild()

    capacitance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Farad)
    max_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    anode_lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [anode])
    cathode_lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [cathode])

    pad_names = [
        fabll.Traits.MakeEdge(
            F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"a|anode|\+"),
            [anode_lead],
        ),
        fabll.Traits.MakeEdge(
            F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"k|c|cathode|-"),
            [cathode_lead],
        ),
    ]

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeEdge(["anode"], ["cathode"]),
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(capacitance, tolerance=True),
            S(max_voltage),
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.C)
    )

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    # optional interface to automatically connect HV to anode and LV to cathode
    # power = F.ElectricPower.MakeChild()

    # anode_edge = fabll.MakeEdge(
    #     [anode],
    #     [power, "hv"],
    #     edge=EdgePointer.build(
    #         identifier="anode", order=None
    #     ),  # TODO: Change to electrical connect
    # )
    # cathode_edge = fabll.MakeEdge(
    #     [cathode],
    #     [power, "lv"],
    #     edge=EdgePointer.build(
    #         identifier="cathode", order=None
    #     ),  # TODO: Change to electrical connect
    # )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import CapacitorPolarized, ElectricPower

        electrolytic_cap = new CapacitorPolarized
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
        ).put_on_type()
    )
