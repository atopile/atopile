# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class B0505S_1WR3_ReferenceDesign(Module):
    ic: F.B0505S_1WR3

    power_in: F.ElectricPower
    power_out: F.ElectricPower

    ferrite_in: F.Inductor
    ferrite_out: F.Inductor

    anti_emi_capacitor: F.Capacitor

    def __preinit__(self):
        self.power_in.voltage.alias_is(self.ic.power_in.voltage)
        self.power_out.voltage.alias_is(self.ic.power_out.voltage)

        self.ferrite_in.inductance.constrain_subset(
            L.Range.from_center_rel(4.7 * P.uH, 0.1)
        )
        self.ferrite_out.inductance.constrain_subset(
            L.Range.from_center_rel(4.7 * P.uH, 0.1)
        )
        # TODO: remove when picker is implemented
        self.ferrite_in.add(F.has_explicit_part.by_supplier("C394952"))
        self.ferrite_out.add(F.has_explicit_part.by_supplier("C394952"))

        self.power_in.decoupled.decouple(owner=self).explicit(
            nominal_capacitance=4.7 * P.uF,
            tolerance=0.2,
            size=SMDSize.I0805,
        )
        self.ic.power_in.decoupled.decouple(owner=self).explicit(
            nominal_capacitance=4.7 * P.uF,
            tolerance=0.2,
            size=SMDSize.I0805,
        )
        self.power_out.decoupled.decouple(owner=self).explicit(
            nominal_capacitance=10 * P.uF,
            tolerance=0.2,
            size=SMDSize.I0805,
        )
        self.anti_emi_capacitor.capacitance.constrain_subset(
            L.Range.from_center_rel(270 * P.pF, 0.2)
        )
        self.anti_emi_capacitor.max_voltage.constrain_subset(L.Range(min=2 * P.kV))
        # TODO: Y5P not yet supported by picker
        self.anti_emi_capacitor.add(F.has_explicit_part.by_supplier("C2914698"))

        self.power_in.lv.connect_via(self.anti_emi_capacitor, self.power_out.lv)

        self.power_in.hv.connect_via(self.ferrite_in, self.ic.power_in.hv)
        self.power_in.lv.connect(self.ic.power_in.lv)

        self.power_out.hv.connect_via(self.ferrite_out, self.ic.power_out.hv)
        self.power_out.lv.connect(self.ic.power_out.lv)
