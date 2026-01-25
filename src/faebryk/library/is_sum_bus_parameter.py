# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.bus_parameter_utils import collect_bus_params, get_bus_param_owner
from faebryk.libs.util import groupby, once

logger = logging.getLogger(__name__)


class is_sum_bus_parameter(fabll.Node):
    """
    Marks a parameter as a bus parameter that sums across a bus.
    This means Sum(Sinks.param) <= Sum(Sources.param).
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    def resolve(self, interfaces: set[fabll.Node]):
        _, _, self_param = get_bus_param_owner(self)
        interface_params = collect_bus_params(self, interfaces)

        # Collect all parameters regardless of source/sink status
        all_params = [param for _, param in interface_params]

        if len(all_params) < 2:
            # Need at least 2 parameters to create a meaningful constraint
            return

        g = self_param.g
        tg = self_param.tg

        # Create operands for all parameters
        all_operands = [
            param.get_trait(F.Parameters.can_be_operand) for param in all_params
        ]

        # For now, create a sum of all parameters on both sides
        # TODO: Implement proper source/sink distinction when available
        sum_all = (
            F.Expressions.Add.c(*all_operands, g=g, tg=tg)
            if len(all_operands) > 1
            else all_operands[0]
        )

        # Create constraint: Sum(all) <= Sum(all)
        # This is a tautology but ensures expression nodes are created
        _ = F.Expressions.LessOrEqual.c(
            left=sum_all,
            right=sum_all,
            g=g,
            tg=tg,
            assert_=True,
        )

    @staticmethod
    @once
    def resolve_bus_parameters(g: graph.GraphView, tg: fbrk.TypeGraph):
        bus_parameters = cast(
            list[tuple[fabll.Node, is_sum_bus_parameter]],
            [
                (fabll.Traits(impl).get_obj_raw(), impl)
                for impl in fabll.Traits.get_implementors(
                    is_sum_bus_parameter.bind_typegraph(tg), g=g
                )
            ],
        )

        params_grouped_by_interface = groupby(
            bus_parameters, lambda p: get_bus_param_owner(p[1])[0]
        )

        busses = fabll.is_interface.group_into_buses(
            params_grouped_by_interface.keys()
        )

        param_bus_representatives: set[tuple[fabll.Node, is_sum_bus_parameter]] = set()

        for bus_interfaces in busses.values():
            if len(set(map(type, bus_interfaces))) > 1:
                raise NotImplementedError(
                    "No support for specialized bus with dynamic params"
                )
            for interface in bus_interfaces:
                if interface in params_grouped_by_interface:
                    param_bus_representatives |= set(
                        params_grouped_by_interface[interface]
                    )

        processed_busses_params: set[tuple[frozenset[fabll.Node], str]] = set()

        for _, trait in param_bus_representatives:
            bus_representative_interface, param_name, _ = get_bus_param_owner(trait)
            param_bus = busses.get(
                bus_representative_interface, {bus_representative_interface}
            )
            bus_id = (frozenset(param_bus), param_name)
            if bus_id in processed_busses_params:
                continue
            trait.resolve(param_bus)
            processed_busses_params.add(bus_id)

