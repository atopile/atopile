# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Mapping

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.core.trait import TraitImpl


class has_descriptive_properties_defined(F.has_descriptive_properties.impl()):
    def __init__(self, properties: Mapping[str, str]) -> None:
        super().__init__()
        self.properties: dict[str, str] = dict(properties)

    def get_properties(self) -> dict[str, str]:
        return self.properties

    def handle_duplicate(self, old: TraitImpl, node: Node) -> bool:
        if not isinstance(old, has_descriptive_properties_defined):
            assert isinstance(old, F.has_descriptive_properties)
            self.properties.update(old.get_properties())
            return super().handle_duplicate(old, node)

        old.properties.update(self.properties)
        return False
