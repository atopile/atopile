# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.core.util import connect_to_all_interfaces
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.I2C import I2C
from faebryk.library.Range import Range
from faebryk.library.UART_Base import UART_Base
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class ESP32_C3(Module):
    """ESP32-C3"""

    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            vdd3p3_cpu = ElectricPower()
            vdd3p3_rtc = ElectricPower()
            vdd_spi = ElectricPower()
            vdd3p3 = ElectricPower()
            vdda = ElectricPower()
            lna_in = Electrical()
            enable = ElectricLogic()
            xtal_p = Electrical()
            xtal_n = Electrical()
            gpio = times(22, ElectricLogic)
            # TODO: map peripherals to GPIOs with pinmux
            usb = USB2_0()
            i2c = I2C()
            uart = times(2, UART_Base)
            # ... etc

        self.IFs = _IFs(self)

        x = self.IFs

        # https://www.espressif.com/sites/default/files/documentation/esp32-c3_technical_reference_manual_en.pdf#uart
        for ser in x.uart:
            ser.PARAMs.baud.merge(Range(0, 5000000))

        # connect all logic references
        # TODO: set correctly for each power domain
        # ref = ElectricLogic.connect_all_module_references(self)
        # self.add_trait(has_single_electric_reference_defined(ref))

        # set power domain constraints to recommended operating conditions
        for power_domain in [self.IFs.vdd3p3_rtc, self.IFs.vdd3p3, self.IFs.vdda]:
            power_domain.PARAMs.voltage.merge(Range.from_center(3.3, 0.3))
        self.IFs.vdd3p3_cpu.PARAMs.voltage.merge(
            Range(3.0, 3.6)
        )  # TODO: max 3.3V when writing eFuses
        self.IFs.vdd_spi.PARAMs.voltage.merge(
            Range.from_center(3.3, 0.3)
        )  # TODO: when configured as input

        # connect all grounds to eachother and power
        connect_to_all_interfaces(
            self.IFs.vdd3p3.IFs.lv,
            [
                self.IFs.vdd3p3_cpu.IFs.lv,
                self.IFs.vdd3p3_rtc.IFs.lv,
                self.IFs.vdda.IFs.lv,
                self.IFs.vdd_spi.IFs.lv,
            ],
        )

        # connect decoupling caps to power domains
        self.IFs.vdd3p3.get_trait(can_be_decoupled).decouple()
        self.IFs.vdd3p3_cpu.get_trait(can_be_decoupled).decouple()
        self.IFs.vdd3p3_rtc.get_trait(can_be_decoupled).decouple()
        self.IFs.vdda.get_trait(can_be_decoupled).decouple()
        self.IFs.vdd_spi.get_trait(can_be_decoupled).decouple()

        # rc delay circuit on enable pin for startup delay
        # https://www.espressif.com/sites/default/files/documentation/esp32-c3-mini-1_datasheet_en.pdf page 24  # noqa E501
        # TODO: add lowpass filter
        # self.IFs.enable.IFs.signal.connect_via(
        #    self.NODEs.en_rc_capacitor, self.IFs.pwr3v3.IFs.lv
        # )
        self.IFs.enable.get_trait(ElectricLogic.can_be_pulled).pull(
            up=True
        )  # TODO: combine with lowpass filter

        # set default boot mode to "SPI Boot mode" (gpio = N.C. or HIGH)
        # https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf page 25  # noqa E501
        # TODO: make configurable
        self.IFs.gpio[8].get_trait(ElectricLogic.can_be_pulled).pull(
            up=True
        )  # boot_resistors[0]
        self.IFs.gpio[2].get_trait(ElectricLogic.can_be_pulled).pull(
            up=True
        )  # boot_resistors[1]
        # TODO: gpio[9] has an internal pull-up at boot = SPI-Boot

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf"
            )
        )

        # TODO: Fix this
        #    # set mux states
        #    # UART 1
        #    self.set_mux(x.gpio[20], self.IFs.serial[1].IFs.rx)
        #    self.set_mux(x.gpio[21], self.IFs.serial[1].IFs.tx)
        #    # UART 0
        #    self.set_mux(x.gpio[0], self.IFs.serial[0].IFs.rx)
        #    self.set_mux(x.gpio[1], self.IFs.serial[0].IFs.tx)

        #    # I2C
        #    self.set_mux(x.gpio[4], self.IFs.i2c.IFs.scl)
        #    self.set_mux(x.gpio[5], self.IFs.i2c.IFs.sda)

        #    class _uart_esphome_config(has_esphome_config.impl()):
        #        def get_config(self_) -> dict:
        #            assert isinstance(self, ESP32_C3)
        #            obj = self_.get_obj()
        #            assert isinstance(obj, UART_Base)
        #            config = {
        #                "uart": [
        #                    {
        #                        "id": obj.get_trait(is_esphome_bus).get_bus_id(),
        #                        "baud_rate": get_parameter_max(obj.PARAMs.baud),
        #                    }
        #                ]
        #            }

        #            try:
        #                config["uart"][0]["rx_pin"] = self.get_mux_pin(obj.IFs.rx)[1]
        #            except IndexError:
        #                ...

        #            try:
        #                config["uart"][0]["tx_pin"] = self.get_mux_pin(obj.IFs.tx)[1]
        #            except IndexError:
        #                ...

        #            # if no rx/tx pin is set, then not in use
        #            if set(config["uart"][0].keys()).isdisjoint({"rx_pin", "tx_pin"}):
        #                return {}

        #            return config

        #    class _i2c_esphome_config(has_esphome_config.impl()):
        #        def get_config(self_) -> dict:
        #            assert isinstance(self, ESP32_C3)
        #            obj = self_.get_obj()
        #            assert isinstance(obj, I2C)

        #            try:
        #                sda = self.get_mux_pin(obj.IFs.sda)[1]
        #                scl = self.get_mux_pin(obj.IFs.scl)[1]
        #            except IndexError:
        #                # Not in use if pinmux is not set
        #                return {}

        #            config = {
        #                "i2c": [
        #                    {
        #                        "id": obj.get_trait(is_esphome_bus).get_bus_id(),
        #                        "frequency": int(get_parameter_max(obj.PARAMs.frequency)), # noqa: E501
        #                        "sda": sda,
        #                        "scl": scl,
        #                    }
        #                ]
        #            }

        #            return config

        #    for serial in self.IFs.serial:
        #        serial.add_trait(
        #            is_esphome_bus_defined(f"uart_{self.IFs.serial.index(serial)}")
        #        )
        #        serial.add_trait(_uart_esphome_config())

        #    for i, gpio in enumerate(self.IFs.gpio):
        #        gpio.add_trait(is_esphome_bus_defined(f"GPIO{i}"))

        #    self.IFs.i2c.add_trait(is_esphome_bus_defined("i2c_0"))
        #    self.IFs.i2c.add_trait(_i2c_esphome_config())
        #    self.IFs.i2c.PARAMs.frequency.merge(
        #        Set(
        #            [
        #                I2C.define_max_frequency_capability(speed)
        #                for speed in [
        #                    I2C.SpeedMode.low_speed,
        #                    I2C.SpeedMode.standard_speed,
        #                ]
        #            ]
        #            + [
        #                Range(10 * k, 800 * k)
        #            ],  # TODO: should be range 200k-800k, but breaks parameter merge
        #        )
        #    )

        #    self.add_trait(
        #        has_esphome_config_defined(
        #            {
        #                "esp32": {
        #                    "board": "Espressif ESP32-C3-DevKitM-1",
        #                    "variant": "esp32c3",
        #                    "framework": {
        #                        "type": "esp-idf",
        #                        "version": "recommended",
        #                    },
        #                },
        #            }
        #        )
        #    )

        # very simple mux that uses pinmap
        # def set_mux(self, gpio: ElectricLogic, target: ElectricLogic):
        #    """Careful not checked"""
        #    pin, _ = self.get_mux_pin(gpio)
        #    self.pinmap[pin] = target.IFs.signal

        # def get_mux_pin(self, target: ElectricLogic) -> tuple[str, int]:
        #    """Returns pin & gpio number"""
        #    pin = [k for k, v in self.pinmap.items() if v == target.IFs.signal][0]
        #    gpio = self.pinmap_default[pin]
        #    gpio_index = [
        #        i for i, g in enumerate(self.IFs.gpio) if g.IFs.signal == gpio
        #    ][0]
        #    return pin, gpio_index
