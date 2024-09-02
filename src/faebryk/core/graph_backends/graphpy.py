# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Mapping, Sized

from faebryk.core.graph import Graph

logger = logging.getLogger(__name__)

# only for typechecker

if TYPE_CHECKING:
    from faebryk.core.link import Link

type L = "Link"


class PyGraph[T](Sized, Iterable[T]):
    def __init__(self, filter: Callable[[T], bool] | None = None):
        # undirected
        self._e = list[tuple[T, T, L]]()
        self._e_cache = defaultdict[T, dict[T, L]](dict)
        self._v = set[T]()

    def __iter__(self) -> Iterator[T]:
        return iter(self._v)

    def __len__(self) -> int:
        return len(self._v)

    def size(self) -> int:
        return len(self._e)

    def add_edge(self, from_obj: T, to_obj: T, link: L):
        self._e.append((from_obj, to_obj, link))
        self._e_cache[from_obj][to_obj] = link
        self._e_cache[to_obj][from_obj] = link
        self._v.add(from_obj)
        self._v.add(to_obj)

    def remove_edge(self, from_obj: T, to_obj: T | None = None):
        targets = [to_obj] if to_obj else list(self.edges(from_obj).keys())
        for target in targets:
            self._e.remove((from_obj, target, self._e_cache[from_obj][target]))
            del self._e_cache[from_obj][target]
            del self._e_cache[target][from_obj]

    def update(self, other: "PyGraph[T]"):
        self._v.update(other._v)
        self._e.extend(other._e)
        self._e_cache.update(other._e_cache)

    def view(self, filter_node: Callable[[T], bool]) -> "PyGraph[T]":
        return PyGraphView[T](self, filter_node)

    def edges(self, obj: T) -> Mapping[T, L]:
        return self._e_cache[obj]


class PyGraphView[T](PyGraph[T]):
    def __init__(self, parent: PyGraph[T], filter: Callable[[T], bool]):
        self._parent = parent
        self._filter = filter

    def update(self, other: "PyGraph[T]"):
        raise TypeError("Cannot update a view")

    def add_edge(self, from_obj: T, to_obj: T, link: L):
        raise TypeError("Cannot add edge to a view")

    def __iter__(self) -> Iterator[T]:
        return filter(self._filter, iter(self._parent))

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def size(self) -> int:
        return sum(
            1 for _ in self._parent._e if self._filter(_[0]) and self._filter(_[1])
        )

    def edges(self, obj: T) -> Mapping[T, L]:
        return {k: v for k, v in self._parent.edges(obj).items() if self._filter(k)}

    def view(self, filter_node: Callable[[T], bool]) -> "PyGraph[T]":
        return PyGraphView[T](
            self._parent, lambda x: self._filter(x) and filter_node(x)
        )


class GraphPY[T](Graph[T, PyGraph[T]]):
    type GI = PyGraph[T]

    def __init__(self):
        super().__init__(PyGraph[T]())

    @property
    def node_cnt(self) -> int:
        return len(self())

    @property
    def edge_cnt(self) -> int:
        return self().size()

    def v(self, obj: T):
        return obj

    def add_edge(self, from_obj: T, to_obj: T, link: L):
        self().add_edge(from_obj, to_obj, link=link)

    def remove_edge(self, from_obj: T, to_obj: T | None = None):
        return self().remove_edge(from_obj, to_obj)

    def is_connected(self, from_obj: T, to_obj: T) -> "Link | None":
        return self.get_edges(from_obj).get(to_obj)

    def get_edges(self, obj: T) -> Mapping[T, L]:
        return self().edges(obj)

    def bfs_visit(self, filter: Callable[[T], bool], start: Iterable[T], G=None):
        return super().bfs_visit(filter, start, G)

    @staticmethod
    def _union(rep: GI, old: GI):
        # merge big into small
        if len(old) > len(rep):
            rep, old = old, rep

        rep.update(old)

        return rep

    def subgraph(self, node_filter: Callable[[T], bool]):
        return self().view(node_filter)

    def __iter__(self) -> Iterator[T]:
        return iter(self())
