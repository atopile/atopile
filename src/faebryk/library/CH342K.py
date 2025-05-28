# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class CH342K(F.CH342):
    """
    USB to double Base UART converter (no modem signals)

    ESSOP-10-150mil
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    uart_base = L.list_field(2, F.UART_Base)
    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    explicit_part = L.f_field(F.has_explicit_part.by_mfr)(
        mfr="WCH(Jiangsu Qin Heng)", partno="CH342K"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_3v.lv: ["GND"],
                self.uart_base[0].rx.line: ["RXD0"],
                self.uart_base[0].tx.line: ["TXD0"],
                self.uart_base[1].rx.line: ["RXD1"],
                self.uart_base[1].tx.line: ["TXD1"],
                self.usb.usb_if.d.p.line: ["UD+"],
                self.usb.usb_if.d.n.line: ["UD-"],
                self.power_3v.hv: ["V3"],
                self.integrated_regulator.power_in.hv: ["VDD5"],
                self.power_io.hv: ["VIO"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass
