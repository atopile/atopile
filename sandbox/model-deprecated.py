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

class Model:
    def __init__(self) -> None:
        self.graph = ig.Graph(directed=True)
        self.data = {}

    def get_logical_graph(self) -> ig.Graph:
        sg = self.graph.subgraph_edges(self.graph.es.select(type_in=[EdgeType.part_of.name, EdgeType.defined_by.name]), delete_vertices=False)
        return sg

    def get_instance_of_graph(self) -> ig.Graph:
        sg = self.graph.subgraph_edges(self.graph.es.select(type_in=EdgeType.instance_of.name), delete_vertices=False)
        return sg

    def get_instance_of_sub_graph(self, root_vertex: int) -> ig.Graph:
        instance_of_graph = self.get_instance_of_graph()
        definition_graph = instance_of_graph.subcomponent(root_vertex)
        subgraph = self.graph.induced_subgraph(definition_graph)
        return subgraph

    def get_part_of_graph(self) -> ig.Graph:
        sg = self.graph.subgraph_edges(self.graph.es.select(type_in=EdgeType.part_of.name), delete_vertices=False)
        return sg

    def get_sub_part_of_graph(self, root_vertex) -> ig.Graph:
        part_of_graph = self.get_part_of_graph()
        instance_graph = part_of_graph.subcomponent(root_vertex)
        subgraph = self.graph.induced_subgraph(instance_graph)
        return subgraph

    def get_electical_graph(self) -> ig.Graph:
        return self.graph.subgraph_edges(self.graph.es.select(type_eg=EdgeType.connects_to), delete_vertices=False)

    def get_idxs_from_paths(self, paths: List[str]) -> List[int]:
        return [self.get_vertex_by_path(path).index for path in paths]

    def get_paths_from_idxs(self, idxs: List[int]) -> List[str]:
        return self.graph.vs[idxs]["path"]

    # untested
    def get_parents_idxs(self, id: int) -> List[int]:
        sg = self.get_logical_graph()
        parents, _, layers = sg.bfs(id, mode="out")
        assert len(parents) == max(layers)  # this should be a single linear chain
        return parents

    # untested
    def get_parents_paths(self, path: str) -> List[str]:
        return self.get_parents_idxs(self.get_vertex_by_path(path).index)["path"]

    # untested
    def get_children_idx(self, idx: int) -> List[int]:
        sg = self.get_logical_graph()
        children = sg.subcomponent(idx, mode="in")
        return children

    # untested
    def get_children_paths(self, path: str) -> List[str]:
        return self.get_children_idx(self.get_vertex_by_path(path).index)["path"]

    def get_vertex_by_path(self, path: str) -> ig.Vertex:
        try:
            return self.graph.vs.find(path_eq=path)
        except ValueError as ex:
            raise KeyError(f"Vertex with path {path} not found") from ex

    def get_vertex_type(self, path: Optional[str] = None, vid: Optional[int] = None) -> VertexType:
        if (path and vid) or (not path and not vid):
            raise ValueError("Provide a path or a vertex id")
        if path:
            return VertexType(self.get_vertex_by_path(path)["type"])
        elif vid:
            return VertexType(self.graph.vs[vid]["type"])

    def add_vertex(self, ref: str, vertex_type: Union[VertexType, str], defined_by: Optional[str] = None, part_of: Optional[str] = None, **kwargs):
        if defined_by and part_of:
            raise ValueError("Vertex cannot be both defined_by and part_of")
        parent = defined_by or part_of  # will result in None if both are None

        path = parent + "/" + ref if parent else ref
        vertex_params = {
            "path": path,
            "ref": ref,
            "type": VertexType(vertex_type).name,
        }

        vertex_params.update(kwargs)
        vertex = self.graph.add_vertex(**vertex_params)

        if part_of:
            self.graph.add_edge(vertex.index, self.get_vertex_by_path(part_of).index, type='part_of')
        elif defined_by:
            self.graph.add_edge(vertex.index, self.get_vertex_by_path(defined_by).index, type='defined_by')

    def add_vertex_parameter(self, path: str, parameter_name: str):
        self.get_vertex_by_path(path)[parameter_name] = None

    def set_vertex_parameter(self, path: str, parameter_name: str, parameter_value: str):
        self.get_vertex_by_path(path)[parameter_name] = parameter_value

    def add_connection(self, from_path: str, to_path: str):
        self.graph.add_edge(self.get_vertex_by_path(from_path).index, self.get_vertex_by_path(to_path).index, type='connects_to')

    def create_instance(self, class_path: str, ref: str, defined_by: Optional[str] = None, part_of: Optional[str] = None):
        if defined_by and part_of:
            raise ValueError("instantiation cannot be both defined_by and part_of")

        sg = self.graph.subgraph(self.get_children_idx(self.get_vertex_by_path(class_path).index))
        if part_of:
            new_path = part_of + "/" + ref or part_of
        elif defined_by:
            new_path = defined_by + "/" + ref or defined_by

        sg.vs["path"] = [p.replace(class_path, new_path) for p in sg.vs["path"]]
        sg.vs.find(path_eq=new_path)["ref"] = ref

        self.graph: ig.Graph = self.graph.disjoint_union(sg)

        self.graph.add_edge(
            self.get_vertex_by_path(new_path).index,
            self.get_vertex_by_path(class_path).index,
            type='instance_of'
        )

        if part_of:
            self.graph.add_edge(
                self.get_vertex_by_path(new_path).index,
                self.get_vertex_by_path(part_of).index,
                type='part_of'
            )
        elif defined_by:
            self.graph.add_edge(
                self.get_vertex_by_path(new_path).index,
                self.get_vertex_by_path(defined_by).index,
                type='defined_by'
            )

    def get_vertex_ref(self, vid: int):
        return self.graph.vs[vid]['ref']

    def get_vertex_path(self, vid: int):
        return self.graph.vs[vid]['path']

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
