import igraph as ig
from atopile.model.model import (
    Model,
    VertexType,
)

from atopile.model.utils import generate_uid_from_path

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

def get_block_from_package(g: Model, package: ig.Vertex) -> ig.Vertex:
    parent_path = get_parent_from_path(package['path'])
    block = g.get_vertex_by_path(parent_path)
    
    return block

def find_blocks_associated_to_package(g: ig.Graph):
    """
    Get all blocks associated to package
    """
    return g.vs.select(type_in='block', _degree_gt=0, type_ne="package")

def get_package_instances_of_seed(g: Model, root_index: int = 0) -> list:
    component_prototype_package_list = []
    
    # Find the vertex from which to start
    root_path = g.get_vertex_path(vid = root_index)
    # The vertex should have a seed associatated
    root_seed_path = root_path + '/seed'
    seed_vertex_index = g.get_vertex_by_path(path = root_seed_path).index
    # Find the neighbors of the seed
    seed_neighbors = g.graph.neighbors(seed_vertex_index, mode="in")
    # To be a component prototype, the block should be a neighbor of the seed and should have a package associated
    for seed_neighbor in seed_neighbors:
        if g.get_vertex_type(vid = seed_neighbor) == VertexType.block:
            logical_graph = g.get_part_of_graph()
            block_neighbors = logical_graph.neighbors(seed_neighbor, mode="in")
            for block_neighbor in block_neighbors:
                if g.get_vertex_type(vid = block_neighbor) == VertexType.package:
                    component_prototype_package_list.append(g.graph.vs[block_neighbor])
    
    return component_prototype_package_list

def get_pin_list_from_package(g: Model, package: ig.Vertex) -> list:
    pin_list = []

    part_of_graph = g.get_part_of_graph()
    package_neighbors = part_of_graph.neighbors(package.index, mode="in")
    for package_neighbor in package_neighbors:
        if g.get_vertex_type(vid = package_neighbor) == VertexType.pin:
            print('found a pin!')
            pin_list.append(g.graph.vs[package_neighbor])
    
    return pin_list
