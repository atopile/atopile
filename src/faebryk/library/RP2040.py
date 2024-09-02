# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class RP2040(Module):
    io_vdd: F.ElectricPower
    adc_vdd: F.ElectricPower
    core_vdd: F.ElectricPower
    vreg_in: F.ElectricPower
    vreg_out: F.ElectricPower
    power_vusb: F.ElectricPower
    gpio = L.list_field(30, F.Electrical)
    run: F.ElectricLogic
    usb: F.USB2_0
    qspi = L.f_field(F.MultiSPI)(data_lane_count=4)
    xin: F.Electrical
    xout: F.Electrical
    test: F.Electrical
    swd: F.SWD
    # TODO: these peripherals and more can be mapped to different pins
    i2c: F.I2C
    uart: F.UART_Base

    def __preinit__(self):
        # TODO
        return
        # decouple power rails and connect GNDs toghether
        gnd = self.io_vdd.lv
        for pwrrail in [
            self.io_vdd,
            self.adc_vdd,
            self.core_vdd,
            self.vreg_in,
            self.vreg_out,
            self.usb.usb_if.buspower,
        ]:
            pwrrail.lv.connect(gnd)
            pwrrail.decoupled.decouple()

        # set parameters
        self.vreg_out.voltage.merge(1.1 * P.V)
        self.io_vdd.voltage.merge(3.3 * P.V)

        F.ElectricLogic.connect_all_node_references(
            self.get_children(direct_only=True, types=ModuleInterface).difference(
                {self.adc_vdd, self.core_vdd}
            )
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf"
    )

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.io_vdd.hv,
                "2": self.gpio[0],
                "3": self.gpio[1],
                "4": self.gpio[2],
                "5": self.gpio[3],
                "6": self.gpio[4],
                "7": self.gpio[5],
                "8": self.gpio[6],
                "9": self.gpio[7],
                "10": self.io_vdd.hv,
                "11": self.gpio[8],
                "12": self.gpio[9],
                "13": self.gpio[10],
                "14": self.gpio[11],
                "15": self.gpio[12],
                "16": self.gpio[13],
                "17": self.gpio[14],
                "18": self.gpio[15],
                "19": self.xin,
                "20": self.xout,
                "21": self.test,
                "22": self.io_vdd.hv,
                "23": self.core_vdd.hv,
                "24": self.swd.clk.signal,
                "25": self.swd.dio.signal,
                "26": self.run.signal,
                "27": self.gpio[16],
                "28": self.gpio[17],
                "29": self.gpio[18],
                "30": self.gpio[19],
                "31": self.gpio[20],
                "32": self.gpio[21],
                "33": self.io_vdd.hv,
                "34": self.gpio[22],
                "35": self.gpio[23],
                "36": self.gpio[24],
                "37": self.gpio[25],
                "38": self.gpio[26],
                "39": self.gpio[27],
                "40": self.gpio[28],
                "41": self.gpio[29],
                "42": self.io_vdd.hv,
                "43": self.adc_vdd.hv,
                "44": self.vreg_in.hv,
                "45": self.vreg_out.hv,
                "46": self.usb.usb_if.d.n,
                "47": self.usb.usb_if.d.p,
                "48": self.usb.usb_if.buspower.hv,
                "49": self.io_vdd.hv,
                "50": self.core_vdd.hv,
                "51": self.qspi.data[3].signal,
                "52": self.qspi.clk.signal,
                "53": self.qspi.data[0].signal,
                "54": self.qspi.data[2].signal,
                "55": self.qspi.data[1].signal,
                "56": self.qspi.cs.signal,
                "57": self.io_vdd.lv,
            }
        )
