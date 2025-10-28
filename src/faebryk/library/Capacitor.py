# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge import can_bridge
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix import has_designator_prefix
from faebryk.library.has_usage_example import has_usage_example
from faebryk.library.is_pickable_by_type import is_pickable_by_type
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import Quantity

# FIXME: this has to go this way to avoid gen_F detecting a circular import
if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower

logger = logging.getLogger(__name__)


class Capacitor(fabll.Node):
    class TemperatureCoefficient(Enum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    @classmethod
    def __create_type__(cls, t: fabll.TypeNodeBoundTG[fabll.Node, Any]) -> None:
        # TODO: Switch to list_field unnamed = fabll.list_field(2, F.Electrical)
        cls.p1 = t.Child(nodetype=Electrical)
        cls.p2 = t.Child(nodetype=Electrical)

        cls.capacitance = t.Child(nodetype=fabll.Parameter)
        cls.max_voltage = t.Child(nodetype=fabll.Parameter)
        cls.temperature_coefficient = t.Child(nodetype=fabll.Parameter)

        cls.can_attach_to_footprint_symmetrically = t.Child(
            nodetype=can_attach_to_footprint_symmetrically
        )

        # Child of the typegraph, not a make child that should be replicated in
        # instances
        cls.designator_prefix = t.BoundChildOfType(nodetype=has_designator_prefix)
        cls.designator_prefix.get().prefix_param.get().constrain_to_literal(
            g=t.tg.get_graph_view(), value=has_designator_prefix.Prefix.C
        )

        cls.is_pickable_by_type = t.Child(nodetype=is_pickable_by_type)
        t.add_link_pointer(
            lhs_reference_path=["is_pickable_by_type", "params"],
            rhs_reference_path=["capacitance"],
            identifier="capacitance",
        )
        t.add_link_pointer(
            lhs_reference_path=["is_pickable_by_type", "params"],
            rhs_reference_path=["max_voltage"],
            identifier="max_voltage",
        )
        t.add_link_pointer(
            lhs_reference_path=["is_pickable_by_type", "params"],
            rhs_reference_path=["temperature_coefficient"],
            identifier="temperature_coefficient",
        )

        cls.can_bridge = t.Child(nodetype=can_bridge)

        cls.usage_example = t.BoundChildOfType(nodetype=has_usage_example)
        cls.usage_example.get().example.get().constrain_to_literal(
            g=t.tg.get_graph_view(),
            value="""
            import Capacitor

            capacitor = new Capacitor
            capacitor.capacitance = 100nF +/- 10%
            assert capacitor.max_voltage within 25V to 50V
            capacitor.package = "0603"

            electrical1 ~ capacitor.unnamed[0]
            electrical2 ~ capacitor.unnamed[1]
            # OR
            electrical1 ~> capacitor ~> electrical2
            """,
        )
        cls.usage_example.get().language.get().constrain_to_literal(
            g=t.tg.get_graph_view(), value=has_usage_example.Language.ato
        )

    @fabll.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.capacitance, tolerance=True),
            S(self.max_voltage),
            S(self.temperature_coefficient),
        )

    def explicit(
        self,
        nominal_capacitance: Quantity | None = None,
        tolerance: float | None = None,
        size: SMDSize | None = None,
    ):
        if nominal_capacitance is not None:
            if tolerance is None:
                tolerance = 0.2
            capacitance = fabll.Range.from_center_rel(nominal_capacitance, tolerance)
            self.capacitance.constrain_subset(capacitance)

        if size is not None:
            self.add(F.has_package_requirements(size=size))

    class _has_power(fabll.Node):
        """
        This trait is used to add power interfaces to
        capacitors who use them, keeping the interfaces
        off caps which don't use it.

        Caps have power-interfaces when used with them.
        """

        def __init__(self, power: "ElectricPower") -> None:
            super().__init__()
            self.power = power

    @property
    def power(self) -> "ElectricPower":
        """An `ElectricPower` interface, which is connected to the capacitor."""
        # FIXME: this has to go this way to avoid gen_F detecting a circular import
        from faebryk.library.ElectricPower import ElectricPower

        if self.has_trait(self._has_power):
            power = self.get_trait(self._has_power).power
        else:
            power = ElectricPower()
            self.add(power, name="power_shim")
            power.hv.connect_via(self, power.lv)
            self.add(self._has_power(power))

        return power
