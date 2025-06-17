# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class CBM9002A_56ILG(Module):
    """
    USB 2.0 peripheral controller with 16K RAM, 40 GPIOs, and serial debugging

    Cypress Semicon CY7C68013A-56L Clone
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    PA = L.list_field(8, F.ElectricLogic)
    PB = L.list_field(8, F.ElectricLogic)
    PD = L.list_field(8, F.ElectricLogic)
    usb: F.USB2_0
    i2c: F.I2C

    avcc: F.ElectricPower
    vcc: F.ElectricPower

    rdy = L.list_field(2, F.ElectricLogic)
    ctl = L.list_field(3, F.ElectricLogic)
    reset: F.ElectricLogic
    wakeup: F.ElectricLogic

    ifclk: F.ElectricLogic
    clkout: F.ElectricLogic
    xtalin: F.Electrical
    xtalout: F.Electrical

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    explicit_part = L.f_field(F.has_explicit_part.by_mfr)(
        "Corebai Microelectronics", "CBM9002A-56ILG"
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                "1": self.rdy[0].line,
                "2": self.rdy[1].line,
                #
                "4": self.xtalout,
                "5": self.xtalin,
                "13": self.ifclk.line,
                "54": self.clkout.line,
                #
                "8": self.usb.usb_if.d.p.line,
                "9": self.usb.usb_if.d.n.line,
                #
                "15": self.i2c.scl.line,
                "16": self.i2c.sda.line,
                #
                "29": self.ctl[0].line,
                "30": self.ctl[1].line,
                "31": self.ctl[2].line,
                #
                "42": self.reset.line,
                #
                "44": self.wakeup.line,
                #
                "3": self.avcc.hv,
                "7": self.avcc.hv,
                #
                "6": self.avcc.lv,
                "10": self.avcc.lv,
                #
                "11": self.vcc.hv,
                "17": self.vcc.hv,
                "27": self.vcc.hv,
                "32": self.vcc.hv,
                "43": self.vcc.hv,
                "55": self.vcc.hv,
                #
                "12": self.vcc.lv,
                "14": self.vcc.lv,  # reserved
                "26": self.vcc.lv,
                "28": self.vcc.lv,
                "41": self.vcc.lv,
                "53": self.vcc.lv,
                "56": self.vcc.lv,
                "57": self.vcc.lv,  # thermal pad
                #
                "33": self.PA[0].line,
                "34": self.PA[1].line,
                "35": self.PA[2].line,
                "36": self.PA[3].line,
                "37": self.PA[4].line,
                "38": self.PA[5].line,
                "39": self.PA[6].line,
                "40": self.PA[7].line,
                #
                "18": self.PB[0].line,
                "19": self.PB[1].line,
                "20": self.PB[2].line,
                "21": self.PB[3].line,
                "22": self.PB[4].line,
                "23": self.PB[5].line,
                "24": self.PB[6].line,
                "25": self.PB[7].line,
                #
                "45": self.PD[0].line,
                "46": self.PD[1].line,
                "47": self.PD[2].line,
                "48": self.PD[3].line,
                "49": self.PD[4].line,
                "50": self.PD[5].line,
                "51": self.PD[6].line,
                "52": self.PD[7].line,
            }
        )

    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.avcc.lv: ["AGND"],
                self.avcc.hv: ["AVCC"],
                self.clkout.line: ["CLKOUT"],
                self.ctl[0].line: ["CTL0_FLAGA"],
                self.ctl[1].line: ["CTL1_FLAGB"],
                self.ctl[2].line: ["CTL2_FLAGC"],
                self.usb.usb_if.d.n.line: ["DMINUS"],
                self.usb.usb_if.d.p.line: ["DPLUS"],
                self.vcc.lv: ["EP"],
                self.vcc.lv: ["GND"],
                self.ifclk.line: ["IFCLK"],
                self.PA[0].line: ["PA0_INT0#"],
                self.PA[1].line: ["PA1_INT1#"],
                self.PA[2].line: ["PA2_SLOE"],
                self.PA[3].line: ["PA3_WU2"],
                self.PA[4].line: ["PA4_FIFOADR0"],
                self.PA[5].line: ["PA5_FIFOADR1"],
                self.PA[6].line: ["PA6_PKEND"],
                self.PA[7].line: ["PA7_FLAGD_SLCS#"],
                self.PB[0].line: ["PB0_FD0"],
                self.PB[1].line: ["PB1_FD1"],
                self.PB[2].line: ["PB2_FD2"],
                self.PB[3].line: ["PB3_FD3"],
                self.PB[4].line: ["PB4_FD4"],
                self.PB[5].line: ["PB5_FD5"],
                self.PB[6].line: ["PB6_FD6"],
                self.PB[7].line: ["PB7_FD7"],
                self.PD[0].line: ["PD0_FD8"],
                self.PD[1].line: ["PD1_FD9"],
                self.PD[2].line: ["PD2_FD10"],
                self.PD[3].line: ["PD3_FD11"],
                self.PD[4].line: ["PD4_FD12"],
                self.PD[5].line: ["PD5_FD13"],
                self.PD[6].line: ["PD6_FD14"],
                self.PD[7].line: ["PD7_FD15"],
                self.rdy[0].line: ["RDY0_SLRD"],
                self.rdy[1].line: ["RDY1_SLWR"],
                self.reset.line: ["RESET#"],
                self.i2c.scl.line: ["SCL"],
                self.i2c.sda.line: ["SDA"],
                self.vcc.hv: ["VCC"],
                self.wakeup.line: ["WAKEUP"],
                self.xtalin: ["XTALIN"],
                self.xtalout: ["XTALOUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    # ----------------------------------------
    #                connections
    # ----------------------------------------
    def __preinit__(self):
        F.ElectricLogic.connect_all_node_references(
            self.get_children(direct_only=False, types=ModuleInterface).difference(
                {self.avcc, self.usb.usb_if.buspower}
            )
        )
