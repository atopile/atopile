# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class ISO1540(Module):
    """
    Low-Power Bidirectional I2C Isolator
    """

    class I2CandPower(ModuleInterface):
        i2c: F.I2C
        power: F.ElectricPower

        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    non_iso: I2CandPower
    iso: I2CandPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def bridge(self):
        return F.can_bridge_defined(self.non_iso.i2c, self.iso.i2c)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Texas Instruments",
            DescriptiveProperties.partno: "ISO1540DR",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_Texas-Instruments-ISO1540DR_C179739.pdf"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.non_iso.power.lv: ["GND1"],
                self.iso.power.lv: ["GND2"],
                self.non_iso.i2c.scl.signal: ["SCL1"],
                self.iso.i2c.scl.signal: ["SCL2"],
                self.non_iso.i2c.sda.signal: ["SDA1"],
                self.iso.i2c.sda.signal: ["SDA2"],
                self.non_iso.power.hv: ["VCC1"],
                self.iso.power.hv: ["VCC2"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                "1": self.non_iso.power.hv,
                "2": self.non_iso.i2c.sda.signal,
                "3": self.non_iso.i2c.scl.signal,
                "4": self.non_iso.power.lv,
                "5": self.iso.power.lv,
                "6": self.iso.i2c.scl.signal,
                "7": self.iso.i2c.sda.signal,
                "8": self.iso.power.hv,
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.non_iso.power.voltage.constrain_subset(L.Range(3.0 * P.V, 5.5 * P.V))
        self.iso.power.voltage.constrain_subset(L.Range(3.0 * P.V, 5.5 * P.V))
