import igraph as ig
from typing import Optional
from atopile.model.find import find_vertex_at_path, find_root_vertex

def add_block(g: ig.Graph, block: ig.Graph, block_ref: str, parent: Optional[str] = None):
    block_start_index = len(g.vs)
    block_root_index = find_root_vertex(block).index + block_start_index
    g += block
    g.vs[block_root_index]['ref'] = block_ref

    if parent:
        g.add_edge(block_root_index, find_vertex_at_path(g, parent).index, type='part_of')
    return g
