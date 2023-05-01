import hashlib
import uuid
from enum import Enum
from typing import List, Optional, Union

import igraph as ig


class VertexType(Enum):
    block = "block"
    package = "package"
    pin = "pin"
    ethereal_pin = "ethereal_pin"

class EdgeType(Enum):
    connects_to = "connects_to"
    part_of = "part_of"
    defined_by = "defined_by"
    instance_of = "instance_of"

class Graph:
    def __init__(self) -> None:
        self.graph = ig.Graph(directed=True)

    def get_children(self, path: str) -> List[int]:
        sg = self.graph.subgraph_edges(self.graph.es.select(type_in=[EdgeType.part_of.name, EdgeType.defined_by.name]), delete_vertices=False)
        children = sg.subcomponent(self.graph.vs.find(path_eq=path).index, mode="in")
        return children

    def add_vertex(self, ref: str, vertex_type: Union[VertexType, str], defined_by: Optional[str] = None, part_of: Optional[str] = None, **kwargs):
        if defined_by and part_of:
            raise ValueError("Vertex cannot be both defined_by and part_of")
        parent = defined_by or part_of  # will result in None if both are None

        vertex_params = {
            "path": parent + "/" + ref if parent else ref,
            "ref": ref,
            "type": VertexType(vertex_type).name,
        }

        vertex_params.update(kwargs)
        vertex = self.graph.add_vertex(**vertex_params)

        if part_of:
            self.graph.add_edge(vertex.index, self.graph.vs.find(path_eq=part_of).index, type='part_of')
        elif defined_by:
            self.graph.add_edge(vertex.index, self.graph.vs.find(path_eq=defined_by).index, type='defined_by')

        return g

    def add_vertex_parameter(self, path: str, parameter_name: str):
        self.graph.vs.find(path_eq=path)[parameter_name] = None

    def set_vertex_parameter(self, path: str, parameter_name: str, parameter_value: str):
        self.graph.vs.find(path_eq=path)[parameter_name] = parameter_value

    def add_connection(self, from_path: str, to_path: str):
        self.graph.add_edge(self.graph.vs.find(path_eq=from_path).index, self.graph.vs.find(path_eq=to_path).index, type='connects_to')

    def create_instance(self, class_path: str, ref: str, defined_by: Optional[str] = None, part_of: Optional[str] = None):
        if defined_by and part_of:
            raise ValueError("instantiation cannot be both defined_by and part_of")

        sg = self.graph.subgraph(self.get_children(class_path))
        if part_of:
            new_path = part_of + "/" + ref or part_of
        elif defined_by:
            new_path = defined_by + "/" + ref or defined_by

        sg.vs["path"] = [p.replace(class_path, new_path) for p in sg.vs["path"]]
        sg.vs.find(path_eq=new_path)["ref"] = ref

        self.graph: ig.Graph = self.graph.disjoint_union(sg)

        self.graph.add_edge(
            self.graph.vs.find(path_eq=new_path).index,
            self.graph.vs.find(path_eq=class_path).index,
            type='instance_of'
        )

        if part_of:
            self.graph.add_edge(
                self.graph.vs.find(path_eq=new_path).index,
                self.graph.vs.find(path_eq=part_of).index,
                type='part_of'
            )
        elif defined_by:
            self.graph.add_edge(
                self.graph.vs.find(path_eq=new_path).index,
                self.graph.vs.find(path_eq=defined_by).index,
                type='defined_by'
            )
    def plot(self, *args, debug=False, **kwargs):
        color_dict = {
            None: "grey",
            "block": "red",
            "package": "green",
            "pin": "cyan",
            "ethereal_pin": "magenta",
            "connects_to": "blue",
            "part_of": "black",
            "defined_by": "green",
            "instance_of": "red",
        }
        assert all(t is not None for t in self.graph.vs["type"])

        kwargs["vertex_color"] = [color_dict.get(type_name, "grey") for type_name in self.graph.vs["type"]]
        kwargs["edge_color"] = [color_dict[type_name] for type_name in self.graph.es["type"]]
        kwargs["vertex_label_size"] = 8
        kwargs["edge_label_size"] = 8
        if debug:
            kwargs["vertex_label"] = [f"{i}: {vs['path']}" for i, vs in enumerate(self.graph.vs)]
            kwargs["edge_label"] = self.graph.es["type"]
        else:
            kwargs["vertex_label"] = self.graph.vs["ref"]
        return ig.plot(self.graph, *args, **kwargs)

# Deprecated -- not used
# def add_to_graph(g: ig.Graph, what_to_add: ig.Graph, new_reference: str, part_of: Optional[str] = None, defined_by: Optional[str] = None) -> ig.Graph:
#     block_start_index = len(g.vs)
#     block_root_index = find_root_vertex(what_to_add).index + block_start_index
#     g += what_to_add
#     g.vs[block_root_index]['ref'] = new_reference

#     if part_of:
#         g.add_edge(block_root_index, find_vertex_at_path(g, part_of).index, type='part_of')
#     if defined_by:
#         g.add_edge(block_root_index, find_vertex_at_path(g, defined_by).index, type='defined_by')
#     return g

# Deprecated -- not used
# def create_instance(g: ig.Graph, instance_of_what: str, instance_ref: str, part_of_what: Optional[str] = None):
#     copy_root = find_vertex_at_path(g, part_of_what)


#     block_start_index = len(g.vs)
#     block_root_index = find_root_vertex(instance_of_what).index + block_start_index
#     g += instance_of_what
#     g.vs[block_root_index]['ref'] = instance_ref

#     g.add_edge(block_root_index, find_vertex_at_path(g, part_of_what).index, type='part_of')

#     if part_of_what:
#         g.add_edge(block_root_index, find_vertex_at_path(g, part_of_what).index, type='part_of')

#     return g

def generate_uid_from_path(path: str) -> str:
    path_as_bytes = path.encode('utf-8')
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return uuid.UUID(bytes=hashed_path)

# def get_vertex_index(vertices: ig.VertexSeq) -> list:
#     return vertices.indices

def get_vertex_ref(g: ig.Graph, vid: int):
    return g.vs[vid]['ref']

def get_vertex_path(g: ig.Graph, vid: int):
    return g.vs[vid]['path']

# def find_vertex_at_path(g: ig.Graph, path: str):
#     path_parts = path.split('.')
#     candidates = g.vs.select(ref_eq=path_parts.pop(0))
#     if len(candidates) > 1:
#         raise ValueError(f"Multiple verticies found at path {path_parts}. Graph is invalid")
#     for ref in path_parts:
#         candidates = ig.VertexSeq(g, {i.index for c in candidates for i in c.neighbors(mode='in')})
#         candidates = candidates.select(ref_eq=ref)
#     return candidates[0]

# def find_root_vertex(g: ig.Graph):
#     candidates = g.vs.select(type_eq='block', _outdegree_eq=0)
#     if len(candidates) > 1:
#         raise ValueError("Multiple root verticies found. Graph is invalid")
#     return candidates[0]

# def ancestory_dot_com(g: ig.Graph, v: int) -> List[int]:
#     """
#     Get a list of all the logical parents above this
#     """
#     connectedness = g.subgraph_edges(g.es.select(type_eq='part_of'), delete_vertices=False)
#     return connectedness.dfs(v, mode='out')[0]

# def who_are_you_part_of(g: ig.Graph, path: str):
#     """
#     Get logical parent of a node
#     """
#     connectedness = g.subgraph_edges(g.es.select(type_eq='part_of'), delete_vertices=False)
#     parent = connectedness.vs[v].neighbors(mode='out')
#     if len(parent) > 1:
#         raise ValueError("Multiple logical parents found. Graph is invalid")
#     elif len(parent) == 0:
#         return None
#     return parent[0]

def get_parent_from_path(path: str):
    """
    Get logical parent of a vertex from path
    """
    path_parts = path.split('/')
    # Remove last element of the list
    path_parts.pop()
    separator = '/'
    parent_path = separator.join(path_parts)
    return parent_path

# def find_blocks_associated_to_package(g: ig.Graph):
#     """
#     Get all blocks associated to package
#     """
#     return g.vs.select(type_in='block', _degree_gt=0, type_ne="package")
