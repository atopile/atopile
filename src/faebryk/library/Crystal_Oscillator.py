# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from copy import copy

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Crystal_Oscillator(Module):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    crystal: F.Crystal
    capacitors = L.list_field(2, F.Capacitor)

    power: F.ElectricPower
    p: F.Electrical
    n: F.Electrical

    # ----------------------------------------
    #               parameters
    # ----------------------------------------
    # https://blog.adafruit.com/2012/01/24/choosing-the-right-crystal-and-caps-for-your-design/
    # http://www.st.com/internet/com/TECHNICAL_RESOURCES/TECHNICAL_LITERATURE/APPLICATION_NOTE/CD00221665.pdf
    _STRAY_CAPACITANCE = F.Range(1 * P.pF, 5 * P.pF)

    @L.rt_field
    def capacitance(self):
        return (self.crystal.load_capacitance - copy(self._STRAY_CAPACITANCE)) * 2

    def __preinit__(self):
        for cap in self.capacitors:
            cap.capacitance.merge(self.capacitance)

        # ----------------------------------------
        #                traits
        # ----------------------------------------

        # ----------------------------------------
        #                aliases
        # ----------------------------------------
        gnd = self.power.lv

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.crystal.gnd.connect(gnd)
        self.crystal.unnamed[0].connect_via(self.capacitors[0], gnd)
        self.crystal.unnamed[1].connect_via(self.capacitors[1], gnd)

        self.crystal.unnamed[0].connect(self.n)
        self.crystal.unnamed[1].connect(self.p)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.p, self.n)
