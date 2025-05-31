# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.util import assert_once, times

logger = logging.getLogger(__name__)


class CH342F(F.CH342):
    """
    USB to double Base UART converter

    QFN-24-EP(4x4)
    """

    class UARTWrapper(Module):
        uart: F.UART
        tnow: F.ElectricLogic
        ...

        @assert_once
        def enable_tnow_mode(self, owner: Module):
            """
            Set TNOW mode for specified UART for use with RS485 tranceivers.
            The TNOW pin can be connected to the tx_enable and rx_enable
            pins of the RS485 tranceiver for automatic half-duplex control.
            """
            self.uart.dtr.set_weak(on=False, owner=owner)
            self.uart.dtr.connect(self.tnow)

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    vbus_detect: F.ElectricLogic

    reset: F.ElectricLogic
    active: F.ElectricLogic

    uart = times(2, UARTWrapper)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.uart[0].uart.ri.line,
                "2": self.usb.usb_if.buspower.lv,
                "3": self.usb.usb_if.d.p.line,
                "4": self.usb.usb_if.d.n.line,
                "5": self.power_io.hv,
                "6": self.power_3v.hv,
                "7": self.integrated_regulator.power_in.hv,
                "8": self.usb.usb_if.buspower.hv,
                "9": self.reset.line,
                "10": self.uart[1].uart.cts.line,
                "11": self.uart[1].uart.rts.line,
                "12": self.uart[1].uart.base_uart.rx.line,
                "13": self.uart[1].uart.base_uart.tx.line,
                "14": self.uart[1].uart.dsr.line,
                "15": self.uart[1].uart.dtr.line,
                "16": self.uart[1].uart.dcd.line,
                "17": self.uart[1].uart.ri.line,
                "18": self.uart[0].uart.cts.line,
                "19": self.uart[0].uart.rts.line,
                "20": self.uart[0].uart.base_uart.rx.line,
                "21": self.uart[0].uart.base_uart.tx.line,
                "22": self.uart[0].uart.dsr.line,
                "23": self.uart[0].uart.dtr.line,
                "24": self.uart[0].uart.dcd.line,
                "25": self.usb.usb_if.buspower.lv,
            }
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.uart[0].uart.cts.line: ["CTS0"],
                self.uart[1].uart.cts.line: ["CTS1"],
                self.uart[0].uart.dcd.line: ["DCD0"],
                self.uart[1].uart.dcd.line: ["DCD1"],
                self.uart[0].uart.dsr.line: ["DSR0"],
                self.uart[1].uart.dsr.line: ["DSR1"],
                self.uart[0].uart.dtr.line: ["DTR0"],
                self.uart[1].uart.dtr.line: ["DTR1"],
                # self.power_3v.lv: ["EP"],
                self.power_3v.lv: ["GND"],
                self.uart[0].uart.ri.line: ["RI0"],
                self.uart[1].uart.ri.line: ["RI1"],
                self.reset.line: ["RST"],
                self.uart[0].uart.rts.line: ["RTS0"],
                self.uart[1].uart.rts.line: ["RTS1"],
                self.uart[0].uart.base_uart.rx.line: ["RXD0"],
                self.uart[1].uart.base_uart.rx.line: ["RXD1"],
                self.uart[0].uart.base_uart.tx.line: ["TXD0"],
                self.uart[1].uart.base_uart.tx.line: ["TXD1"],
                self.usb.usb_if.d.p.line: ["UD+"],
                self.usb.usb_if.d.n.line: ["UD-"],
                self.power_3v.hv: ["V3"],
                self.vbus_detect.line: ["VBUS"],
                self.integrated_regulator.power_in.hv: ["VDD5"],
                self.power_io.hv: ["VIO"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    explicit_part = L.f_field(F.has_explicit_part.by_mfr)(
        mfr="WCH(Jiangsu Qin Heng)", partno="CH342F"
    )

    def __preinit__(self) -> None:
        # ----------------------------------------
        #                aliasess
        # ----------------------------------------

        # ----------------------------------------
        #            parametrization
        # ----------------------------------------

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        pass
        # TODO: specialize base uarts from CH342 base class
        # uarts = times(2, F.UART)
        # for uart, uart_base in zip(uarts, self.uart_base):
        #    uart_base.specialize(uart)
        #    self.add(uart)
