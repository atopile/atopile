from typing import Callable

from faebryk.core.faebrykpy import EdgeTraversal
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class EdgeOperand:
    @staticmethod
    def create(
        *, expression: Node, operand: Node, operand_identifier: str | None = ...
    ) -> Edge: ...
    @staticmethod
    def build(*, operand_identifier: str | None = ...) -> EdgeCreationAttributes: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def visit_operand_edges[T](
        *,
        bound_node: BoundNode,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def visit_operands_of_type[T](
        *,
        bound_node: BoundNode,
        operand_type: Node,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def visit_expression_edges[T](
        *,
        bound_node: BoundNode,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def visit_expression_edges_of_type[T](
        *,
        bound_node: BoundNode,
        expression_type: Node,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def get_expression_edge(*, bound_node: BoundNode) -> BoundEdge | None: ...
    @staticmethod
    def get_expression_node(*, bound_edge: BoundEdge) -> Node: ...
    @staticmethod
    def get_operands_set_node(*, bound_node: BoundNode) -> BoundNode | None: ...
    @staticmethod
    def get_operand_node(*, edge: Edge) -> Node: ...
    @staticmethod
    def get_operand_of(*, edge: Edge, node: Node) -> Node | None: ...
    @staticmethod
    def get_expression_of(*, bound_edge: BoundEdge, node: Node) -> Node | None: ...
    @staticmethod
    def add_operand(
        *, bound_node: BoundNode, operand: Node, operand_identifier: str | None = ...
    ) -> BoundEdge: ...
    @staticmethod
    def get_name(*, edge: Edge) -> str | None: ...
    @staticmethod
    def get_tid() -> Edge.Type: ...
    @staticmethod
    def get_operand_by_identifier(
        *, node: BoundNode, operand_identifier: str
    ) -> BoundNode | None: ...
    @staticmethod
    def traverse(*, identifier: str) -> EdgeTraversal:
        """Create an EdgeTraversal for finding an operand by identifier."""
        ...
