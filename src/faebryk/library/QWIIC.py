# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class QWIIC(Module):
    """
    Sparkfun QWIIC connection spec. Also compatible with Adafruits STEMMA QT.
    Delivers 3.3V power + F.I2C over JST SH 1mm pitch 4 pin connectors
    """

    # interfaces
    i2c: F.I2C
    power: F.ElectricPower

    def __preinit__(self):
        # set constraints
        self.power.voltage.merge(F.Range.from_center_rel(3.3 * P.V, 0.05))
        # TODO: self.power.source_current.merge(F.Constant(226 * P.mA))

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("J")

    datasheet = L.f_field(F.has_datasheet_defined)("https://www.sparkfun.com/qwiic")
