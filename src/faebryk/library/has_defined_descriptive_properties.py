# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.library.has_descriptive_properties import has_descriptive_properties


class has_defined_descriptive_properties(has_descriptive_properties.impl()):
    def __init__(self, properties: dict[str, str]) -> None:
        super().__init__()
        self.properties = properties

    def add_properties(self, properties: dict[str, str]):
        self.properties.update(properties)

    def get_properties(self) -> dict[str, str]:
        return self.properties
