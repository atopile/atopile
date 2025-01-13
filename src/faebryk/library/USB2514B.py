# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P
from faebryk.libs.util import assert_once

logger = logging.getLogger(__name__)


class USB2514B(Module):
    class ConfigurableUSB(Module):
        """
        USB port wrapper with configuration pins and power enable pin.
        """

        usb: F.USB2_0_IF.Data
        usb_power_enable: F.ElectricLogic
        over_current_sense: F.ElectricLogic

        # configuration interfaces
        battery_charging_enable: F.ElectricLogic
        usb_port_disable_p: F.ElectricLogic
        usb_port_disable_n: F.ElectricLogic

        @assert_once
        def configure_usb_port(
            self,
            owner: Module,
            enable_usb: bool = True,
            enable_battery_charging: bool = True,
        ):
            """
            Configure the specified USB port.
            """
            # enable/disable usb port
            if not enable_usb:
                self.usb_port_disable_p.set_weak(on=True, owner=owner)
                self.usb_port_disable_n.set_weak(on=True, owner=owner)

            # enable/disable battery charging
            if not enable_battery_charging:
                self.battery_charging_enable.set_weak(on=False, owner=owner)

        def __preinit__(self):
            F.ElectricLogic.connect_all_module_references(self)
            self.usb_port_disable_p.signal.connect(self.usb.p.signal)
            self.usb_port_disable_n.signal.connect(self.usb.n.signal)
            self.usb_power_enable.connect(self.battery_charging_enable)

    class ConfigurationSource(Enum):
        DEFAULT = auto()
        """
        - Strap options enabled
        - Self-powered operation enabled
        - Individual power switching
        - Individual over-current sensing
        """
        BUS_POWERED = auto()
        """
        Default configuration with the following overrides:
        - Bus-powered operation
        """
        SMBUS = auto()
        """"
        The hub is configured externally over SMBus (as an SMBus slave device):
        - Strap options disabled
        - All registers configured over SMBus
        """
        EEPROM = auto()
        """
        The hub is configured over 2-wire I2C EEPROM:
        - Strap options disabled
        - All registers configured by I2C EEPROM
        """

    @assert_once
    def set_configuration_source(
        self,
        owner: Module,
        configuration_source: ConfigurationSource = ConfigurationSource.DEFAULT,
    ):
        """
        Set the source of configuration settings for the USB2514B.
        """
        if configuration_source == USB2514B.ConfigurationSource.DEFAULT:
            self.configuration_source_input[0].pulled.pull(up=False, owner=owner)
            self.configuration_source_input[1].pulled.pull(up=False, owner=owner)
        elif configuration_source == USB2514B.ConfigurationSource.BUS_POWERED:
            self.configuration_source_input[0].pulled.pull(up=False, owner=owner)
            self.configuration_source_input[1].pulled.pull(up=True, owner=owner)
        elif configuration_source == USB2514B.ConfigurationSource.SMBUS:
            self.configuration_source_input[0].pulled.pull(up=True, owner=owner)
            self.configuration_source_input[1].pulled.pull(up=False, owner=owner)
        elif configuration_source == USB2514B.ConfigurationSource.EEPROM:
            self.configuration_source_input[0].pulled.pull(up=True, owner=owner)
            self.configuration_source_input[1].pulled.pull(up=True, owner=owner)

    class NonRemovablePortConfiguration(Enum):
        ALL_PORTS_REMOVABLE = auto()
        PORT_0_NOT_REMOVABLE = auto()
        PORT_0_1_NOT_REMOVABLE = auto()
        PORT_0_1_2_NOT_REMOVABLE = auto()

    @assert_once
    def set_non_removable_ports(
        self,
        owner: Module,
        non_removable_port_configuration: NonRemovablePortConfiguration,
    ):
        """
        Set the non-removable port configuration of the USB2514.
        """
        if (
            non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.ALL_PORTS_REMOVABLE
        ):
            self.usb_removability_configuration_intput[0].set_weak(
                on=False, owner=owner
            )
            self.usb_removability_configuration_intput[1].set_weak(
                on=False, owner=owner
            )
        elif (
            non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.PORT_0_NOT_REMOVABLE
        ):
            self.usb_removability_configuration_intput[0].set_weak(on=True, owner=owner)
            self.usb_removability_configuration_intput[1].set_weak(
                on=False, owner=owner
            )
        elif (
            non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.PORT_0_1_NOT_REMOVABLE
        ):
            self.usb_removability_configuration_intput[0].set_weak(
                on=False, owner=owner
            )
            self.usb_removability_configuration_intput[1].set_weak(on=True, owner=owner)
        elif (
            non_removable_port_configuration
            == USB2514B.NonRemovablePortConfiguration.PORT_0_1_2_NOT_REMOVABLE
        ):
            self.usb_removability_configuration_intput[0].set_weak(on=True, owner=owner)
            self.usb_removability_configuration_intput[1].set_weak(on=True, owner=owner)

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power_3v3_regulator: F.ElectricPower
    power_3v3_analog: F.ElectricPower
    power_pll: F.ElectricPower
    power_core: F.ElectricPower
    power_io: F.ElectricPower

    usb_upstream: F.USB2_0_IF.Data
    configurable_downstream_usb = L.list_field(4, ConfigurableUSB)

    xtal_if: F.XtalIF
    external_clock_input: F.ElectricLogic

    usb_bias_resistor_input: F.SignalElectrical
    vbus_detect: F.SignalElectrical

    test: F.Electrical
    reset: F.ElectricLogic
    local_power_detection: F.SignalElectrical

    usb_removability_configuration_intput = L.list_field(2, F.ElectricLogic)
    configuration_source_input = L.list_field(2, F.ElectricLogic)

    suspense_indicator: F.ElectricLogic
    high_speed_upstream_indicator: F.ElectricLogic

    i2c: F.I2C

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Microchip Tech",
            DescriptiveProperties.partno: "USB2514B-AEZC-TR",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf"
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.configurable_downstream_usb[0].usb.n.signal,
                "2": self.configurable_downstream_usb[0].usb.p.signal,
                "3": self.configurable_downstream_usb[1].usb.n.signal,
                "4": self.configurable_downstream_usb[1].usb.p.signal,
                "5": self.power_3v3_analog.hv,
                "6": self.configurable_downstream_usb[2].usb.n.signal,
                "7": self.configurable_downstream_usb[2].usb.p.signal,
                "8": self.configurable_downstream_usb[3].usb.n.signal,
                "9": self.configurable_downstream_usb[3].usb.p.signal,
                "10": self.power_3v3_analog.hv,
                "11": self.test,
                "12": self.configurable_downstream_usb[
                    0
                ].battery_charging_enable.signal,
                "13": self.configurable_downstream_usb[0].over_current_sense.signal,
                "14": self.power_core.hv,
                "15": self.power_3v3_regulator.hv,
                "16": self.configurable_downstream_usb[
                    1
                ].battery_charging_enable.signal,
                "17": self.configurable_downstream_usb[1].over_current_sense.signal,
                "18": self.configurable_downstream_usb[
                    2
                ].battery_charging_enable.signal,
                "19": self.configurable_downstream_usb[2].over_current_sense.signal,
                "20": self.configurable_downstream_usb[
                    3
                ].battery_charging_enable.signal,
                "21": self.configurable_downstream_usb[3].over_current_sense.signal,
                "22": self.usb_removability_configuration_intput[1].signal,
                "23": self.power_io.hv,
                "24": self.configuration_source_input[0].signal,
                "25": self.configuration_source_input[1].signal,
                "26": self.reset.signal,
                "27": self.vbus_detect.signal,
                "28": self.usb_removability_configuration_intput[0].signal,
                "29": self.power_3v3_analog.hv,
                "30": self.usb_upstream.n.signal,
                "31": self.usb_upstream.p.signal,
                "32": self.xtal_if.xout,
                "33": self.xtal_if.xin,
                "34": self.power_pll.hv,
                "35": self.usb_bias_resistor_input.signal,
                "36": self.power_3v3_analog.hv,
                "37": self.power_3v3_analog.lv,
            }
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_core.hv: ["CRFILT"],
                self.power_core.lv: ["EP"],
                self.configuration_source_input[1].signal: ["HS_IND/CFG_SEL1"],
                self.configurable_downstream_usb[0].over_current_sense.signal: [
                    "OCS_N1"
                ],
                self.configurable_downstream_usb[1].over_current_sense.signal: [
                    "OCS_N2"
                ],
                self.configurable_downstream_usb[2].over_current_sense.signal: [
                    "OCS_N3"
                ],
                self.configurable_downstream_usb[3].over_current_sense.signal: [
                    "OCS_N4"
                ],
                self.power_pll.hv: ["PLLFILT"],
                self.configurable_downstream_usb[0].battery_charging_enable.signal: [
                    "PRTPWR1/BC_EN1"
                ],
                self.configurable_downstream_usb[1].battery_charging_enable.signal: [
                    "PRTPWR2/BC_EN2"
                ],
                self.configurable_downstream_usb[2].battery_charging_enable.signal: [
                    "PRTPWR3/BC_EN3"
                ],
                self.configurable_downstream_usb[3].battery_charging_enable.signal: [
                    "PRTPWR4/BC_EN4"
                ],
                self.usb_bias_resistor_input.signal: ["RBIAS"],
                self.reset.signal: ["RESET_N"],
                self.configuration_source_input[0].signal: ["SCL/SMBCLK/CFG_SEL0"],
                self.usb_removability_configuration_intput[1].signal: [
                    "SDA/SMBDATA/NON_REM1"
                ],
                self.usb_removability_configuration_intput[0].signal: [
                    "SUSP_IND/LOCAL_PWR/NON_REM0"
                ],
                self.test: ["TEST"],
                self.configurable_downstream_usb[0].usb.n.signal: [
                    "USBDM_DN1/PRT_DIS_M1"
                ],
                self.configurable_downstream_usb[1].usb.n.signal: [
                    "USBDM_DN2/PRT_DIS_M2"
                ],
                self.configurable_downstream_usb[2].usb.n.signal: [
                    "USBDM_DN3/PRT_DOS_M3"
                ],
                self.configurable_downstream_usb[3].usb.n.signal: [
                    "USBDM_DN4/PRT_DIS_M4"
                ],
                self.usb_upstream.p.signal: ["USBDM_UP"],
                self.configurable_downstream_usb[0].usb.p.signal: [
                    "USBDP_DN1/PRT_DIS_P1"
                ],
                self.configurable_downstream_usb[1].usb.p.signal: [
                    "USBDP_DN2/PRT_DIS_P2"
                ],
                self.configurable_downstream_usb[2].usb.p.signal: [
                    "USBDP_DN3/PRT_DIS_P3"
                ],
                self.configurable_downstream_usb[3].usb.p.signal: [
                    "USBDP_DN4/PRT_DIS_P4"
                ],
                self.usb_upstream.p.signal: ["USBDP_UP"],
                self.vbus_detect.signal: ["VBUS_DET"],
                self.power_3v3_regulator.hv: ["VDD33"],
                self.power_3v3_analog.hv: ["VDDA33"],
                self.xtal_if.xin: ["XTALIN/CLKIN"],
                self.xtal_if.xout: ["XTALOUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ----------------------------------------
        #              connections
        # ----------------------------------------
        self.configuration_source_input[0].connect(self.i2c.scl)
        self.configuration_source_input[1].connect(self.high_speed_upstream_indicator)
        self.usb_removability_configuration_intput[0].signal.connect(
            self.suspense_indicator.signal,
            self.local_power_detection.signal,
        )
        self.usb_removability_configuration_intput[1].connect(self.i2c.sda)
        self.test.connect(self.power_core.lv)

        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(
            self,
            exclude={
                self.power_pll,
                self.power_core,
                # self.power_io,
                self.vbus_detect,
                self.local_power_detection,
                self.power_3v3_regulator,
                self.power_3v3_analog,
            },
        )

        # ----------------------------------------
        #              parametrization
        # ----------------------------------------
        self.power_pll.voltage.constrain_subset(
            L.Range.from_center_rel(1.8 * P.V, 0.05)
        )  # datasheet does not specify a voltage range
        self.power_core.voltage.constrain_subset(
            L.Range.from_center_rel(1.8 * P.V, 0.05)
        )  # datasheet does not specify a voltage range
        self.power_3v3_regulator.voltage.constrain_subset(
            L.Range.from_center(3.3 * P.V, 0.3 * P.V)
        )
        self.power_3v3_analog.voltage.constrain_subset(
            L.Range.from_center(3.3 * P.V, 0.3 * P.V)
        )
        self.power_io.voltage.constrain_subset(
            L.Range.from_center(3.3 * P.V, 0.3 * P.V)
        )
