import copy
import logging
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union

import igraph as ig
from schema import Schema

from atopile.model import utils

log = logging.getLogger(__name__)


MODULE_PATH_SEPERATOR = "."

class VertexType(Enum):
    file = "file"
    module = "module"
    component = "component"
    interface = "interface"
    pin = "pin"
    signal = "signal"

block_types = [VertexType.module, VertexType.component, VertexType.interface]
pin_types = [VertexType.pin, VertexType.signal]

class EdgeType(Enum):
    connects_to = "connects_to"
    part_of = "part_of"
    option_of = "option_of"
    instance_of = "instance_of"
    inherits_from = "inherits_from"
    imported_to = "imported_to"
    subclass_of = "subclass_of"

class Model:
    def __init__(self) -> None:
        self.graph = ig.Graph(directed=True)
        self.graph.vs["type"] = []
        self.graph.vs["path"] = []
        self.graph.es["uid"] = []

        self.data = {}
        self.schema = Schema({})

        self.src_files: list[Path] = []

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

    def _instantiate_block(self, class_path: str, instance_ref: str, part_of_path: str, instance_path: Optional[str] = None) -> str:
        """
        Take the feature, component or module and create an instance of it.
        """
        class_root = self.graph.vs.find(path_eq=class_path)
        part_of_graph = self.get_graph_view([EdgeType.part_of, EdgeType.option_of])
        class_children_idxs = part_of_graph.subcomponent(class_root.index, mode="in")
        class_children = part_of_graph.vs[class_children_idxs]
        sg = self.graph.subgraph(class_children)

        if instance_path is None:
            # this is dumb, because it assumes that part_of_path is a module already, it doesn't expect it could be a file
            instance_path = part_of_path + MODULE_PATH_SEPERATOR + instance_ref

        # replace the paths and references of all the blocks/subcomponents
        class_paths = copy.copy(sg.vs["path"])
        sg.vs.find(path_eq=class_path)["ref"] = instance_ref
        sg.vs["path"] = [p.replace(class_path, instance_path) for p in class_paths]

        self.graph: ig.Graph = self.graph.disjoint_union(sg)

        # create new part_of edges
        # instance_of edges are created in the caller of this function
        self.new_edge(
            EdgeType.part_of,
            instance_path,
            part_of_path,
        )

        # link existing instance edges to the new instance
        # TODO: see if there's a better or more preformant way to do this, it's a bit unreadable
        instance_edges = self.graph.es.select(_from_in=class_children_idxs, type_eq=EdgeType.instance_of.name)
        class_instance_of_edge_tuples = [e.tuple for e in instance_edges]
        class_instance_of_edge_from_idxs = [e[0] for e in class_instance_of_edge_tuples]
        class_instance_of_from_paths = self.graph.vs[class_instance_of_edge_from_idxs]["path"]
        instance_instance_of_from_paths = [p.replace(class_path, instance_path) for p in class_instance_of_from_paths]
        instance_instance_of_edge_from_idxs = [self.graph.vs.find(path_eq=p).index for p in instance_instance_of_from_paths]
        class_instance_of_edge_to_idxs = [e[1] for e in class_instance_of_edge_tuples]
        instance_instance_of_edge_tuples = list(zip(instance_instance_of_edge_from_idxs, class_instance_of_edge_to_idxs))
        self.graph.add_edges(instance_instance_of_edge_tuples, attributes={"type": [EdgeType.instance_of.name] * len(instance_instance_of_edge_tuples)})

        # copy the data and schemas
        for instance_vertex_path, class_vertex_path in zip(sg.vs["path"], class_paths):
            self.data[instance_vertex_path] = copy.deepcopy(self.data.get(class_vertex_path, {}))
            # self.schemas[instance_vertex_path] = copy.deepcopy(self.schemas.get(class_vertex_path, {}))

        return instance_path

    def instantiate_block(self, class_path: str, instance_ref: str, part_of_path: str) -> str:
        """
        Take the feature, component or module and create an instance of it.
        """
        instance_path = self._instantiate_block(class_path, instance_ref, part_of_path)
        self.new_edge(
            EdgeType.instance_of,
            instance_path,
            class_path,
        )
        return instance_path

    def subclass_block(self, block_type: VertexType, superclass_path: str, subclass_ref: str, part_of_path: str) -> str:
        """
        Take the feature, component or module and create a subclass of it.
        """
        assert block_type in block_types
        # in the case of subclassing, a subclass's part_of_path must always be a file. This is checked in parser.py
        # we just need to join them with a ":" instead of a "."
        subclass_path = part_of_path + ":" + subclass_ref
        self._instantiate_block(superclass_path, subclass_ref, part_of_path, subclass_path)
        self.graph.vs.find(path_eq=subclass_path)["type"] = block_type.name

        self.new_edge(
            EdgeType.subclass_of,
            subclass_path,
            superclass_path,
        )

        return subclass_path

    def enable_option(self, option_path: str) -> str:
        """
        Enable an option in the graph
        """
        option_idx = self.graph.vs.find(path_eq=option_path).index
        parent_edges = self.graph.es.select(type_eq=EdgeType.option_of.name, _from=option_idx)
        parent_edges["type"] = EdgeType.part_of.name
        return option_path

    def new_vertex(self, vertex_type: VertexType, ref: str, part_of: Optional[str] = None, option_of: Optional[str] = None) -> str:
        """
        Create a new vertex in the graph.
        """
        if part_of and option_of:
            raise ValueError("Cannot be both part_of and option_of")

        if not (part_of or option_of):
            path = ref
        else:
            parent_path = part_of or option_of
            if parent_path not in self.graph.vs["path"]:
                raise ValueError(f"Parent path {parent_path} does not exist")
            # TODO: this is hacky, make sure to avoid it in corev3
            if self.graph.vs.find(path_eq=parent_path)["type"] == VertexType.file.name:
                path = f"{parent_path}:{ref}"
            else:
                path = f"{parent_path}{MODULE_PATH_SEPERATOR}{ref}"

        if path in self.graph.vs["path"]:
            raise ValueError(f"Path {path} already exists")
        self.graph.add_vertex(ref=ref, type=vertex_type.name, path=path)

        if part_of:
            self.new_edge(EdgeType.part_of, path, part_of)
        elif option_of:
            self.new_edge(EdgeType.option_of, path, option_of)

        return path

    def new_edge(self, edge_type: EdgeType, from_path: str, to_path: str, uid: Optional[str] = None) -> None:
        """
        Create a new edge in the graph.
        """
        assert edge_type in EdgeType
        self.graph.add_edge(
            self.graph.vs.find(path_eq=from_path),
            self.graph.vs.find(path_eq=to_path),
            type=edge_type.name,
            uid=uid,
        )

    def find_ref(self, ref: str, context: str, return_unfound=False) -> Tuple[str, List[str], List[str]]:
        """
        Find what reference means in the current context.
        Returns a tuple of the graph-path, the data-path and an optional list of remaining parts that weren't found.
        """
        context_vertex = self.graph.vs.find(path_eq=context)
        part_of_view = self.get_graph_view([EdgeType.part_of, EdgeType.option_of, EdgeType.imported_to])
        ref_parts = ref.split(".")
        # 1. ascending loop
        # TODO: we need to figure out scoping and whether we should be allowed to scope indefinately above our context
        for elder in part_of_view.bfsiter(context_vertex.index, mode="out"):
            elder_direct_children = self.graph.vs[part_of_view.neighbors(elder.index, mode="in")]
            if ref_parts[0] in elder_direct_children["ref"] or ref_parts[0] in self.data.get(elder["path"], {}):
                break  # found the first element in the sequence
        else:
            # otherwise, we're searching internally
            # this should entirely skip the descending loop next up
            elder = context_vertex

        # 2. desecending loop
        ref_vertex_trail = [elder]
        for ref_parts_checked_in_graph, ref_part in enumerate(ref_parts):
            child_candidates = self.graph.vs[part_of_view.neighbors(ref_vertex_trail[-1].index, mode="in")]
            try:
                ref_vertex_trail.append(child_candidates.find(ref_eq=ref_part))
            except ValueError:
                break
        else:
            # completely a graph element
            if return_unfound:
                return ref_vertex_trail[-1]["path"], [], []
            else:
                return ref_vertex_trail[-1]["path"], []

        # 3. desecending data loop
        # data trail, like the vertex trail, staring where the graph left off
        ref_data_trail = [self.data[ref_vertex_trail[-1]["path"]]]
        # if we're down here, it's because we didn't get to the end of our reference in the graph
        # so let's check for data where the graph left off
        remaining_ref_parts = ref_parts[ref_parts_checked_in_graph:]
        for ref_parts_checked_in_data, ref_part in enumerate(remaining_ref_parts):
            try:
                ref_data_trail.append(ref_data_trail[-1][ref_part])
            except KeyError as ex:
                if return_unfound:
                    return ref_vertex_trail[-1]["path"], remaining_ref_parts[:ref_parts_checked_in_data], remaining_ref_parts[ref_parts_checked_in_data:]
                else:
                    raise KeyError(f"Could not find {ref} in {context}") from ex
        else:
            # found a complete match in the data
            if return_unfound:
                return ref_vertex_trail[-1]["path"], remaining_ref_parts, []
            else:
                return ref_vertex_trail[-1]["path"], remaining_ref_parts
