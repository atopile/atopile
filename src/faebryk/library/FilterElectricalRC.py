# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval_Disjoint, Quantity_Set

logger = logging.getLogger(__name__)


class FilterElectricalRC(F.Filter):
    """
    Basic Electrical RC filter
    """

    in_: F.ElectricSignal
    out: F.ElectricSignal
    resistor: F.Resistor
    capacitor: F.Capacitor

    def __init__(self, *, _hardcoded: bool = False):
        super().__init__()
        self._hardcoded = _hardcoded

    def __preinit__(self):
        self.response.alias_is(F.Filter.Response.LOWPASS)
        self.order.alias_is(1)

        R = self.resistor.resistance
        C = self.capacitor.capacitance
        fc = self.cutoff_frequency

        # Equations
        if not self._hardcoded:
            C.alias_is(1 / (R * 2 * math.pi * fc))
            R.alias_is(1 / (C * 2 * math.pi * fc))
            fc.alias_is(1 / (2 * math.pi * R * C))

        # Connections
        self.in_.line.connect_via(
            (self.resistor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.line.connect_via(self.resistor, self.out.line)

        # Set the max voltage of the capacitor to min 1.5 times the output voltage
        self.capacitor.max_voltage.constrain_ge(self.out.reference.voltage * 1.5)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.in_.line, self.out.line)

    @classmethod
    def hardcoded_fc(cls, fc: Quantity_Set, r: Quantity_Set, c: Quantity_Set):
        # TODO: Remove hardcoded when normal equations solve faster
        self = cls(_hardcoded=True)
        r = None
        c = None
        self.cutoff_frequency.constrain_subset(fc)
        self.resistor.resistance.constrain_subset(r)
        self.capacitor.capacitance.constrain_subset(c)
        return self

    @classmethod
    def hardcoded_rc(cls, resistance: Quantity_Set, capacitance: Quantity_Set):
        self = cls(_hardcoded=True)
        fc = 1 / (
            Quantity_Interval_Disjoint.from_value(resistance * capacitance)
            * 2
            * math.pi
        )
        self.resistor.resistance.constrain_subset(resistance)
        self.capacitor.capacitance.constrain_subset(capacitance)
        self.cutoff_frequency.constrain_subset(fc)
        return self
