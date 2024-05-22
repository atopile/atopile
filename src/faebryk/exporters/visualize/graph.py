# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from copy import copy

import networkx as nx
from faebryk.core.core import (
    GraphInterface,
    GraphInterfaceHierarchical,
    GraphInterfaceModuleConnection,
    GraphInterfaceModuleSibling,
    GraphInterfaceSelf,
    Link,
    LinkDirect,
    LinkNamedParent,
    LinkSibling,
    Node,
)
from faebryk.library.Electrical import Electrical
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)


def _direction_to_str(direction: tuple[GraphInterface, GraphInterface] | None):
    if direction is None:
        return str(direction)
    return [str(x) for x in direction]


def merge(G: nx.Graph, root: GraphInterface, group: set[GraphInterface]) -> nx.Graph:
    if len(group) == 0:
        return G

    nodes = set(G.nodes)
    to_merge = group - {root}
    assert root in group

    Gout = nx.Graph(G.subgraph(nodes - to_merge))
    assert group.issubset(nodes)

    # find connections to the outside (of group) to move to root node
    edges: dict[GraphInterface, dict] = {}
    for n in to_merge:
        for d in set(G[n]) - group:
            # TODO also merge links
            data = dict(G.get_edge_data(n, d))

            # connection to representative
            if d not in edges:
                edges[d] = {"merged": []}
            e = edges[d]

            # Direction
            direction = data["direction"]
            direction_new = None
            if direction is not None:
                direction_new = tuple(
                    intf if intf is not n else root for intf in direction
                )

            e["merged"].extend(data["merged"])

            if "direction" not in e:
                e["direction"] = direction_new
            if direction_new is not None and e["direction"] != direction_new:
                e["direction"] = None

    Gout.add_edges_from([(root, d, data) for d, data in edges.items()])
    # print("Merge:", len(G.nodes), root, len(group), "->", len(Gout.nodes))
    return Gout


# TODO untested
def make_abstract(G: nx.Graph, root: Node) -> nx.Graph:
    merged_ifs = _get_all_sub_GIFs(G, root)
    assert all(map(lambda n: n in G.nodes, merged_ifs))

    # Remove to be merged ifs from graph
    Gout = G.copy()
    Gout.remove_nodes_from(merged_ifs)

    node = Node()
    edges: list[tuple[GraphInterface, GraphInterface, dict]] = []

    for child in [root] + _get_children(G, root):
        gifs = _get_neighbor_gifs(G, child.GIFs.self)
        for gif in gifs:
            if gif.name not in [x.name for x in node.GIFs.get_all()]:
                # TODO not sure if thats ok or needed
                copied_gif = copy(gif)
                copied_gif.connections = []
                setattr(node.GIFs, gif.name, copied_gif)
            node_gif = getattr(node.GIFs, gif.name)
            assert isinstance(node_gif, GraphInterface)

            for e in G[gif]:
                assert isinstance(e, GraphInterface)
                if e in merged_ifs:
                    continue
                data = dict(G.get_edge_data(gif, e))

                direction = data["direction"]
                if direction is not None:
                    direction_new = tuple(
                        intf if intf is not gif else node_gif for intf in direction
                    )
                    print(
                        "Replace",
                        _direction_to_str(direction),
                        _direction_to_str(direction_new),
                    )
                    data["direction"] = direction_new

                # connection to representative
                edges.append((e, node_gif, data))

    Gout.add_nodes_from(node.GIFs.get_all())
    Gout.add_edges_from([(e, node_gif, d) for e, node_gif, d in edges])

    return Gout


def merge_sub(G: nx.Graph, node: Node):
    return merge(G, node.GIFs.self, set(_get_all_sub_GIFs(G, node)))


def _get_neighbor_gifs(G: nx.Graph, gif: GraphInterface) -> list[GraphInterface]:
    if gif not in G:
        return []
    return [cast_assert(GraphInterface, x) for x in G[gif]]


def _get_neighbor_nodes(G: nx.Graph, gif: GraphInterface) -> list[Node]:
    if gif not in G:
        return []
    return [
        n
        for neighbor_gif in G[gif]
        if (n := cast_assert(GraphInterface, neighbor_gif).node) is not gif.node
    ]


def _get_all_sub_GIFs(G: nx.Graph, node: Node) -> list[GraphInterface]:
    node_if = node.GIFs.self

    if node_if not in G:
        return []

    out: list[GraphInterface] = [node_if]
    # all siblings
    out.extend(_get_neighbor_gifs(G, node_if))
    # all gifs of children
    for c in _get_children(G, node, recursive=False):
        out.extend(_get_all_sub_GIFs(G, c))
    return out


def _get_parents(G: nx.Graph, node: Node, recursive=True) -> list[Node]:
    node_if = node.GIFs.self

    parent_if = [
        x
        for x in _get_neighbor_gifs(G, node_if)
        if isinstance(x, GraphInterfaceHierarchical) and not x.is_parent
    ]
    assert len(parent_if) == 1

    parent_if = parent_if[0]

    parents = _get_neighbor_nodes(G, parent_if)
    if len(parents) == 0:
        return parents
    if not recursive:
        return parents

    return parents + [
        p
        for direct_p in parents
        for p in _get_parents(G, direct_p, recursive=recursive)
    ]


def _get_children(G: nx.Graph, node: Node, recursive=True) -> list[Node]:
    node_if = node.GIFs.self

    children_if = [
        x
        for x in _get_neighbor_gifs(G, node_if)
        if isinstance(x, GraphInterfaceHierarchical) and x.is_parent
    ]
    assert len(children_if) == 1
    children_if = children_if[0]

    children = _get_neighbor_nodes(G, children_if)
    if len(children) == 0:
        return children
    if not recursive:
        return children

    return children + [
        c
        for direct_c in children
        for c in _get_children(G, direct_c, recursive=recursive)
    ]


def _get_top_level_nodes(G: nx.Graph, level: int):
    # print(level, "-" * 40)
    top_nodes: set[Node] = set()

    for i in G.nodes:
        assert isinstance(i, GraphInterface)
        if not isinstance(i, GraphInterfaceSelf):
            continue

        n = i.node
        # find top-level nodes
        if len(_get_parents(G, n, recursive=False)) > 0:
            continue

        # get children <level> deep in hierarchy
        targets: list[Node] = [n]
        for i in range(level):
            targets = [
                i for _n in targets for i in _get_children(G, _n, recursive=False)
            ]
        for t in targets:
            top_nodes.add(t)

    # print("Top", level, top_nodes)
    return top_nodes


def _add_node(G: nx.Graph, node: Node):
    G_ = node.get_graph().G
    tag_with_info(G_)
    G.add_nodes_from(G_.nodes)
    G.add_edges_from(G_.edges(data=True))


def sub_graph(G: nx.Graph, nodes: list[Node]):
    """
    Merge all GIFs that are not part of the specified nodes into the highest level
    representantive that is not a parent of nodes.
    """

    # no duplicate
    assert len(set(nodes)) == len(nodes)

    gifs = {gif for node in nodes for gif in _get_all_sub_GIFs(G, node)}
    other_gifs: set[GraphInterface] = set(G.nodes) - gifs

    G_ = G.copy()

    # Detach from parents
    for n in nodes:
        ps = _get_parents(G, n, recursive=False)
        for p in ps:
            G_.remove_edge(n.GIFs.parent, p.GIFs.children)

    # Make representing node for rest of graph
    repr_node = Node()
    repr_gif = GraphInterface()
    repr_node.GIFs.sub_conns = repr_gif
    _add_node(G_, repr_node)
    root = repr_gif
    other_gifs.add(root)

    Gout = merge(G_, root, other_gifs)

    return Gout


def sub_tree(G: nx.Graph, nodes: list[Node]):
    return G.subgraph([gif for node in nodes for gif in _get_all_sub_GIFs(G, node)])


def node_graph(G: nx.Graph, level: int) -> nx.Graph:
    Gout = G
    for n in _get_top_level_nodes(G, level):
        Gout = merge_sub(Gout, n)
    return Gout


def tag_with_info(G: nx.Graph):
    for t0, t1, d in G.edges(data=True):
        link = d["link"]
        assert isinstance(link, Link)

        # Direction
        direction = None
        if isinstance(link, LinkNamedParent):
            assert link.get_parent() in [t0, t1]
            assert link.get_child() in [t0, t1]
            direction = (link.get_parent(), link.get_child())
        elif isinstance(link, LinkSibling):
            assert isinstance(t0, GraphInterfaceSelf) or isinstance(
                t1, GraphInterfaceSelf
            )
            direction = (t0, t1) if isinstance(t0, GraphInterfaceSelf) else (t1, t0)

        d["direction"] = direction

        # Merged info
        d["merged"] = [d]


def render_graph(G: nx.Graph, ax=None):
    import matplotlib.pyplot as plt

    DIRECTIONAL = False
    MULTI = True
    assert not DIRECTIONAL or not MULTI

    if DIRECTIONAL:
        G_ = nx.DiGraph()
        G_.add_nodes_from(G)
        for t0, t1, d in G.edges(data=True):
            assert isinstance(t0, GraphInterface)
            assert isinstance(t1, GraphInterface)
            assert isinstance(d, dict)

            direction = d.get("direction")
            if direction is None:
                G_.add_edge(t0, t1, **d)
                G_.add_edge(t1, t0, **d)
            else:
                assert t0 in direction and t1 in direction
                G_.add_edge(*direction, **d)

        G = G_

    if MULTI:
        G_ = nx.MultiDiGraph()
        G_.add_nodes_from(G)
        for t0, t1, d in G.edges(data=True):
            assert isinstance(t0, GraphInterface)
            assert isinstance(t1, GraphInterface)
            assert isinstance(d, dict)

            for d_ in d["merged"]:
                G_.add_edge(t0, t1, **d_, root=d)

        G = G_

    for t0, t1, d in G.edges(data=True):
        assert isinstance(d, dict)

        merged: list[dict] = d["merged"]

        def params_for_link(link):
            color = "#000000"
            weight = 1

            if isinstance(link, LinkSibling):
                color = "#000000"  # black
                weight = 100
            elif isinstance(link, LinkNamedParent):
                color = "#FF0000"  # red
                weight = 40
            elif isinstance(link, LinkDirect) and all(
                isinstance(c.node, Electrical) for c in link.get_connections()
            ):
                color = "#00FF00"  # green
                weight = 1
            elif isinstance(link, LinkDirect) and all(
                isinstance(c, GraphInterfaceModuleSibling)
                for c in link.get_connections()
            ):
                color = "#AD139D"  # purple-like
                weight = 40
            elif isinstance(link, LinkDirect) and all(
                isinstance(c, GraphInterfaceModuleConnection)
                for c in link.get_connections()
            ):
                color = "#C1BE0F"  # yellow-like
                weight = 1
            else:
                color = "#1BD0D3"  # turqoise-like
                weight = 10

            return color, weight

        params = [params_for_link(m["link"]) for m in merged]
        param = max(params, key=lambda x: x[1])

        d["color"], d["weight"] = param

    # Draw
    layout = nx.spring_layout(G.to_undirected(as_view=True))
    nx.draw_networkx_nodes(G, ax=ax, pos=layout, node_size=150)
    # nx.draw_networkx_edges(
    #    G,
    #    ax=ax,
    #    pos=layout,
    #    # edgelist=G.edges,
    #    edge_color=[c for _, __, c in G.edges.data("color")]  # type: ignore
    #    # edge_color=color_edges_by_type(G.edges(data=True)),
    # )

    def dir_to_arrow(t0, t1, data):
        direction = d["root"].get("direction")
        if direction is None:
            return "-"
        assert t0 in direction and t1 in direction
        return "<-" if direction == (t0, t1) else "->"

    pos = layout
    for t0, t1, k, d in G.edges(data=True, keys=True):
        ax.annotate(
            "",
            xy=pos[t0],
            xycoords="data",
            xytext=pos[t1],
            textcoords="data",
            arrowprops=dict(
                arrowstyle=dir_to_arrow(t0, t1, d),
                color=d["color"],
                shrinkA=5,
                shrinkB=5,
                patchA=None,
                patchB=None,
                connectionstyle=f"arc3,rad={0.1 * k}",
            ),
        )

    # nx.draw_networkx_edges(
    #    G, pos=layout, edgelist=intra_comp_edges, edge_color="#0000FF"
    # )

    nodes: list[GraphInterface] = list(G.nodes)
    vertex_names = {
        vertex: f"{type(vertex.node).__name__}.{vertex.name}"
        + (
            f"|{vertex.node.get_full_name()}"
            if isinstance(vertex, GraphInterfaceSelf) and vertex.node is not None
            else ""
        )
        for vertex in nodes
    }
    nx.draw_networkx_labels(G, ax=ax, pos=layout, labels=vertex_names, font_size=10)

    # nx.draw_networkx_edge_labels(
    #    G,
    #    pos=layout,
    #    edge_labels=intra_edge_dict,
    #    font_size=10,
    #    rotate=False,
    #    bbox=dict(fc="blue"),
    #    font_color="white",
    # )

    return plt


def render_sidebyside(G: nx.Graph, nodes: list[Node] | None = None, depth=2):
    tag_with_info(G)

    import matplotlib.pyplot as plt

    if nodes is not None:
        G = sub_tree(G, nodes)

    # fig = plt.figure()
    fig, axs = plt.subplots(1, depth + 1)
    fig.subplots_adjust(0, 0, 1, 1)
    # plt.subplot(111)
    for i in range(depth + 1):
        nG = node_graph(G, i)
        render_graph(nG, ax=axs[i] if depth > 0 else axs)

    # render_graph(G, ax=axs[-1])
    return plt


def render_matrix(
    G: nx.Graph,
    nodes_rows: list[list[Node]],
    depth=2,
    min_depth=0,
    show_full=True,
    show_non_sum=True,
):
    tag_with_info(G)

    import matplotlib.pyplot as plt

    _nodes_rows: list[list[Node] | None] = list(nodes_rows)
    if show_full:
        _nodes_rows.append(None)

    depths: list[int | None] = list(range(min_depth, depth + 1))
    if show_non_sum:
        depths.append(None)

    row_cnt = len(_nodes_rows)
    col_cnt = len(depths)
    fig, _axs = plt.subplots(row_cnt, col_cnt)

    def axs(row, col):
        if row_cnt > 1 and col_cnt > 1:
            return _axs[row, col]
        if col_cnt > 1:
            return _axs[col]
        if row_cnt > 1:
            return _axs[row]
        return _axs

    for j, nodes in enumerate(_nodes_rows):
        Gn = G
        if nodes is not None:
            # Gn = sub_tree(G, nodes)
            Gn = sub_graph(Gn, nodes)

        for i, level in enumerate(depths):
            ax = axs(j, i)

            if level is not None:
                nG = node_graph(Gn, level)
                # print(Gn, "->", nG)
            else:
                nG = Gn

            render_graph(nG, ax=ax)

            # ax.set_title(
            #    f"row={j if nodes is not None else 'full'}"
            #    f"depth={i if level is not None else 'full'}",
            #    fontsize=8,
            # )

    plt.tight_layout()
    fig.subplots_adjust(0, 0, 1, 1)
    return plt
