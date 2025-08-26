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

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Regulator, ElectricPower

        regulator = new Regulator

        # Connect input power (unregulated)
        power_input = new ElectricPower
        assert power_input.voltage within 7V to 20V  # Wide input range
        regulator.power_in ~ power_input

        # Connect output power (regulated)
        power_output = new ElectricPower
        regulator.power_out ~ power_output

        # Output voltage depends on regulator type:
        # - LDO: Vout = Vin - Dropout_voltage
        # - Switching: Vout = Function(Vin, feedback network)

        # Connect to load
        load_circuit ~ power_output

        # Note: This is a generic regulator interface
        # Use specific regulator types for actual implementations:
        # - LDO for low noise, low efficiency
        # - Buck for high efficiency step-down
        # - Boost for step-up conversion
        # - Buck-boost for bidirectional conversion
        """,
        language=F.has_usage_example.Language.ato,
    )
