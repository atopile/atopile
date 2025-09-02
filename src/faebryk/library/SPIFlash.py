# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class SPIFlash(Module):
    power: F.ElectricPower
    qspi = L.f_field(F.MultiSPI)(4)

    memory_size = L.p_field(
        units=P.byte,
        domain=L.Domains.Numbers.NATURAL(),
    )
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def single_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import SPIFlash, ElectricPower, ElectricLogic

        module UsageExample:
            spi_flash = new SPIFlash
            spi_flash.memory_size = 16000000  # 16MB in bytes

            # Connect power supply
            power_3v3 = new ElectricPower
            assert power_3v3.voltage within 3.3V +/- 5%
            spi_flash.power ~ power_3v3

            # Chip select
            chip_select = new ElectricLogic
            chip_select.reference ~ power_3v3
            spi_flash.qspi.chip_select ~ chip_select
        """,
        language=F.has_usage_example.Language.ato,
    )
