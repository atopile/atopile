# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.parameter import Add, ParameterOperatable
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import Quantity
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
        super().__init__()
        self._count = count

    pickable = None  # type: ignore

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
        self.capacitance.alias_is(Add(*(c.capacitance for c in self.capacitors)))
        for c in self.capacitors:
            # TODO use min once available
            self.max_voltage.constrain_le(c.max_voltage)
            self.temperature_coefficient.constrain_superset(c.temperature_coefficient)

    def set_equal_capacitance(self, capacitance: ParameterOperatable):
        op = capacitance / self._count

        self.set_equal_capacitance_each(op)

    def set_equal_capacitance_each(self, capacitance: ParameterOperatable.NumberLike):
        for c in self.capacitors:
            c.capacitance.constrain_subset(capacitance)

    # TODO kinda weird
    def explicit(
        self,
        nominal_capacitance: Quantity | None = None,
        tolerance: float | None = None,
        size: SMDSize | None = None,
    ):
        for c in self.capacitors:
            c.explicit(nominal_capacitance, tolerance, size=size)

    @classmethod
    def from_capacitors(cls, *capacitors: F.Capacitor):
        # TODO consider merging them more flatly (for multicaps)
        obj = cls(len(capacitors))
        for c_old, c_new in zip(capacitors, obj.capacitors):
            c_new.specialize(c_old)
        return obj

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import MultiCapacitor

        multicapacitor = new MultiCapacitor<count=4>
        for c in multicapacitor.capacitors:
            c.capacitance = 100nF +/- 10%
            c.package = "0402"

        electrical1 ~ multicapacitor.unnamed[0]
        electrical2 ~ multicapacitor.unnamed[1]
        """,
        language=F.has_usage_example.Language.ato,
    )
