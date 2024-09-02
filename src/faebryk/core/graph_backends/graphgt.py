# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Mapping

import graph_tool as gt
from graph_tool.generation import graph_union

from faebryk.core.graph import Graph

logger = logging.getLogger(__name__)

# only for typechecker

if TYPE_CHECKING:
    from faebryk.core.link import Link


class GraphGT[T](Graph[T, gt.Graph]):
    GI = gt.Graph

    PROPS: dict[gt.Graph, dict[str, gt.PropertyMap | dict]] = defaultdict(dict)

    def __init__(self):
        G = gt.Graph(directed=False)
        super().__init__(G)

        lookup: dict[T, int] = {}

        # direct
        # G.vp["KV"] = G.new_vertex_property("object")
        # G.gp["VK"] = G.new_graph_property("object", lookup)
        # G.ep["L"] = G.new_edge_property("object")

        # indirect (2x faster)
        type(self).PROPS[self()]["KV"] = G.new_vertex_property("object")
        type(self).PROPS[self()]["VK"] = lookup
        type(self).PROPS[self()]["L"] = G.new_edge_property("object")

        # full python (2x faster than indirect, but no searching for props in C++)
        # kv: dict[int, T] = {}
        # lp: dict[tuple[int, int], "Link"] = {}
        # type(self).PROPS[self()]["KV"] = kv
        # type(self).PROPS[self()]["VK"] = lookup
        # type(self).PROPS[self()]["L"] = lp

    @classmethod
    def ckv(cls, g: gt.Graph) -> gt.VertexPropertyMap:
        return cls.PROPS[g]["KV"]

    @classmethod
    def cvk(cls, g: gt.Graph) -> dict[T, int]:
        return cls.PROPS[g]["VK"]

    @classmethod
    def clp(cls, g: gt.Graph) -> gt.EdgePropertyMap:
        return cls.PROPS[g]["L"]

    @property
    def kv(self) -> gt.VertexPropertyMap:
        return type(self).ckv(self())

    @property
    def vk(self) -> dict[T, int]:
        return type(self).cvk(self())

    @property
    def lp(self) -> gt.EdgePropertyMap:
        return type(self).clp(self())

    @property
    def node_cnt(self) -> int:
        return self().num_vertices()

    @property
    def edge_cnt(self) -> int:
        return self().num_edges()

    def v(self, obj: T):
        v_i = self.vk.get(obj)
        if v_i is not None:
            return self().vertex(v_i)

        v = self().add_vertex()
        v_i = self().vertex_index[v]
        self.kv[v] = obj
        self.vk[obj] = v_i
        return v

    def _v_to_obj(self, v: gt.VertexBase | int) -> T:
        return self.kv[v]

    def _as_graph_vertex_func[O](
        self, f: Callable[[T], O]
    ) -> Callable[[gt.VertexBase | int], O]:
        return lambda v: f(self._v_to_obj(v))

    def add_edge(self, from_obj: T, to_obj: T, link: "Link"):
        from_v = self.v(from_obj)
        to_v = self.v(to_obj)
        e = self().add_edge(from_v, to_v, add_missing=False)
        self.lp[e] = link

    def is_connected(self, from_obj: T, to_obj: T) -> "Link | None":
        from_v = self.v(from_obj)
        to_v = self.v(to_obj)
        e = self().edge(from_v, to_v, add_missing=False)
        if not e:
            return None
        return self.lp[e]

    def get_edges(self, obj: T) -> Mapping[T, "Link"]:
        v = self.v(obj)
        v_i = self().vertex_index[v]

        def other(v_i_l, v_i_r):
            return v_i_l if v_i_r == v_i else v_i_r

        return {
            self._v_to_obj(other(v_i_l, v_i_r)): self.lp[v_i_l, v_i_r]
            for v_i_l, v_i_r in self().get_all_edges(v)
        }

    @classmethod
    def _union(cls, g1: gt.Graph, g2: gt.Graph) -> gt.Graph:
        v_is = len(g1.get_vertices())
        # slower than manual, but merges properties
        graph_union(
            g1,
            g2,
            internal_props=True,
            include=True,
            props=[
                (cls.ckv(g1), cls.ckv(g2)),
                (cls.clp(g1), cls.clp(g2)),
            ],
        )

        # manual
        # g1.add_vertex(g2.num_vertices())
        # g1.add_edge_list(g2.get_edges() + v_is)
        # this does not work with objects
        # cls.ckv(g1).a = np.append(cls.ckv(g1).a, cls.ckv(g2).a)
        # cls.clp(g1).a = np.append(cls.clp(g1).a, cls.clp(g2).a)

        # full python
        # cls.ckv(g1).update({v: o for v, o in cls.ckv(g2).items()})
        # cls.clp(g1).update({e: l for e, l in cls.clp(g2).items()})

        cls.cvk(g1).update({k: v + v_is for k, v in cls.cvk(g2).items()})

        del cls.PROPS[g2]

        return g1

    def bfs_visit(
        self, filter: Callable[[T], bool], start: Iterable[T], G: gt.Graph | None = None
    ):
        # TODO implement with gt bfs
        return super().bfs_visit(filter, start, G)

    def _iter(self, g: gt.Graph):
        return (self._v_to_obj(v) for v in g.iter_vertices())

    def __iter__(self) -> Iterator[T]:
        return self._iter(self())

    def subgraph(self, node_filter: Callable[[T], bool]):
        return self._iter(
            gt.GraphView(self(), vfilt=self._as_graph_vertex_func(node_filter))
        )
