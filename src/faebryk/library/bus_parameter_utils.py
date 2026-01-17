# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
from faebryk.core.node import NodeException


def get_bus_param_owner(trait: fabll.Node) -> tuple[fabll.Node, str, fabll.Node]:
    obj = fabll.Traits(trait).get_obj_raw()
    try:
        parent, _ = obj.get_parent_with_trait(fabll.is_interface, include_self=False)
    except KeyError as ex:
        raise NodeException(
            trait, "Bus parameter does not belong to an interface node"
        ) from ex
    _, name = obj.get_parent_force()
    children = fabll.Node.with_names(
        parent.get_children(direct_only=True, types=fabll.Node, include_root=False)
    )
    if name not in children or not children[name].is_same(obj):
        raise NodeException(trait, "Key not mapping to parameter")
    return parent, name, obj


def collect_bus_params(
    trait: fabll.Node, interfaces: set[fabll.Node]
) -> list[tuple[fabll.Node, fabll.Node]]:
    _, param_name, _ = get_bus_param_owner(trait)
    params = []
    for interface in interfaces:
        children = fabll.Node.with_names(
            interface.get_children(
                direct_only=True, types=fabll.Node, include_root=False
            )
        )
        if param_name not in children:
            raise NodeException(trait, "Key not mapping to parameter")
        params.append((interface, children[param_name]))
    return params
