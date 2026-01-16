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


class is_alias_bus_parameter(fabll.Node):
    """
    Marks a parameter as a bus parameter that aliases across a bus.
    This means that its constraints are dependent on the bus connections.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())
    _resolved_graphs: set[int] = set()

    def __init__(self, instance: fabll.graph.BoundNode):
        super().__init__(instance)

        self._guard = False
        self._merged: set[int] = set()

    @staticmethod
    def _ensure_operand(obj: fabll.Node) -> "F.Parameters.can_be_operand":
        if isinstance(obj, F.Parameters.can_be_operand):
            return obj
        return obj.get_trait(F.Parameters.can_be_operand)

    @classmethod
    def _alias_is(cls, left: fabll.Node, right: fabll.Node) -> None:
        F.Expressions.Is.bind_typegraph(tg=left.tg).create_instance(g=left.g).setup(
            cls._ensure_operand(left),
            cls._ensure_operand(right),
            assert_=True,
        )

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

    @assert_once
    def resolve(self, interfaces: set[fabll.Node]):
        if self._guard:
            return

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

        params = [
            fabll.Node.with_names(
                interface.get_children(
                    direct_only=True, types=fabll.Node, include_root=False
                )
            )[param_name]
            for interface in interfaces
        ]
        params_with_guard = [
            (param, param.get_trait(is_alias_bus_parameter)) for param in params
        ]

        # Disable guards to prevent infinite recursion
        for param, guard in params_with_guard:
            guard._guard = True
            guard._merged.add(id(self_param))

        new_merge = {p for p in params if id(p) not in self._merged}

        # Alias bus parameters
        for param in new_merge:
            self._merged.add(id(param))
            self._alias_is(self_param, param)

        # Enable guards again
        for _, guard in params_with_guard:
            guard._guard = False

    @staticmethod
    def resolve_bus_parameters(g: graph.GraphView, tg: fbrk.TypeGraph):
        bus_parameters = cast(
            list[tuple[fabll.Node, is_alias_bus_parameter]],
            [
                (fabll.Traits(impl).get_obj_raw(), impl)
                for impl in fabll.Traits.get_implementors(
                    is_alias_bus_parameter.bind_typegraph(tg), g=g
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

        # find for all buses an interface that represents it, and puts its params here
        # we use that connected interfaces are the same type and thus have the same params
        # TODO: limitation: specialization (need to subgroup by type) (see exception)
        param_bus_representatives: set[tuple[fabll.Node, is_alias_bus_parameter]] = set()

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

        # exec resolution
        for _, trait in param_bus_representatives:
            bus_representative_interface = (
                trait._get_interface_parent_and_param_name()[0]
            )
            param_bus = busses.get(
                bus_representative_interface, {bus_representative_interface}
            )
            trait.resolve(param_bus)

        times.add("merge parameters")
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
