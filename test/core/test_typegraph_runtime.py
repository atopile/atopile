# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.core.graph import InstanceGraphFunctions


def test_moduleinterface_get_connected_requires_typegraph():
    class Harness(fabll.Node):
        left: fabll.ModuleInterface
        right: fabll.ModuleInterface

    app = Harness()
    app.left.connect(app.right)

    # Before TypeGraph: requires TypeGraph to be built
    with pytest.raises(RuntimeError, match="requires runtime graph access"):
        app.left.get_connected()

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


def _make_graph_and_typegraph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_fabll_basic():
    @dataclass(frozen=True)
    class FileLocationAttributes(NodeAttributes):
        start_line: int
        start_column: int
        end_line: int
        end_column: int

    class FileLocation(Node[FileLocationAttributes]):
        Attributes = FileLocationAttributes

    class TestNodeWithoutAttr(Node):
        pass

    @dataclass(frozen=True)
    class SliceAttributes(NodeAttributes):
        start: int
        end: int
        step: int

    class Slice(Node[SliceAttributes]):
        Attributes = SliceAttributes
        tnwa = _ChildField(TestNodeWithoutAttr)

    class TestNodeWithChildren(Node):
        tnwa1 = _ChildField(TestNodeWithoutAttr)
        tnwa2 = _ChildField(TestNodeWithoutAttr)
        _edge = _EdgeField(
            lhs=[tnwa1],
            rhs=[tnwa2],
            edge=fbrk.EdgePointer.build(identifier=None, order=None),
        )

    g, tg = _make_graph_and_typegraph()
    fileloc = FileLocation.bind_typegraph(tg).create_instance(
        g=g,
        attributes=FileLocationAttributes(
            start_line=1,
            start_column=1,
            end_line=1,
            end_column=1,
        ),
    )

    print("fileloc.start_column:", fileloc.attributes().start_column)
    print("fileloc:", fileloc.attributes())

    tnwa = TestNodeWithoutAttr.bind_typegraph(tg).create_instance(g=g)
    print("tnwa:", tnwa.instance.node().get_dynamic_attrs())

    slice = Slice.bind_typegraph(tg).create_instance(
        g=g, attributes=SliceAttributes(start=1, end=1, step=1)
    )
    print("Slice:", slice.attributes())
    print("Slice.tnwa:", slice.tnwa.get().attributes())

    tnwc = TestNodeWithChildren.bind_typegraph(tg).create_instance(g=g)
    assert (
        not_none(
            fbrk.EdgePointer.get_referenced_node_from_node(
                node=tnwc.tnwa1.get().instance
            )
        )
        .node()
        .is_same(other=tnwc.tnwa2.get().instance.node())
    )

    tnwc_children = tnwc.get_children(direct_only=False, types=(TestNodeWithoutAttr,))
    assert len(tnwc_children) == 2
    assert tnwc_children[0].get_name() == "tnwa1"
    assert tnwc_children[1].get_name() == "tnwa2"
    print(tnwc_children[0].get_full_name())


def test_typegraph_of_type_and_instance_roundtrip():
    g, tg = _make_graph_and_typegraph()

    class Simple(Node):
        """Minimal node to exercise fbrk.TypeGraph helpers."""

        pass

    bound_simple = Simple.bind_typegraph(tg)
    type_node = bound_simple.get_or_create_type()

    tg_from_type = fbrk.TypeGraph.of_type(type_node=type_node)
    assert tg_from_type is not None
    rebound = tg_from_type.get_type_by_name(type_identifier=Simple._type_identifier())
    assert rebound is not None
    assert rebound.node().is_same(other=type_node.node())

    simple_instance = bound_simple.create_instance(g=g)
    tg_from_instance = fbrk.TypeGraph.of_instance(
        instance_node=simple_instance.instance
    )
    assert tg_from_instance is not None
    rebound_from_instance = tg_from_instance.get_type_by_name(
        type_identifier=Simple._type_identifier()
    )
    assert rebound_from_instance is not None
    assert rebound_from_instance.node().is_same(other=type_node.node())

    root_uuid = simple_instance.instance.node().get_uuid()
    assert simple_instance.get_root_id() == f"0x{root_uuid:X}"


def test_trait_mark_as_trait():
    g, tg = _make_graph_and_typegraph()

    class ExampleTrait(Node):
        _is_trait = ImplementsTrait.MakeChild().put_on_type()

    class ExampleNode(Node):
        example_trait = ExampleTrait.MakeChild()

    node = ExampleNode.bind_typegraph(tg).create_instance(g=g)
    assert node.try_get_trait(ExampleTrait) is not None


def test_set_basic():
    """Test basic Set functionality: append, as_list, as_set."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    # Create a Set and some elements
    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)
    elem3 = Element.bind_typegraph(tg).create_instance(g=g)

    # Test empty set
    assert len(set_node.as_list()) == 0
    assert len(set_node.as_set()) == 0

    # Test single append
    set_node.append(elem1)
    elems = set_node.as_list()
    assert len(elems) == 1
    assert elems[0].instance.node().is_same(other=elem1.instance.node())

    # Test multiple appends
    set_node.append(elem2, elem3)
    elems = set_node.as_list()
    assert len(elems) == 3
    assert elems[0].instance.node().is_same(other=elem1.instance.node())
    assert elems[1].instance.node().is_same(other=elem2.instance.node())
    assert elems[2].instance.node().is_same(other=elem3.instance.node())

    # Test as_set returns correct type and size
    elem_set = set_node.as_set()
    assert isinstance(elem_set, set)
    assert len(elem_set) == 3


def test_set_deduplication():
    """Test that Set correctly deduplicates elements by UUID."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)

    # Append elem1 multiple times
    set_node.append(elem1)
    set_node.append(elem1)
    set_node.append(elem1)

    # Should only have one element
    elems = set_node.as_list()
    assert len(elems) == 1
    assert elems[0].instance.node().is_same(other=elem1.instance.node())

    # Append elem2 and elem1 again
    set_node.append(elem2, elem1)
    elems = set_node.as_list()
    # Should still only have 2 unique elements
    assert len(elems) == 2
    assert elems[0].instance.node().is_same(other=elem1.instance.node())
    assert elems[1].instance.node().is_same(other=elem2.instance.node())


def test_set_order_preservation():
    """Test that Set preserves insertion order of unique elements."""

    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)
    elem3 = Element.bind_typegraph(tg).create_instance(g=g)

    # Append in specific order
    set_node.append(elem2)
    set_node.append(elem1)
    set_node.append(elem3)

    elems = set_node.as_list()
    assert len(elems) == 3
    # Order should be preserved: elem2, elem1, elem3
    assert elems[0].instance.node().is_same(other=elem2.instance.node())
    assert elems[1].instance.node().is_same(other=elem1.instance.node())
    assert elems[2].instance.node().is_same(other=elem3.instance.node())

    # Appending duplicates shouldn't change order
    set_node.append(elem1, elem2)
    elems = set_node.as_list()
    assert len(elems) == 3
    assert elems[0].instance.node().is_same(other=elem2.instance.node())
    assert elems[1].instance.node().is_same(other=elem1.instance.node())
    assert elems[2].instance.node().is_same(other=elem3.instance.node())


def test_set_chaining():
    """Test that Set.append returns self for method chaining."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)
    elem3 = Element.bind_typegraph(tg).create_instance(g=g)

    # Test method chaining
    result = set_node.append(elem1).append(elem2).append(elem3)

    # Result should be the same set_node
    assert result.instance.node().is_same(other=set_node.instance.node())

    # All elements should be in the set
    elems = set_node.as_list()
    assert len(elems) == 3


def test_type_children():
    import faebryk.library._F as F

    g, tg = _make_graph_and_typegraph()
    Resistor = F.Resistor.bind_typegraph(tg=tg)

    children = Node.bind_instance(Resistor.get_or_create_type()).get_children(
        direct_only=True,
        types=Node,
    )
    print(indented_container([c.get_full_name(types=True) for c in children]))
