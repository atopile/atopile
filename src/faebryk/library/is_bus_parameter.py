# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, cast

from faebryk.core.cpp import Graph
from faebryk.core.graph import GraphFunctions
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import NodeException
from faebryk.core.parameter import Expression, Parameter
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    assert_once,
    cast_assert,
    groupby,
    not_none,
    once,
)

logger = logging.getLogger(__name__)


class is_bus_parameter(Parameter.TraitT.decless()):
    """
    Marks a parameter as a bus parameter.
    This means that it's constraints are dependent on the bus connections.
    """

    type KEY = Callable[[ModuleInterface], Parameter] | Parameter
    type EXPR_FACTORY = Callable[[], Expression]
    type REDUCE = tuple[KEY, EXPR_FACTORY]

    def __init__(self, key: KEY | None = None, reduce: REDUCE | None = None):
        """
        args:
            key: name of the parameter to be reduced given as lambda: node.param
            reduce: operation and 'name' of source parameters to be reduced
        example:
            See ElectricPower.py
        """
        super().__init__()

        self._key = key
        self._reduce = reduce

        self._guard = False
        self._merged: set[int] = set()

    @staticmethod
    def _get_key_from_parameter(
        obj: Parameter,
    ) -> Callable[[ModuleInterface], Parameter]:
        # TODO consider handling fields as obj
        # e.g ElectricPower.max_current instead of self.max_current

        p = obj.get_parent()
        if not p:
            raise NodeException(obj, "Can't auto-detect key for non-parented parameter")
        parent, name = p
        if not isinstance(parent, ModuleInterface):
            raise NodeException(
                obj, "Can't auto-detect key for non-mif child parameter"
            )

        return lambda mif: getattr(mif, name)

    def on_obj_set(self):
        if isinstance(self._key, Callable):
            return

        if self._key is None:
            obj = self.get_obj(Parameter)
        else:
            obj = self._key

        self._key = self._get_key_from_parameter(obj)

    @once
    def mif_parent(self) -> ModuleInterface:
        return cast_assert(ModuleInterface, not_none(self.obj.get_parent())[0])

    @assert_once
    def resolve(self, mifs: set[ModuleInterface]):
        if self._guard:
            return

        assert isinstance(self._key, Callable)

        mif_parent = self.mif_parent()
        self_param = self.get_obj(Parameter)
        if self._key(mif_parent) is not self_param:
            raise NodeException(self, "Key not mapping to parameter")

        params = [self._key(mif) for mif in mifs]
        params_with_guard = [
            (param, param.get_trait(is_bus_parameter)) for param in params
        ]

        # Disable guards to prevent infinite recursion
        for param, guard in params_with_guard:
            guard._guard = True
            guard._merged.add(id(self_param))

        new_merge = {p for p in params if id(p) not in self._merged}

        # Alias bus parameters
        for param in new_merge:
            self._merged.add(id(param))
            self_param.alias_is(param)

        # Reduce
        if self._reduce:
            # TODO use new_merge, then we can get rid of assert_once
            source_key, reducer = self._reduce
            if not isinstance(source_key, Callable):
                source_key = self._get_key_from_parameter(source_key)
            source_params = [source_key(mif) for mif in mifs]
            self_param.alias_is(reducer(*source_params))

        # Enable guards again
        for _, guard in params_with_guard:
            guard._guard = False

    @staticmethod
    def resolve_bus_parameters(graph: Graph):
        bus_parameters = cast(
            list[tuple[Parameter, is_bus_parameter]],
            GraphFunctions(graph).nodes_with_trait(is_bus_parameter),
        )

        times = Times()

        busses: list[set[ModuleInterface]] = []

        params_grouped_by_mif = groupby(bus_parameters, lambda p: p[1].mif_parent())

        # find for all busses a mif that represents it, and puts its dynamic params here
        # we use the that connected mifs are the same type and thus have the same params
        # TODO: limitation: specialization (need to subgroup by type) (see exception)
        param_bus_representatives: set[tuple[Parameter, is_bus_parameter]] = set()

        while params_grouped_by_mif:
            bus_representative_mif, bus_representative_params = (
                params_grouped_by_mif.popitem()
            )
            # expensive call
            paths = bus_representative_mif.get_connected(include_self=True)
            connections = set(paths.keys())

            busses.append(connections)
            if len(set(map(type, connections))) > 1:
                raise NotImplementedError(
                    "No support for specialized bus with dynamic params"
                )

            for m in connections:
                if m in params_grouped_by_mif:
                    del params_grouped_by_mif[m]
            param_bus_representatives |= set(bus_representative_params)

        times.add("get parameter connections")

        # exec resolution
        for _, trait in param_bus_representatives:
            bus_representative_mif = trait.mif_parent()
            # param_bus = find(busses, lambda bus: bus_representative_mif in bus)
            # FIXME: dirty workaround for mif bug
            param_busses = [bus for bus in busses if bus_representative_mif in bus]
            param_bus = {m for bus in param_busses for m in bus}
            trait.resolve(param_bus)

        times.add("merge parameters")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(times)
