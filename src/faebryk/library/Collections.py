from typing import TYPE_CHECKING, Callable, Protocol, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll

RefPath = fabll.RefPath
EdgeField = fabll._EdgeField


def _get_pointer_references(
    node: fabll.NodeT, identifier: str | None = None
) -> "list[fabll.NodeT]":
    references: list[tuple[int | None, graph.BoundNode]] = []

    def _collect(
        ctx: list[tuple[int | None, graph.BoundNode]], bound_edge: graph.BoundEdge
    ) -> None:
        edge_name = bound_edge.edge().name()
        if identifier is not None and edge_name != identifier:
            return
        target = fbrk.EdgePointer.get_referenced_node(edge=bound_edge.edge())
        if target is None:
            return
        edge_order = fbrk.EdgePointer.get_order(edge=bound_edge.edge())
        node = bound_edge.g().bind(node=target)
        ctx.append((edge_order, node))

    if identifier is None:
        fbrk.EdgePointer.visit_pointed_edges(
            bound_node=node.instance,
            ctx=references,
            f=_collect,
        )
    else:
        fbrk.EdgePointer.visit_pointed_edges_with_identifier(
            bound_node=node.instance,
            identifier=identifier,
            ctx=references,
            f=_collect,
        )
    return [
        fabll.Node(instance=instance)
        for _, instance in sorted(references, key=lambda x: x[0] or 0)
    ]


class PointerEdgeFactory(Protocol):
    def __call__(self, identifier: str | None) -> fbrk.EdgeCreationAttributes: ...


class CollectionProtocol(Protocol):
    def as_list(self) -> list[fabll.NodeT]: ...


class PointerProtocol(CollectionProtocol):
    def deref(self) -> fabll.NodeT: ...
    def point(self, node: fabll.NodeT) -> None: ...

    @classmethod
    def MakeChild(cls) -> fabll._ChildField[Self]: ...  # type: ignore[invalid-method-override]
    @classmethod
    def MakeEdge(cls, pointer_ref: RefPath, elem_ref: RefPath) -> fabll._EdgeField:
        """
        Directional pointer edge from `pointer_ref` -> `elem_ref`
        """
        ...

    @classmethod
    def MakeEdgeForField(
        cls, out: fabll._ChildField, pointer_ref: RefPath, field: fabll._ChildField
    ) -> None: ...


def AbstractPointer(
    edge_factory: PointerEdgeFactory,
    retrieval_function: Callable[[fabll.NodeT], fabll.NodeT],
    typename: str | None = None,
) -> type[PointerProtocol]:
    class ConcretePointer(fabll.Node):
        _edge_factory = edge_factory
        _retrieval_function = retrieval_function

        def as_list(self) -> list[fabll.NodeT]:
            return [self.deref()]

        def deref(self) -> fabll.NodeT:
            return type(self)._retrieval_function(self)

        def point(self, node: fabll.NodeT) -> None:
            self.connect(node, type(self)._edge_factory(identifier=None))

        @classmethod
        def MakeEdge(cls, pointer_ref: RefPath, elem_ref: RefPath) -> fabll._EdgeField:
            """
            Directional pointer edge from `pointer_ref` -> `elem_ref`
            """
            return fabll._EdgeField(
                pointer_ref,
                elem_ref,
                edge=cls._edge_factory(identifier=None),
            )

        @classmethod
        def MakeEdgeForField(
            cls, out: fabll._ChildField, pointer_ref: RefPath, field: fabll._ChildField
        ):
            out.add_dependant(cls.MakeEdge(pointer_ref, [field]))
            out.add_dependant(field, before=True)

    ConcretePointer.__name__ = typename or f"ConcretePointer_{id(ConcretePointer):x}"
    return ConcretePointer  # type: ignore


class SequenceProtocol(CollectionProtocol):
    def append(self, *elems: fabll.NodeT) -> Self: ...

    @classmethod
    def MakeChild(cls) -> fabll._ChildField[Self]: ...  # type: ignore[invalid-method-override]

    @classmethod
    def MakeEdge(cls, seq_ref: RefPath, elem_ref: RefPath, order: int) -> EdgeField: ...

    @classmethod
    def MakeEdges(
        cls, seq_ref: RefPath, elem_ref: list[RefPath]
    ) -> "list[EdgeField]": ...


if TYPE_CHECKING:

    class _SequenceNodeType(fabll.Node, SequenceProtocol): ...


class SequenceEdgeFactory(Protocol):
    def __call__(
        self, identifier: str, order: int | None
    ) -> fbrk.EdgeCreationAttributes: ...


def AbstractSequence(
    edge_factory: SequenceEdgeFactory,
    retrieval_function: Callable[[fabll.NodeT, str], list[fabll.NodeT]],
    typename: str | None = None,
) -> "type[_SequenceNodeType]":
    class ConcreteSequence(fabll.Node):
        """
        A sequence of (non-unique) elements.
        Sorted by insertion order.
        """

        _elem_identifier = "e"
        _edge_factory = edge_factory
        _retrieval_function = retrieval_function

        def append(self, *elems: fabll.NodeT) -> Self:
            cur_len = len(self.as_list())
            for i, elem in enumerate(elems):
                self.connect(
                    elem,
                    type(self)._edge_factory(
                        identifier=self._elem_identifier, order=cur_len + i
                    ),
                )
            return self

        def as_list(self) -> list[fabll.NodeT]:
            return type(self)._retrieval_function(self, self._elem_identifier)

        @classmethod
        def MakeEdge(
            cls, seq_ref: RefPath, elem_ref: RefPath, order: int
        ) -> fabll._EdgeField:
            return fabll._EdgeField(
                seq_ref,
                elem_ref,
                edge=type(cls)._edge_factory(
                    identifier=cls._elem_identifier, order=order
                ),
            )

        @classmethod
        def MakeEdges(
            cls, seq_ref: RefPath, elem_ref: list[RefPath]
        ) -> "list[fabll._EdgeField]":
            return [cls.MakeEdge(seq_ref, elem, i) for i, elem in enumerate(elem_ref)]

    ConcreteSequence.__name__ = typename or f"ConcreteSequence_{id(ConcreteSequence):x}"
    return ConcreteSequence  # type: ignore


class SetProtocol(Protocol):
    def append(self, *elems: fabll.NodeT) -> Self: ...
    def as_list(self) -> list[fabll.NodeT]: ...
    def as_set(self) -> set[fabll.NodeT]: ...
    @classmethod
    def MakeChild(cls, *elems: RefPath) -> fabll._ChildField[Self]: ...
    @classmethod
    def MakeEdge(cls, set_ref: RefPath, elem_ref: RefPath) -> fabll._EdgeField: ...
    @classmethod
    def MakeEdges(
        cls, set_ref: RefPath, elem_ref: list[RefPath]
    ) -> "list[fabll._EdgeField]": ...


class SetEdgeFactory(Protocol):
    def __call__(
        self, identifier: str, order: int | None
    ) -> fbrk.EdgeCreationAttributes: ...


def AbstractSet(
    edge_factory: SetEdgeFactory,
    retrieval_function: Callable[[fabll.NodeT, str], list[fabll.NodeT]],
    typename: str | None = None,
) -> type[SetProtocol]:
    class ConcreteSet(fabll.Node):
        _elem_identifier = "e"
        _edge_factory = edge_factory
        _retrieval_function = retrieval_function

        def append(self, *elems: fabll.NodeT) -> Self:
            by_uuid = {elem.instance.node().get_uuid(): elem for elem in elems}
            cur = self.as_list()
            cur_len = len(cur)
            for node in cur:
                by_uuid.pop(node.instance.node().get_uuid(), None)

            for i, elem in enumerate(by_uuid.values()):
                edge_attrs = type(self)._edge_factory(
                    identifier=self._elem_identifier, order=cur_len + i
                )
                self.connect(elem, edge_attrs)

            return self

        @classmethod
        def MakeEdge(cls, set_ref: RefPath, elem_ref: RefPath) -> fabll._EdgeField:
            return fabll._EdgeField(
                set_ref,
                elem_ref,
                edge=cls._edge_factory(identifier=cls._elem_identifier, order=None),
            )

        @classmethod
        def MakeEdges(
            cls, set_ref: RefPath, elem_ref: list[RefPath]
        ) -> "list[fabll._EdgeField]":
            return [cls.MakeEdge(set_ref, elem) for elem in elem_ref]

        @classmethod
        def MakeChild(cls, *elems: RefPath) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
            out = fabll._ChildField(cls)
            for elem in elems:
                out.add_dependant(
                    fabll._EdgeField(
                        [out],
                        elem,
                        edge=cls._edge_factory(
                            identifier=cls._elem_identifier,
                            order=None,
                        ),
                    )
                )
            return out

        def as_list(self) -> list[fabll.NodeT]:
            return type(self)._retrieval_function(self, self._elem_identifier)

        def as_set(self) -> set[fabll.NodeT]:
            return set(self.as_list())

    ConcreteSet.__name__ = typename or f"ConcreteSet_{id(ConcreteSet):x}"
    return ConcreteSet


# --------------------------------------------------------------------------------------

# TODO this is an abomination
# get rid of the abstract bs and just reimplement sets wherever needed

Pointer = AbstractPointer(
    edge_factory=lambda identifier: fbrk.EdgePointer.build(
        identifier=identifier, order=None
    ),
    retrieval_function=lambda node: _get_pointer_references(node, None)[0],
    typename="Pointer",
)

PointerSequence = AbstractSequence(
    edge_factory=lambda identifier, order: fbrk.EdgePointer.build(
        identifier=identifier, order=order
    ),
    retrieval_function=_get_pointer_references,
    typename="PointerSequence",
)

PointerSet = AbstractSet(
    edge_factory=lambda identifier, order: fbrk.EdgePointer.build(
        identifier=identifier, order=order
    ),
    retrieval_function=_get_pointer_references,
    typename="PointerSet",
)


# TODO this is way too specific
class PointerTuple(fabll.Node):
    pointer = Pointer.MakeChild()
    literals = PointerSet.MakeChild()

    @classmethod
    def SetPointer(cls, tup_ref: RefPath, elem_ref: RefPath) -> fabll._EdgeField:
        ptr_ref = tup_ref
        ptr_ref.append(cls.pointer)
        return Pointer.MakeEdge(
            ptr_ref,
            elem_ref,
        )

    @classmethod
    def AppendLiteral(cls, tup_ref: RefPath, elem_ref: RefPath) -> fabll._EdgeField:
        set_ref = tup_ref  # TODO: Can this be done in a more elegant way?
        set_ref.append(cls.literals)
        return PointerSet.MakeEdge(
            tup_ref,
            elem_ref,
        )

    def deref_pointer(self) -> fabll.NodeT:
        electrical_ptr = self.pointer.get()
        return electrical_ptr.deref()

    def get_literals_as_list(self) -> list[fabll.LiteralT]:
        from faebryk.library import Literals

        def _lit_value(lit_node: fabll.Node) -> fabll.LiteralT:
            string_lit = Literals.Strings.bind_instance(instance=lit_node.instance)
            values = string_lit.get_values()
            if not values:
                raise ValueError("String literal has no values")
            return values[0]

        return [_lit_value(lit) for lit in self.literals.get().as_list()]

    def append_literal(self, literal: fabll.LiteralT) -> None:
        from faebryk.library import Literals

        lit = (
            Literals.Strings.bind_typegraph(tg=self.tg)
            .create_instance(g=self.instance.g())
            .setup_from_values(str(literal))
        )
        self.literals.get().append(lit)


# TESTS --------------------------------------------------------------------------------
def test_pointer_helpers():
    g, tg = fabll._make_graph_and_typegraph()

    class Leaf(fabll.Node):
        pass

    class Parent(fabll.Node):
        left = Leaf.MakeChild()
        right = Leaf.MakeChild()

    parent = Parent.bind_typegraph(tg).create_instance(g=g)
    left_child = parent.left.get()
    right_child = parent.right.get()

    parent.connect(
        left_child, fbrk.EdgePointer.build(identifier="left_ptr", order=None)
    )
    parent.connect(
        right_child, fbrk.EdgePointer.build(identifier="right_ptr", order=None)
    )

    pointed_edges: list[str | None] = []

    def _collect(names: list[str | None], edge: graph.BoundEdge):
        names.append(edge.edge().name())

    fbrk.EdgePointer.visit_pointed_edges(
        bound_node=parent.instance,
        ctx=pointed_edges,
        f=_collect,
    )
    assert pointed_edges.count("left_ptr") == 1
    assert pointed_edges.count("right_ptr") == 1

    left = fbrk.EdgePointer.get_pointed_node_by_identifier(
        bound_node=parent.instance,
        identifier="left_ptr",
    )
    assert left is not None
    assert left.node().is_same(other=left_child.instance.node())

    right = fbrk.EdgePointer.get_pointed_node_by_identifier(
        bound_node=parent.instance,
        identifier="right_ptr",
    )
    assert right is not None
    assert right.node().is_same(other=right_child.instance.node())

    parent.connect(left_child, fbrk.EdgePointer.build(identifier="shared", order=None))
    parent.connect(right_child, fbrk.EdgePointer.build(identifier="shared", order=None))

    shared_edges: list[graph.BoundEdge] = []

    def _collect_shared(ctx: list[graph.BoundEdge], edge: graph.BoundEdge):
        ctx.append(edge)

    fbrk.EdgePointer.visit_pointed_edges_with_identifier(
        bound_node=parent.instance,
        identifier="shared",
        ctx=shared_edges,
        f=_collect_shared,
    )
    assert len(shared_edges) == 2

    shared_nodes = _get_pointer_references(parent, identifier="shared")
    uuids = {node.instance.node().get_uuid() for node in shared_nodes}
    assert uuids == {
        left_child.instance.node().get_uuid(),
        right_child.instance.node().get_uuid(),
    }


def test_pointer_fabll():
    class Pointee(fabll.Node):
        pass

    class Holder(fabll.Node):
        pointer = Pointer.MakeChild()

        @classmethod
        def MakeChild(cls) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
            out = fabll._ChildField(cls)
            Pointer.MakeEdgeForField(out, [out, cls.pointer], Pointee.MakeChild())
            return out

    class App(fabll.Node):
        holder = Holder.MakeChild()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = App.bind_typegraph(tg).create_instance(g=g)

    pointee = app.holder.get().pointer.get().deref().try_cast(Pointee)
    assert pointee is not None
