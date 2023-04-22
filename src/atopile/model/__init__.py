import igraph as ig

from .find import find_root_vertex, find_vertex_at_path, ancestory_dot_com, whos_your_daddy
from .model import add_block
from .plot import plot

def get_vertex_path(g: ig.Graph, vid: int):
    return ".".join(g.vs[ancestory_dot_com(g, vid)[::-1]]['ref'])
