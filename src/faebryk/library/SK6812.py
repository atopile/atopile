# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class SK6812(Module):
    """
    RGB digital LED with SK6812 controller

    SMD5050-4P
    RGB LEDs(Built-in IC) ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power: F.ElectricPower
    data_in: F.ElectricLogic
    data_out: F.ElectricLogic

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.data_in, self.data_out)

    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C5378720"})
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.LED
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "OPSCO Optoelectronics",
            DescriptiveProperties.partno: "SK6812",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2303300930_OPSCO-Optoelectronics-SK6812_C5378720.pdf"  # noqa: E501
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.data_in.signal: ["DIN"],
                self.data_out.signal: ["DOUT"],
                self.power.lv: ["VSS", "GND"],
                self.power.hv: ["VDD"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        # FIXME
        # self.power.decoupled.decouple()
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(self, exclude=[self.power])

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range(3.3 * P.V, 5.5 * P.V))
