# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod

import pytest


def test_add():
    from faebryk.core.cpp import add, call_python_function

    assert add(1, 2) == 3
    assert add(1) == 2

    assert call_python_function(lambda: 1) == 1


def test_cnodes():
    from faebryk.core.cpp import LinkNamedParent, Node

    n1 = Node()
    n1.transfer_ownership(n1)
    n2 = Node()
    n2.transfer_ownership(n2)

    class _Node(Node):
        def __init__(self) -> None:
            super().__init__()
            self.transfer_ownership(self)

    n3 = _Node()

    n1.children.connect(n2.parent, LinkNamedParent("test1"))
    n2.children.connect(n3.parent, LinkNamedParent("test2"))
    print(n1)
    print(n2)
    print(n3)
    print(n1.children.get_children())
    print(n1.get_children(direct_only=True, sort=True))
    print(n2.get_children(direct_only=True, sort=True))
    print(n1.get_children(include_root=True, direct_only=False, sort=True))


def test_pynode():
    from faebryk.core.node import Node

    n = Node()
    print(n)
    print("---")

    class SubNode(Node):
        a: Node
        b: Node

    sn = SubNode()
    print(sn.a)

    print(sn.get_children(direct_only=True, types=Node))


def test_derived_pynodes():
    from faebryk.core.module import Module
    from faebryk.core.moduleinterface import ModuleInterface

    class App(Module):
        mif1: ModuleInterface
        mif2: ModuleInterface

    app = App()
    app.mif1.connect(app.mif2)

    print(app.mif1)
    print(app.mif1.get_connected())


def test_traits_basic():
    from faebryk.core.node import Node
    from faebryk.core.trait import Trait

    class T(Trait):
        @abstractmethod
        def do(self): ...

    class T_do(T.impl()):
        def do(self):
            print("do")

    class A(Node):
        t: T_do

    a = A()

    print(a.t)
    print(a.get_trait(T))
    a.get_trait(T).do()


def test_forgotten_superinit():
    from faebryk.core.node import Node

    class A(Node):
        def __init__(self):
            pass

    with pytest.raises(Exception):
        A()


def test_library_nodes():
    import faebryk.library._F as F

    x = F.Electrical()

    print(x)


def test_cobject():
    from faebryk.core.cpp import (
        GraphInterface,
        GraphInterfaceHierarchical,
        GraphInterfaceSelf,
        LinkDirect,
        LinkNamedParent,
    )

    g1 = GraphInterfaceSelf()
    g2 = GraphInterfaceHierarchical(True)
    g3 = GraphInterface()
    g4 = GraphInterfaceHierarchical(False)

    g2.connect(g3)
    g1.connect(g2, LinkDirect())
    g2.connect(g4, LinkNamedParent("test"))

    print(g1.edges)
    print(g2.edges)
    print(g1.get_graph())

    g1.get_graph().invalidate()


def test_link():
    from faebryk.core.cpp import GraphInterface, LinkDirect

    g1 = GraphInterface()
    g2 = GraphInterface()
    g1.connect(g2, LinkDirect())


def test_mif_link():
    from faebryk.core.link import LinkDirectConditional
    from faebryk.core.moduleinterface import ModuleInterface

    mif1 = ModuleInterface()
    mif2 = ModuleInterface()
    mif1.connect_shallow(mif2)
    paths = mif1.is_connected_to(mif2)
    assert len(paths) == 1
    path = paths[0]
    assert len(path) == 4
    assert isinstance(path[1].is_connected_to(path[2]), LinkDirectConditional)


def test_cpp_type():
    from faebryk.core.cpp import LinkDirect

    class LinkDirectDerived(LinkDirect):
        pass

    obj = LinkDirect()
    assert LinkDirect.is_cloneable(obj)

    obj2 = LinkDirectDerived()
    assert not LinkDirect.is_cloneable(obj2)


def test_isinstance_base():
    from faebryk.core.node import Node

    assert Node._mro == []
    assert Node._mro_ids == set()

    n = Node()
    assert n.isinstance(Node)
    assert n.isinstance([Node])


def test_isinstance_existing():
    from faebryk.core.module import Module
    from faebryk.core.node import Node

    assert Module._mro == [Module, Node]
    assert Module._mro_ids == {id(Module), id(Node)}

    m = Module()
    assert m.isinstance(Module)
    assert m.isinstance(Node)


def test_isinstance_new():
    from faebryk.core.module import Module
    from faebryk.core.node import Node

    class A(Module):
        pass

    class B(Module):
        pass

    a = A()
    assert a.isinstance(A)
    assert a.isinstance(Module)
    assert a.isinstance(Node)
    assert not a.isinstance(B)

    assert a.isinstance([A, Module, Node])
    assert a.isinstance([B, Module])
