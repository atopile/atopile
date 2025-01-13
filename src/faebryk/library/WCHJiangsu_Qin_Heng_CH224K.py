# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Literal

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module, ModuleException
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P
from faebryk.libs.util import assert_once  # noqa: F401

logger = logging.getLogger(__name__)


class WCHJiangsu_Qin_Heng_CH224K(Module):
    """
    USB PD and Other Fast Charging Protocol Sink Controller

    ESSOP-10-150mil-1mm ROHS
    """

    @assert_once
    def config_voltage(
        self,
        owner: Module,
        voltage: Literal["5V", "9V", "12V", "15V", "20V"],
        mode: Literal["Resistor", "LogicLevel"] = "LogicLevel",
    ):
        """
        Configure the voltage selection for the USB PD controller.
        """
        # voltage | resistance | cfg connections [1, 2, 3]
        connection_matrix = {
            "5V": (None, [1, 0, 0]),
            "9V": (L.Range.from_center_rel(6.8 * P.kohm, 0.001), [0, 0, 0]),
            "12V": (L.Range.from_center_rel(24 * P.kohm, 0.001), [0, 0, 1]),
            "15V": (L.Range.from_center_rel(56 * P.kohm, 0.001), [0, 1, 1]),
            "20V": (None, [0, 1, 0]),
        }
        if mode == "Resistor":
            if voltage == "5V":
                raise ModuleException(
                    self,
                    "Cannot use resistor mode for 5V",
                )
            elif voltage == "20V":
                return  # no resistor connected

            self.cfg[0].set_weak(on=False, owner=owner).resistance.constrain_subset(
                connection_matrix[voltage][0]
            )
        elif mode == "LogicLevel":
            self.cfg[0].set(on=bool(connection_matrix[voltage][1][0]))
            self.cfg[1].set(on=bool(connection_matrix[voltage][1][1]))
            self.cfg[2].set(on=bool(connection_matrix[voltage][1][2]))

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power: F.ElectricPower
    vbus_detect: F.ElectricLogic
    cfg = L.list_field(3, F.ElectricLogic)
    power_good: F.ElectricLogic
    cc2: F.SignalElectrical
    cc1: F.SignalElectrical
    usb: F.USB2_0_IF.Data

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C970725"})
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "WCH(Jiangsu Qin Heng)",
            DescriptiveProperties.partno: "CH224K",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_2403131354_WCH-Jiangsu-Qin-Heng-CH224K_C970725.pdf"
    )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power.hv,
                "2": self.cfg[1].signal,
                "3": self.cfg[2].signal,
                "4": self.usb.p.signal,
                "5": self.usb.n.signal,
                "6": self.cc2.signal,
                "7": self.cc1.signal,
                "8": self.vbus_detect.signal,
                "9": self.cfg[0].signal,
                "10": self.power_good.signal,
                "11": self.power.lv,
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range(3.0 * P.V, 3.6 * P.V))

        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        self.power.connect(F.ElectricLogic.connect_all_references(self.cfg))
