# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.parameter import ParameterOperatable
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.util import times  # noqa: F401

logger = logging.getLogger(__name__)


class MultiCapacitor(F.Capacitor):
    """
    MultiCapacitor acts a single cap but contains multiple in parallel.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __init__(self, count: int):
        self._count = count

    @L.rt_field
    def capacitors(self) -> list[F.Capacitor]:
        return times(self._count, F.Capacitor)

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        self.unnamed[0].connect(*(c.unnamed[0] for c in self.capacitors))
        self.unnamed[1].connect(*(c.unnamed[1] for c in self.capacitors))

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.capacitance.alias_is(sum(c.capacitance for c in self.capacitors))

    def set_equal_capacitance(self, capacitance: ParameterOperatable):
        op = capacitance / self._count

        self.set_equal_capacitance_each(op)

    def set_equal_capacitance_each(self, capacitance: ParameterOperatable.NumberLike):
        for c in self.capacitors:
            c.capacitance.constrain_subset(capacitance)
