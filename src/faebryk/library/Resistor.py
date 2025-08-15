# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Resistor(Module):
    unnamed = L.list_field(2, F.Electrical)

    resistance = L.p_field(units=P.ohm)
    max_power = L.p_field(units=P.W)
    max_voltage = L.p_field(units=P.V)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.R
    )

    @L.rt_field
    def pickable(self) -> F.is_pickable_by_type:
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.RESISTORS,
            params=[self.resistance, self.max_power, self.max_voltage],
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.resistance, tolerance=True),
            S(self.max_power),
        )

    def allow_removal_if_zero(self):
        # FIXME: enable as soon as solver works
        return
        # import faebryk.library._F as F

        # @once
        # def do_replace():
        #     self.resistance.constrain_subset(0.0 * P.ohm)
        #     self.unnamed[0].connect(self.unnamed[1])
        #     self.add(F.has_part_removed())
        #
        # self.resistance.operation_is_superset(0.0 * P.ohm).if_then_else(
        #     lambda: do_replace(),
        #     lambda: None,
        #     preference=True,
        # )
        #
        # def replace_zero(m: Module, solver: Solver):
        #     assert m is self
        #
        #     solver.assert_any_predicate(
        #         [(Is(self.resistance, 0.0 * P.ohm), None)], lock=True
        #     )
        #
        # self.add(
        #    F.has_multi_picker(-100, F.has_multi_picker.FunctionPicker(replace_zero))
        # )

    # TODO: remove @https://github.com/atopile/atopile/issues/727
    @property
    def p1(self) -> F.Electrical:
        """One side of the resistor."""
        return self.unnamed[0]

    @property
    def p2(self) -> F.Electrical:
        """The other side of the resistor."""
        return self.unnamed[1]

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Resistor

        resistor = new Resistor
        resistor.resistance = 10kohm +/- 5%
        resistor.package = "0402"

        electrical1 ~ resistor.unnamed[0]
        electrical2 ~ resistor.unnamed[1]
        # OR
        electrical1 ~> resistor ~> electrical2
        """,
        language=F.has_usage_example.Language.ato,
    )
