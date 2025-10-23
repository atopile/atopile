# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from typing import Any

import faebryk.core.node as fabll
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge import can_bridge
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix import has_designator_prefix
from faebryk.library.has_simple_value_representation_based_on_params_chain import (
    has_simple_value_representation_based_on_params_chain,
)
from faebryk.library.has_usage_example import has_usage_example
from faebryk.library.is_pickable_by_type import is_pickable_by_type

# from faebryk.libs.units import P


class Resistor(fabll.Node):
    @classmethod
    def __create_type__(cls, t: fabll.BoundNodeType[fabll.Node, Any]) -> None:
        # TODO: change to list_field
        cls.p1 = t.Child(nodetype=Electrical)
        cls.p2 = t.Child(nodetype=Electrical)

        # TODO: add units to parameters
        cls.resistance = t.Child(nodetype=fabll.Parameter)
        cls.max_power = t.Child(nodetype=fabll.Parameter)
        cls.max_voltage = t.Child(nodetype=fabll.Parameter)

        cls.can_attach_to_footprint_symmetrically = t.Child(
            nodetype=can_attach_to_footprint_symmetrically
        )

        cls.designator_prefix = t.BoundChildOfType(nodetype=has_designator_prefix)
        cls.designator_prefix.get().prefix_param.get().constrain_to_literal(
            g=t.tg.get_graph_view(), value=has_designator_prefix.Prefix.R
        )

        cls.can_bridge = t.Child(nodetype=can_bridge)

        # TODO: Constrain is_pickable_by_type.endpoint to 'resistors'
        cls.is_pickable_by_type = t.Child(nodetype=is_pickable_by_type)
        t.add_link_pointer(
            lhs_reference_path=["is_pickable_by_type", "params_"],
            rhs_reference_path=["resistance"],
            identifier="resistance",
        )
        t.add_link_pointer(
            lhs_reference_path=["is_pickable_by_type", "params_"],
            rhs_reference_path=["max_power"],
        )
        t.add_link_pointer(
            lhs_reference_path=["is_pickable_by_type", "params_"],
            rhs_reference_path=["max_voltage"],
        )

        cls.simple_value_representation = t.Child(
            nodetype=has_simple_value_representation_based_on_params_chain
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

        cls.usage_example = t.BoundChildOfType(nodetype=has_usage_example)
        cls.usage_example.get().example.get().constrain_to_literal(
            g=t.tg.get_graph_view(),
            value="""
            import Resistor
            resistor = new Resistor
            resistor.resistance = 10kohm +/- 5%
            """,
        )
        cls.usage_example.get().language.get().constrain_to_literal(
            g=t.tg.get_graph_view(), value=has_usage_example.Language.ato
        )
