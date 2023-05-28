from typing import List, Union, Optional

import igraph as ig

from atopile.model.model import EdgeType, Model, VertexType

EdgeIterable = Union[ig.EdgeSeq, List[ig.Edge]]

class ModelVertexView:
    def __init__(self, model: Model, index: int) -> None:
        self.model = model
        self.index = index

    @property
    def graph(self) -> ig.Graph:
        return self.model.graph

    @property
    def vertex(self) -> ig.Vertex:
        return self.graph.vs[self.index]

    @property
    def vertex_type(self) -> VertexType:
        return VertexType(self.vertex["type"])

    @property
    def ref(self) -> str:
        return self.vertex["ref"]

    @property
    def path(self) -> str:
        return self.vertex["path"]

    @property
    def data(self) -> dict:
        return self.model.data.get(self.path, {})

    @property
    def parent_vidx(self) -> int:
        return self.model.graph.es.find(_source=self.index, type_eq=EdgeType.part_of.name).target

    @property
    def parent_path(self) -> str:
        return self.model.graph.vs[self.parent_vidx]["path"]

    @property
    def parent(self) -> "ModelVertexView":
        return ModelVertexView(self.model, self.parent_vidx)

    def get_edges(self, mode: str, edge_type: Union[EdgeType, List[EdgeType]] = None) -> ig.EdgeSeq:
        selector = {}
        if edge_type is not None:
            if isinstance(edge_type, list):
                selector["type_in"] = [e.name for e in edge_type]
            else:
                selector["type_eq"] = edge_type.name

        if mode == "in":
            selector["_target"] = self.index
        elif mode == "out":
            selector["_source"] = self.index
        else:
            raise ValueError(f"Invalid mode: {mode}")

        return self.graph.es.select(**selector)

    @classmethod
    def from_path(cls, model: Model, path: str) -> "ModelVertexView":
        try:
            root_node = model.graph.vs.find(path_eq=path)
        except ValueError as ex:
            raise ValueError(f"Path {path} not found in model") from ex
        return cls(model, root_node.index)

    @classmethod
    def from_edges(cls, model: Model, mode: str, edges: EdgeIterable) -> List["ModelVertexView"]:
        if mode == "out":
            return [cls(model, e.target) for e in edges]
        elif mode == "in":
            return [cls(model, e.source) for e in edges]
        else:
            raise ValueError(f"Invalid mode: {mode}")

    def get_adjacents(self, mode: str, edge_type: Union[EdgeType, List]) -> List["ModelVertexView"]:
        edges = self.get_edges(mode, edge_type)
        return self.from_edges(self.model, mode, edges)

    def get_descendants(self, vertex_type: Union[VertexType, List]) -> List["ModelVertexView"]:
        if isinstance(vertex_type, VertexType):
            vertex_type = [vertex_type]
        vertex_type_names: List[str] = [v.name for v in vertex_type]

        type_matched_vids = {v.index for v in self.model.graph.vs.select(type_in=vertex_type_names)}
        part_of_view = self.model.get_graph_view([EdgeType.part_of])
        descendant_vids = set(part_of_view.subcomponent(self.index, mode="in"))
        return [ModelVertexView(self.model, vid) for vid in type_matched_vids & descendant_vids]

    @classmethod
    def from_view(cls, view: "ModelVertexView"):
        return cls(view.model, view.index)

def get_all_idx(model: Model, vertex_type: VertexType) -> List[int]:
    return model.graph.vs.select(type_eq=vertex_type.name)

def get_all_as(model: Model, vertex_type: VertexType, as_what) -> List[ModelVertexView]:
    return [as_what(model, v.index) for v in get_all_idx(model, vertex_type)]

def get_all(model: Model, vertex_type: VertexType) -> List[ModelVertexView]:
    return get_all_as(model, vertex_type, ModelVertexView)
