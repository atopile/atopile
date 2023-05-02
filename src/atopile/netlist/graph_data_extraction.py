import igraph as ig
from atopile.model.model import (
    Graph,
    VertexType,
    generate_uid_from_path,
)

def get_packages(g: ig.Graph) -> ig.VertexSeq:
    return g.vs.select(type_in='package')

def get_vertex_parameter(vertex: ig.Vertex, parameter: str)-> str:
    return vertex[parameter]

def get_parent_from_path(path: str) -> str:
    """
    Get logical parent of a vertex from path
    """
    path_parts = path.split('/')
    # Remove last element of the list
    path_parts.pop()
    separator = '/'
    parent_path = separator.join(path_parts)
    return parent_path

def get_block_from_package(g: Graph, package: ig.Vertex) -> ig.Vertex:
    parent_path = get_parent_from_path(package['path'])
    block = g.get_vertex_by_path(parent_path)
    
    return block
