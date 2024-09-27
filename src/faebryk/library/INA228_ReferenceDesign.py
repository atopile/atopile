# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class INA228_ReferenceDesign(Module):
    """
    TODO: add description
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
            self.power_in.voltage.merge(
                self.power_out.voltage
            )  # TODO: minus voltagedrop over shunt
            self.shunt_sense.p.connect_via(self.shunt, self.shunt_sense.n)
            if self._lowside:
                self.power_in.hv.connect_via(self.shunt, self.power_out.hv)
                self.power_in.lv.connect(self.power_out.lv)
            else:
                # TODO:short? self.power_in.lv.connect_via(self.shunt, self.power_out.lv
                self.power_in.hv.connect(self.power_out.hv)

            if self._filtered:
                raise NotImplementedError
            # TODO: add filter
            #    filter_cap = self.add(F.Capacitor())
            #    filter_resistors = L.list_field(2, F.Resistor)
            #
            #    filter_cap.capacitance.merge(F.Range.from_center_rel(0.1 * P.uF, 0.01))
            #    filter_cap.rated_voltage.merge(F.Range.from_center_rel(170 * P.V, 0.01)
            #    for res in filter_resistors:
            #        res.resistance.merge(10 * P.kohm)
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
        shunted_power.shunt.resistance.merge(F.Range.from_center_rel(15 * P.mohm, 0.01))
        shunted_power.shunt.rated_power.merge(F.Range.from_center_rel(2 * P.W, 0.01))
        # TODO: calculate according to datasheet p36

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

        self.power_load.connect_via(shunted_power, self.power_source)
        self.ina288.bus_voltage_sense.signal.connect(self.power_load.hv)

        self.ina288.shunt_input.connect(shunted_power.shunt_sense)

        # decouple power rail
        self.ina288.power.get_trait(F.can_be_decoupled).decouple().capacitance.merge(
            F.Range.from_center_rel(0.1 * P.uF, 0.01)
        )
