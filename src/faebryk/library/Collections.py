from typing import Any, Callable, Protocol, Self

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode

Node = fabll.Node
RefPath = fabll.RefPath
ChildField = fabll.ChildField
EdgeField = fabll.EdgeField


def _get_pointer_references(
    node: Node[Any], identifier: str | None = None
) -> "list[Node[Any]]":
    references: list[tuple[int | None, BoundNode]] = []

    def _collect(
        ctx: list[tuple[int | None, BoundNode]], bound_edge: BoundEdge
    ) -> None:
        edge_name = bound_edge.edge().name()
        if identifier is not None and edge_name != identifier:
            return
        target = EdgePointer.get_referenced_node(edge=bound_edge.edge())
        if target is None:
            return
        edge_order = EdgePointer.get_order(edge=bound_edge.edge())
        node = bound_edge.g().bind(node=target)
        ctx.append((edge_order, node))

    if identifier is None:
        EdgePointer.visit_pointed_edges(
            bound_node=node.instance,
            ctx=references,
            f=_collect,
        )
    else:
        EdgePointer.visit_pointed_edges_with_identifier(
            bound_node=node.instance,
            identifier=identifier,
            ctx=references,
            f=_collect,
        )
    return [
        Node(instance=instance)
        for _, instance in sorted(references, key=lambda x: x[0] or 0)
    ]


class PointerEdgeFactory(Protocol):
    def __call__(self, identifier: str | None) -> EdgeCreationAttributes: ...


class CollectionProtocol(Protocol):
    def as_list(self) -> list[Node[Any]]: ...


class PointerProtocol(CollectionProtocol):
    def deref(self) -> Node[Any]: ...
    def point(self, node: Node[Any]) -> None: ...

    @classmethod
    def MakeChild(cls) -> ChildField[Any]: ...
    @classmethod
    def EdgeField(cls, pointer_ref: RefPath, elef_ref: RefPath) -> EdgeField: ...


def AbstractPointer(
    edge_factory: PointerEdgeFactory,
    retrieval_function: Callable[[Node[Any]], Node[Any]],
) -> type[PointerProtocol]:
    class ConcretePointer(Node):
        _edge_factory = edge_factory
        _retrieval_function = retrieval_function

        def as_list(self) -> list[Node[Any]]:
            return [self.deref()]

        def deref(self) -> Node[Any]:
            return type(self)._retrieval_function(self)

        def point(self, node: Node[Any]) -> None:
            self.connect(node, type(self)._edge_factory(identifier=None))

        @classmethod
        def EdgeField(cls, pointer_ref: RefPath, elem_ref: RefPath) -> EdgeField:
            return EdgeField(
                pointer_ref,
                elem_ref,
                edge=cls._edge_factory(identifier=None),
            )

    ConcretePointer.__name__ = f"ConcretePointer_{id(ConcretePointer):x}"
    return ConcretePointer


class SequenceProtocol(CollectionProtocol):
    def append(self, *elems: Node[Any]) -> Self: ...

    @classmethod
    def MakeChild(cls) -> ChildField[Any]: ...

    @classmethod
    def EdgeField(
        cls, seq_ref: RefPath, elem_ref: RefPath, order: int
    ) -> EdgeField: ...

    @classmethod
    def EdgeFields(
        cls, seq_ref: RefPath, elem_ref: list[RefPath]
    ) -> "list[EdgeField]": ...


class SequenceEdgeFactory(Protocol):
    def __call__(
        self, identifier: str, order: int | None
    ) -> EdgeCreationAttributes: ...


def AbstractSequence(
    edge_factory: SequenceEdgeFactory,
    retrieval_function: Callable[[Node[Any], str], list[Node[Any]]],
) -> type[SequenceProtocol]:
    class ConcreteSequence(Node):
        """
        A sequence of (non-unique) elements.
        Sorted by insertion order.
        """

        _elem_identifier = "e"
        _edge_factory = edge_factory
        _retrieval_function = retrieval_function

        def append(self, *elems: Node[Any]) -> Self:
            cur_len = len(self.as_list())
            for i, elem in enumerate(elems):
                self.connect(
                    elem,
                    type(self)._edge_factory(
                        identifier=self._elem_identifier, order=cur_len + i
                    ),
                )
            return self

        def as_list(self) -> list[Node[Any]]:
            return type(self)._retrieval_function(self, self._elem_identifier)

        @classmethod
        def EdgeField(
            cls, seq_ref: RefPath, elem_ref: RefPath, order: int
        ) -> EdgeField:
            return EdgeField(
                seq_ref,
                elem_ref,
                edge=type(cls)._edge_factory(
                    identifier=cls._elem_identifier, order=order
                ),
            )

        @classmethod
        def EdgeFields(
            cls, seq_ref: RefPath, elem_ref: list[RefPath]
        ) -> "list[EdgeField]":
            return [cls.EdgeField(seq_ref, elem, i) for i, elem in enumerate(elem_ref)]

    ConcreteSequence.__name__ = f"ConcreteSequence_{id(ConcreteSequence):x}"
    return ConcreteSequence


class SetProtocol(Protocol):
    def append(self, *elems: Node[Any]) -> Self: ...
    def as_list(self) -> list[Node[Any]]: ...
    def as_set(self) -> set[Node[Any]]: ...
    @classmethod
    def MakeChild(cls, *elems: RefPath) -> ChildField[Any]: ...
    @classmethod
    def EdgeField(cls, set_ref: RefPath, elem_ref: RefPath) -> EdgeField: ...
    @classmethod
    def EdgeFields(
        cls, set_ref: RefPath, elem_ref: list[RefPath]
    ) -> "list[EdgeField]": ...


class SetEdgeFactory(Protocol):
    def __call__(
        self, identifier: str, order: int | None
    ) -> EdgeCreationAttributes: ...


def AbstractSet(
    edge_factory: SetEdgeFactory,
    retrieval_function: Callable[[Node, str], list[Node[Any]]],
) -> type[SetProtocol]:
    class ConcreteSet(Node):
        _elem_identifier = "e"
        _edge_factory = edge_factory
        _retrieval_function = retrieval_function

        def append(self, *elems: Node[Any]) -> Self:
            by_uuid = {elem.instance.node().get_uuid(): elem for elem in elems}
            cur = self.as_list()
            cur_len = len(cur)
            for node in cur:
                by_uuid.pop(node.instance.node().get_uuid(), None)

            for i, elem in enumerate(by_uuid.values()):
                self.connect(
                    elem,
                    type(self)._edge_factory(
                        identifier=self._elem_identifier, order=cur_len + i
                    ),
                )

            return self

        @classmethod
        def EdgeField(cls, set_ref: RefPath, elem_ref: RefPath) -> EdgeField:
            return EdgeField(
                set_ref,
                elem_ref,
                edge=cls._edge_factory(identifier=cls._elem_identifier, order=None),
            )

        @classmethod
        def EdgeFields(
            cls, set_ref: RefPath, elem_ref: list[RefPath]
        ) -> "list[EdgeField]":
            return [cls.EdgeField(set_ref, elem) for elem in elem_ref]

        @classmethod
        def MakeChild(cls, *elems: RefPath):
            out = ChildField(cls)
            for elem in elems:
                out.add_dependant(
                    EdgeField(
                        [out],
                        elem,
                        edge=cls._edge_factory(
                            identifier=cls._elem_identifier,
                            order=None,
                        ),
                    )
                )
            return out

        def as_list(self) -> list[Node[Any]]:
            return type(self)._retrieval_function(self, self._elem_identifier)

        def as_set(self) -> set[Node[Any]]:
            return set(self.as_list())

    ConcreteSet.__name__ = f"ConcreteSet_{id(ConcreteSet):x}"
    return ConcreteSet


# --------------------------------------------------------------------------------------

# TODO this is an abomination
# get rid of the abstract bs and just reimplement sets wherever needed

Pointer = AbstractPointer(
    edge_factory=lambda identifier: EdgePointer.build(
        identifier=identifier, order=None
    ),
    retrieval_function=lambda node: _get_pointer_references(node, None)[0],
)

PointerSequence = AbstractSequence(
    edge_factory=lambda identifier, order: EdgePointer.build(
        identifier=identifier, order=order
    ),
    retrieval_function=_get_pointer_references,
)

PointerSet = AbstractSet(
    edge_factory=lambda identifier, order: EdgePointer.build(
        identifier=identifier, order=order
    ),
    retrieval_function=_get_pointer_references,
)


class PointerTuple(Node):
    pointer = Pointer.MakeChild()
    literals = PointerSet.MakeChild()

    @classmethod
    def SetPointer(cls, tup_ref: RefPath, elem_ref: RefPath) -> EdgeField:
        ptr_ref = tup_ref
        ptr_ref.append(cls.pointer)
        return Pointer.EdgeField(
            ptr_ref,
            elem_ref,
        )

    @classmethod
    def AppendLiteral(cls, tup_ref: RefPath, elem_ref: RefPath) -> EdgeField:
        set_ref = tup_ref  # TODO: Can this be done in a more elegant way?
        set_ref.append(cls.literals)
        return PointerSet.EdgeField(
            tup_ref,
            elem_ref,
        )

    def deref_pointer(self) -> Node:
        electrical_ptr = self.pointer.get()
        return electrical_ptr.deref()

    def get_literals_as_list(self) -> list[fabll.LiteralT]:
        return [
            fabll.LiteralNode.bind_instance(instance=lit.instance).get_value()
            for lit in self.literals.get().as_list()
        ]
