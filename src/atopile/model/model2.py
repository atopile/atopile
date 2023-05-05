from enum import Enum
from typing import List, Optional, Union
from atopile.model import utils
import logging
import copy

import igraph as ig

log = logging.getLogger(__name__)

class VertexType(Enum):
    file = "file"
    module = "module"
    component = "component"
    pin = "pin"
    signal = "signal"

block_types = [VertexType.module, VertexType.component]
pin_types = [VertexType.pin, VertexType.signal]

class EdgeType(Enum):
    connects_to = "connects_to"
    part_of = "part_of"
    option_of = "option_of"
    instance_of = "instance_of"
    inherits_from = "inherits_from"

class Model:
    def __init__(self) -> None:
        self.graph = ig.Graph(directed=True)
        self.graph.vs["type"] = []
        self.graph.vs["path"] = []

        self.data = {}
        self.schemas = {}

    def plot(self, *args, **kwargs):
        return utils.plot(self.graph, *args, **kwargs)

    def get_graph_view(self, edge_types: Union[EdgeType, List[EdgeType]]) -> ig.Graph:
        """
        Look at the graph from the perspective of the given edge types.
        """
        if not isinstance(edge_types, list):
            edge_types = [EdgeType(edge_types)]
        edge_type_names = [e.name for e in edge_types]
        sg = self.graph.subgraph_edges(self.graph.es.select(type_in=edge_type_names), delete_vertices=False)
        return sg

    def instantiate_block(self, class_path: str, instance_ref: str, part_of_path: str) -> str:
        """
        Take the feature, component or module and create an instance of it.
        """
        class_root = self.graph.vs.find(path_eq=class_path)
        part_of_graph = self.get_graph_view(EdgeType.part_of)
        class_children = part_of_graph.vs[part_of_graph.subcomponent(class_root.index, mode="in")]
        sg = self.graph.subgraph(class_children)
        instance_path = part_of_path + "/" + instance_ref

        # replace the paths and references of all the blocks/subcomponents
        class_paths = copy.copy(sg.vs["path"])
        sg.vs.find(path_eq=class_path)["ref"] = instance_path
        sg.vs["path"] = [p.replace(class_path, instance_path) for p in class_paths]

        self.graph: ig.Graph = self.graph.disjoint_union(sg)

        self.new_edge(
            EdgeType.instance_of,
            instance_path,
            class_path,
        )

        self.new_edge(
            EdgeType.part_of,
            instance_path,
            part_of_path,
        )

        # copy the data and schemas
        for instance_vertex_path, class_vertex_path in zip(sg.vs["path"], class_paths):
            self.data[instance_vertex_path] = copy.deepcopy(self.data.get(class_vertex_path, {}))
            self.schemas[instance_vertex_path] = copy.deepcopy(self.schemas.get(class_vertex_path, {}))

    def new_vertex(self, vertex_type: VertexType, ref: str, part_of: Optional[str] = None, option_of: Optional[str] = None) -> str:
        """
        Create a new vertex in the graph.
        """
        if part_of and option_of:
            raise ValueError("Cannot be both part_of and option_of")

        if not (part_of or option_of):
            path = ref
        elif part_of:
            path = f"{part_of}/{ref}"
        elif option_of:
            path = f"{option_of}/{ref}"

        assert path not in self.graph.vs["path"]
        self.graph.add_vertex(ref=ref, type=vertex_type.name, path=path)

        if part_of:
            self.new_edge(EdgeType.part_of, path, part_of)
        elif option_of:
            self.new_edge(EdgeType.option_of, path, option_of)

        return path

    def new_block(self, block_type: VertexType, ref: str, part_of: str) -> str:
        """
        Create a new empty block in the graph.
        """
        assert block_type in block_types
        path = self.new_vertex(block_type, ref, part_of)
        self.data[path] = {}
        self.schemas[path] = {}
        return path

    def new_edge(self, edge_type: EdgeType, from_path: str, to_path: str) -> None:
        """
        Create a new edge in the graph.
        """
        assert edge_type in EdgeType
        self.graph.add_edge(
            self.graph.vs.find(path_eq=from_path),
            self.graph.vs.find(path_eq=to_path),
            type=edge_type.name
        )
