# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P
from test.common.resources.fabll_modules.RP2040Pinmux import RP2040Pinmux

logger = logging.getLogger(__name__)


class RP2040(Module):
    """
    Raspberry Pi RP2040 MCU
    Note: Don't forget to use the pinmux!
    """

    class PIO(F.ElectricLogic):
        pass

    class ADC(F.ElectricSignal):
        pass

    class PWM(ModuleInterface):
        A: F.ElectricLogic
        B: F.ElectricLogic

        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    class CoreRegulator(Module):
        power_in: F.ElectricPower
        power_out: F.ElectricPower

        def __preinit__(self):
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

            # TODO get tolerance
            self.power_out.voltage.constrain_subset(
                L.Range.from_center_rel(1.1 * P.V, 0.05)
            )
            self.power_in.voltage.constrain_subset(L.Range(1.8 * P.V, 3.3 * P.V))

        @L.rt_field
        def bridge(self):
            return F.can_bridge_defined(self.power_in, self.power_out)

    class SPI(F.SPI):
        cs: F.ElectricLogic

    class UART(ModuleInterface):
        base_uart: F.UART_Base
        rts: F.ElectricLogic
        cts: F.ElectricLogic

        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    class USBPowerControl(ModuleInterface):
        ovcur_det: F.ElectricLogic
        vbus_det: F.ElectricLogic
        vbus_en: F.ElectricLogic

        @L.rt_field
        def single_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    # power
    power_io: F.ElectricPower
    power_adc: F.ElectricPower
    power_core: F.ElectricPower
    power_usb_phy: F.ElectricPower
    core_regulator: CoreRegulator

    io = L.list_field(30, F.Electrical)
    io_soft = L.list_field(6, F.Electrical)

    # IO
    qspi = L.f_field(F.MultiSPI)(data_lane_count=4)
    swd: F.SWD
    xtal_if: F.XtalIF

    run: F.ElectricLogic
    usb: F.USB2_0_IF.Data
    factory_test_enable: F.Electrical
    usb_power_control: USBPowerControl

    # peripherals
    spi = L.list_field(2, SPI)
    pwm = L.list_field(8, PWM)
    i2c = L.list_field(2, F.I2C)
    uart = L.list_field(2, UART)
    pio = L.list_field(2, PIO)
    adc = L.list_field(4, ADC)
    clock_in = L.list_field(2, F.ElectricLogic)
    clock_out = L.list_field(4, F.ElectricLogic)
    gpio = L.list_field(30 + 6, F.ElectricLogic)

    def __preinit__(self):
        # TODO get tolerance
        self.power_adc.voltage.constrain_subset(
            L.Range.from_center_rel(3.3 * P.V, 0.05)
        )
        self.power_usb_phy.voltage.constrain_subset(
            L.Range.from_center_rel(3.3 * P.V, 0.05)
        )
        self.power_core.voltage.constrain_subset(
            L.Range.from_center_rel(1.1 * P.V, 0.05)
        )
        self.power_io.voltage.constrain_subset(L.Range(1.8 * P.V, 3.3 * P.V))

        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_node_references(
            [self.power_io]
            + self.gpio
            + self.spi
            + self.pwm
            + self.uart
            + self.i2c
            + self.pio
            + self.clock_in
            + self.clock_out
            + [self.usb_power_control]  # TODO is this the right ref?
            + [self.run]
            + [self.swd]
            + [self.qspi]
        )
        self.power_io.lv.connect(self.xtal_if.gnd)

        # QSPI pins reusable for soft gpio
        self.qspi.data[3].line.connect(self.io_soft[0])
        self.qspi.clock.line.connect(self.io_soft[1])
        self.qspi.data[0].line.connect(self.io_soft[2])
        self.qspi.data[2].line.connect(self.io_soft[3])
        self.qspi.data[1].line.connect(self.io_soft[4])
        self.qspi.chip_select.line.connect(self.io_soft[5])

        # ADC pins shared with GPIO
        self.adc[0].line.connect(self.io[26])
        self.adc[1].line.connect(self.io[27])
        self.adc[2].line.connect(self.io[28])
        self.adc[3].line.connect(self.io[29])
        F.ElectricLogic.connect_all_node_references(self.adc + [self.power_adc])

    @L.rt_field
    def pinmux(self):
        return RP2040Pinmux(self)

    @L.rt_field
    def decoupled(self):
        return F.can_be_decoupled_rails(self.power_io, self.power_core)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf"
    )

    mfr = L.f_field(F.has_explicit_part.by_mfr)("Raspberry Pi", "RP2040")

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power_io.hv,
                "2": self.io[0],
                "3": self.io[1],
                "4": self.io[2],
                "5": self.io[3],
                "6": self.io[4],
                "7": self.io[5],
                "8": self.io[6],
                "9": self.io[7],
                "10": self.power_io.hv,
                "11": self.io[8],
                "12": self.io[9],
                "13": self.io[10],
                "14": self.io[11],
                "15": self.io[12],
                "16": self.io[13],
                "17": self.io[14],
                "18": self.io[15],
                "19": self.factory_test_enable,
                "20": self.xtal_if.xin,
                "21": self.xtal_if.xout,
                "22": self.power_io.hv,
                "23": self.power_core.hv,
                "24": self.swd.clk.line,
                "25": self.swd.dio.line,
                "26": self.run.line,
                "27": self.io[16],
                "28": self.io[17],
                "29": self.io[18],
                "30": self.io[19],
                "31": self.io[20],
                "32": self.io[21],
                "33": self.power_io.hv,
                "34": self.io[22],
                "35": self.io[23],
                "36": self.io[24],
                "37": self.io[25],
                "38": self.io[26],
                "39": self.io[27],
                "40": self.io[28],
                "41": self.io[29],
                "42": self.power_io.hv,
                "43": self.power_adc.hv,
                "44": self.core_regulator.power_in.hv,
                "45": self.core_regulator.power_out.hv,
                "46": self.usb.n.line,
                "47": self.usb.p.line,
                "48": self.power_usb_phy.hv,
                "49": self.power_io.hv,
                "50": self.power_core.hv,
                "51": self.qspi.data[3].line,
                "52": self.qspi.clock.line,
                "53": self.qspi.data[0].line,
                "54": self.qspi.data[2].line,
                "55": self.qspi.data[1].line,
                "56": self.qspi.chip_select.line,
                "57": self.power_io.lv,  # center pad
            }
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_adc.hv: ["ADC_AVDD"],
                self.power_core.hv: ["DVDD"],
                self.power_io.lv: ["GND"],
                self.io[0]: ["GPIO0"],
                self.io[1]: ["GPIO1"],
                self.io[10]: ["GPIO10"],
                self.io[11]: ["GPIO11"],
                self.io[12]: ["GPIO12"],
                self.io[13]: ["GPIO13"],
                self.io[14]: ["GPIO14"],
                self.io[15]: ["GPIO15"],
                self.io[16]: ["GPIO16"],
                self.io[17]: ["GPIO17"],
                self.io[18]: ["GPIO18"],
                self.io[19]: ["GPIO19"],
                self.io[2]: ["GPIO2"],
                self.io[20]: ["GPIO20"],
                self.io[21]: ["GPIO21"],
                self.io[22]: ["GPIO22"],
                self.io[23]: ["GPIO23"],
                self.io[24]: ["GPIO24"],
                self.io[25]: ["GPIO25"],
                self.io[26]: ["GPIO26_ADC0"],
                self.io[27]: ["GPIO27_ADC1"],
                self.io[28]: ["GPIO28_ADC2"],
                self.io[29]: ["GPIO29_ADC3"],
                self.io[3]: ["GPIO3"],
                self.io[4]: ["GPIO4"],
                self.io[5]: ["GPIO5"],
                self.io[6]: ["GPIO6"],
                self.io[7]: ["GPIO7"],
                self.io[8]: ["GPIO8"],
                self.io[9]: ["GPIO9"],
                self.power_io.hv: ["IOVDD"],
                self.qspi.clock.line: ["QSPI_SCLK"],
                self.qspi.data[0].line: ["QSPI_SD0"],
                self.qspi.data[1].line: ["QSPI_SD1"],
                self.qspi.data[2].line: ["QSPI_SD2"],
                self.qspi.data[3].line: ["QSPI_SD3"],
                self.qspi.chip_select.line: ["QSPI_SS", "QSPI_SS_N"],
                self.run.line: ["RUN"],
                self.swd.clk.line: ["SWCLK"],
                self.swd.dio.line: ["SWD"],
                self.factory_test_enable: ["TESTEN"],
                self.usb.n.line: ["USB_DM"],
                self.usb.p.line: ["USB_DP"],
                self.power_usb_phy.hv: ["USB_VDD"],
                self.core_regulator.power_in.hv: ["VREG_IN"],
                self.core_regulator.power_out.hv: ["VREG_VOUT"],
                self.xtal_if.xin: ["XIN"],
                self.xtal_if.xout: ["XOUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
