# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import typing
from dataclasses import dataclass

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_defined_footprint import has_defined_footprint
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_simple_value_representation_defined import (
    has_simple_value_representation_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.JTAG import JTAG
from faebryk.library.QFN import QFN
from faebryk.library.UART_Base import UART_Base
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


# TODO
class _ESP_ADC(ModuleInterface):
    def __init__(self, channel_count: int) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            CHANNELS = times(channel_count, Electrical)

        self.IFs = IFS(self)


class _ESP_SDIO(ModuleInterface):
    def __init__(self):
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            DATA = times(4, Electrical)
            CLK = Electrical()
            CMD = Electrical()
            GND = Electrical()

        self.IFs = IFS(self)


class _ESP32_EMAC(ModuleInterface):
    def __init__(self):
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            TXD = times(4, Electrical)
            RXD = times(4, Electrical)
            TX_CLK = Electrical()
            RX_CLK = Electrical()
            TX_EN = Electrical()
            RX_ER = Electrical()
            RX_DV = Electrical()
            CLK_OUT = Electrical()
            CLK_OUT_180 = Electrical()
            TX_ER = Electrical()
            MDC_out = Electrical()
            MDI_in = Electrical()
            MDO_out = Electrical()
            CRS_out = Electrical()
            COL_out = Electrical()

        self.IFs = IFS(self)


class _ESP32_SPI(ModuleInterface):
    def __init__(self):
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            D = Electrical()
            Q = Electrical()
            WP = Electrical()
            HD = Electrical()

            CS = Electrical()

            CLK = Electrical()
            GND = Electrical()

        self.IFs = IFS(self)


class ESP32(Module):
    def __init__(self):
        super().__init__()

        self.add_trait(has_simple_value_representation_defined("ESP32"))
        self.add_trait(has_designator_prefix_defined("U"))

        class IFS(Module.IFS()):
            # Analog
            VDDA0 = Electrical()
            LNA_IN = Electrical()
            VDD3P30 = Electrical()
            VDD3P31 = Electrical()
            SENSOR_VP = Electrical()
            # VDD3P3_RTC
            SENSOR_CAPP = Electrical()
            SENSOR_CAPN = Electrical()
            SENSOR_VN = Electrical()
            CHIP_PU = Electrical()
            VDET_1 = Electrical()
            VDET_2 = Electrical()
            _32K_XP = Electrical()
            _32K_XN = Electrical()
            GPIO25 = Electrical()
            GPIO26 = Electrical()
            GPIO27 = Electrical()
            MTMS = Electrical()
            MTDI = Electrical()
            VDD3P3_RTC = Electrical()
            MTCK = Electrical()
            MTDO = Electrical()
            GPIO2 = Electrical()
            GPIO0 = Electrical()
            GPIO4 = Electrical()
            # VDD_SDIO
            GPIO16 = Electrical()
            VDD_SDIO = Electrical()
            GPIO17 = Electrical()
            SD_DATA_2 = Electrical()
            SD_DATA_3 = Electrical()
            SD_CMD = Electrical()
            SD_CLK = Electrical()
            SD_DATA_0 = Electrical()
            SD_DATA_1 = Electrical()
            # VDD3P3_CPU
            GPIO5 = Electrical()
            GPIO18 = Electrical()
            GPIO23 = Electrical()
            VDD3P3_CPU = Electrical()
            GPIO19 = Electrical()
            GPIO22 = Electrical()
            U0RXD = Electrical()
            U0TXD = Electrical()
            GPIO21 = Electrical()
            # Analog
            VDDA1 = Electrical()
            XTAL_N = Electrical()
            XTAL_P = Electrical()
            VDDA2 = Electrical()
            CAP2 = Electrical()
            CAP1 = Electrical()
            GND = Electrical()

            # High Level Functions
            I2C = times(2, I2C)
            SDIO_SLAVE = _ESP_SDIO()
            SDIO_HOST = times(2, _ESP_SDIO)
            UART = UART_Base()
            JTAG = JTAG()
            TOUCH = times(10, Electrical)
            GPIO = times(40 - 6, Electrical)
            RTC_GPIO = times(18, Electrical)
            ADC = [
                None,
                _ESP_ADC(channel_count=8),
                _ESP_ADC(channel_count=10),
            ]
            SPI = times(4, _ESP32_SPI)
            EMAC = _ESP32_EMAC()

            # Power
            POWER_RTC = ElectricPower()
            POWER_CPU = ElectricPower()
            POWER_SDIO = ElectricPower()
            POWER_ANALOG = ElectricPower()

        self.IFs = IFS(self)

        x = self.IFs
        self.pinmap = {
            # Analog
            "1": x.VDDA0,
            "2": x.LNA_IN,
            "3": x.VDD3P30,
            "4": x.SENSOR_VP,
            # VDD"3"P3_RTC
            "5": x.SENSOR_CAPP,
            "6": x.SENSOR_CAPN,
            "7": x.SENSOR_VN,
            "8": x.CHIP_PU,
            "9": x.VDET_1,
            "10": x.VDET_2,
            "11": x._32K_XP,
            "12": x._32K_XN,
            "13": x.GPIO25,
            "14": x.GPIO26,
            "15": x.GPIO27,
            "16": x.MTMS,
            "17": x.MTDI,
            "18": x.VDD3P3_RTC,
            "19": x.MTCK,
            "20": x.MTDO,
            "21": x.GPIO2,
            "22": x.GPIO0,
            "23": x.GPIO4,
            # VDD_SDIO
            "24": x.GPIO16,
            "25": x.VDD_SDIO,
            "26": x.GPIO17,
            "27": x.SD_DATA_2,
            "28": x.SD_DATA_3,
            "29": x.SD_CMD,
            "30": x.SD_CLK,
            "31": x.SD_DATA_0,
            "32": x.SD_DATA_1,
            # VDD"3"P3_CPU
            "33": x.GPIO5,
            "34": x.GPIO18,
            "35": x.GPIO23,
            "36": x.VDD3P3_CPU,
            "37": x.GPIO19,
            "38": x.GPIO22,
            "39": x.U0RXD,
            "40": x.U0TXD,
            "41": x.GPIO21,
            # Analog
            "42": x.VDDA1,
            "43": x.XTAL_N,
            "44": x.XTAL_P,
            "45": x.VDDA2,
            "46": x.CAP2,
            "47": x.CAP1,
            "48": x.GND,
        }

        self.add_trait(can_attach_to_footprint_via_pinmap(self.pinmap))

        # SPI0 is connected to SPI1 (Arbiter)
        x.SPI[0].IFs.Q.connect(x.SPI[1].IFs.Q)
        x.SPI[0].IFs.D.connect(x.SPI[1].IFs.D)
        x.SPI[0].IFs.HD.connect(x.SPI[1].IFs.HD)
        x.SPI[0].IFs.WP.connect(x.SPI[1].IFs.WP)
        x.SPI[0].IFs.CLK.connect(x.SPI[1].IFs.CLK)
        x.SPI[0].IFs.CS.connect(x.SPI[1].NODES.CS)

        x.POWER_RTC.IFs.hv.connect(x.VDD3P3_RTC)
        x.POWER_RTC.IFs.lv.connect(x.GND)
        x.POWER_CPU.IFs.hv.connect(x.VDD3P3_CPU)
        x.POWER_CPU.IFs.lv.connect(x.GND)
        x.POWER_SDIO.IFs.hv.connect(x.VDD_SDIO)
        x.POWER_SDIO.IFs.lv.connect(x.GND)
        x.POWER_ANALOG.IFs.hv.connect(x.VDDA0)
        x.POWER_ANALOG.IFs.hv.connect(x.VDDA1)
        x.POWER_ANALOG.IFs.hv.connect(x.VDDA2)
        x.POWER_ANALOG.IFs.lv.connect(x.GND)

        self.pinmux = _ESP32_Pinmux(self)

    def get_gpio(self, idx: int):
        filtered = [20, 24, 28, 29, 30, 31]
        # count of elements in filtered that are smaller than idx:
        offset = len([x for x in filtered if x < idx])
        return self.IFs.GPIO[idx - offset]


class _ESP32_D0WD(ESP32):
    def __init__(self):
        super().__init__()

        self.add_trait(
            has_defined_footprint(
                QFN(
                    pin_cnt=48,
                    size_xy_mm=(5, 5),
                    pitch_mm=0.350,
                    exposed_thermal_pad_cnt=1,
                    exposed_thermal_pad_dimensions_mm=(3.700, 3.700),
                    has_thermal_vias=True,
                )
            )
        )


class _ESP32_D0WD_V3(_ESP32_D0WD):
    # Dual core - No embedded flash/PSRAM
    ...


class _ESP32_D0WDR2_V3(_ESP32_D0WD):
    # Dual core - 2 MB PSRAM
    ...


@dataclass(frozen=True)
class _Function:
    interface: Electrical
    name: str
    type: "typing.Any"


@dataclass(frozen=False)
class _Pad:
    no: int
    name: str
    interface: ModuleInterface
    power_domain: "typing.Any"
    #
    at_reset: "typing.Any"
    after_reset: "typing.Any"
    drive_strenght: "typing.Any"
    #
    functions: dict[int, _Function]
    #
    current_function: _Function | None = None


class _Mux(Module):
    def __init__(self, input: Electrical, *outputs: Electrical) -> None:
        super().__init__()

        class _IFS(Module.IFS()):
            IN = Electrical()
            OUT = times(len(outputs), Electrical)

        self.IFs = _IFS(self)

        input.connect(self.IFs.IN)
        self.map = dict(zip(outputs, self.IFs.OUT))
        for o1, o2 in self.map.items():
            o1.connect(o2)

    def select(self, output: Electrical):
        self.IFs.IN.connect(self.map[output])


def _matrix(esp32: ESP32):
    x = esp32.IFs

    # fmt: off
    return [
        # Power
        _Pad(1,  "VDDA",         x.VDDA0,        "VDDA supply in",           None, None, None, {}),                          # noqa: E501
        _Pad(43, "VDDA",         x.VDDA1,        "VDDA supply in",           None, None, None, {}),                          # noqa: E501
        _Pad(46, "VDDA",         x.VDDA2,        "VDDA supply in",           None, None, None, {}),                          # noqa: E501
        _Pad(2,  "LNA_IN",       x.LNA_IN,       "VDD3P3",                   None, None, None, {}),                          # noqa: E501
        _Pad(3,  "VDD3P3",       x.VDD3P30,      "VDD3P3 supply in",         None, None, None, {}),                          # noqa: E501
        _Pad(4,  "VDD3P3",       x.VDD3P31,      "VDD3P3 supply in",         None, None, None, {}),                          # noqa: E501
        _Pad(19, "VDD3P3_RTC",   x.VDD3P3_RTC,   "VDD3P3_RTC supply in",     None, None, None, {}),                          # noqa: E501
        _Pad(26, "VDD_SDIO",     x.VDD_SDIO,     "VDD_SDIO supply out/in",   None, None, None, {}),                          # noqa: E501
        _Pad(37, "VDD3P3_CPU",   x.VDD3P3_CPU,   "VDD3P3_CPU supply in",     None, None, None, {}),                          # noqa: E501
        _Pad(5,  "SENSOR_VP",    x.SENSOR_VP,    "VDD3P3_RTC",               "oe=0,ie=0", "oe=0,ie=0", None, {               # noqa: E501
            1 : _Function(x.ADC[1].CHANNELS[0],           "ADC1_CH0",     None),                                             # noqa: E501
            3 : _Function(x.RTC_GPIO[0],                  "RTC_GPIO0",    None),                                             # noqa: E501
            5 : _Function(esp32.get_gpio(36),             "GPIO36",       "I"),                                              # noqa: E501
        }),                                                                                                                 # noqa: E501
        _Pad(6,  "SENSOR_CAPP",  x.SENSOR_CAPP,  "VDD3P3_RTC",               "oe=0,ie=0", "oe=0,ie=0", None, {               # noqa: E501
            1 : _Function(x.ADC[1].CHANNELS[1],           "ADC1_CH1",     None),                                             # noqa: E501
            3 : _Function(x.RTC_GPIO[1],                  "RTC_GPIO1",    None),                                             # noqa: E501
            5 : _Function(esp32.get_gpio(37),             "GPIO37",       "I"),                                              # noqa: E501
        }),                                                                                                                 # noqa: E501
        _Pad(7,  "SENSOR_CAPN",  x.SENSOR_CAPN,  "VDD3P3_RTC",               "oe=0,ie=0", "oe=0,ie=0", None, {               # noqa: E501
            1 : _Function(x.ADC[1].CHANNELS[2],           "ADC1_CH2",     None),                                             # noqa: E501
            3 : _Function(x.RTC_GPIO[2],                  "RTC_GPIO2",    None),                                             # noqa: E501
            5 : _Function(esp32.get_gpio(38),             "GPIO38",       "I"),                                              # noqa: E501
        }),                                                                                                                 # noqa: E501
        _Pad(18, "MTDI",         x.MTDI,         "VDD3P3_RTC",               "oe=0,ie=1,wpd", "oe=0,ie=1,wpd", "2'd2", {     # noqa: E501
            1 : _Function(x.ADC[2].CHANNELS[5],           "ADC2_CH5",     None),                                             # noqa: E501
            2 : _Function(x.TOUCH[5],                     "TOUCH5",       None),                                             # noqa: E501
            3 : _Function(x.RTC_GPIO[15],                 "RTC_GPIO15",   None),                                             # noqa: E501
            5 : _Function(x.JTAG.IFs.tdi.IFs.signal,  "MTDI",         "I1"),                                             # noqa: E501
            6 : _Function(x.SPI[2].IFs.Q,               "HSPIQ",        "I/O/T"),                                          # noqa: E501
            7 : _Function(esp32.get_gpio(12),             "GPIO12",       "I/O/T"),                                          # noqa: E501
            8 : _Function(x.SDIO_HOST[1].IFs.DATA[2],   "HS2_DATA2",    "I1/O/T"),                                         # noqa: E501
            9 : _Function(x.SDIO_SLAVE.IFs.DATA[2],     "SD_DATA2",     "I1/O/T"),                                         # noqa: E501
            10: _Function(x.EMAC.IFs.TXD[3],           "EMAC_TXD3",    "O")                                                # noqa: E501
        }),                                                                                                                 # noqa: E501
    ]
    # fmt: on


class _ESP32_Pinmux(Module):
    def __init__(self, esp32: ESP32) -> None:
        default_function = 5
        self.matrix = _matrix(esp32)

        class _NODES(ModuleInterface.NODES()):
            MUXES = [
                _Mux(
                    esp32.pinmap[str(pad.interface)],
                    *[f.interface for f in pad.functions.values()],
                )
                for pad in self.matrix
            ]

        self.NODEs = _NODES(self)

        for pad in self.matrix:
            if len(pad.functions.items()) == 0:
                continue
            self._mux(pad.functions[default_function], pad)

    def _mux(self, function: _Function, pad: _Pad):
        if pad.current_function == function:
            return

        # Check if already set
        # TODO remove, and make sure that reconnection is legal or spit warning or so
        # assert (pad.current_function == None), "Already set"

        pad.current_function = function
        self.NODEs.MUXES[self.matrix.index(pad)].select(function.interface)

    def mux(self, internal: ModuleInterface, pad: ModuleInterface):
        # Check if combination legal
        row = [pin for pin in self.matrix if pin.interface == pad][0]
        col = [
            function
            for function in row.functions.values()
            if function.interface == internal
        ][0]

        self._mux(col, row)

    def mux_if(self, internal: ModuleInterface):
        for pad in self.matrix:
            for function in pad.functions.values():
                if function.interface == internal:
                    self._mux(function, pad)
                    return
        assert False, "Not a pinmux interface"

    def mux_peripheral(self, peripheral: ModuleInterface):
        ...
        # ifs = peripheral.get_trait(can_list_interfaces).get_interfaces()
        # for interface in ifs:
        #    self.mux_if(interface)
        # TODO
        # is this not ambiguous?
