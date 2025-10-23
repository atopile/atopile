# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class has_descriptive_properties(fabll.Node):
    """
    Attributes that will be written to PCB footprint
    """

    def get_properties(self) -> dict[str, str]:
        raise NotImplementedError()

    def add_properties(self, properties: dict[str, str]):
        raise NotImplementedError()

    @staticmethod
    def get_from(obj: fabll.Node, key: str) -> str | None:
        if not obj.has_trait(has_descriptive_properties):
            return None
        return obj.get_trait(has_descriptive_properties).get_properties().get(key)
