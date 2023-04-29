#%%
import hashlib
import uuid
from typing import List, Optional

import igraph as ig

#%%
def add_to_graph(g: ig.Graph, what_to_add: ig.Graph, new_reference: str, part_of: Optional[str] = None, defined_by: Optional[str] = None) -> ig.Graph:
    block_start_index = len(g.vs)
    block_root_index = find_root_vertex(what_to_add).index + block_start_index
    g += what_to_add
    g.vs[block_root_index]['ref'] = new_reference

    if part_of:
        g.add_edge(block_root_index, find_vertex_at_path(g, part_of).index, type='part_of')
    if defined_by:
        g.add_edge(block_root_index, find_vertex_at_path(g, defined_by).index, type='defined_by')
    return g


def create_instance(g: ig.Graph, instance_of_what: str, instance_ref: str, part_of_what: Optional[str] = None):
    copy_root = find_vertex_at_path(g, part_of_what)


    block_start_index = len(g.vs)
    block_root_index = find_root_vertex(instance_of_what).index + block_start_index
    g += instance_of_what
    g.vs[block_root_index]['ref'] = instance_ref

    g.add_edge(block_root_index, find_vertex_at_path(g, part_of_what).index, type='part_of')

    if part_of_what:
        g.add_edge(block_root_index, find_vertex_at_path(g, part_of_what).index, type='part_of')

    return g


def generate_uid_from_path(path: str) -> str:
    path_as_bytes = path.encode('utf-8')
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return uuid.UUID(bytes=hashed_path)

def get_vertex_path(g: ig.Graph, vid: int):
    return ".".join(g.vs[ancestory_dot_com(g, vid)[::-1]]['ref'])

def get_vertex_index(vertices: ig.VertexSeq) -> list:
    return vertices.indices

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
#%%
import hashlib
import uuid
from typing import List, Optional

import igraph as ig
from enum import Enum
from typing import Union, Optional, List

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

#%%

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

    def add_connection(self, from_path: str, to_path: str):
        self.graph.add_edge(self.graph.vs.find(path_eq=from_path).index, self.graph.vs.find(path_eq=to_path).index, type='connects_to')

    def create_instance(self, instance_of_what: str, ref: str, part_of: Optional[str] = None):
        block_start_index = len(g.vs)
        block_root_index = find_root_vertex(instance_of_what).index + block_start_index
        g += instance_of_what
        g.vs[block_root_index]['ref'] = instance_ref

        g.add_edge(block_root_index, find_vertex_at_path(g, part_of_what).index, type='part_of')

        if part_of_what:
            g.add_edge(block_root_index, find_vertex_at_path(g, part_of_what).index, type='part_of')

        return g

    def plot(self, *args, **kwargs):
        color_dict = {
            "block": "red",
            "package": "green",
            "pin": "cyan",
            "ethereal_pin": "magenta",
            "connects_to": "blue",
            "part_of": "black",
            "defined_by": "green",
            "instance_of": "red",
        }
        try:
            self.graph.vs["type"]
        except KeyError as ex:
            raise KeyError("Graph is missing a 'type' vertex attribute. Is there enough data in this graph") from ex

        kwargs["vertex_color"] = [color_dict.get(type_name, "grey") for type_name in self.graph.vs["type"]]
        kwargs["vertex_label"] = [f"{i}: {ref}" for i, ref in enumerate(self.graph.vs["ref"])]
        kwargs["edge_color"] = [color_dict[type_name] for type_name in self.graph.es["type"]]
        return ig.plot(self.graph, *args, **kwargs)

#%%

g = Graph()
g.add_vertex("resistor.ato", VertexType.block)
g.add_vertex("resistor", VertexType.block, defined_by="resistor.ato")
g.add_vertex("package", VertexType.package, part_of="resistor.ato/resistor")
g.add_vertex("1", VertexType.ethereal_pin, part_of="resistor.ato/resistor")
g.add_vertex("2", VertexType.ethereal_pin, part_of="resistor.ato/resistor")
g.add_vertex("1", VertexType.pin, part_of="resistor.ato/resistor/package")
g.add_vertex("2", VertexType.pin, part_of="resistor.ato/resistor/package")
g.add_connection("resistor.ato/resistor/1", "resistor.ato/resistor/package/1")
g.add_connection("resistor.ato/resistor/2", "resistor.ato/resistor/package/2")

g.plot()

# %%
g.get_children("block")

# %%
g.plot()

# %%
print(g.graph.vs["path"])
# %%
