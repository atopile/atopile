# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class SerializableMetadata(fabll.Node):
    """
    Attribute that will be written to PCB footprint
    """

    class MetaDataNode(fabll.Node):
        key = F.Parameters.StringParameter.MakeChild()
        value = F.Parameters.StringParameter.MakeChild()

        @classmethod
        def MakeChild(cls, key: str, value: str) -> fabll._ChildField[Self]:
            out = fabll._ChildField(cls)
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.key], key)
            )
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.value], value)
            )
            return out

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    data = F.Collections.PointerSet.MakeChild()

    @classmethod
    def get_properties(cls, node: fabll.Node) -> dict[str, str]:
        trait_obj = node.try_get_trait(cls)
        properties: dict[str, str] = {}
        if trait_obj:
            for data in trait_obj.data.get().as_list():
                data = data.cast(cls.MetaDataNode)
                properties[data.key.get().extract_singleton()] = (
                    data.value.get().extract_singleton()
                )
        return dict(sorted(properties.items()))

    @classmethod
    def MakeChild(cls, data: dict[str, str]) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        for key, value in data.items():
            meta_node = cls.MetaDataNode.MakeChild(key, value)
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge([out, cls.data], [meta_node])
            )
        return out

    def setup(self, data: dict[str, str]) -> Self:
        for key, value in data.items():
            data_node = self.MetaDataNode.bind_typegraph_from_instance(
                self.instance
            ).create_instance(g=self.instance.g())
            data_node.key.get().set_singleton(value=key)
            data_node.value.get().set_singleton(value=value)
            self.add_child(data_node)
            self.data.get().append(data_node)

        return self
