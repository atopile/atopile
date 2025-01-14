# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module, ModuleException
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P
from faebryk.libs.util import assert_once

logger = logging.getLogger(__name__)


class CH342(Module):
    """
    Base class for CH342x USB to double UART converter
    """

    class IntegratedLDO(Module):
        power_in: F.ElectricPower
        power_out: F.ElectricPower

        def __preinit__(self):
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

            self.power_out.voltage.constrain_superset(
                L.Range.from_center_rel(3.3 * P.V, 0.1)
            )
            self.power_in.voltage.constrain_subset(L.Range(4 * P.V, 5.5 * P.V))

        @L.rt_field
        def bridge(self):
            return F.can_bridge_defined(self.power_in, self.power_out)

    class IOPowerConfiguration(Enum):
        USB_5V = auto()
        """IO powered by USB 5V"""
        INTERNAL_3V3 = auto()
        """IO powered by the integrated 3.3V regulator"""
        EXTERNAL = auto()
        """IO powered by an external 1.8V-5V source"""

    class ChipPowerConfiguration(Enum):
        USB_5V = auto()
        """Chip powered by USB 5V"""
        EXTERNAL_5V = auto()
        """Chip powered by an external 5V source"""
        EXTERNAL_3V3 = auto()
        """Chip powered by an external 3.3V source"""

    @assert_once
    def set_power_configuration(
        self,
        chip_power_configuration: ChipPowerConfiguration = ChipPowerConfiguration.USB_5V,  # noqa: E501
        io_voltage_configuration: IOPowerConfiguration = IOPowerConfiguration.INTERNAL_3V3,  # noqa: E501
    ):
        """Configure how the chip is powered, and what the io voltage will be."""
        # how is the chip powered
        if chip_power_configuration == self.ChipPowerConfiguration.EXTERNAL_3V3:
            # short the integrated regulator power input to the output to disable
            self.integrated_regulator.power_in.connect(self.power_3v)
        elif chip_power_configuration == self.ChipPowerConfiguration.USB_5V:
            # use the USB power to power the chip
            self.usb.usb_if.buspower.connect(self.integrated_regulator.power_in)
        else:
            # use an external 5V power source for the chip
            ...

        # how is the IO powered
        if io_voltage_configuration == self.IOPowerConfiguration.INTERNAL_3V3:
            # check if the integrated regulator is not disabled
            if chip_power_configuration == self.ChipPowerConfiguration.EXTERNAL_3V3:
                raise ModuleException(
                    self,
                    "Cannot power IO from the integrated regulator when it is disabled, use 'EXTERNAL' power configuration instead",  # noqa: E501
                )
            # io is 3v3 and powered by the integrated regulator (10mA max)
            self.power_io.connect(self.power_3v)
            F.ElectricLogic.connect_all_module_references(
                self,
                exclude={
                    self.integrated_regulator.power_in,
                },
            )
        elif io_voltage_configuration == self.IOPowerConfiguration.USB_5V:
            # io is 5v and powered by USB
            self.power_io.connect(self.usb.usb_if.buspower)
            F.ElectricLogic.connect_all_module_references(
                self,
                exclude={
                    self.integrated_regulator.power_in,
                    self.integrated_regulator.power_out,
                    self.power_3v,
                },
            )
        else:
            # io is 1.8V-5V and powered by an external source
            ...

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb: F.USB2_0
    # uart_base = L.list_field(2, F.UART_Base)

    integrated_regulator: IntegratedLDO
    power_io: F.ElectricPower
    power_3v: F.ElectricPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wch-ic.com/downloads/CH342DS1_PDF.html"
    )
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    def __preinit__(self):
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.power_3v.voltage.constrain_subset(L.Range.from_center_rel(3.3 * P.V, 0.1))
        self.power_io.voltage.constrain_subset(L.Range(1.7 * P.V, 5.5 * P.V))

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

        # chip internal connection
        self.integrated_regulator.power_out.connect(self.power_3v)
