from typing import List, Optional, Tuple, Union, Any

import igraph as ig

from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.accessors import ModelVertexView

EdgeIterable = Union[ig.EdgeSeq, List[ig.Edge]]


class ModelVisitor:
    """
    This class is used to descend through the model.

    Subclass it and replace it's methods to make it do your bidding as it traverses the model.
    """

    # Probably don't touch these

    def __init__(self, model: Model) -> None:
        self.model = model
        self._stack: List[Tuple[Optional[ig.Edge], ModelVertexView]] = []

    @property
    def vertex_stack(self) -> List[ModelVertexView]:
        return [v for _, v in self._stack]

    def _do_visit(self, vertex: ModelVertexView) -> Any:
        """
        Execture a visit on the given vertex.
        """
        type_specific_method_name = f"visit_{vertex.vertex_type.name}"
        if hasattr(self, type_specific_method_name):
            return getattr(self, type_specific_method_name)(vertex)
        return self.visit(vertex)

    # Use these things publically

    def tour(self, vertex: ModelVertexView = None) -> Any:
        """
        Call this to start walking through the model.
        """
        if vertex is None:
            vertex = ModelVertexView(self.model, 0)
        self._stack.append((None, vertex))
        result = self._do_visit(vertex)
        self._stack.pop()
        return result

    def wander(self, vertex: ModelVertexView, mode: str, edge_type: Union[EdgeType, List[EdgeType]] = None, vertex_type: Union[VertexType, List[VertexType]] = None, return_verticie=False) -> Union[List[Any], Tuple[List[ModelVertexView], List[Any]]]:
        """
        Call this method to follow a specific link type through the model.
        """
        if vertex_type is not None and not isinstance(vertex_type, list):
            vertex_type = [vertex_type]

        verticies_visited = []
        results = []

        for edge in vertex.get_edges(edge_type=edge_type, mode=mode):
            if mode == "in":
                next = ModelVertexView(self.model, edge.source)
            else:
                next = ModelVertexView(self.model, edge.target)

            if vertex_type is not None and next.vertex_type not in vertex_type:
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

    def visit(self, vertex: ModelVertexView) -> Any:
        """
        Default visit method used if there's no specific method for the vertex type.

        Decend into the parts of that vertex.
        """
        return self.wander(vertex, edge_type=EdgeType.part_of, mode="in")
