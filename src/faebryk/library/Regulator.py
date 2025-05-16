# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class Regulator(Module):
    power_in: F.ElectricPower
    power_out: F.ElectricPower

    def __preinit__(self):
        self.power_out.add(F.Power.is_power_source.impl()())
        self.power_in.add(F.Power.is_power_sink.impl()())

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)
