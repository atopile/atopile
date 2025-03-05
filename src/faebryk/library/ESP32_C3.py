# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class ESP32_C3(Module):
    """ESP32-C3"""

    vdd3p3_cpu: F.ElectricPower
    vdd3p3_rtc: F.ElectricPower
    vdd_spi: F.ElectricPower
    vdd3p3: F.ElectricPower
    vdda: F.ElectricPower
    lna_in: F.Electrical
    enable: F.ElectricLogic
    xtal_p: F.Electrical
    xtal_n: F.Electrical
    gpio = L.list_field(22, F.ElectricLogic)
    # TODO: map peripherals to GPIOs with pinmux
    usb: F.USB2_0
    i2c: F.I2C
    uart = L.list_field(2, F.UART_Base)
    # ... etc

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf"
    )

    def __preinit__(self):
        x = self

        # https://www.espressif.com/sites/default/files/documentation/esp32-c3_technical_reference_manual_en.pdf#uart
        for ser in x.uart:
            ser.baud.constrain_le(5 * P.mbaud)

        # connect all logic references
        # TODO: set correctly for each power domain
        # ref = F.ElectricLogic.connect_all_module_references(self)
        # self.add(F.has_single_electric_reference_defined(ref))

        # set power domain constraints to recommended operating conditions
        for power_domain in [self.vdd3p3_rtc, self.vdd3p3, self.vdda]:
            power_domain.voltage.constrain_subset(
                L.Range.from_center(3.3 * P.V, 0.3 * P.V)
            )
        self.vdd3p3_cpu.voltage.constrain_subset(
            L.Range(3.0 * P.V, 3.6 * P.V)
        )  # TODO: max 3.3V when writing eFuses
        self.vdd_spi.voltage.constrain_subset(
            L.Range.from_center(3.3 * P.V, 0.3 * P.V)
        )  # TODO: when configured as input

        # connect all grounds to eachother and power
        self.vdd3p3.lv.connect(
            self.vdd3p3_cpu.lv,
            self.vdd3p3_rtc.lv,
            self.vdda.lv,
            self.vdd_spi.lv,
        )

        # FIXME: this has to be done in ReferenceDesign or parent
        # connect decoupling caps to power domains
        # self.vdd3p3.decoupled.decouple()
        # self.vdd3p3_cpu.decoupled.decouple()
        # self.vdd3p3_rtc.decoupled.decouple()
        # self.vdda.decoupled.decouple()
        # self.vdd_spi.decoupled.decouple()

        # rc delay circuit on enable pin for startup delay
        # https://www.espressif.com/sites/default/files/documentation/esp32-c3-mini-1_datasheet_en.pdf page 24  # noqa E501
        # TODO: add lowpass filter
        # self.enable.line.connect_via(
        #    self.en_rc_capacitor, self.pwr3v3.lv
        # )
        # FIXME: this has to be done in ReferenceDesign or parent
        # self.enable.pulled.pull(up=True)  # TODO: combine with lowpass filter

    # TODO: Fix this
    #    # set mux states
    #    # UART 1
    #    self.set_mux(x.gpio[20], self.serial[1].rx)
    #    self.set_mux(x.gpio[21], self.serial[1].tx)
    #    # UART 0
    #    self.set_mux(x.gpio[0], self.serial[0].rx)
    #    self.set_mux(x.gpio[1], self.serial[0].tx)

    #    # F.I2C
    #    self.set_mux(x.gpio[4], self.i2c.scl)
    #    self.set_mux(x.gpio[5], self.i2c.sda)

    #    class _uart_esphome_config(has_esphome_config.impl()):
    #        def get_config(self_) -> dict:
    #            assert isinstance(self, ESP32_C3)
    #            obj = self_.obj
    #            assert isinstance(obj, F.UART_Base)
    #            config = {
    #                "uart": [
    #                    {
    #                        "id": obj.get_trait(is_esphome_bus).get_bus_id(),
    #                        "baud_rate": get_parameter_max(obj.baud),
    #                    }
    #                ]
    #            }

    #            try:
    #                config["uart"][0]["rx_pin"] = self.get_mux_pin(obj.rx)[1]
    #            except IndexError:
    #                ...

    #            try:
    #                config["uart"][0]["tx_pin"] = self.get_mux_pin(obj.tx)[1]
    #            except IndexError:
    #                ...

    #            # if no rx/tx pin is set, then not in use
    #            if set(config["uart"][0].keys()).isdisjoint({"rx_pin", "tx_pin"}):
    #                return {}

    #            return config

    #    class _i2c_esphome_config(has_esphome_config.impl()):
    #        def get_config(self_) -> dict:
    #            assert isinstance(self, ESP32_C3)
    #            obj = self_.obj
    #            assert isinstance(obj, F.I2C)

    #            try:
    #                sda = self.get_mux_pin(obj.sda)[1]
    #                scl = self.get_mux_pin(obj.scl)[1]
    #            except IndexError:
    #                # Not in use if pinmux is not set
    #                return {}

    #            config = {
    #                "i2c": [
    #                    {
    #                        "id": obj.get_trait(is_esphome_bus).get_bus_id(),
    #                        "frequency": int(get_parameter_max(obj.frequency)), # noqa: E501
    #                        "sda": sda,
    #                        "scl": scl,
    #                    }
    #                ]
    #            }

    #            return config

    #    for serial in self.serial:
    #        serial.add(
    #            is_esphome_bus_defined(f"uart_{self.serial.index(serial)}")
    #        )
    #        serial.add(_uart_esphome_config())

    #    for i, gpio in enumerate(self.gpio):
    #        gpio.add(is_esphome_bus_defined(f"GPIO{i}"))

    #    self.i2c.add(is_esphome_bus_defined("i2c_0"))
    #    self.i2c.add(_i2c_esphome_config())
    #    self.i2c.frequency.constrain_subset(
    #        Set(
    #            [
    #                F.I2C.define_max_frequency_capability(speed)
    #                for speed in [
    #                    F.I2C.SpeedMode.low_speed,
    #                    F.I2C.SpeedMode.standard_speed,
    #                ]
    #            ]
    #            + [
    #                L.Range(10 * P.khertz, 800 * P.khertz)
    #            ],  # TODO: should be range 200k-800k, but breaks parameter merge
    #        )
    #    )

    #    self.add(
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
    # def set_mux(self, gpio: F.ElectricLogic, target: F.ElectricLogic):
    #    """Careful not checked"""
    #    pin, _ = self.get_mux_pin(gpio)
    #    self.pinmap[pin] = target.line

    # def get_mux_pin(self, target: F.ElectricLogic) -> tuple[str, int]:
    #    """Returns pin & gpio number"""
    #    pin = [k for k, v in self.pinmap.items() if v == target.line][0]
    #    gpio = self.pinmap_default[pin]
    #    gpio_index = [
    #        i for i, g in enumerate(self.gpio) if g.line == gpio
    #    ][0]
    #    return pin, gpio_index

    def set_default_boot_mode(
        self, owner: Module, default_boot_to_spi_flash: bool = True
    ):
        # set default boot mode to "SPI Boot mode"
        # https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf page 26 # noqa E501
        # TODO: make configurable
        self.gpio[8].pulled.pull(up=True, owner=owner).resistance.constrain_subset(
            L.Range.from_center_rel(10 * P.kohm, 0.1)
        )
        self.gpio[2].pulled.pull(up=True, owner=owner).resistance.constrain_subset(
            L.Range.from_center_rel(10 * P.kohm, 0.1)
        )
        # gpio[9] has an internal pull-up at boot = SPI-Boot
        if not default_boot_to_spi_flash:
            self.gpio[9].pulled.pull(up=False, owner=owner).resistance.constrain_subset(
                L.Range.from_center_rel(10 * P.kohm, 0.1)
            )
