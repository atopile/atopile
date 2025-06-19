# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
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
            self.uart.dtr.set_weak(on=False, owner=owner).resistance.constrain_subset(
                L.Range.from_center_rel(4.7 * P.kohm, 0.05)
            )
            self.uart.dtr.connect(self.tnow)

    uartwrapper = L.list_field(4, UARTWrapper)

    @assert_once
    def enable_chip_default_settings(self, owner: Module):
        """
        Use the chip default settings instead of the ones stored in the internal EEPROM
        """
        self.uart[0].rts.set_weak(on=False, owner=owner).resistance.constrain_subset(
            L.Range.from_center_rel(4.7 * P.kohm, 0.05)
        )

    @assert_once
    def enable_status_or_modem_signals(
        self, owner: Module, modem_signals: bool = False
    ):
        """
        Enable rx, tx and usb status signal outputs instead of UART modem signals.
        """
        if modem_signals:
            self.uart[3].rts.set_weak(
                on=False, owner=owner
            ).resistance.constrain_subset(L.Range.from_center_rel(4.7 * P.kohm, 0.05))
            return
        self.act.connect(self.uart[3].dcd)
        self.indicator_tx.connect(self.uart[3].ri)
        self.indicator_rx.connect(self.uart[3].dsr)

    @assert_once
    def enable_hardware_flow_conrol(self, owner: Module):
        """
        Enable UART hardware flow control
        """
        self.uart[3].dcd.set_weak(on=False, owner=owner).resistance.constrain_subset(
            L.Range.from_center_rel(4.7 * P.kohm, 0.05)
        )
        # TODO: check if this should just be connected to gnd as there is an
        # internal pull-up resistor

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C2988084")

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                # 1 nc
                "2": self.uart[2].dsr.line,
                "3": self.uart[2].ri.line,
                "4": self.uart[2].dcd.line,
                "5": self.osc[1],
                "6": self.osc[0],
                "7": self.reset.line,
                "8": self.power.lv,
                "9": self.power.hv,
                "10": self.uart[1].cts.line,
                "11": self.uart[1].rts.line,
                "12": self.uart[1].base_uart.tx.line,
                "13": self.uart[1].base_uart.rx.line,
                "14": self.uart[3].dcd.line,
                "15": self.uart[3].ri.line,
                "16": self.uart[3].dsr.line,
                "17": self.uart[1].dsr.line,
                "18": self.uart[1].dtr.line,
                "19": self.uart[2].dtr.line,
                "20": self.power.lv,
                "21": self.uart[2].base_uart.tx.line,
                "22": self.uart[2].base_uart.rx.line,
                "23": self.power.lv,
                "24": self.power.hv,
                "25": self.uart[1].ri.line,
                "26": self.uart[2].cts.line,
                "27": self.uart[2].rts.line,
                "28": self.uart[1].dcd.line,
                "29": self.uart[0].dsr.line,
                "30": self.uart[0].base_uart.tx.line,
                "31": self.uart[0].base_uart.rx.line,
                "32": self.uart[0].ri.line,
                "33": self.uart[0].dcd.line,
                "34": self.uart[3].dtr.line,
                "35": self.power.lv,
                "36": self.power.hv,
                "37": self.uart[3].base_uart.tx.line,
                "38": self.uart[3].base_uart.rx.line,
                "39": self.uart[0].dtr.line,
                "40": self.uart[0].rts.line,
                "41": self.uart[0].cts.line,
                "42": self.usb.n.line,
                "43": self.usb.p.line,
                "44": self.test.line,
                "45": self.uart[3].rts.line,
                "46": self.uart[3].cts.line,
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
