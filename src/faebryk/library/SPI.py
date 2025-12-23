# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class SPI(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    sclk = F.ElectricLogic.MakeChild()
    miso = F.ElectricLogic.MakeChild()
    mosi = F.ElectricLogic.MakeChild()

    frequency = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Hertz)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="SCLK", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[sclk],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="MISO", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[miso],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="MOSI", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[mosi],
        ),
    ]

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
