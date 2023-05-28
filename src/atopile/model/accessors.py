from typing import List, Union

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
        return cls(model, model.graph.vs.find(path_eq=path).index)

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

    @classmethod
    def from_view(cls, view: "ModelVertexView"):
        return cls(view.model, view.index)

class ComponentVertexView(ModelVertexView):
    @property
    def vertex_type(self) -> VertexType:
        return VertexType.component

def get_all_idx(model: Model, vertex_type: VertexType) -> List[int]:
    return model.graph.vs.select(type_eq=vertex_type.name)

def get_all_as(model: Model, vertex_type: VertexType, as_what) -> List[ModelVertexView]:
    return [as_what(model, v.index) for v in get_all_idx(model, vertex_type)]

def get_all(model: Model, vertex_type: VertexType) -> List[ModelVertexView]:
    return get_all_as(model, vertex_type, ModelVertexView)
