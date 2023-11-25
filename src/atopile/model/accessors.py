import itertools
from typing import Any, Iterable, List, Tuple, Union

import igraph as ig

from atopile.model.model import EdgeType, Model, VertexType

EdgeIterable = Union[ig.EdgeSeq, List[ig.Edge]]


def mvvs_to_path(mvvs: List["ModelVertexView"]) -> str:
    if not mvvs:
        raise ValueError("Can't get path from empty list")

    if mvvs[0].vertex_type == VertexType.file:
        file_path = mvvs.pop(0).ref
    else:
        file_path = None

    module_path = ".".join(mvv.ref for mvv in mvvs) or None

    if file_path and module_path:
        return f"{file_path}:{module_path}"
    if file_path:
        return file_path
    if module_path:
        return module_path

    raise ValueError(f"Couldn't compute path from mvvs {[mvv.ref for mvv in mvvs]}")


class NodeNotFoundError(Exception):
    """
    Does what it says on the box.
    """


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

    @vertex_type.setter
    def vertex_type(self, value: VertexType) -> VertexType:
        self.vertex["type"] = value.name

    @property
    def ref(self) -> str:
        return self.vertex["ref"]

    @property
    def path(self) -> str:
        """
        Paths come in the form of: path/to/file.ato:module.inside.a.b.c
        """
        return self.vertex["path"]

    @property
    def file_path(self) -> str:
        return self.path.split(":")[0]

    @property
    def class_path(self) -> str:
        return self.path.split(":")[1]

    # TODO: remove this if the core model's working properly
    # @property
    # def path(self) -> str:
    #     path_as_mvvs: List[ModelVertexView] = self.get_ancestors()[::-1]
    #     # TODO: consider using URI format instead, it's probably far better designed
    #     return mvvs_to_path(path_as_mvvs)

    @property
    def data(self) -> dict:
        return self.model.data.setdefault(self.path, {})

    @property
    def parent_vidx(self) -> int:
        return self.model.graph.es.find(_source=self.index, type_eq=EdgeType.part_of.name).target

    @property
    def parent_path(self) -> str:
        return self.model.graph.vs[self.parent_vidx]["path"]

    @property
    def parent(self) -> "ModelVertexView":
        return ModelVertexView(self.model, self.parent_vidx)

    @property
    def instance_of(self) -> "ModelVertexView":
        try:
            class_vidx = self.model.graph.es.find(_source=self.index, type_eq=EdgeType.instance_of.name).target
        except ValueError:
            return None
        return ModelVertexView(self.model, class_vidx)

    @property
    def is_instance(self) -> bool:
        return self.instance_of is not None

    @property
    def superclass(self) -> "ModelVertexView":
        superclasses = self.get_adjacents("out", EdgeType.subclass_of)
        if len(superclasses) == 0:
            return None
        if len(superclasses) > 1:
            raise ValueError(f"Vertex {self.index} has multiple superclasses")
        return superclasses[0]

    @property
    def superclasses(self) -> Iterable["ModelVertexView"]:
        # got a little social climbing here, eh?
        superclass = self  # little white lie
        while superclass := superclass.superclass:
            yield superclass

    def i_am_an_instance_of(self, of: "ModelVertexView") -> bool:
        if self.is_class:
            return False
        if self.instance_of == of:
            return True
        return self.instance_of.is_instance(of)

    @property
    def is_class(self) -> bool:
        return not self.is_instance

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
            raise NodeNotFoundError(f"Path {path} not found in model") from ex
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

    def get_adjacents_with_edge_types(self, mode: str, edge_type: Union[EdgeType, List]) -> List[Tuple[EdgeType, "ModelVertexView"]]:
        edges = self.get_edges(mode, edge_type)
        return zip((EdgeType(e["type"]) for e in edges), self.from_edges(self.model, mode, edges))

    def get_descendants(self, vertex_type: Union[VertexType, List]) -> List["ModelVertexView"]:
        if isinstance(vertex_type, VertexType):
            vertex_type = [vertex_type]
        vertex_type_names: List[str] = [v.name for v in vertex_type]

        type_matched_vids = {v.index for v in self.model.graph.vs.select(type_in=vertex_type_names)}
        part_of_view = self.model.get_graph_view([EdgeType.part_of])
        descendant_vids = set(part_of_view.subcomponent(self.index, mode="in"))
        return [ModelVertexView(self.model, vid) for vid in type_matched_vids & descendant_vids if vid != self.index]

    def get_ancestor_ids(self) -> List["ModelVertexView"]:
        part_of_view = self.model.get_graph_view([EdgeType.part_of])
        return part_of_view.subcomponent(self.index, mode="out")

    def get_ancestors(self) -> List["ModelVertexView"]:
        return [ModelVertexView(self.model, vid) for vid in self.get_ancestor_ids()]

    @classmethod
    def from_view(cls, view: "ModelVertexView"):
        return cls(view.model, view.index)

    @classmethod
    def from_indicies(cls, model: Model, indicies: Iterable[int]) -> List["ModelVertexView"]:
        return [cls(model, i) for i in indicies]

    def relative_mvv_path(self, other: "ModelVertexView") -> List["ModelVertexView"]:
        if other.model != self.model:
            raise ValueError("Can't get relative path between verticies from different models")
        if self.index == other.index:
            raise ValueError("Can't get relative path between the same vertex")
        if self.index not in other.get_ancestor_ids():
            raise ValueError("Other vertex must be a child of this vertex")
        relative_idxs = [i for i in other.get_ancestor_ids() if i not in self.get_ancestor_ids()][::-1]
        return [ModelVertexView(self.model, i) for i in relative_idxs]

    def relative_path(self, other: "ModelVertexView") -> str:
        return mvvs_to_path([mvv for mvv in self.relative_mvv_path(other)])

    def get_data(self, path: Union[str, Tuple[str]], failure=None) -> Any:
        """
        Helper function to get data from an object's data dict.
        This is better than just accessing the data directly,
        because it will check superclasses for the requested data as well.
        """
        # forward declare data as None, so that if we don't find it / anything
        # useful we can still run the exception logic beyond the loop
        data = None

        # if we're an instance, we need to look in ourself, our class and then our supers
        # if we're a class, we need to look in ourself and our supers
        if self.is_instance:
            objs = itertools.chain([self, self.instance_of], self.instance_of.superclasses)
        else:
            objs = itertools.chain([self], self.superclasses)

        for obj in objs:
            try:
                if isinstance(path, str):
                    return obj.data[path]
                elif isinstance(path, tuple):
                    data = obj.data[path[0]]
                    break
            except KeyError:
                continue

        # find any child of data that matches the rest of the path
        # if the path is a string and we haven't already returned, we've failed and we skip this
        # if the path is a tuple, we try to find the rest of the path
        # if we didn't find any data in the first place, we'll hit the type error and break out of this loop
        if isinstance(path, tuple):
            for path_segment in path[1:]:
                try:
                    data = data[path_segment]
                except (KeyError, TypeError):
                    # break to exception logic
                    break
            else:
                # we finished the loop, so we've found our data - yay!
                return data

        # we've failed to find our data's key
        if isinstance(failure, Exception):
            raise failure

        try:
            if isinstance(failure(), Exception):
                raise failure
        except TypeError:
            pass

        return failure

    def get_all_data(self) -> dict:
        """
        Helper function to get all data from an object's data dict.
        This is better than just accessing the data directly,
        because it will check superclasses for data as well.
        """
        # if we're an instance, we need to look in ourself, our class and then our supers
        # if we're a class, we need to look in ourself and our supers
        if self.is_instance:
            objs = itertools.chain([self, self.instance_of], self.instance_of.superclasses)
        else:
            objs = itertools.chain([self], self.superclasses)

        # We store the fields we want to return
        fields_found = {}
        objs_list = list(objs)
        for obj in objs_list[::-1]:
            for field in obj.data:
                fields_found[field] = obj.data[field]

        return fields_found

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ModelVertexView):
            return False
        return self.model == o.model and self.index == o.index


def get_all_idx(model: Model, vertex_type: VertexType) -> List[int]:
    return model.graph.vs.select(type_eq=vertex_type.name)

def get_all_as(model: Model, vertex_type: VertexType, as_what) -> List[ModelVertexView]:
    return [as_what(model, v.index) for v in get_all_idx(model, vertex_type)]

def get_all(model: Model, vertex_type: VertexType) -> List[ModelVertexView]:
    return get_all_as(model, vertex_type, ModelVertexView)

def lowest_common_ancestor_with_ancestor_ids(verticies: Iterable[ModelVertexView]) -> tuple[ModelVertexView, Iterable[Iterable[ModelVertexView]]]:
    if len(verticies) == 0:
        return None, []
    if len(verticies) == 1:
        return verticies[0], []
    if len({v.model for v in verticies}) != 1:
        raise ValueError("All verticies must be from the same model")

    abs_ancestor_ids: List[List[int]] = [v.get_ancestor_ids()[::-1] for v in verticies]
    depths = [len(ids) for ids in abs_ancestor_ids]
    for depth in range(min(depths)):
        ids = [ids[depth] for ids in abs_ancestor_ids]
        if len(set(ids)) != 1:
            if depth == 0:
                raise ValueError("Verticies aren't in the same tree")
            common_ancestor = ModelVertexView(verticies[0].model, abs_ancestor_ids[0][depth - 1])
            rel_ancestor_ids = [abs_anc_ids[depth:-1] for abs_anc_ids in abs_ancestor_ids]
            return common_ancestor, rel_ancestor_ids

    friendly_verticies = ", ".join(v.path for v in verticies)
    raise ValueError(f"No common ancestor found for {friendly_verticies}")

def lowest_common_ancestor(verticies: Iterable[ModelVertexView]) -> ModelVertexView:
    return lowest_common_ancestor_with_ancestor_ids(verticies)[0]
