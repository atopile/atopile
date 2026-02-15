# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import faebryk.core.node as fabll

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer


class implements_board_shape(fabll.Node):
    """
    Marker trait for nodes that can apply a board shape to a PCB transformer.

    Implementing node classes must provide:
    - `__apply_board_shape__(self, transformer)`
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def apply(self, transformer: "PCB_Transformer") -> None:
        owner_instance = fabll.Traits(self).get_obj_raw()
        owner_class: type[fabll.Node] = type(owner_instance)

        # Resolve the original Python class from the type graph so methods
        # defined on custom node types are available.
        type_node = owner_instance.get_type_node()
        type_map = fabll.TypeNodeBoundTG.__TYPE_NODE_MAP__
        if type_node is not None and type_node in type_map:
            owner_class = type_map[type_node].t
            owner_instance = owner_class.bind_instance(owner_instance.instance)

        apply_method = getattr(owner_class, "__apply_board_shape__", None)
        if apply_method is None:
            raise TypeError(
                f"{type(owner_instance).__name__} implements `implements_board_shape` "
                "but has no `__apply_board_shape__` method."
            )

        apply_method(owner_instance, transformer)
