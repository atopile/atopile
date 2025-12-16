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
    #                 enums
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

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    capacitance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Farad.MakeChild()
    )
    max_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt.MakeChild())
    temperature_coefficient = F.Parameters.EnumParameter.MakeChild(
        enum_t=TemperatureCoefficient
    )
    count = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless.MakeChild(),
        domain=F.NumberDomain.Args(negative=False, integer=True),
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    for e in unnamed:
        lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
        lead.add_dependant(
            fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead])
        )
        e.add_dependant(lead)

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeEdge(["unnamed[0]"], ["unnamed[1]"])
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(capacitance, tolerance=True),
            S(max_voltage),
            # S(temperature_coefficient),
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.C)
    )

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    # def capacitors(self) -> list[F.Capacitor]:
    #     count = self.count
    #     return times(count, F.Capacitor)

    # def __preinit__(self):
    #     # ------------------------------------
    #     #           connections
    #     # ------------------------------------

    #     self.unnamed[0].connect(*(c.unnamed[0] for c in self.capacitors))
    #     self.unnamed[1].connect(*(c.unnamed[1] for c in self.capacitors))

    #     # ------------------------------------
    #     #          parametrization
    #     # ------------------------------------
    #     self.capacitance.alias_is(Add(*(c.capacitance for c in self.capacitors)))
    #     for c in self.capacitors:
    #         # TODO use min once available
    #         self.max_voltage.constrain_le(c.max_voltage)
    #         self.temperature_coefficient.constrain_superset(c.temperature_coefficient)

    # def set_equal_capacitance(self, capacitance: ParameterOperatable):
    #     op = capacitance / self._count

    #     self.set_equal_capacitance_each(op)

    # def set_equal_capacitance_each(self, capacitance: ParameterOperatable.NumberLike):
    #     for c in self.capacitors:
    #         c.capacitance.constrain_subset(capacitance)

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
