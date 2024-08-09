# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD
from faebryk.libs.util import times


class Crystal(Module):
    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _PARAMs(Module.PARAMS()):
            frequency = TBD[float]()
            frequency_tolerance = TBD[Range]()
            frequency_temperature_tolerance = TBD[Range]()
            frequency_ageing = TBD[Range]()
            equivalent_series_resistance = TBD[float]()
            shunt_capacitance = TBD[float]()
            load_impedance = TBD[float]()

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            gnd = Electrical()
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        # ----------------------------------------
        #               parameters
        # ----------------------------------------

        # ----------------------------------------
        #                traits
        # ----------------------------------------
        self.add_trait(has_designator_prefix_defined("XTAL"))

        # ----------------------------------------
        #                aliases
        # ----------------------------------------

        # ----------------------------------------
        #                connections
        # ----------------------------------------
