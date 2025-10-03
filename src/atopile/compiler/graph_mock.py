"""Lightweight Python mock of the Zig-backed graph API.

This can be used while the Zig implementation is still in flux.  The goal is
API compatibility, not feature parity, so only the pieces exercised by the
current Python code are implemented.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Generator
from itertools import count
from typing import (
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    TypedDict,
    TypeVar,
    Unpack,
)

from faebryk.libs.util import Tree

Literal = int | float | str | bool
_ContextT = TypeVar("_ContextT")


# TODO: @python3.15 (PEP 728) extra_items=Literal
class LiteralArgs(TypedDict): ...


class Node:
    """In-memory Node equivalent."""

    _uuid_counter = count()
    __slots__ = ("_uuid", "_attrs")

    def __init__(self, **attrs: Unpack[LiteralArgs]) -> None:
        self._uuid = next(Node._uuid_counter)
        self._attrs: Mapping[str, Literal] = attrs  # type: ignore

    @classmethod
    def create(cls, **attrs: Unpack[LiteralArgs]) -> Node:
        return cls(**attrs)

    def get_attr(self, *, key: str) -> Literal | None:
        return self._attrs.get(key)

    def is_same(self, *, other: Node) -> bool:
        return isinstance(other, Node) and self._uuid == other._uuid

    # Provide stable hashing/eq so Nodes can be dictionary keys.
    def __hash__(self) -> int:
        return hash(self._uuid)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Node) and self._uuid == other._uuid

    def __repr__(self) -> str:
        return f"Node(uuid={self._uuid}, attrs={self._attrs})"


class Edge:
    """In-memory Edge equivalent."""

    Type = int
    _uuid_counter = count()
    _type_counter = count()

    __slots__ = (
        "_uuid",
        "_source",
        "_target",
        "_edge_type",
        "_directional",
        "_name",
        "_attrs",
    )

    def __init__(
        self,
        *,
        source: Node,
        target: Node,
        edge_type: Type,
        directional: bool | None = None,
        name: str | None = None,
        **attrs: Literal,
    ) -> None:
        self._uuid = next(Edge._uuid_counter)
        self._source = source
        self._target = target
        self._edge_type = edge_type
        self._directional = directional
        self._name = name
        self._attrs: Dict[str, Literal] = dict(attrs)

    @staticmethod
    def create(
        *,
        source: Node,
        target: Node,
        edge_type: Type,
        directional: bool | None = None,
        name: str | None = None,
        **attrs: Literal,
    ) -> Edge:
        return Edge(
            source=source,
            target=target,
            edge_type=edge_type,
            directional=directional,
            name=name,
            **attrs,
        )

    @staticmethod
    def register_type() -> Type:
        return next(Edge._type_counter)

    def source(self) -> Node:
        return self._source

    def target(self) -> Node:
        return self._target

    def edge_type(self) -> Type:
        return self._edge_type

    def directional(self) -> bool | None:
        return self._directional

    def name(self) -> str | None:
        return self._name

    def get_attr(self, *, key: str) -> Literal | None:
        return self._attrs.get(key)

    def is_same(self, *, other: Edge) -> bool:
        return isinstance(other, Edge) and self._uuid == other._uuid

    def __repr__(self) -> str:  # pragma: no cover - trivial helper
        return (
            "Edge(uuid={uuid}, type={etype}, src={src_uuid}, dst={dst_uuid}, "
            "directional={dirn}, name={name})"
        ).format(
            uuid=self._uuid,
            etype=self._edge_type,
            src_uuid=self._source._uuid,
            dst_uuid=self._target._uuid,
            dirn=self._directional,
            name=self._name,
        )


class BoundEdge:
    edge: Edge
    g: GraphView

    def __init__(self, edge: Edge, g: GraphView) -> None:
        self.edge = edge
        self.g = g


class BoundNode:
    node: Node
    g: GraphView

    def __init__(self, node: Node, g: GraphView) -> None:
        self.node = node
        self.g = g

    def visit_edges_of_type(
        self,
        *,
        edge_type: Edge.Type,
        ctx: _ContextT,
        f: Callable[[_ContextT, BoundEdge], None],
    ) -> None:
        for edge in self.g._edges_for_node_and_type(self.node, edge_type):
            bound = BoundEdge(edge, self.g)
            f(ctx, bound)

    def get_neighbours(self, edge_type: Edge.Type) -> Generator[BoundNode, None, None]:
        for edge in self.g._edges_for_node_and_type(self.node, edge_type):
            # Return the opposite endpoint regardless of direction
            if edge.source().is_same(other=self.node):
                yield BoundNode(edge.target(), self.g)
            elif edge.target().is_same(other=self.node):
                yield BoundNode(edge.source(), self.g)

    def print_tree(self, renderer: Callable[[BoundNode], str] = repr) -> None:
        edge_type = EdgeComposition.get_tid()

        def iter_children(node: BoundNode) -> list[BoundNode]:
            children: list[BoundNode] = []
            for edge in self.g._edges_for_node_and_type(node.node, edge_type):
                if not edge.source().is_same(other=node.node):
                    continue
                children.append(BoundNode(edge.target(), self.g))
            return children

        def build_tree(node: BoundNode, ancestors: set[int]) -> Tree[BoundNode]:
            if node.node._uuid in ancestors:
                return Tree()
            next_ancestors = set(ancestors)
            next_ancestors.add(node.node._uuid)
            children = iter_children(node)
            return Tree(
                OrderedDict(
                    (child, build_tree(child, next_ancestors))
                    for child in children
                )
            )

        root = self
        tree = Tree(OrderedDict([(root, build_tree(root, set()))]))

        pretty = tree.pretty_print(node_renderer=renderer)
        if pretty:
            print(pretty, end="")


class GraphView:
    """Tracks nodes and edges with the same surface API as the Zig binding."""

    def __init__(self) -> None:
        self._nodes: Dict[int, Node] = {}
        self._edges: List[Edge] = []
        self._edges_by_node: MutableMapping[Node, List[Edge]] = {}
        self._edges_by_type: MutableMapping[Node, MutableMapping[int, List[Edge]]] = {}

    @staticmethod
    def create() -> GraphView:
        return GraphView()

    def insert_node(self, *, node: Node) -> BoundNode:
        node_id = node._uuid
        if node_id in self._nodes:
            raise ValueError("node already inserted")
        self._nodes[node_id] = node
        self._edges_by_node[node] = []
        self._edges_by_type[node] = {}
        return self.bind(node=node)

    def insert_edge(self, *, edge: Edge) -> BoundEdge:
        self._ensure_node_present(edge.source())
        self._ensure_node_present(edge.target())
        self._edges.append(edge)
        for endpoint in (edge.source(), edge.target()):
            node_edges = self._edges_by_node.setdefault(endpoint, [])
            node_edges.append(edge)
            by_type = self._edges_by_type.setdefault(endpoint, {})
            by_type.setdefault(edge.edge_type(), []).append(edge)
        return BoundEdge(edge, self)

    def bind(self, *, node: Node) -> BoundNode:
        self._ensure_node_present(node)
        return BoundNode(node, self)

    def _ensure_node_present(self, node: Node) -> None:
        if node._uuid not in self._nodes:
            raise ValueError("node must be inserted into the graph before binding")

    def _edges_for_node_and_type(self, node: Node, edge_type: int) -> Sequence[Edge]:
        by_type = self._edges_by_type.get(node)
        if not by_type:
            return ()
        return tuple(by_type.get(edge_type, ()))


class EdgeComposition:
    """Partial Python reproduction of the Zig EdgeComposition helper."""

    _tid: Edge.Type = 1

    @staticmethod
    def get_tid() -> Edge.Type:
        return EdgeComposition._tid

    @staticmethod
    def create(*, parent: Node, child: Node, child_identifier: str) -> Edge:
        return Edge.create(
            source=parent,
            target=child,
            edge_type=EdgeComposition.get_tid(),
            directional=True,
            name=child_identifier,
        )

    @staticmethod
    def is_instance(*, edge: Edge) -> bool:
        return isinstance(edge, Edge) and edge.edge_type() == EdgeComposition.get_tid()

    @staticmethod
    def visit_children_edges(
        *,
        bound_node: BoundNode,
        ctx: _ContextT,
        f: Callable[[_ContextT, BoundEdge], None],
    ) -> None:
        def _visitor(inner_ctx: _ContextT, bound_edge: BoundEdge) -> None:
            edge = bound_edge.edge
            if edge.source().is_same(other=bound_node.node):
                f(inner_ctx, bound_edge)

        bound_node.visit_edges_of_type(
            edge_type=EdgeComposition.get_tid(),
            ctx=ctx,
            f=_visitor,
        )

    @staticmethod
    def get_parent_edge(*, bound_node: BoundNode) -> BoundEdge | None:
        tid = EdgeComposition.get_tid()
        for edge in bound_node.g._edges_for_node_and_type(bound_node.node, tid):
            if edge.target().is_same(other=bound_node.node):
                return BoundEdge(edge, bound_node.g)
        return None

    @staticmethod
    def add_child(
        *,
        bound_node: BoundNode,
        child: Node,
        child_identifier: str,
    ) -> BoundEdge:
        edge = EdgeComposition.create(
            parent=bound_node.node, child=child, child_identifier=child_identifier
        )
        return bound_node.g.insert_edge(edge=edge)

    @staticmethod
    def get_name(*, edge: Edge) -> str:
        if not EdgeComposition.is_instance(edge=edge):
            raise ValueError("edge is not an EdgeComposition edge")
        name = edge.name()
        if name is None:
            raise ValueError("edge has no name")
        return name


class EdgeSource:
    """Helper for edges that attach source context to nodes.

    This is distinct from composition edges: a node may have one or more
    composition children that describe structure, and a separate edge linking
    it to its `SourceChunk`.
    """

    _tid: Edge.Type = 2

    @staticmethod
    def get_tid() -> Edge.Type:
        return EdgeSource._tid

    @staticmethod
    def create(*, node: Node, source_node: Node) -> Edge:
        return Edge.create(
            source=node,
            target=source_node,
            edge_type=EdgeSource.get_tid(),
            directional=True,
            name=None,
        )

    @staticmethod
    def is_instance(*, edge: Edge) -> bool:
        return isinstance(edge, Edge) and edge.edge_type() == EdgeSource.get_tid()

    @staticmethod
    def add_source(*, bound_node: BoundNode, source_node: Node) -> BoundEdge:
        edge = EdgeSource.create(node=bound_node.node, source_node=source_node)
        return bound_node.g.insert_edge(edge=edge)

    @staticmethod
    def get_source_edge(*, bound_node: BoundNode) -> BoundEdge | None:
        tid = EdgeSource.get_tid()
        for edge in bound_node.g._edges_for_node_and_type(bound_node.node, tid):
            if edge.source().is_same(other=bound_node.node):
                return BoundEdge(edge, bound_node.g)
        return None


class EdgeType:
    _tid: Edge.Type = 3

    @staticmethod
    def get_tid() -> Edge.Type:
        return EdgeType._tid

    @staticmethod
    def create(*, node: Node, type_node: Node) -> Edge:
        return Edge.create(
            source=node,
            target=type_node,
            edge_type=EdgeType.get_tid(),
            directional=True,
            name=None,
        )

    @staticmethod
    def is_instance(*, edge: Edge) -> bool:
        return isinstance(edge, Edge) and edge.edge_type() == EdgeType.get_tid()

    @staticmethod
    def add_type(*, bound_node: BoundNode, type_node: Node) -> BoundEdge:
        edge = EdgeType.create(node=bound_node.node, type_node=type_node)
        return bound_node.g.insert_edge(edge=edge)

    @staticmethod
    def get_type_edge(*, bound_node: BoundNode) -> BoundEdge | None:
        tid = EdgeType.get_tid()
        for edge in bound_node.g._edges_for_node_and_type(bound_node.node, tid):
            if edge.target().is_same(other=bound_node.node):
                return BoundEdge(edge, bound_node.g)
        return None
