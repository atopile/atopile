# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, Iterable, TypeVar

import networkx as nx
from faebryk.core.core import GraphInterface, Node

logger = logging.getLogger(__name__)

T = TypeVar("T")


def bfs_visit(neighbours: Callable[[T], list[T]], nodes: Iterable[T]) -> set[T]:
    """
    Generic BFS (not depending on Graph)
    Returns all visited nodes.
    """
    queue: list[T] = list(nodes)
    visited: set[T] = set(queue)

    while queue:
        m = queue.pop(0)

        for neighbour in neighbours(m):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    return visited


def _get_connected_GIFs(nodes: list[Node]) -> Iterable[GraphInterface]:
    """
    Gets GIFs from supplied Nodes.
    Then traces all connected GIFs from them to find the rest.
    """
    GIFs = {gif for n in nodes for gif in n.GIFs.get_all()}

    out = bfs_visit(
        lambda i: [
            j for link in i.connections for j in link.get_connections() if j != i
        ],
        GIFs,
    )

    return GIFs | out


class Graph:
    def __init__(self, nodes: list[Node]):
        G = nx.Graph()
        GIFs = _get_connected_GIFs(nodes)
        links = {gif_link for i in GIFs for gif_link in i.connections}

        assert all(map(lambda link: len(link.get_connections()) == 2, links))
        edges = [tuple(link.get_connections() + [{"link": link}]) for link in links]

        G.add_edges_from(edges)
        G.add_nodes_from(GIFs)

        self.G = G
