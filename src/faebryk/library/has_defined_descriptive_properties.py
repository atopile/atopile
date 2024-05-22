# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module
from faebryk.library.has_descriptive_properties import has_descriptive_properties


class has_defined_descriptive_properties(has_descriptive_properties.impl()):
    def __init__(self, properties: dict[str, str]) -> None:
        super().__init__()
        self.properties = properties

    def add_properties(self, properties: dict[str, str]):
        self.properties.update(properties)

    def get_properties(self) -> dict[str, str]:
        return self.properties

    @classmethod
    def add_properties_to(cls, module: Module, properties: dict[str, str]):
        if not module.has_trait(has_descriptive_properties):
            module.add_trait(cls(properties))
        else:
            module.get_trait(has_descriptive_properties).add_properties(properties)
