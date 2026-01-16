# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.node import NodeException
from faebryk.libs.test.times import Times
from faebryk.libs.util import assert_once, groupby

logger = logging.getLogger(__name__)


class is_sum_bus_parameter(fabll.Node):
    """
    Marks a parameter as a bus parameter that sums across a bus.
    This means Sum(Sinks.param) <= Sum(Sources.param).
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())
    _resolved_graphs: set[int] = set()

    @staticmethod
    def _ensure_operand(obj: fabll.Node) -> "F.Parameters.can_be_operand":
        if isinstance(obj, F.Parameters.can_be_operand):
            return obj
        return obj.get_trait(F.Parameters.can_be_operand)

    def _get_interface_parent_and_param_name(self) -> tuple[fabll.Node, str]:
        obj = fabll.Traits(self).get_obj_raw()
        try:
            parent, _ = obj.get_parent_with_trait(fabll.is_interface, include_self=False)
        except KeyError as ex:
            raise NodeException(
                self, "Bus parameter does not belong to an interface node"
            ) from ex
        _, name = obj.get_parent_force()
        return parent, name

    @classmethod
    def _sum_operands(
        cls,
        operands: list[fabll.Node],
        *,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
    ) -> "F.Parameters.can_be_operand | None":
        if not operands:
            return None
        if len(operands) == 1:
            return cls._ensure_operand(operands[0])
        return F.Expressions.Add.c(
            *[cls._ensure_operand(op) for op in operands],
            g=g,
            tg=tg,
        )

    @assert_once
    def resolve(self, interfaces: set[fabll.Node]):
        interface_parent, param_name = self._get_interface_parent_and_param_name()
        self_param = fabll.Traits(self).get_obj_raw()

        children = fabll.Node.with_names(
            interface_parent.get_children(
                direct_only=True, types=fabll.Node, include_root=False
            )
        )
        if param_name not in children:
            raise NodeException(self, "Key not mapping to parameter")
        if not children[param_name].is_same(self_param):
            raise NodeException(self, "Key not mapping to parameter")

        interface_params = []
        for interface in interfaces:
            interface_children = fabll.Node.with_names(
                interface.get_children(
                    direct_only=True, types=fabll.Node, include_root=False
                )
            )
            if param_name not in interface_children:
                raise NodeException(self, "Key not mapping to parameter")
            interface_params.append((interface, interface_children[param_name]))

        sources = [
            param
            for interface, param in interface_params
            if interface.has_trait(F.is_source)
        ]
        sinks = [
            param
            for interface, param in interface_params
            if interface.has_trait(F.is_sink)
        ]

        if not sources or not sinks:
            return

        g = self_param.g
        tg = self_param.tg
        sum_sources = self._sum_operands(sources, g=g, tg=tg)
        sum_sinks = self._sum_operands(sinks, g=g, tg=tg)
        if sum_sources is None or sum_sinks is None:
            return

        F.Expressions.LessOrEqual.bind_typegraph(tg=tg).create_instance(g=g).setup(
            left=sum_sinks,
            right=sum_sources,
            assert_=True,
        )

    @staticmethod
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

        times = Times()

        params_grouped_by_interface = groupby(
            bus_parameters, lambda p: p[1]._get_interface_parent_and_param_name()[0]
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

        times.add("get parameter connections")

        for _, trait in param_bus_representatives:
            bus_representative_interface = (
                trait._get_interface_parent_and_param_name()[0]
            )
            param_bus = busses.get(
                bus_representative_interface, {bus_representative_interface}
            )
            trait.resolve(param_bus)

        times.add("sum parameters")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(times)

    @F.implements_design_check.register_post_instantiation_setup_check
    def __check_post_instantiation_setup__(self):
        obj = fabll.Traits(self).get_obj_raw()
        graph_id = id(obj.g)
        if graph_id in self._resolved_graphs:
            return
        self._resolved_graphs.add(graph_id)
        self.resolve_bus_parameters(obj.g, obj.tg)
