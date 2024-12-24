# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Mapping

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.trait import TraitImpl
from faebryk.libs.picker.picker import DescriptiveProperties


class has_descriptive_properties_defined(F.has_descriptive_properties.impl()):
    def __init__(
        self,
        properties: Mapping[str, str]
        | Mapping[DescriptiveProperties, str]
        | Mapping[str | DescriptiveProperties, str],
    ) -> None:
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
        old._handle_prop_set()
        return False

    def _handle_prop_set(self):
        obj = self.get_obj(type=Module)

        # TODO: deprecate using DescriptiveProperties directly and then get rid of this
        if (
            DescriptiveProperties.partno in self.properties
            and DescriptiveProperties.manufacturer in self.properties
        ):
            obj.add(
                F.is_pickable_by_part_number(
                    self.properties[DescriptiveProperties.manufacturer],
                    self.properties[DescriptiveProperties.partno],
                )
            )

        if "LCSC" in self.properties:
            obj.add(
                F.is_pickable_by_supplier_id(
                    self.properties["LCSC"],
                    supplier=F.is_pickable_by_supplier_id.Supplier.LCSC,
                )
            )

    def on_obj_set(self):
        super().on_obj_set()
        self._handle_prop_set()
