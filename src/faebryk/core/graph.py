# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Mapping, Self

from typing_extensions import deprecated

from faebryk.libs.util import (
    ConfigFlag,
    LazyMixin,
    SharedReference,
    bfs_visit,
    lazy_construct,
)

logger = logging.getLogger(__name__)

# only for typechecker

if TYPE_CHECKING:
    from faebryk.core.link import Link

# TODO create GraphView base class

LAZY = ConfigFlag("LAZY", False, "Use lazy construction for graphs")


class Graph[T, GT](LazyMixin, SharedReference[GT]):
    # perf counter
    counter = 0

    def __init__(self, G: GT):
        super().__init__(G)
        type(self).counter += 1

    @property
    @deprecated("Use call")
    def G(self):
        return self()

    def merge(self, other: Self) -> tuple[Self, bool]:
        lhs, rhs = self, other

        # if node not init, graph is empty / not existing
        # thus we dont have to merge the graph, just need to setup the ref
        if LAZY:
            if not lhs.is_init or not rhs.is_init:
                if not lhs.is_init:
                    lhs, rhs = rhs, lhs
                rhs.links = lhs.links
                rhs.object = lhs.object
                lhs.links.add(rhs)
                rhs._init = True
                return lhs, True

        if lhs() == rhs():
            return self, False

        unioned = self._union(self(), other())
        if unioned is rhs():
            lhs, rhs = rhs, lhs
        if unioned is not lhs():
            lhs.set(unioned)

        res = lhs.link(rhs)
        if not res:
            return self, False

        # TODO remove, should not be needed
        assert isinstance(res.representative, type(self))

        return res.representative, True

    def __repr__(self) -> str:
        G = self()
        node_cnt = self.node_cnt
        edge_cnt = self.edge_cnt
        g_repr = f"{type(G).__name__}({node_cnt=},{edge_cnt=})({hex(id(G))})"
        return f"{type(self).__name__}({g_repr})"

    @property
    @abstractmethod
    def node_cnt(self) -> int: ...

    @property
    @abstractmethod
    def edge_cnt(self) -> int: ...

    @abstractmethod
    def v(self, obj: T): ...

    @abstractmethod
    def add_edge(self, from_obj: T, to_obj: T, link: "Link"): ...

    # TODO implement everywhere
    @abstractmethod
    def remove_edge(self, from_obj: T, to_obj: T | None = None): ...

    @abstractmethod
    def is_connected(self, from_obj: T, to_obj: T) -> "Link | None": ...

    @abstractmethod
    def get_edges(self, obj: T) -> Mapping[T, "Link"]: ...

    @staticmethod
    @abstractmethod
    def _union(rep: GT, old: GT) -> GT: ...

    def bfs_visit(
        self, filter: Callable[[T], bool], start: Iterable[T], G: GT | None = None
    ):
        G = G or self()

        return bfs_visit(lambda n: [o for o in self.get_edges(n) if filter(o)], start)

    def __str__(self) -> str:
        return f"{type(self).__name__}(V={self.node_cnt}, E={self.edge_cnt})"

    @abstractmethod
    def __iter__(self) -> Iterator[T]: ...

    # TODO subgraph should return a new GraphView
    @abstractmethod
    def subgraph(self, node_filter: Callable[[T], bool]) -> Iterable[T]: ...

    def subgraph_type(self, *types: type[T]):
        return self.subgraph(lambda n: isinstance(n, types))

    # TODO remove boilerplate for lazy, if it becomes a bit more usable
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if LAZY:
            lazy_construct(cls)
