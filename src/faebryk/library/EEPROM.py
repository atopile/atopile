# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class EEPROM(Module):
    """
    Generic EEPROM module with F.I2C interface.
    """

    def set_address(self, addr: int):
        """
        Configure the address of the EEPROM by setting the address pins.
        """
        assert addr < (1 << len(self.address))

        for i, e in enumerate(self.address):
            e.set(addr & (1 << i) != 0)

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    memory_size = L.p_field(
        units=P.bit,
        likely_constrained=True,
        domain=L.Domains.Numbers.NATURAL(),
        soft_set=L.Range(128 * P.bit, 1024 * P.kbit),
    )

    power: F.ElectricPower
    i2c: F.I2C
    write_protect: F.ElectricLogic
    address = L.list_field(3, F.ElectricLogic)

    # ----------------------------------------
    #                traits
    # ----------------------------------------

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import EEPROM, ElectricPower, I2C, Resistor

        eeprom = new EEPROM
        eeprom.memory_size = 32kbit

        # Connect power supply
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        eeprom.power ~ power_3v3

        # Connect I2C bus
        i2c_bus = new I2C
        i2c_bus.frequency = 400kHz  # Fast mode
        eeprom.i2c ~ i2c_bus

        # Connect to microcontroller
        microcontroller.i2c ~ i2c_bus

        # Set device address using address pins
        eeprom.set_address(0)  # Device address 0b000

        # Connect address pins to power rails for different addresses
        eeprom.address[0].line ~ power_3v3.lv  # A0 = 0
        eeprom.address[1].line ~ power_3v3.lv  # A1 = 0
        eeprom.address[2].line ~ power_3v3.lv  # A2 = 0

        # Write protect control (optional)
        eeprom.write_protect.reference ~ power_3v3
        eeprom.write_protect.line ~ power_3v3.lv  # Enable writes

        # Pull-up resistors for I2C (if not provided elsewhere)
        sda_pullup = new Resistor
        scl_pullup = new Resistor
        sda_pullup.resistance = 4.7kohm +/- 5%
        scl_pullup.resistance = 4.7kohm +/- 5%
        i2c_bus.sda.line ~> sda_pullup ~> power_3v3.hv
        i2c_bus.scl.line ~> scl_pullup ~> power_3v3.hv
        """,
        language=F.has_usage_example.Language.ato,
    )
