# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.util import times


class MultiSPI(ModuleInterface):
    def __init__(self, data_lane_count: int) -> None:
        super().__init__()
        self._data_lane_count = data_lane_count

    clock: F.ElectricLogic
    chip_select: F.ElectricLogic

    @L.rt_field
    def data(self):
        return times(self._data_lane_count, F.ElectricLogic)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.clock.line.add(
            F.has_net_name("clock", level=F.has_net_name.Level.SUGGESTED)
        )
        self.chip_select.line.add(
            F.has_net_name("chip_select", level=F.has_net_name.Level.SUGGESTED)
        )
        for i, line in enumerate(self.data):
            line.add(F.has_net_name(f"data_{i}", level=F.has_net_name.Level.SUGGESTED))

    # ----------------------------------------
    #              usage example
    # ----------------------------------------
    usage_example = L.f_field(F.has_usage_example)(
        example="""
        #pragma experiment("MODULE_TEMPLATING")

        import MultiSPI, ElectricLogic, ElectricPower

        module UsageExample:
            # Connect power reference for logic levels
            power_3v3 = new ElectricPower
            assert power_3v3.voltage within 3.3V +/- 5%

            # Standard MultiSPI interface
            multi_spi = new MultiSPI<data_lane_count=4>
            multi_spi.reference_shim ~ power_3v3

            # Connect to external signals
            spi_clock = new ElectricLogic
            spi_cs = new ElectricLogic
            spi_data = new ElectricLogic[4]

            multi_spi.clock ~ spi_clock
            multi_spi.chip_select ~ spi_cs
            multi_spi.data[0] ~ spi_data[0]
            multi_spi.data[1] ~ spi_data[1]
            multi_spi.data[2] ~ spi_data[2]
            multi_spi.data[3] ~ spi_data[3]
        """,
        language=F.has_usage_example.Language.ato,
    )
