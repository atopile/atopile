# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any

from _pytest.hookspec import pytest_assertion_pass

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
import faebryk.library._F as F


class SerializableMetadata(fabll.Node):
    """
    Attribute that will be written to PCB footprint
    """

    key_ = fabll.Parameter.MakeChild()
    value_ = fabll.Parameter.MakeChild()

    @classmethod
    def get_properties(cls, node: fabll.Node) -> dict[str, str]:
        properties = {}
        metadata_nodes = node.get_children(direct_only=True, types=cls)
        for meta in metadata_nodes:
            meta = SerializableMetadata.bind_instance(meta.instance)
            properties[meta.key] = meta.value
        return properties

    @classmethod
    def get_property(cls, node: fabll.Node, key: str) -> fabll.LiteralT | None:
        metadata_nodes = node.get_children(direct_only=True, types=cls)
        for meta in metadata_nodes:
            meta = SerializableMetadata.bind_instance(meta.instance)
            if meta.key == key:
                return meta.value
        return None

    @property
    def key(self) -> fabll.LiteralT | None:
        return self.key_.get().try_extract_constrained_literal()

    @property
    def value(self) -> fabll.LiteralT | None:
        return self.value_.get().try_extract_constrained_literal()

    # def handle_duplicate(self, old: TraitImpl, node: fabll.Node) -> bool:
    #     if not isinstance(old, has_descriptive_properties_defined):
    #         assert isinstance(old, F.has_descriptive_properties)
    #         self.properties.update(old.get_properties())
    #         return super().handle_duplicate(old, node)

    #     old.properties.update(self.properties)
    #     return False

    @staticmethod
    def get_from(obj: fabll.Node, key: str) -> str | None:
        if not obj.has_trait(has_descriptive_properties):
            return None
        return obj.get_trait(has_descriptive_properties).get_properties().get(key)

    @classmethod
    def MakeChild(cls, key: str, value: str) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.key_], key)
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.value_], value)
        )
        return out
