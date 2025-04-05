# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from types import UnionType
from typing import TYPE_CHECKING, cast, overload

from faebryk.core.cpp import Graph
from faebryk.core.node import Node
from faebryk.libs.util import union_list

if TYPE_CHECKING:
    from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


# TODO move these to C++
# just here for making refactoring easier for the moment
# a bit weird typecheck
class GraphFunctions:
    # Make all kinds of graph filtering functions so we can optimize them in the future
    # Avoid letting user query all graph nodes always because quickly very slow
    def __init__(self, *graph: Graph):
        self.graph = graph

    @property
    def node_projection(self) -> list["Node"]:
        # TODO node_projection should not return cNode
        nodes_nested = [g.node_projection() for g in self.graph]
        return union_list(*nodes_nested)  # type: ignore

    def nodes_with_trait[T: "Trait"](self, trait: type[T]) -> list[tuple["Node", T]]:
        return [
            (n, n.get_trait(trait)) for n in self.node_projection if n.has_trait(trait)
        ]

    # TODO: Waiting for python to add support for type mapping
    def nodes_with_traits[*Ts](
        self, traits: tuple[*Ts]
    ):  # -> list[tuple[Node, tuple[*Ts]]]:
        return [
            (n, tuple(n.get_trait(trait) for trait in traits))  # type: ignore
            for n in self.node_projection
            if all(n.has_trait(trait) for trait in traits)  # type: ignore
        ]

    def nodes_of_type[T: "Node"](self, t: type[T]) -> set[T]:
        if t is Node:
            return cast(set[T], set(self.node_projection))
        return set(union_list(*(g.nodes_by_type(t) for g in self.graph)))  # type: ignore

    @overload
    def nodes_of_types(self, t: tuple[type["Node"], ...]) -> set["Node"]: ...
    @overload
    def nodes_of_types(self, t: UnionType) -> set["Node"]: ...

    def nodes_of_types(self, t):  # type: ignore TODO
        return {n for g in self.graph for n in g.node_projection() if isinstance(n, t)}
