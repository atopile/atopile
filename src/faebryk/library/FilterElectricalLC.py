# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class FilterElectricalLC(fabll.Node):
    """
    Basic Electrical LC filter
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    in_ = F.ElectricSignal.MakeChild()
    out = F.ElectricSignal.MakeChild()
    capacitor = F.Capacitor.MakeChild()
    inductor = F.Inductor.MakeChild()

    z0 = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    filter = F.Filter.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    # def __preinit__(self):
    #     self.order.alias_is(2)
    #     self.response.alias_is(F.Filter.Response.LOWPASS)

    #     Li = self.inductor.inductance
    #     C = self.capacitor.capacitance
    #     fc = self.cutoff_frequency

    #     fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))
    #     Li.alias_is((1 / (2 * math.pi * fc)) ** 2 / C)
    #     C.alias_is((1 / (2 * math.pi * fc)) ** 2 / Li)

    #     # low pass
    #     self.in_.line.connect_via(
    #         (self.inductor, self.capacitor),
    #         self.in_.reference.lv,
    #     )

    #     self.in_.line.connect_via(self.inductor, self.out.line)
