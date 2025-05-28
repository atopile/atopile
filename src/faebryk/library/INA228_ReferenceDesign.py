# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class INA228_ReferenceDesign(Module):
    """
    INA228 high or low side current shunt and voltage monitor with I2C interface.
    This module implements a minimal reference design for common use cases.
    """

    class ShuntedElectricPower(Module):
        power_in: F.ElectricPower
        power_out: F.ElectricPower
        shunt_sense: F.DifferentialPair

        shunt: F.Resistor

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.power_in, self.power_out)

        def __init__(self, lowside: bool = False, filtered: bool = False):
            super().__init__()
            self._lowside = lowside
            self._filtered = filtered

        def __preinit__(self):
            self.shunt_sense.p.line.connect_via(self.shunt, self.shunt_sense.n.line)
            # TODO: minus voltagedrop over shunt
            self.power_in.voltage.alias_is(self.power_out.voltage)
            if self._lowside:
                self.power_in.lv.connect_via(self.shunt, self.power_out.lv)
                self.power_in.hv.connect(self.power_out.hv)
            else:
                self.power_in.hv.connect_via(self.shunt, self.power_out.hv)
                self.power_in.lv.connect(self.power_out.lv)

            if self._filtered:
                raise NotImplementedError
            # TODO: add filter
            #    filter_cap = self.add(F.Capacitor())
            #    filter_resistors = L.list_field(2, F.Resistor)
            #
            #    filter_cap.capacitance.constrain_subset(
            #        L.Range.from_center_rel(0.1 * P.uF, 0.01)
            #    )
            #    filter_cap.max_voltage.constrain_subset(
            #        L.Range.from_center_rel(170 * P.V, 0.01)
            #    )
            #    for res in filter_resistors:
            #        res.resistance.constrain_subset(10 * P.kohm)
            # TODO: auto calculate, see: https://www.ti.com/lit/ug/tidu473/tidu473.pdf

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    ina288: F.INA228

    power_load: F.ElectricPower
    power_source: F.ElectricPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def can_bridge(self):
        (F.can_bridge_defined(self.power_load, self.power_source))

    def __init__(self, filtered: bool = False, lowside: bool = False):
        super().__init__()
        self._filtered = filtered
        self._lowside = lowside

    def __preinit__(self):
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        shunted_power = self.add(
            self.ShuntedElectricPower(lowside=self._lowside, filtered=self._filtered)
        )
        shunted_power.shunt.resistance.constrain_subset(
            L.Range.from_center_rel(15 * P.mohm, 0.01)
        )
        shunted_power.shunt.max_power.constrain_subset(
            L.Range.from_center_rel(2 * P.W, 0.01)
        )
        # TODO: calculate according to datasheet p36

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

        self.power_load.connect_via(shunted_power, self.power_source)
        self.ina288.bus_voltage_sense.line.connect(self.power_load.hv)

        self.ina288.shunt_input.connect(shunted_power.shunt_sense)

        # decouple power rail
        self.ina288.power.decoupled.decouple(owner=self).explicit(
            nominal_capacitance=100 * P.nF,
            tolerance=0.2,
            size=SMDSize.I0603,
        )
