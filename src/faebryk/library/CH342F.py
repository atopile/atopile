# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
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
                "1": self.uart[0].uart.ri.signal,
                "2": self.usb.usb_if.buspower.lv,
                "3": self.usb.usb_if.d.p.signal,
                "4": self.usb.usb_if.d.n.signal,
                "5": self.power_io.hv,
                "6": self.power_3v.hv,
                "7": self.integrated_regulator.power_in.hv,
                "8": self.usb.usb_if.buspower.hv,
                "9": self.reset.signal,
                "10": self.uart[1].uart.cts.signal,
                "11": self.uart[1].uart.rts.signal,
                "12": self.uart[1].uart.base_uart.rx.signal,
                "13": self.uart[1].uart.base_uart.tx.signal,
                "14": self.uart[1].uart.dsr.signal,
                "15": self.uart[1].uart.dtr.signal,
                "16": self.uart[1].uart.dcd.signal,
                "17": self.uart[1].uart.ri.signal,
                "18": self.uart[0].uart.cts.signal,
                "19": self.uart[0].uart.rts.signal,
                "20": self.uart[0].uart.base_uart.rx.signal,
                "21": self.uart[0].uart.base_uart.tx.signal,
                "22": self.uart[0].uart.dsr.signal,
                "23": self.uart[0].uart.dtr.signal,
                "24": self.uart[0].uart.dcd.signal,
                "25": self.usb.usb_if.buspower.lv,
            }
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.uart[0].uart.cts.signal: ["CTS0"],
                self.uart[1].uart.cts.signal: ["CTS1"],
                self.uart[0].uart.dcd.signal: ["DCD0"],
                self.uart[1].uart.dcd.signal: ["DCD1"],
                self.uart[0].uart.dsr.signal: ["DSR0"],
                self.uart[1].uart.dsr.signal: ["DSR1"],
                self.uart[0].uart.dtr.signal: ["DTR0"],
                self.uart[1].uart.dtr.signal: ["DTR1"],
                # self.power_3v.lv: ["EP"],
                self.power_3v.lv: ["GND"],
                self.uart[0].uart.ri.signal: ["RI0"],
                self.uart[1].uart.ri.signal: ["RI1"],
                self.reset.signal: ["RST"],
                self.uart[0].uart.rts.signal: ["RTS0"],
                self.uart[1].uart.rts.signal: ["RTS1"],
                self.uart[0].uart.base_uart.rx.signal: ["RXD0"],
                self.uart[1].uart.base_uart.rx.signal: ["RXD1"],
                self.uart[0].uart.base_uart.tx.signal: ["TXD0"],
                self.uart[1].uart.base_uart.tx.signal: ["TXD1"],
                self.usb.usb_if.d.p.signal: ["UD+"],
                self.usb.usb_if.d.n.signal: ["UD-"],
                self.power_3v.hv: ["V3"],
                self.vbus_detect.signal: ["VBUS"],
                self.integrated_regulator.power_in.hv: ["VDD5"],
                self.power_io.hv: ["VIO"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "WCH(Jiangsu Qin Heng)",
            DescriptiveProperties.partno: "CH342F",
        }
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
