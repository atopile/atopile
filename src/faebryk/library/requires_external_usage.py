# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


class requires_external_usage(Trait.decless()):
    @property
    def fulfilled(self) -> bool:
        obj = self.get_obj(type=ModuleInterface)
        connected_to = set(obj.connected.get_connected_nodes(types=[type(obj)]))
        # no connections
        if not connected_to:
            return False
        parent = obj.get_parent()
        # no shared parent possible
        if parent is None:
            return True
        parent, _ = parent

        for c in connected_to:
            if parent not in {p for p, _ in c.get_hierarchy()}:
                return True

        return False

    def on_obj_set(self):
        if not isinstance(self.obj, ModuleInterface):
            raise NotImplementedError("Only supported on ModuleInterfaces")

        super().on_obj_set()
