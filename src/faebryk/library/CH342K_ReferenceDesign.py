# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class CH342K_ReferenceDesign(Module):
    """
    Minimal reference implementation of the CH342K.

    - Single power source (USB)
    - IO at 3.3V
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb_uart_converter: F.CH342K

    def __preinit__(self):
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.usb_uart_converter.set_power_configuration(
            F.CH342.ChipPowerConfiguration.USB_5V,
            F.CH342.IOPowerConfiguration.INTERNAL_3V3,
        )

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        self.usb_uart_converter.integrated_regulator.power_in.get_trait(
            F.can_be_decoupled
        ).decouple(owner=self)
        self.usb_uart_converter.power_3v.get_trait(F.can_be_decoupled).decouple(
            owner=self
        )
        self.usb_uart_converter.power_io.get_trait(F.can_be_decoupled).decouple(
            owner=self
        )
