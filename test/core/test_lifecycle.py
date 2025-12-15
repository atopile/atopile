# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.node as fabll


class _Bare(fabll.Node):
    pass


class _Harness(fabll.Node):
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())


def test_lifecycle_transitions_and_guards():
    collection_root = _Bare()
    collection_root.add_child(_Bare())

    assert collection_root.get_lifecycle_stage() == "collection"

    # Building the typegraph keeps us in collection
    collection_root.create_typegraph()
    assert collection_root.get_lifecycle_stage() == "collection"

    # Instantiation transitions to runtime
    runtime_root = _Harness()
    fabll.Node.instantiate(runtime_root)
    assert runtime_root.get_lifecycle_stage() == "runtime"

    # Collection-only APIs now fail
    with pytest.raises(RuntimeError, match="Operation only permitted before"):
        runtime_root.create_typegraph()

    with pytest.raises(RuntimeError, match="Operation only permitted before"):
        runtime_root.add_child(_Bare())


def test_moduleinterface_runtime_only_operations():
    iface = fabll.ModuleInterface()
    assert iface.get_lifecycle_stage() == "collection"

    # Runtime-only API is blocked until instantiation
    with pytest.raises(RuntimeError, match="Operation requires runtime graph access"):
        iface.get_connected()

    fabll.Node.instantiate(iface)
    assert iface.get_lifecycle_stage() == "runtime"
    assert iface.get_connected() == {}
