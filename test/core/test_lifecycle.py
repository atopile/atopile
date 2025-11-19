# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node


class _Bare(Node):
    pass


class _Harness(Module):
    iface: ModuleInterface


def test_lifecycle_transitions_and_guards():
    collection_root = _Bare()
    collection_root.add(_Bare())

    assert collection_root.get_lifecycle_stage() == "collection"

    # Building the typegraph keeps us in collection
    collection_root.create_typegraph()
    assert collection_root.get_lifecycle_stage() == "collection"

    # Instantiation transitions to runtime
    runtime_root = _Harness()
    Node.instantiate(runtime_root)
    assert runtime_root.get_lifecycle_stage() == "runtime"

    # Collection-only APIs now fail
    with pytest.raises(RuntimeError, match="Operation only permitted before"):
        runtime_root.create_typegraph()

    with pytest.raises(RuntimeError, match="Operation only permitted before"):
        runtime_root.add(_Bare())


def test_moduleinterface_runtime_only_operations():
    iface = ModuleInterface()
    assert iface.get_lifecycle_stage() == "collection"

    # Runtime-only API is blocked until instantiation
    with pytest.raises(RuntimeError, match="Operation requires runtime graph access"):
        iface.get_connected()

    Node.instantiate(iface)
    assert iface.get_lifecycle_stage() == "runtime"
    assert iface.get_connected() == {}
