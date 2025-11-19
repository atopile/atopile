# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.trait import Trait
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition


def test_moduleinterface_get_connected_requires_typegraph():
    class Harness(Module):
        left: ModuleInterface
        right: ModuleInterface

    app = Harness()
    app.left.connect(app.right)

    # Before TypeGraph: requires TypeGraph to be built
    with pytest.raises(RuntimeError, match="requires runtime graph access"):
        app.left.get_connected()

    from faebryk.core.graph import InstanceGraphFunctions

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

    class Harness(Module):
        trait: HasDemoTraitImpl

    app = Harness()

    with pytest.raises(RuntimeError):
        app.trait._ensure_instance_bound()

    from faebryk.core.graph import InstanceGraphFunctions

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
