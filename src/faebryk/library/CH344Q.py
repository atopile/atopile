# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.util import assert_once

logger = logging.getLogger(__name__)


class CH344Q(F.CH344):
    """
    Quad UART to USB bridge
    """

    class UARTWrapper(Module):
        uart: F.UART
        tnow: F.ElectricLogic

        @assert_once
        def enable_tnow_mode(self, owner: Module):
            """
            Set TNOW mode for specified UART for use with RS485 tranceivers.
            The TNOW pin can be connected to the tx_enable and rx_enable
            pins of the RS485 tranceiver for automatic half-duplex control.
            """
            self.uart.dtr.set_weak(on=False, owner=owner)
            self.uart.dtr.connect(self.tnow)

    uartwrapper = L.list_field(4, UARTWrapper)

    @assert_once
    def enable_chip_default_settings(self, owner: Module):
        """
        Use the chip default settings instead of the ones stored in the internal EEPROM
        """
        self.uart[0].rts.set_weak(on=False, owner=owner)

    @assert_once
    def enable_status_or_modem_signals(
        self, owner: Module, modem_signals: bool = False
    ):
        """
        Enable rx, tx and usb status signal outputs instead of UART modem signals.
        """
        if modem_signals:
            self.uart[3].rts.set_weak(on=False, owner=owner)
            return
        self.act.connect(self.uart[3].dcd)
        self.indicator_tx.connect(self.uart[3].ri)
        self.indicator_rx.connect(self.uart[3].dsr)

    @assert_once
    def enable_hardware_flow_conrol(self, owner: Module):
        """
        Enable UART hardware flow control
        """
        self.uart[3].dcd.set_weak(on=False, owner=owner)
        # TODO: check if this should just be connected to gnd as there is an
        # internal pull-up resistor

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def descriptive_properties(self):
        return F.has_descriptive_properties_defined(
            {
                DescriptiveProperties.manufacturer: "WCH",
                DescriptiveProperties.partno: "CH344Q",
            },
        )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                # 1 nc
                "2": self.uart[2].dsr.signal,
                "3": self.uart[2].ri.signal,
                "4": self.uart[2].dcd.signal,
                "5": self.osc[1],
                "6": self.osc[0],
                "7": self.reset.signal,
                "8": self.power.lv,
                "9": self.power.hv,
                "10": self.uart[1].cts.signal,
                "11": self.uart[1].rts.signal,
                "12": self.uart[1].base_uart.tx.signal,
                "13": self.uart[1].base_uart.rx.signal,
                "14": self.uart[3].dcd.signal,
                "15": self.uart[3].ri.signal,
                "16": self.uart[3].dsr.signal,
                "17": self.uart[1].dsr.signal,
                "18": self.uart[1].dtr.signal,
                "19": self.uart[2].dtr.signal,
                "20": self.power.lv,
                "21": self.uart[2].base_uart.tx.signal,
                "22": self.uart[2].base_uart.rx.signal,
                "23": self.power.lv,
                "24": self.power.hv,
                "25": self.uart[1].ri.signal,
                "26": self.uart[2].cts.signal,
                "27": self.uart[2].rts.signal,
                "28": self.uart[1].dcd.signal,
                "29": self.uart[0].dsr.signal,
                "30": self.uart[0].base_uart.tx.signal,
                "31": self.uart[0].base_uart.rx.signal,
                "32": self.uart[0].ri.signal,
                "33": self.uart[0].dcd.signal,
                "34": self.uart[3].dtr.signal,
                "35": self.power.lv,
                "36": self.power.hv,
                "37": self.uart[3].base_uart.tx.signal,
                "38": self.uart[3].base_uart.rx.signal,
                "39": self.uart[0].dtr.signal,
                "40": self.uart[0].rts.signal,
                "41": self.uart[0].cts.signal,
                "42": self.usb.n.signal,
                "43": self.usb.p.signal,
                "44": self.test.signal,
                "45": self.uart[3].rts.signal,
                "46": self.uart[3].cts.signal,
                "47": self.power.lv,
                "48": self.power.hv,
            }
        )

    def __preinit__(self):
        ...
        # ------------------------------------
        #           connections
        # ------------------------------------
        for uart, uartwrapper in zip(self.uart, self.uartwrapper):
            uart.connect(uartwrapper.uart)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
