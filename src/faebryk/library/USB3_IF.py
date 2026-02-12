# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB3_IF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb_if = F.USB2_0_IF.MakeChild()
    rx = F.DifferentialPair.MakeChild()
    tx = F.DifferentialPair.MakeChild()
    gnd_drain = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RX", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[rx],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="TX", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[tx],
        ),
    ]

    # USB 3.2 spec constraints
    # Note: USB 2.0 constraints (VBUS, D+/D- reference, D+/D- impedance)
    # are inherited via usb_if (USB2_0_IF)
    _parameter_constraints = [
        # SuperSpeed RX differential impedance: 90 Ohm +/- 15% (USB 3.2 spec Table 6-12)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [rx, F.DifferentialPair.impedance], 76.5, 103.5, unit=F.Units.Ohm
        ),
        # SuperSpeed TX differential impedance: 90 Ohm +/- 15% (USB 3.2 spec Table 6-12)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [tx, F.DifferentialPair.impedance], 76.5, 103.5, unit=F.Units.Ohm
        ),
        # SuperSpeed RX reference voltage: 0.8V to 1.2V (USB 3.2 spec Table 6-12)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [
                rx,
                F.DifferentialPair.p,
                F.ElectricSignal.reference,
                F.ElectricPower.voltage,
            ],
            0.8,
            1.2,
            unit=F.Units.Volt,
        ),
        # SuperSpeed TX reference voltage: 0.8V to 1.2V (USB 3.2 spec Table 6-12)
        F.Literals.Numbers.MakeChild_SetSuperset(
            [
                tx,
                F.DifferentialPair.p,
                F.ElectricSignal.reference,
                F.ElectricPower.voltage,
            ],
            0.8,
            1.2,
            unit=F.Units.Volt,
        ),
    ]
