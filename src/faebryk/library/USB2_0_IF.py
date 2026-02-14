# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB2_0_IF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    d = F.DifferentialPair.MakeChild()
    buspower = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="DATA", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[d],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="VBUS", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[buspower],
        ),
    ]

    # USB 2.0 spec constraints
    _parameter_constraints = [
        # VBUS: 5V +/- 5% (USB 2.0 spec section 7.2.1)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [buspower, F.ElectricPower.voltage], 4.75, 5.25, unit=F.Units.Volt
        ),
        # D+/D- reference voltage: 3.0V to 3.6V (USB 2.0 spec section 7.1.1)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [
                d,
                F.DifferentialPair.p,
                F.ElectricSignal.reference,
                F.ElectricPower.voltage,
            ],
            3.0,
            3.6,
            unit=F.Units.Volt,
        ),
        # Differential impedance: 90 Ohm +/- 15% (USB 2.0 spec section 7.1.1)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [d, F.DifferentialPair.impedance], 76.5, 103.5, unit=F.Units.Ohm
        ),
    ]
