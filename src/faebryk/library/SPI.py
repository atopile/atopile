# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class SPI(ModuleInterface):
    sclk: F.ElectricLogic
    miso: F.ElectricLogic
    mosi: F.ElectricLogic

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.sclk.line.add(F.has_net_name("SCLK", level=F.has_net_name.Level.SUGGESTED))
        self.miso.line.add(F.has_net_name("MISO", level=F.has_net_name.Level.SUGGESTED))
        self.mosi.line.add(F.has_net_name("MOSI", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import SPI, ElectricPower, ElectricLogic

        spi_bus = new SPI

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        spi_bus.sclk.reference ~ power_3v3
        spi_bus.miso.reference ~ power_3v3
        spi_bus.mosi.reference ~ power_3v3

        # Connect to microcontroller
        microcontroller.spi ~ spi_bus

        # Connect to SPI device with chip select
        chip_select = new ElectricLogic
        chip_select.reference ~ power_3v3
        flash_memory.spi ~ spi_bus
        flash_memory.cs ~ chip_select
        """,
        language=F.has_usage_example.Language.ato,
    )
