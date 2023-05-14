from typing import List, Optional, Tuple, Union, Any

import igraph as ig

from atopile.model.model import EdgeType, Model, VertexType


class ModelVertex:
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
    def type(self) -> VertexType:
        return VertexType(self.vertex["type"])

    @property
    def ref(self) -> str:
        return self.vertex["ref"]

    @property
    def path(self) -> str:
        return self.vertex["path"]

    def get_edges(self, mode: str, edge_type: Union[EdgeType, List[EdgeType]] = None) -> List[ig.Edge]:
        if mode not in ["in", "out"]:
            raise ValueError(f"Invalid mode: {mode}")

        selector = {}
        if edge_type is not None:
            if isinstance(edge_type, list):
                selector["type_in"] = [e.name for e in edge_type]
            else:
                selector["type_eq"] = edge_type.name

        if mode == "in":
            selector["_target"] = self.index
        else:
            selector["_source"] = self.index

        return self.graph.es.select(**selector)

    @classmethod
    def from_path(cls, model: Model, path: str) -> "ModelVertex":
        return cls(model, model.graph.vs.find(path_eq=path).index)

class ModelVisitor:
    """
    This class is used to descend through the model.

    Subclass it and replace it's methods to make it do your bidding as it traverses the model.
    """

    # Probably don't touch these

    def __init__(self, model: Model) -> None:
        self.model = model
        self._stack: List[Tuple[Optional[ig.Edge], ModelVertex]] = []

    @property
    def vertex_stack(self) -> List[ModelVertex]:
        return [v for _, v in self._stack]

    def _do_visit(self, vertex: ModelVertex) -> Any:
        """
        Execture a visit on the given vertex.
        """
        type_specific_method_name = f"visit_{vertex.type.name}"
        if hasattr(self, type_specific_method_name):
            return getattr(self, type_specific_method_name)(vertex)
        return self.visit(vertex)

    # Use these things publically

    def tour(self, vertex: ModelVertex = None) -> Any:
        """
        Call this to start walking through the model.
        """
        if vertex is None:
            vertex = ModelVertex(self.model, 0)
        self._stack.append((None, vertex))
        result = self._do_visit(vertex)
        self._stack.pop()
        return result

    def wander(self, vertex: ModelVertex, mode: str, edge_type: Union[EdgeType, List[EdgeType]] = None, vertex_type: Union[VertexType, List[VertexType]] = None, return_verticie=False) -> Union[List[Any], Tuple[List[ModelVertex], List[Any]]]:
        """
        Call this method to follow a specific link type through the model.
        """
        if vertex_type is not None and not isinstance(vertex_type, list):
            vertex_type = [vertex_type]

        verticies_visited = []
        results = []

        for edge in vertex.get_edges(edge_type=edge_type, mode=mode):
            if mode == "in":
                next = ModelVertex(self.model, edge.source)
            else:
                next = ModelVertex(self.model, edge.target)

            if vertex_type is not None and next.type not in vertex_type:
                continue

            if (edge, next) in self._stack:
                raise RecursionError(f"Recursion detected: {edge} -> {next}")
            self._stack.append((edge, next))
            verticies_visited.append(next)
            results.append(self._do_visit(next))
            self._stack.pop()

        if return_verticie:
            return verticies_visited, results
        return results

    # Override these methods to do your bidding

    def visit(self, vertex: ModelVertex) -> Any:
        """
        Default visit method used if there's no specific method for the vertex type.

        Decend into the parts of that vertex.
        """
        return self.wander(vertex, edge_type=EdgeType.part_of, mode="in")
