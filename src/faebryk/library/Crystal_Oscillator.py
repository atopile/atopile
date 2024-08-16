# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.Crystal import Crystal
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Range import Range
from faebryk.libs.units import P
from faebryk.libs.util import times


class Crystal_Oscillator(Module):
    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _NODEs(Module.NODES()):
            crystal = Crystal()
            capacitors = times(2, Capacitor)

        self.NODEs = _NODEs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            p = Electrical()
            n = Electrical()

        self.IFs = _IFs(self)

        # ----------------------------------------
        #               parameters
        # ----------------------------------------
        # https://blog.adafruit.com/2012/01/24/choosing-the-right-crystal-and-caps-for-your-design/
        STRAY_CAPACITANCE = Range(1 * P.nF, 5 * P.nF)
        load_capacitance = self.NODEs.crystal.PARAMs.load_impedance
        capacitance = Constant(2 * P.dimesionless) * (
            load_capacitance - STRAY_CAPACITANCE
        )

        for cap in self.NODEs.capacitors:
            cap.PARAMs.capacitance.merge(capacitance)

        # ----------------------------------------
        #                traits
        # ----------------------------------------

        # ----------------------------------------
        #                aliases
        # ----------------------------------------
        gnd = self.IFs.power.IFs.lv

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        self.NODEs.crystal.IFs.gnd.connect(gnd)
        self.NODEs.crystal.IFs.unnamed[0].connect_via(self.NODEs.capacitors[0], gnd)
        self.NODEs.crystal.IFs.unnamed[1].connect_via(self.NODEs.capacitors[1], gnd)

        self.NODEs.crystal.IFs.unnamed[0].connect(self.IFs.n)
        self.NODEs.crystal.IFs.unnamed[1].connect(self.IFs.p)
