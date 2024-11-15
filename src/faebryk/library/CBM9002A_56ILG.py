# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties


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
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://corebai.com/Data/corebai/upload/file/20240201/CBM9002A.pdf"
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Corebai Microelectronics",
            DescriptiveProperties.partno: "CBM9002A-56ILG",
        }
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                "1": self.rdy[0].signal,
                "2": self.rdy[1].signal,
                #
                "4": self.xtalout,
                "5": self.xtalin,
                "13": self.ifclk.signal,
                "54": self.clkout.signal,
                #
                "8": self.usb.usb_if.d.p.signal,
                "9": self.usb.usb_if.d.n.signal,
                #
                "15": self.i2c.scl.signal,
                "16": self.i2c.sda.signal,
                #
                "29": self.ctl[0].signal,
                "30": self.ctl[1].signal,
                "31": self.ctl[2].signal,
                #
                "42": self.reset.signal,
                #
                "44": self.wakeup.signal,
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
                "33": self.PA[0].signal,
                "34": self.PA[1].signal,
                "35": self.PA[2].signal,
                "36": self.PA[3].signal,
                "37": self.PA[4].signal,
                "38": self.PA[5].signal,
                "39": self.PA[6].signal,
                "40": self.PA[7].signal,
                #
                "18": self.PB[0].signal,
                "19": self.PB[1].signal,
                "20": self.PB[2].signal,
                "21": self.PB[3].signal,
                "22": self.PB[4].signal,
                "23": self.PB[5].signal,
                "24": self.PB[6].signal,
                "25": self.PB[7].signal,
                #
                "45": self.PD[0].signal,
                "46": self.PD[1].signal,
                "47": self.PD[2].signal,
                "48": self.PD[3].signal,
                "49": self.PD[4].signal,
                "50": self.PD[5].signal,
                "51": self.PD[6].signal,
                "52": self.PD[7].signal,
            }
        )

    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.avcc.lv: ["AGND"],
                self.avcc.hv: ["AVCC"],
                self.clkout.signal: ["CLKOUT"],
                self.ctl[0].signal: ["CTL0_FLAGA"],
                self.ctl[1].signal: ["CTL1_FLAGB"],
                self.ctl[2].signal: ["CTL2_FLAGC"],
                self.usb.usb_if.d.n.signal: ["DMINUS"],
                self.usb.usb_if.d.p.signal: ["DPLUS"],
                self.vcc.lv: ["EP"],
                self.vcc.lv: ["GND"],
                self.ifclk.signal: ["IFCLK"],
                self.PA[0].signal: ["PA0_INT0#"],
                self.PA[1].signal: ["PA1_INT1#"],
                self.PA[2].signal: ["PA2_SLOE"],
                self.PA[3].signal: ["PA3_WU2"],
                self.PA[4].signal: ["PA4_FIFOADR0"],
                self.PA[5].signal: ["PA5_FIFOADR1"],
                self.PA[6].signal: ["PA6_PKEND"],
                self.PA[7].signal: ["PA7_FLAGD_SLCS#"],
                self.PB[0].signal: ["PB0_FD0"],
                self.PB[1].signal: ["PB1_FD1"],
                self.PB[2].signal: ["PB2_FD2"],
                self.PB[3].signal: ["PB3_FD3"],
                self.PB[4].signal: ["PB4_FD4"],
                self.PB[5].signal: ["PB5_FD5"],
                self.PB[6].signal: ["PB6_FD6"],
                self.PB[7].signal: ["PB7_FD7"],
                self.PD[0].signal: ["PD0_FD8"],
                self.PD[1].signal: ["PD1_FD9"],
                self.PD[2].signal: ["PD2_FD10"],
                self.PD[3].signal: ["PD3_FD11"],
                self.PD[4].signal: ["PD4_FD12"],
                self.PD[5].signal: ["PD5_FD13"],
                self.PD[6].signal: ["PD6_FD14"],
                self.PD[7].signal: ["PD7_FD15"],
                self.rdy[0].signal: ["RDY0_SLRD"],
                self.rdy[1].signal: ["RDY1_SLWR"],
                self.reset.signal: ["RESET#"],
                self.i2c.scl.signal: ["SCL"],
                self.i2c.sda.signal: ["SDA"],
                self.vcc.hv: ["VCC"],
                self.wakeup.signal: ["WAKEUP"],
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
