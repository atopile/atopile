# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class SPIFlash(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power = F.ElectricPower.MakeChild()
    qspi = F.MultiSPI.MakeChild(4)

    memory_size = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Byte)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.U
    )

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import SPIFlash, ElectricPower, ElectricLogic

        spi_flash = new SPIFlash
        spi_flash.memory_size = 16MB  # Common sizes: 1MB, 2MB, 4MB, 8MB, 16MB, 32MB

        # Connect power supply
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        spi_flash.power ~ power_3v3

        # Connect SPI/QSPI interface
        microcontroller.qspi ~ spi_flash.qspi

        # For standard SPI (using only 2 data lines)
        microcontroller.spi.sclk ~ spi_flash.qspi.sclk
        microcontroller.spi.mosi ~ spi_flash.qspi.ios[0]  # DI/IO0
        microcontroller.spi.miso ~ spi_flash.qspi.ios[1]  # DO/IO1

        # Chip select
        chip_select = new ElectricLogic
        chip_select.reference ~ power_3v3
        microcontroller.gpio_cs ~ chip_select.line
        spi_flash.qspi.cs ~ chip_select

        # For Quad SPI (4x faster)
        # microcontroller.qspi.ios[2] ~ spi_flash.qspi.ios[2]  # WP/IO2
        # microcontroller.qspi.ios[3] ~ spi_flash.qspi.ios[3]  # HOLD/IO3

        # Common applications: firmware storage, data logging, file systems
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
