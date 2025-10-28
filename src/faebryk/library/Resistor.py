# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from typing import Any

import faebryk.core.node as fabll
from faebryk.library import _F as F

# from faebryk.libs.units import P


class Resistor(fabll.Node):
    @classmethod
    def __create_type__(cls, t: fabll.BoundNodeType[fabll.Node, Any]) -> None:
        # TODO: change to list_field
        cls.p1 = t.Child(nodetype=F.Electrical)
        cls.p2 = t.Child(nodetype=F.Electrical)

        # TODO: add units to parameters
        cls.resistance = t.Child(nodetype=fabll.Parameter)
        cls.max_power = t.Child(nodetype=fabll.Parameter)
        cls.max_voltage = t.Child(nodetype=fabll.Parameter)

        cls.can_attach_to_footprint_symmetrically = t.Child(
            nodetype=F.can_attach_to_footprint_symmetrically
        )

        # TODO: Add child and constrain to new literal
        cls.designator_prefix = t.BoundChildOfType(nodetype=F.has_designator_prefix)
        cls.designator_prefix.get().prefix_param.get().constrain_to_literal(
            g=t.tg.get_graph_view(), value=F.has_designator_prefix.Prefix.R
        )

        cls.can_bridge = t.Child(nodetype=F.can_bridge)

        # TODO: Constrain is_pickable_by_type.endpoint to 'resistors'
        cls.is_pickable_by_type = t.Child(nodetype=F.is_pickable_by_type)
        fabll.Set.append_make_links(
            t=t,
            set_child=cls.is_pickable_by_type.nodetype.params_,
            children_to_append=[cls.resistance, cls.max_power, cls.max_voltage],
        )
        t.add_make_constrain_to_literal(
            child_to_constrain=["is_pickable_by_type", "endpoint_"],
            value=F.is_pickable_by_type.Endpoint.RESISTORS,
        )

        # TODO: Add specs
        # S(self.resistance, tolerance=True),
        # S(self.max_power),
        cls.simple_value_representation = t.Child(
            nodetype=F.has_simple_value_representation_based_on_params_chain
        )
        t.add_link_pointer(
            lhs_reference_path=["simple_value_representation", "params"],
            rhs_reference_path=["resistance"],
            identifier="resistance",
        )
        t.add_link_pointer(
            lhs_reference_path=["simple_value_representation", "params"],
            rhs_reference_path=["max_power"],
            identifier="max_power",
        )

        cls.usage_example = t.BoundChildOfType(nodetype=F.has_usage_example)
        cls.usage_example.get().example.get().constrain_to_literal(
            g=t.tg.get_graph_view(),
            value="""
            import Resistor
            resistor = new Resistor
            resistor.resistance = 10kohm +/- 5%
            """,
        )
        cls.usage_example.get().language.get().constrain_to_literal(
            g=t.tg.get_graph_view(), value=F.has_usage_example.Language.ato
        )
