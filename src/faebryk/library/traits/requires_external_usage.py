# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


class requires_external_usage(Trait.decless()):
    class RequiresExternalUsageNotFulfilled(
        F.implements_design_check.UnfulfilledCheckException
    ):
        def __init__(self, nodes: list[Node]):
            super().__init__(
                "Nodes requiring external usage but not used externally",
                nodes=nodes,
            )

    @property
    def fulfilled(self) -> bool:
        obj = self.get_obj(type=ModuleInterface)
        connected_to = set(obj.connected.get_connected_nodes(types=[type(obj)]))
        parent = obj.get_parent()
        # no shared parent possible
        if parent is None:
            return True
        # TODO: disables checks for floating modules
        if parent[0].get_parent() is None:
            return True
        # no connections
        if not connected_to:
            return False
        parent, _ = parent

        for c in connected_to:
            if parent not in {p for p, _ in c.get_hierarchy()}:
                return True

        return False

    def on_obj_set(self):
        if not isinstance(self.obj, ModuleInterface):
            raise NotImplementedError("Only supported on ModuleInterfaces")

        super().on_obj_set()

    design_check: F.implements_design_check

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        if not self.fulfilled:
            raise requires_external_usage.RequiresExternalUsageNotFulfilled(
                nodes=[self.obj],
            )
