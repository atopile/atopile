# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import NodeException
from faebryk.core.parameter import Parameter
from faebryk.libs.util import cast_assert, not_none, once

logger = logging.getLogger(__name__)


class is_dynamic_by_connections_alias(F.is_dynamic.impl()):
    def __init__(self, key: Callable[[ModuleInterface], Parameter]) -> None:
        super().__init__()
        self._key = key
        self._guard = False
        self._merged: set[int] = set()

    @once
    def mif_parent(self) -> ModuleInterface:
        return cast_assert(ModuleInterface, not_none(self.obj.get_parent())[0])

    def exec_for_mifs(self, mifs: set[ModuleInterface]):
        if self._guard:
            return

        mif_parent = self.mif_parent()
        self_param = self.get_obj(Parameter)
        if self._key(mif_parent) is not self_param:
            raise NodeException(self, "Key not mapping to parameter")

        # only self
        if len(mifs) == 1:
            return

        params = [self._key(mif) for mif in mifs]
        params_with_guard = [
            (
                param,
                cast_assert(
                    is_dynamic_by_connections_alias, param.get_trait(F.is_dynamic)
                ),
            )
            for param in params
        ]

        # Disable guards to prevent infinite recursion
        for param, guard in params_with_guard:
            guard._guard = True
            guard._merged.add(id(self_param))

        # Merge parameters
        for param in params:
            if id(param) in self._merged:
                continue
            self._merged.add(id(param))
            self_param.alias_is(param)

        # Enable guards again
        for _, guard in params_with_guard:
            guard._guard = False

    def exec(self):
        mif_parent = self.mif_parent()
        self.exec_for_mifs(set(mif_parent.get_connected()))
