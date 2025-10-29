# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Mapping

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_descriptive_properties_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, properties: Mapping[str, str]) -> None:
        super().__init__()
        self.properties: dict[str, str] = dict(properties)

    def get_properties(self) -> dict[str, str]:
        return self.properties

    # def handle_duplicate(self, old: TraitImpl, node: fabll.Node) -> bool:
    #     if not isinstance(old, has_descriptive_properties_defined):
    #         assert isinstance(old, F.has_descriptive_properties)
    #         self.properties.update(old.get_properties())
    #         return super().handle_duplicate(old, node)

    #     old.properties.update(self.properties)
    #     return False
