import igraph as ig
from typing import List

def find_vertex_at_path(g: ig.Graph, path: str):
    path_parts = path.split('.')
    candidates = g.vs.select(ref_eq=path_parts.pop(0))
    if len(candidates) > 1:
        raise ValueError(f"Multiple verticies found at path {path_parts}. Graph is invalid")
    for ref in path_parts:
        candidates = ig.VertexSeq(g, {i.index for c in candidates for i in c.neighbors(mode='in')})
        candidates = candidates.select(ref_eq=ref)
    return candidates[0]

def find_root_vertex(g: ig.Graph):
    candidates = g.vs.select(type_eq='block', _outdegree_eq=0)
    if len(candidates) > 1:
        raise ValueError("Multiple root verticies found. Graph is invalid")
    return candidates[0]

def ancestory_dot_com(g: ig.Graph, v: int) -> List[int]:
    """
    Get a list of all the logical parents above this
    """
    connectedness = g.subgraph_edges(g.es.select(type_eq='part_of'), delete_vertices=False)
    return connectedness.dfs(v, mode='out')[0]

def whos_your_daddy(g: ig.Graph, v: int):
    """
    Get logical parent of a node
    """
    connectedness = g.subgraph_edges(g.es.select(type_eq='part_of'), delete_vertices=False)
    parent = connectedness.vs[v].neighbors(mode='out')
    if len(parent) > 1:
        raise ValueError("Multiple logical parents found. Graph is invalid")
    return parent[0]

def find_blocks_associated_to_package(g: ig.Graph):
    """
    Get all blocks associated to package
    """
    return g.vs.select(type_in='block', _degree_gt=0, type_ne="package")