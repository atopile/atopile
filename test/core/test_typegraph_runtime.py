# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.graph import InstanceGraphFunctions


def test_moduleinterface_get_connected_requires_typegraph():
    class NodeWithInterface(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    class Harness(fabll.Node):
        left: NodeWithInterface
        right: NodeWithInterface

    app = Harness()
    app.left._is_interface.get().connect(app.right)

    # Before TypeGraph: requires TypeGraph to be built
    with pytest.raises(RuntimeError, match="requires runtime graph access"):
        app.left._is_interface.get().get_connected()

    typegraph, _ = app.create_typegraph()

    # After create_typegraph, still requires instantiation+binding
    with pytest.raises(RuntimeError, match="requires runtime graph access"):
        app.left.get_connected()

    # Instantiate, bind, execute runtime
    instance_root = InstanceGraphFunctions.create(typegraph, type(app).__qualname__)
    app._bind_instance_hierarchy(instance_root)
    app._execute_runtime_functions()

    # Now binding succeeds, but pathfinder not implemented yet
    # Returns empty (mock result until pathfinder is ported to Zig)
    connected = app.left.get_connected()
    assert set(connected.keys()) == set()  # TODO: Will be {app.right} after pathfinder


def test_trait_binding_has_composition_edge():
    class HasDemoTrait(Trait):
        pass

    class HasDemoTraitImpl(HasDemoTrait.impl()):
        pass

    class Harness(fabll.Node):
        trait: HasDemoTraitImpl

    app = Harness()

    with pytest.raises(RuntimeError):
        app.trait._ensure_instance_bound()

    typegraph, _ = app.create_typegraph()

    # Still fails without instantiation+binding
    with pytest.raises(RuntimeError, match="requires runtime graph access"):
        app.trait._ensure_instance_bound()

    # Instantiate, bind, execute runtime
    instance_root = InstanceGraphFunctions.create(typegraph, type(app).__qualname__)
    app._bind_instance_hierarchy(instance_root)
    app._execute_runtime_functions()

    trait_bound = app.trait._ensure_instance_bound()
    parent_edge = EdgeComposition.get_parent_edge(bound_node=trait_bound)
    assert parent_edge is not None
    assert EdgeComposition.get_name(edge=parent_edge.edge()) == "trait"
