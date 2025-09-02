# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class FilterElectricalLC(F.Filter):
    """
    Basic Electrical LC filter
    """

    in_: F.ElectricSignal
    out: F.ElectricSignal
    capacitor: F.Capacitor
    inductor: F.Inductor

    z0 = L.p_field(units=P.ohm)

    def __preinit__(self):
        self.order.alias_is(2)
        self.response.alias_is(F.Filter.Response.LOWPASS)

        Li = self.inductor.inductance
        C = self.capacitor.capacitance
        fc = self.cutoff_frequency

        fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))
        Li.alias_is((1 / (2 * math.pi * fc)) ** 2 / C)
        C.alias_is((1 / (2 * math.pi * fc)) ** 2 / Li)

        # low pass
        self.in_.line.connect_via(
            (self.inductor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.line.connect_via(self.inductor, self.out.line)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import FilterElectricalLC, ElectricSignal, ElectricPower

        module UsageExample:
            power_supply = new ElectricPower
            power_supply.voltage = 5V +/- 5%

            input_signal = new ElectricSignal
            input_signal.reference ~ power_supply
            output_signal = new ElectricSignal
            output_signal.reference ~ power_supply

            lc_filter = new FilterElectricalLC
            lc_filter.cutoff_frequency = 1000Hz +/- 10%
            lc_filter.z0 = 50ohm +/- 5%

            lc_filter.in_ ~ input_signal
            lc_filter.out ~ output_signal
        """,
        language=F.has_usage_example.Language.ato,
    )
