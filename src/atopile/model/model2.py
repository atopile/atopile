from enum import Enum
from typing import List, Optional, Union
from atopile.model import utils

import igraph as ig

class VertexType(Enum):
    file = "file"
    module = "module"
    component = "component"
    feature = "feature"
    pin = "pin"
    signal = "signal"

block_types = [VertexType.module, VertexType.component, VertexType.feature]
pin_types = [VertexType.pin, VertexType.signal]

class EdgeType(Enum):
    connects_to = "connects_to"
    part_of = "part_of"
    instance_of = "instance_of"
    inherits_from = "inherits_from"

class Model:
    def __init__(self) -> None:
        self.graph = ig.Graph(directed=True)
        self.data = {}
        self.schemas = {}

    def plot(self, *args, **kwargs):
        utils.plot(self.graph, *args, **kwargs)

    def get_graph_view(self, edge_types: Union[EdgeType, List[EdgeType]]) -> ig.Graph:
        """
        Look at the graph from the perspective of the given edge types.
        """
        if not isinstance(edge_types, list):
            edge_types = list(EdgeType(edge_types))
        sg = self.graph.subgraph_edges(self.graph.es.select(type_in=edge_types), delete_vertices=False)
        return sg

    def instantiate_block(self, class_path: str, parent_path: str) -> str:
        """
        Take the feature, component or module and create an instance of it.
        """
        class_block = self.graph.vs.find(path_eq=class_path)
        assert class_block["type"] in block_types

        graph_view_part_of = self.get_graph_view(EdgeType.part_of)
        graph_view_inherits_from = self.get_graph_view(EdgeType.inherits_from)

        # inheretance walk
        for block_idx, layer, _ in graph_view_inherits_from.bfsiter(class_block.index, mode="in"):
            # we're assuming that there aren't any conflicting keys in the various blocks
            # if there are, we should probably raise an error
            # consider using `layer` for that

            # copy the subcomponents' (except features) graphs, schemas and datas of each of these blocks to the new instance
            # if there's a key collision, ignore the new data
            # in this case, earlier data is better, since it's lower down the tree of inheritance
            pass

        # attach the new instance to the parent

        # return the new instance path as a reference
