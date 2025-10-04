# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class EdgeSource:
    @staticmethod
    def create(*, node: Node, source_node: Node) -> Edge: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def add_source(*, bound_node: BoundNode, source_node: Node) -> BoundEdge: ...
    @staticmethod
    def get_subject_node(*, edge: Edge) -> Node | None: ...
    @staticmethod
    def get_source_node(*, edge: Edge) -> Node | None: ...
    @staticmethod
    def get_source_edge(*, bound_node: BoundNode) -> BoundEdge | None: ...
    @staticmethod
    def visit_source_edges[T](
        *,
        bound_node: BoundNode,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def get_tid() -> Edge.Type: ...
