# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Mapping

import networkx as nx
from faebryk.core.graph import Graph

logger = logging.getLogger(__name__)

# only for typechecker

if TYPE_CHECKING:
    from faebryk.core.core import Link


class GraphNX[T](Graph[T, nx.Graph]):
    GI = nx.Graph

    def __init__(self):
        super().__init__(self.GI())

    @property
    def node_cnt(self) -> int:
        return len(self())

    @property
    def edge_cnt(self) -> int:
        return self().size()

    def v(self, obj: T):
        return obj

    def add_edge(self, from_obj: T, to_obj: T, link: "Link"):
        self().add_edge(from_obj, to_obj, link=link)

    def is_connected(self, from_obj: T, to_obj: T) -> "Link | None":
        return self.get_edges(from_obj).get(to_obj)

    def get_edges(self, obj: T) -> Mapping[T, "Link"]:
        return {other: d["link"] for other, d in self().adj.get(obj, {}).items()}

    def bfs_visit(self, filter: Callable[[T], bool], start: Iterable[T], G=None):
        # nx impl, >3x slower
        # fG = nx.subgraph_view(G, filter_node=filter)
        # return [o for _, o in nx.bfs_edges(fG, start[0])]
        return super().bfs_visit(filter, start, G)

    @staticmethod
    def _union(rep: GI, old: GI):
        # merge big into small
        if len(old) > len(rep):
            rep, old = old, rep

        # print(f"union: {len(rep.nodes)=} {len(old.nodes)=}")
        rep.update(old)

        return rep

    def subgraph(self, node_filter: Callable[[T], bool]):
        return nx.subgraph_view(self(), filter_node=node_filter)

    def __repr__(self) -> str:
        from textwrap import dedent

        return dedent(f"""
            {type(self).__name__}(
                {self.graph_repr(self())}
            )
        """)

    @staticmethod
    def graph_repr(G: nx.Graph) -> str:
        from textwrap import dedent, indent

        nodes = indent("\n".join(f"{k}" for k in G.nodes), " " * 4 * 5)
        longest_node_name = max(len(str(k)) for k in G.nodes)

        def edge_repr(u, v, d) -> str:
            if "link" not in d:
                link = ""
            else:
                link = f"({type(d['link']).__name__})"
            return f"{str(u)+' ':-<{longest_node_name+1}}--{link:-^20}" f"--> {v}"

        edges = indent(
            "\n".join(edge_repr(u, v, d) for u, v, d in G.edges(data=True)),
            " " * 4 * 5,
        )

        return dedent(f"""
            Nodes ----- {len(G)}\n{nodes}
            Edges ----- {G.size()}\n{edges}
        """)

    def __iter__(self) -> Iterator[T]:
        return iter(self())
