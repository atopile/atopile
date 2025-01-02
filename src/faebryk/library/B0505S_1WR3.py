# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class _B0505S_1WR3(Module):
    """
    Isolated 5V DC to 5V DC converter.
    R suffix is for shortcircuit protection
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power_in: F.ElectricPower
    power_out: F.ElectricPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2307211806_EVISUN-B0505S-1WR3_C7465178.pdf"
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                "1": self.power_in.lv,
                "2": self.power_in.hv,
                "3": self.power_out.lv,
                "4": self.power_out.hv,
            }
        )

    @L.rt_field
    def has_descriptive_properties_defined(self):
        return F.has_descriptive_properties_defined(
            {
                DescriptiveProperties.partno: "B0505S-1WR3",
            },
        )

    def __preinit__(self):
        self.power_in.voltage.constrain_subset(L.Range(4.3 * P.V, 9 * P.V))
        self.power_out.voltage.constrain_superset(L.Range.from_center_rel(5 * P.V, 0.1))


# TODO should be a reference design
class B0505S_1WR3(Module):
    ic: _B0505S_1WR3

    def __preinit__(self):
        self.ic.power_in.get_trait(F.can_be_decoupled).decouple(
            owner=self
        ).capacitance.constrain_subset(L.Range.from_center_rel(4.7 * P.uF, 0.1))
        self.ic.power_out.get_trait(F.can_be_decoupled).decouple(
            owner=self
        ).capacitance.constrain_subset(L.Range.from_center_rel(10 * P.uF, 0.1))
