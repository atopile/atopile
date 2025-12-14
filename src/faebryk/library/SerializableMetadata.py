# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class SerializableMetadata(fabll.Node):
    """
    Attribute that will be written to PCB footprint
    """

    # TODO: this is used as trait with multi instance, but is not a trait itself.
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

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
    def key(self) -> str:
        return self.key_.get().force_extract_literal().get_values()[0]

    @property
    def value(self) -> str:
        return self.value_.get().force_extract_literal().get_values()[0]

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
    def MakeChild(cls, key: str, value: str) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.key_], key)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.value_], value)
        )
        return out

    def setup(self, key: str, value: str) -> Self:
        self.key_.get().alias_to_single(value=key)
        self.value_.get().alias_to_single(value=value)
        return self
