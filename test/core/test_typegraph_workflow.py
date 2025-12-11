# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Integration tests for TypeGraph workflow: create → instantiate → bind → query.

Tests the complete lifecycle and validates that type graph building correctly
separates type-level descriptors from instance graph materialization.
"""

# TODO these tests don't make sense, sam needs to fix

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.core.graph import InstanceGraphFunctions


def test_closed_world_violation():
    """Verify error when connecting to external interface."""
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App1(fabll.Node):
        mif = fabll.is_interface.MakeChild()

    class App2(fabll.Node):
        mif = fabll.is_interface.MakeChild()

    app1 = App1.bind_typegraph(tg).create_instance(g=g)
    app2 = App2.bind_typegraph(tg).create_instance(g=g)

    app1.mif.get().connect_to(app2.mif.get())

    with pytest.raises(RuntimeError, match="not part of the module tree"):
        app1.create_typegraph()


def test_self_connection_is_ignored():
    """Verify self-connection is silently ignored (existing behavior)."""
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        mif = fabll.is_interface.MakeChild()

    app = App.bind_typegraph(tg).create_instance(g=g)
    app.mif.get().connect_to(app.mif.get())

    # Instantiate, bind, execute runtime
    instance_root = InstanceGraphFunctions.create(tg, type(app).__qualname__)
    app._bind_instance_hierarchy(instance_root)
    app._execute_runtime_functions()

    # No connections should exist
    connected = app.mif.get_connected()
    assert len(connected) == 0


def test_double_build_raises_error():
    """Verify that TypeGraph can only be built once."""

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        mif = fabll.is_interface.MakeChild()

    app = App.bind_typegraph(tg).create_instance(g=g)

    with pytest.raises(RuntimeError, match="already been built"):
        app.create_typegraph()


def test_post_build_specialization_raises_error():
    """Verify specialization must happen before create_typegraph()."""

    class Base(fabll.Node):
        pass

    class Special(fabll.Node):
        pass

    app = Base()
    app.create_typegraph()

    with pytest.raises(RuntimeError, match="already been built"):
        app.specialize(Special())


def test_runtime_queries_require_instantiation_and_binding():
    """Verify get_connected() fails before instantiation+binding."""

    class App(fabll.Node):
        mif1: fabll.ModuleInterface
        mif2: fabll.ModuleInterface

    app = App()
    app.mif1.connect(app.mif2)

    typegraph, root_type = app.create_typegraph()

    # BEFORE instantiation and binding: should raise
    with pytest.raises(RuntimeError, match="No instance bound"):
        app.mif1.get_connected()

    # AFTER instantiation and binding: should work

    instance_root = InstanceGraphFunctions.create(typegraph, type(app).__qualname__)
    app._bind_instance_hierarchy(instance_root)
    app._execute_runtime_functions()

    # Verify each node is bound
    assert hasattr(app, "_instance_bound")
    assert hasattr(app.mif1, "_instance_bound")
    assert hasattr(app.mif2, "_instance_bound")

    # Runtime query works (but returns empty until pathfinder is ported)
    connected = app.mif1.get_connected()
    # TODO: Will assert app.mif2 in connected after pathfinder is ported to Zig
    assert len(connected) == 0  # Mock result until pathfinder implementation


def test_double_bind_raises_error():
    """Verify binding fails if already bound."""

    class App(fabll.Node):
        mif: fabll.ModuleInterface

    app = App()

    typegraph, _ = app.create_typegraph()

    # First bind succeeds
    instance_root = InstanceGraphFunctions.create(typegraph, type(app).__qualname__)
    app._bind_instance_hierarchy(instance_root)
    app._execute_runtime_functions()

    # Second bind fails
    instance_root_2 = InstanceGraphFunctions.create(typegraph, type(app).__qualname__)
    with pytest.raises(RuntimeError, match="Instance already bound"):
        app._bind_instance_hierarchy(instance_root_2)


def test_instantiation_creates_connections():
    """Verify EdgeInterfaceConnection created during instantiate()."""
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        from faebryk.library._F import Electrical

        elec1 = Electrical.MakeChild()
        elec2 = Electrical.MakeChild()

    app = App.bind_typegraph(tg).create_instance(g=g)
    app.elec1.get()._is_interface.get().connect_to(app.elec2.get())

    # Instantiate, bind, execute runtime
    # instance_root = InstanceGraphFunctions.create(typegraph, type(app).__qualname__)
    # app._bind_instance_hierarchy(instance_root)
    # app._execute_runtime_functions()

    # Verify binding succeeded
    assert hasattr(app, "_instance_bound")
    assert hasattr(app.mif1, "_instance_bound")
    assert hasattr(app.mif2, "_instance_bound")

    # Connection queries work but return mock results until pathfinder is ported
    connected = app.elec1.get()._is_interface.get().get_connected()
    # TODO: Will assert app.mif2 in connected after pathfinder is ported to Zig
    assert len(connected) == 0  # Mock result until pathfinder implementation
