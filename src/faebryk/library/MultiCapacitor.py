# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.parameter import Add, Parameter, ParameterOperatable
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P, Quantity
from faebryk.libs.util import once, times  # noqa: F401

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

    # Not pickable
    pickable = None

    @L.rt_field
    def capacitors(self) -> list[F.Capacitor]:
        return times(self._count, F.Capacitor)

    # hack to make faster
    @property
    @once
    def capacitance(self) -> Parameter:
        raise Exception("not implemented")
        c = self.add(Parameter(units=P.F), "capacitance")
        c.alias_is(Add(*(c_inner.capacitance for c_inner in self.capacitors)))
        return c

    @property
    @once
    def max_voltage(self) -> Parameter:
        max_voltage = self.add(Parameter(units=P.V), "max_voltage")
        for c_inner in self.capacitors:
            max_voltage.constrain_le(c_inner.max_voltage)
        return max_voltage

    @property
    @once
    def temperature_coefficient(self) -> Parameter:
        raise Exception("not implemented")
        temperature_coefficient = self.add(
            Parameter(domain=L.Domains.ENUM(F.Capacitor.TemperatureCoefficient)),
            "temperature_coefficient",
        )
        for c_inner in self.capacitors:
            temperature_coefficient.constrain_superset(c_inner.temperature_coefficient)
        return temperature_coefficient

    simple_value_representation = None

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        self.unnamed[0].connect(*(c.unnamed[0] for c in self.capacitors))
        self.unnamed[1].connect(*(c.unnamed[1] for c in self.capacitors))

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        # self.capacitance.alias_is(Add(*(c.capacitance for c in self.capacitors)))
        # for c in self.capacitors:
        #    # TODO use min once available
        #    self.max_voltage.constrain_le(c.max_voltage)
        #    self.temperature_coefficient.constrain_superset(c.temperature_coefficient)

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
        footprint: str | None = None,
    ):
        for c in self.capacitors:
            c.explicit(nominal_capacitance, tolerance, footprint)

    @classmethod
    def from_capacitors(cls, *capacitors: F.Capacitor):
        # TODO consider merging them more flatly (for multicaps)
        obj = cls(len(capacitors))
        for c_old, c_new in zip(capacitors, obj.capacitors):
            c_new.specialize(c_old)
        return obj
