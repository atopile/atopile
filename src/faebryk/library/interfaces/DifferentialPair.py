# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class DifferentialPair(ModuleInterface):
    p: F.ElectricSignal
    n: F.ElectricSignal

    impedance = L.p_field(
        units=P.Ω,
        likely_constrained=True,
        soft_set=L.Range(10 * P.Ω, 100 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricSignal.connect_all_module_references(self)
        )

    usage_example = L.f_field(F.has_usage_example)(
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
    )
