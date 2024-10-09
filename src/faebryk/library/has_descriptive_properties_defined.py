# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Mapping

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.core.trait import TraitImpl
from faebryk.libs.picker.picker import DescriptiveProperties


class has_descriptive_properties_defined(F.has_descriptive_properties.impl()):
    def __init__(
        self, properties: Mapping[str, str] | Mapping[DescriptiveProperties, str]
    ) -> None:
        super().__init__()
        self.properties = dict(properties.items())

    def get_properties(self) -> dict[str, str]:
        return self.properties

    def handle_duplicate(self, other: TraitImpl, node: Node) -> bool:
        if not isinstance(other, has_descriptive_properties_defined):
            self.properties.update(other.get_properties())
            return super().handle_duplicate(other, node)

        other.properties.update(self.properties)
        return False
