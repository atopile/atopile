# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class SerializableMetadata(fabll.Node):
    """
    Attribute that will be written to PCB footprint
    """

    key_ = F.Parameters.StringParameter.MakeChild()
    value_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def get_properties(cls, node: fabll.Node) -> dict[str, str]:
        properties = {}
        metadata_nodes = node.get_children(direct_only=True, types=cls)
        for meta in metadata_nodes:
            meta = SerializableMetadata.bind_instance(meta.instance)
            properties[meta.key] = meta.value
        return properties

    @classmethod
    def get_property(cls, node: fabll.Node, key: str) -> str | None:
        metadata_nodes = node.get_children(direct_only=True, types=cls)
        for meta in metadata_nodes:
            meta = SerializableMetadata.bind_instance(meta.instance)
            if meta.key == key:
                return None if meta.value is None else str(meta.value)
        return None

    @property
    def key(self) -> F.Literals.Strings | None:
        return self.key_.get().try_extract_constrained_literal()

    @property
    def value(self) -> F.Literals.Strings | None:
        return self.value_.get().try_extract_constrained_literal()

    # def handle_duplicate(self, old: TraitImpl, node: fabll.Node) -> bool:
    #     if not isinstance(old, has_descriptive_properties_defined):
    #         assert isinstance(old, F.has_descriptive_properties)
    #         self.properties.update(old.get_properties())
    #         return super().handle_duplicate(old, node)

    #     old.properties.update(self.properties)
    #     return False

    @staticmethod
    def get_from(node: fabll.Node, key: str) -> str | None:
        return SerializableMetadata.get_property(node, key)

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

    def setup(self, key: str, value: str) -> Self:
        self.key_.get().constrain_to_single(value=key)
        self.value_.get().constrain_to_single(value=value)
        return self
