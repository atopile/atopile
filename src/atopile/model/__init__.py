import igraph as ig

from .find import find_root_vertex, find_vertex_at_path, ancestory_dot_com, whos_your_daddy
from .model import add_block
from .plot import plot

def get_path(g: ig.Graph, vid: int):
    return ".".join(g[ancestory_dot_com(g, vid)]['ref'])
