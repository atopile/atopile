# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.core.node as fabll  # noqa: F401
import faebryk.library._F as F  # noqa: F401

# from faebryk.core.parameter import Add, ParameterOperatable
from faebryk.libs.util import times  # noqa: F401

logger = logging.getLogger(__name__)


class MultiCapacitor(fabll.Node):
    """
    MultiCapacitor acts a single cap but contains multiple in parallel.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    class TemperatureCoefficient(Enum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    unnamed = [F.Electrical.MakeChild() for _ in range(2)]
    capacitance = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Farad)
    max_voltage = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Volt)
    # temperature_coefficient = fabll.Parameter.MakeChild_Enum(
    #     enum_t=TemperatureCoefficient
    # )
    count = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Natural)

    _can_attach = F.can_attach_to_footprint_symmetrically.MakeChild()
    _can_bridge = F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])

    _simple_repr = F.has_simple_value_representation_based_on_params_chain.MakeChild(
        params={
            "capacitance": capacitance,
            "max_voltage": max_voltage,
            # "temperature_coefficient": temperature_coefficient,
        }
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.C
    ).put_on_type()

    def capacitors(self) -> list[F.Capacitor]:
        count = self.count
        return times(count, F.Capacitor)

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

    # def set_equal_capacitance(self, capacitance: ParameterOperatable):
    #     op = capacitance / self._count

    #     self.set_equal_capacitance_each(op)

    # def set_equal_capacitance_each(self, capacitance: ParameterOperatable.NumberLike):
    #     for c in self.capacitors:
    #         c.capacitance.constrain_subset(capacitance)

    @classmethod
    def from_capacitors(cls, *capacitors: F.Capacitor):
        # TODO consider merging them more flatly (for multicaps)
        obj = cls(len(capacitors))
        for c_old, c_new in zip(capacitors, obj.capacitors):
            c_new.specialize(c_old)
        return obj

    usage_example = F.has_usage_example.MakeChild(
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
    ).put_on_type()
