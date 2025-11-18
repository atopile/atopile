# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Protocol, Self, TypeGuard, cast, override

from ordered_set import OrderedSet
from typing_extensions import Callable, deprecated

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.libs.util import (
    KeyErrorNotFound,
    Tree,
    cast_assert,
    dataclass_as_kwargs,
    indented_container,
    not_none,
    zip_dicts_by_key,
)

# Exceptions ---------------------------------------------------------------------------


class FabLLException(Exception):
    pass


class InvalidState(FabLLException):
    pass


class TraitNotFound(FabLLException):
    pass


class NodeException(FabLLException):
    def __init__(self, node: "NodeT", message: str):
        self.node = node
        super().__init__(message)


class NodeNoParent(NodeException):
    def __init__(self, node: "NodeT"):
        super().__init__(node, "Node has no parent")


class ChildNotFound(NodeException):
    def __init__(self, node: "NodeT", identifier: str):
        super().__init__(node, f"Child with identifier {identifier} not found")


class PathNotResolvable(NodeException):
    def __init__(
        self,
        node: "NodeT",
        path: "list[str] | RefPath",
        error_node: "NodeT",
        error_identifier: str,
    ):
        # get all children of error_node
        try:
            children = error_node.get_children(
                direct_only=True, include_root=False, types=Node
            )
            children_str = "\n".join(f"- {c}" for c in children)
        except Exception as e:
            children_str = f"Error getting children of '{error_node}': {e}"

        super().__init__(
            node,
            f"Path {path} not resolvable from '{node}'.\n"
            f" No child found at '{error_node}' with identifier '{error_identifier}'.\n"
            f"Available children: {indented_container(children_str)}",
        )


# --------------------------------------------------------------------------------------

# Child Definitions --------------------------------------------------------------------


class PLACEHOLDER:
    def __repr__(self) -> str:
        return "<PLACEHOLDER>"


class Field:
    def __init__(self, identifier: str | None | PLACEHOLDER = PLACEHOLDER()):
        self.identifier: str | PLACEHOLDER = PLACEHOLDER()
        if not isinstance(identifier, PLACEHOLDER):
            self._set_identifier(identifier)

        self.locator: str | None | PLACEHOLDER = PLACEHOLDER()
        self._type_child = False

    def _set_identifier(self, identifier: str | None) -> None:
        if identifier is None:
            identifier = f"anon_{id(self):04x}"
        self.identifier = identifier

    def get_identifier(self) -> str:
        if isinstance(self.identifier, PLACEHOLDER):
            raise FabLLException("Identifier is not set")
        return not_none(self.identifier)

    def get_locator(self) -> str:
        if isinstance(self.locator, PLACEHOLDER):
            raise FabLLException("Locator is not set")
        if self.locator is None:
            raise FabLLException("Locator is None")
        return self.locator

    def _set_locator(self, locator: str | None) -> None:
        self.locator = locator
        if isinstance(self.identifier, PLACEHOLDER):
            self._set_identifier(locator)

    def put_on_type(self) -> Self:
        self._type_child = True
        return self

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(identifier={self.identifier},"
            f" locator={self.locator})"
        )


class ChildAccessor[T: NodeT](Protocol):
    """
    Protocol to trick python LSP into thinking there is a get() function on Stage 0 & 1
    We replace Stage 0 & 1 with Stage 2 during init, but the LSP doesn't know that
    So we have to pretend there is a get() function on Stage 0 & 1
    """

    def get(self) -> T: ...


class _ChildField[T: NodeT](Field, ChildAccessor[T]):
    """
    Stage 0: Child in a python class definition (pre-graph)
    """

    def __init__(
        self,
        nodetype: type[T],
        *,
        attributes: "NodeAttributes | None" = None,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
    ):
        self.nodetype = nodetype
        self._dependants: list["_ChildField[Any] | _EdgeField"] = []
        self._prepend_dependants: list["_ChildField[Any] | _EdgeField"] = []
        self.attributes = attributes
        super().__init__(identifier=identifier)

    def bind_to_parent_type[N: NodeT](
        self, t: "TypeNodeBoundTG[N, Any]"
    ) -> "InstanceChildBoundType[T]":
        return InstanceChildBoundType(nodetype=self.nodetype, t=t)

    def get(self) -> T:
        raise InvalidState(
            f"Called on {type(self).__name__} instead of "
            f"{type(InstanceChildBoundInstance).__name__}"
        ) from None

    def add_dependant(
        self,
        *dependant: "_ChildField[Any] | _EdgeField",
        identifier: str | None = None,
        before: bool = False,
    ):
        for d in dependant:
            if identifier is not None:
                d._set_locator(f"{identifier}_{id(d):04x}")
            else:
                d._set_locator(None)
            if before:
                self._prepend_dependants.append(d)
            else:
                self._dependants.append(d)

    def __repr__(self) -> str:
        return (
            f"ChildField(nodetype={self.nodetype.__qualname__},"
            f" identifier={self.identifier}, attributes={self.attributes})"
            f" dependants={indented_container(self._dependants)}, "
            f"prepend_dependants={indented_container(self._prepend_dependants)})"
            f" type_child={self._type_child})"
        )


class InstanceChildBoundType[T: NodeT](ChildAccessor[T]):
    """
    Stage 1: Child on a type node (type graph)
    """

    def __init__[N: NodeT](
        self,
        nodetype: type[T],
        t: "TypeNodeBoundTG[N, Any]",
        attributes: "NodeAttributes | None" = None,
        identifier: str | None | PLACEHOLDER = None,
    ) -> None:
        self.nodetype = nodetype
        self.t = t
        self.identifier = identifier
        self.attributes = attributes

        if nodetype.Attributes is not NodeAttributes and not isinstance(
            attributes, nodetype.Attributes
        ):
            raise FabLLException(
                f"Attributes mismatch: {nodetype.__name__} expects"
                f" {nodetype.Attributes} but got {type(attributes)}"
            )

    def _add_to_typegraph(self) -> None:
        identifier = self.identifier
        if isinstance(identifier, PLACEHOLDER):
            raise FabLLException("Placeholder identifier not allowed")

        self.t.tg.add_make_child(
            type_node=self.t.get_or_create_type(),
            child_type_node=self.nodetype.bind_typegraph(
                self.t.tg
            ).get_or_create_type(),
            identifier=identifier,
            node_attributes=self.attributes.to_node_attributes()
            if self.attributes is not None
            else None,
        )

    def get(self) -> T:
        raise InvalidState(
            f"Called on {type(self).__name__} instead of "
            f"{type(InstanceChildBoundInstance).__name__}"
        ) from None

    def cast_to_child_type(self, instance: graph.BoundNode) -> T:
        """
        Casts instance node to the child type
        """
        assert not isinstance(self.identifier, PLACEHOLDER), (
            "Bug: Needs to be set on setattr"
        )

        if self.identifier is None:
            raise FabLLException("Can only be called on named children")

        child_instance = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound

    def get_identifier(self) -> str | None:
        if isinstance(self.identifier, PLACEHOLDER):
            raise FabLLException("Identifier is not set")
        return self.identifier

    def bind_instance(self, instance: graph.BoundNode):
        return InstanceChildBoundInstance(
            nodetype=self.nodetype,
            identifier=self.get_identifier(),
            instance=instance,
        )


class InstanceChildBoundInstance[T: Node](ChildAccessor[T]):
    """
    Stage 2: Child on an instance (instance graph)
    """

    def __init__(
        self, nodetype: type[T], identifier: str | None, instance: graph.BoundNode
    ) -> None:
        self.nodetype = nodetype
        self.identifier = identifier
        self.instance = instance

    def get(self) -> T:
        """
        Return reference to py-wrapped child node
        """
        if self.identifier is None:
            raise FabLLException("Can only be called on named children")

        child_instance = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=self.instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound


class TypeChildBoundInstance[T: NodeT]:
    """
    Child of type
    Adds child directly to type node, will not create child in every instance
    Inherintly bound to the type node by definition, therefore no unbound version
    """

    def __init__[N: Node](
        self, nodetype: type[T], t: "TypeNodeBoundTG[N, Any]"
    ) -> None:
        # TODO: why so many nodetype references
        self.nodetype = nodetype
        self.t = t
        self.identifier: str = None  # type: ignore
        self._instance = t.get_or_create_type()

        if nodetype.Attributes is not NodeAttributes:
            raise FabLLException(
                f"Can't have Child with custom Attributes: {nodetype.__name__}"
            )

    def get(self) -> T:
        return self.get_unbound(instance=self._instance)

    def get_unbound(self, instance: graph.BoundNode) -> T:
        assert self.identifier is not None, "Bug: Needs to be set on setattr"

        child_instance = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound


RefPath = list[str | _ChildField[Any]]


SELF_OWNER_PLACEHOLDER: RefPath = [""]
"""
When creating trait, default reference path to self is [""].
"""


class _EdgeField(Field):
    def __init__(
        self,
        lhs: RefPath,
        rhs: RefPath,
        *,
        edge: fbrk.EdgeCreationAttributes,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
    ):
        super().__init__(identifier=identifier)
        for arg in [lhs, rhs]:
            for r in arg:
                if not isinstance(r, (_ChildField, str)):
                    raise FabLLException(
                        f"Only ChildFields and strings are allowed, got {type(r)}"
                    )
        self.lhs = lhs
        self.rhs = rhs
        self.edge = edge

    @staticmethod
    def _resolve_path(path: RefPath) -> list[str]:
        # TODO dont think we can assert here, raise FabLLException
        return [
            not_none(field.get_identifier())
            if isinstance(field, _ChildField)
            else field
            for field in path
        ]

    @staticmethod
    def _resolve_path_from_node(
        path: list[str] | RefPath, instance: graph.BoundNode
    ) -> graph.BoundNode:
        target = instance

        for segment in path:
            if not isinstance(segment, str):
                segment = segment.get_identifier()

            if segment == SELF_OWNER_PLACEHOLDER[0]:
                # keep target unchanged (self-reference)
                continue

            child = fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=target, child_identifier=segment
            )
            if child is None:
                raise PathNotResolvable(
                    node=Node.bind_instance(instance),
                    path=path,
                    error_node=Node.bind_instance(target),
                    error_identifier=segment,
                )
            target = child
        return target

    def lhs_resolved(self) -> list[str]:
        return self._resolve_path(self.lhs)

    def lhs_resolved_on_node(self, instance: graph.BoundNode) -> graph.BoundNode:
        return self._resolve_path_from_node(self.lhs_resolved(), instance)

    def rhs_resolved(self) -> list[str]:
        return self._resolve_path(self.rhs)

    def rhs_resolved_on_node(self, instance: graph.BoundNode) -> graph.BoundNode:
        return self._resolve_path_from_node(self.rhs_resolved(), instance)

    def __repr__(self) -> str:
        return (
            f"EdgeField(lhs={self.lhs_resolved()}, "
            f"rhs={self.rhs_resolved()}, "
            f"edge={self.edge})"
        )


def MakeEdge(
    lhs: RefPath,
    rhs: RefPath,
    *,
    edge: fbrk.EdgeCreationAttributes,
    identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
) -> "_EdgeField":
    return _EdgeField(
        lhs=lhs,
        rhs=rhs,
        edge=edge,
        identifier=identifier,
    )


class ListField(Field, list[Field]):
    def __init__(
        self,
        fields: list[Field],
        *,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
    ):
        list.__init__(self, fields)
        Field.__init__(self, identifier=identifier)

    def get_fields(self) -> list[Field]:
        locator = self.get_locator()
        for i, f in enumerate(self):
            f_id = f"{locator}[{i}]" if locator is not None else None
            f._set_locator(locator=f_id)
        return self


class EdgeFactoryAccessor(Protocol):
    def connect(self, target: "NodeT") -> None: ...
    def get_single(self) -> "NodeT": ...
    def get_all(self) -> list["NodeT"]: ...


class EdgeFactoryField(Field, EdgeFactoryAccessor):
    def __init__(
        self,
        edge_factory: Callable[[str], fbrk.EdgeCreationAttributes],
        *,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
        single: bool = False,
    ):
        super().__init__(identifier=identifier)
        self.edge_factory = edge_factory
        self.edge_attrs = self.edge_factory(self.get_identifier())
        self.single = single
        raise NotImplementedError("Not sure whether we want to keep this")

    def _connect(self, source: "NodeT", target: "NodeT"):
        source.connect(target, self.edge_attrs)

    def _get_single(self, source: "NodeT") -> "NodeT":
        return self._get_all(source)[0]

    def _get_all(self, source: "NodeT") -> list["NodeT"]:
        class Ctx:
            nodes: list[graph.BoundNode] = []

        source.instance.visit_edges_of_type(
            edge_type=self.edge_attrs.get_tid(),
            ctx=Ctx,
            f=lambda ctx, bound_edge: ctx.nodes.append(
                bound_edge.g().bind(node=bound_edge.edge().target())
            ),
        )
        return [Node.bind_instance(instance=node) for node in Ctx.nodes]

    def connect(self, target: "NodeT") -> None:
        raise FabLLException("Wrong stage")

    def get_single(self) -> "NodeT":
        raise FabLLException("Wrong stage")

    def get_all(self) -> list["NodeT"]:
        raise FabLLException("Wrong stage")


class InstanceBoundEdgeFactory(EdgeFactoryField):
    def __init__(self, instance: "NodeT", edge_factory_field: EdgeFactoryField):
        self.instance = instance
        self.edge_factory_field = edge_factory_field

    def connect(self, target: "NodeT") -> None:
        self.edge_factory_field._connect(source=self.instance, target=target)

    def get_single(self) -> "NodeT":
        return self.edge_factory_field._get_single(source=self.instance)

    def get_all(self) -> list["NodeT"]:
        return self.edge_factory_field._get_all(source=self.instance)


class Path:
    """
    Wrapper around Zig's graph.BFSPath object.

    This is a lightweight Python wrapper around a path object that lives in Zig memory.
    The underlying graph.BFSPath is automatically freed when this Python object
    is garbage collected.

    Access path information via properties that call back into Zig:
    - length: Number of edges in the path
    - start_node: Starting node (graph.BoundNode)
    - end_node: Ending node (graph.BoundNode)
    - edges: List of edges (creates Python objects, use sparingly for long paths)
    """

    def __init__(self, bfs_path: "graph.BFSPath"):  # type: ignore
        self._bfs_path = bfs_path

    @property
    def length(self) -> int:
        return self._bfs_path.get_length()

    @property
    def start_node(self) -> graph.BoundNode:
        return self._bfs_path.get_start_node()

    @property
    def end_node(self) -> graph.BoundNode:
        return self._bfs_path.get_end_node()

    @property
    def edges(self) -> list[graph.BoundEdge]:
        return self._bfs_path.get_edges()

    def get_start_node(self) -> "Node[Any]":
        return Node[Any].bind_instance(instance=self.start_node)

    def get_end_node(self) -> "Node[Any]":
        return Node[Any].bind_instance(instance=self.end_node)

    @staticmethod
    def from_connection(a: "Node[Any]", b: "Node[Any]") -> "Path | None":
        bfs_path = fbrk.EdgeInterfaceConnection.is_connected_to(
            source=a.instance, target=b.instance
        )
        path = Path(bfs_path)

        # this was a node on the previous implementation
        # basically we can do this more efficiently

        # FIXME: Notes: from the master of graphs:
        #  - iterate through all paths
        #  - make a helper function
        #    Path.get_subpaths(path: Path, search: SubpathSearch)
        #    e.g SubpathSearch = tuple[Callable[[fabll.ModuleInterface], bool], ...]
        #  - choose out of subpaths
        #    - be careful with LinkDirectDerived edges (if there is a faulting edge
        #      is derived, save it as candidate and only yield it if no other found)
        #    - choose first shortest

        end_node = path.end_node.node()
        if end_node.is_same(other=b.instance.node()):
            # TODO: support implied paths yielding multiple results again
            return path
        return None

    def __repr__(self) -> str:
        start = self.start_node
        end = self.end_node
        start_str = f"graph.BoundNode({start.node().get_uuid()})"
        end_str = f"graph.BoundNode({end.node().get_uuid()})"
        return f"Path(start={start_str}, end={end_str}, length={self.length})"


# --------------------------------------------------------------------------------------

LiteralT = float | int | str | bool
Literal = LiteralT  # Type alias for compatibility with generated types


class NodeMeta(type):
    """
    Handles _setattr_ on Node subclasses
    e.g `cls.resistance = ChildField(Resistor)`
    """

    @override
    def __setattr__(cls, name: str, value: Any, /) -> None:
        try:
            cls._handle_cls_attr(name, value)  # type: ignore
        except NameError:
            pass
        return super().__setattr__(name, value)


@dataclass(frozen=True)
class NodeAttributes:
    def __init_subclass__(cls) -> None:
        # TODO collect all fields (like dataclasses)
        # TODO check Attributes is dataclass and frozen
        # TODO check all values are literals
        pass

    @classmethod
    def of(cls: type[Self], node: "graph.BoundNode | NodeT") -> Self:
        if isinstance(node, Node):
            node = node.instance
        return cls(**node.node().get_dynamic_attrs())

    def to_dict(self) -> dict[str, Literal]:
        return dataclass_as_kwargs(self)

    def to_node_attributes(self) -> fbrk.NodeCreationAttributes | None:
        attrs = self.to_dict()
        if not attrs:
            return None
        return fbrk.NodeCreationAttributes.init(dynamic=attrs)


class Node[T: NodeAttributes = NodeAttributes](metaclass=NodeMeta):
    Attributes = NodeAttributes
    __fields: list[Field] = []
    # TODO do we need this?
    # _fields_bound_tg: dict[fbrk.TypeGraph, list[InstanceChildBoundType]] = {}

    def __init__(self, instance: graph.BoundNode) -> None:
        self.instance = instance

        # setup instance accessors
        # overrides fields in instance
        for field in type(self).__fields:
            if field.locator is None:
                continue
            if isinstance(field, _ChildField):
                child = InstanceChildBoundInstance(
                    nodetype=field.nodetype,
                    identifier=field.get_identifier(),
                    instance=instance,
                )
                setattr(self, field.get_locator(), child)
            if isinstance(field, ListField):
                list_attr = list[InstanceChildBoundInstance[Any]]()
                for nested_field in field.get_fields():
                    if isinstance(nested_field, _ChildField):
                        child = InstanceChildBoundInstance(
                            nodetype=nested_field.nodetype,
                            identifier=nested_field.get_identifier(),
                            instance=instance,
                        )
                        list_attr.append(child)
                setattr(self, field.get_locator(), list_attr)
            if isinstance(field, EdgeFactoryField):
                edge_factory_field = InstanceBoundEdgeFactory(
                    instance=self,
                    edge_factory_field=field,
                )
                setattr(self, field.get_locator(), edge_factory_field)

    def __init_subclass__(cls) -> None:
        # Ensure single-level inheritance: NodeType subclasses should not themselves
        # be subclassed further.
        if len(cls.__mro__) > len(Node.__mro__) + 1:
            # mro(): [Leaf, NodeType, object] is allowed (len==3),
            # deeper (len>3) is forbidden
            raise FabLLException(
                f"NodeType subclasses cannot themselves be subclassed "
                f"more than one level deep (found: {cls.__mro__})"
            )
        super().__init_subclass__()
        cls.__fields = []

        # Scan through class fields and add handle ChildFields
        # e.g ```python
        # class Resistor(Node):
        #     resistance = InstanceChildField(Parameter)
        # ```
        for name, child in vars(cls).items():
            cls._handle_cls_attr(name, child)

    @classmethod
    def _exec_field(
        cls, t: "TypeNodeBoundTG[Self, T]", field: Field, type_field: bool = False
    ) -> None:
        type_field = type_field or field._type_child
        if isinstance(field, _ChildField):
            identifier = field.get_identifier()
            for dependant in field._prepend_dependants:
                cls._exec_field(t=t, field=dependant, type_field=type_field)
            if type_field:
                child_nodetype: type[NodeT] = field.nodetype
                child_instance = child_nodetype.bind_typegraph(tg=t.tg).create_instance(
                    g=t.tg.get_graph_view(),
                    attributes=field.attributes,
                )
                fbrk.EdgeComposition.add_child(
                    bound_node=t.get_or_create_type(),
                    child=child_instance.instance.node(),
                    child_identifier=identifier,
                )
            else:
                mc = t.MakeChild(
                    nodetype=field.nodetype,
                    identifier=identifier,
                    attributes=field.attributes,
                )
                mc._add_to_typegraph()
            for dependant in field._dependants:
                cls._exec_field(t=t, field=dependant, type_field=type_field)
        elif isinstance(field, ListField):
            for nested_field in field.get_fields():
                cls._exec_field(t=t, field=nested_field, type_field=type_field)
        elif isinstance(field, _EdgeField):
            if type_field:
                type_node = t.get_or_create_type()
                edge_instance = field.edge.create_edge(
                    source=field.lhs_resolved_on_node(instance=type_node).node(),
                    target=field.rhs_resolved_on_node(instance=type_node).node(),
                )
                type_node.g().insert_edge(edge=edge_instance)
            else:
                t.MakeEdge(
                    lhs_reference_path=field.lhs_resolved(),
                    rhs_reference_path=field.rhs_resolved(),
                    edge=field.edge,
                )

    @classmethod
    def _create_type(cls, t: "TypeNodeBoundTG[Self, T]") -> None:
        # read out fields
        # construct typegraph
        for field in cls.__fields:
            cls._exec_field(t=t, field=field)
        # TODO
        # call stage1
        # call stage2
        pass

    @classmethod
    def _create_instance(cls, tg: fbrk.TypeGraph, g: graph.GraphView) -> Self:
        return cls.bind_typegraph(tg=tg).create_instance(g=g)

    @classmethod
    def _type_identifier(cls) -> str:
        return cls.__name__

    # type construction ----------------------------------------------------------------

    @classmethod
    def _handle_cls_attr(cls, name: str, value: Any) -> None:
        """
        Collect all fields (from class body and stage0 setattr)
        """
        # TODO the __fields is a hack
        if name.startswith("__") or name.endswith("__fields"):
            return
        if isinstance(value, Field):
            cls._add_field(locator=name, field=value)
        if (
            isinstance(value, list)
            and len(value)
            and all(isinstance(c, Field) for c in value)
        ):
            cls._add_field(locator=name, field=ListField(fields=value))

    @classmethod
    def _add_field(cls, locator: str, field: Field):
        # TODO check if identifier is already in use
        field._set_locator(locator=locator)
        cls.__fields.append(field)

    @classmethod
    def _add_instance_child(
        cls,
        child: InstanceChildBoundType,
    ) -> graph.BoundNode:
        tg = child.t.tg
        identifier = child.get_identifier()
        nodetype = child.nodetype

        child_type_node = nodetype.bind_typegraph(tg).get_or_create_type()
        return tg.add_make_child(
            type_node=cls.bind_typegraph(tg).get_or_create_type(),
            child_type_node=child_type_node,
            identifier=identifier,
        )

    @classmethod
    def _add_type_child(
        cls,
        child: TypeChildBoundInstance,
    ) -> graph.BoundNode:
        tg = child.t.tg
        identifier = child.identifier
        nodetype = child.nodetype

        child_node = nodetype.bind_typegraph(tg).create_instance(g=tg.get_graph_view())
        fbrk.EdgeComposition.add_child(
            bound_node=cls.bind_typegraph(tg).get_or_create_type(),
            child=child_node.instance.node(),
            child_identifier=identifier,
        )
        return child_node

    @classmethod
    def add_anon_child(
        cls,
        child: InstanceChildBoundType[Any],
    ):
        cls._add_instance_child(child)

    @classmethod
    def MakeChild(cls) -> _ChildField[Self]:
        return _ChildField(cls)

    def setup(self) -> Self:
        return self

    # bindings -------------------------------------------------------------------------
    @classmethod
    def bind_typegraph[N: NodeT](
        cls: type[N], tg: fbrk.TypeGraph
    ) -> "TypeNodeBoundTG[N, T]":
        return TypeNodeBoundTG[N, T](tg=tg, t=cls)

    @classmethod
    def bind_typegraph_from_instance[N: NodeT](
        cls: type[N], instance: graph.BoundNode
    ) -> "TypeNodeBoundTG[N, T]":
        return cls.bind_instance(instance=instance).bind_typegraph_from_self()

    @classmethod
    def bind_instance(cls, instance: graph.BoundNode) -> Self:
        return cls(instance=instance)

    # instance methods -----------------------------------------------------------------
    @deprecated("Use compose_with instead")
    def add(self, node: "NodeT"):
        # TODO node name
        self.connect(
            to=node,
            edge_attrs=fbrk.EdgeComposition.build(child_identifier=f"{id(node)}"),
        )

    def __setattr__(self, name: str, value: Any, /) -> None:
        if isinstance(value, Node) and not name.startswith("_"):
            self.connect(
                to=value, edge_attrs=fbrk.EdgeComposition.build(child_identifier=name)
            )
        return super().__setattr__(name, value)

    def attributes(self) -> T:
        Attributes = cast(type[T], type(self).Attributes)
        return Attributes.of(self.instance)

    def get_root_id(self) -> str:
        return f"0x{self.instance.node().get_uuid():X}"

    def get_name(self, accept_no_parent: bool = False) -> str:
        parent = self.get_parent()
        if parent is None:
            if accept_no_parent:
                return self.get_root_id()
            raise FabLLException("Node has no parent")
        return parent[1]

    def get_parent(self) -> tuple["Node", str] | None:
        parent_edge = fbrk.EdgeComposition.get_parent_edge(bound_node=self.instance)
        if parent_edge is None:
            return None
        parent_node = parent_edge.g().bind(
            node=fbrk.EdgeComposition.get_parent_node(edge=parent_edge.edge())
        )
        return (
            Node(instance=parent_node),
            fbrk.EdgeComposition.get_name(edge=parent_edge.edge()),
        )

    def get_parent_force(self) -> tuple["Node", str]:
        parent = self.get_parent()
        if parent is None:
            raise NodeNoParent(self)
        return parent

    # TODO get_parent_f, get_parent_of_type, get_parent_with_trait should be called
    # get_ancestor_...
    def get_parent_f(
        self,
        filter_expr: Callable[["NodeT"], bool],
        direct_only: bool = False,
        include_root: bool = True,
    ) -> "NodeT | None":
        parents = [p for p, _ in self.get_hierarchy()]
        if not include_root:
            parents = parents[:-1]
        if direct_only:
            parents = parents[-1:]
        for p in reversed(parents):
            if filter_expr(p):
                return p
        return None

    def get_parent_of_type[P: NodeT](
        self,
        parent_type: type[P],
        direct_only: bool = False,
        include_root: bool = True,
    ) -> P | None:
        return cast(
            P | None,
            self.get_parent_f(
                filter_expr=lambda p: p.isinstance(parent_type),
                direct_only=direct_only,
                include_root=include_root,
            ),
        )

    def get_parent_with_trait[TR: Node](
        self,
        trait: type[TR],
        include_self: bool = True,
    ) -> tuple["NodeT", TR]:
        hierarchy = self.get_hierarchy()
        if not include_self:
            hierarchy = hierarchy[:-1]
        for parent, _ in reversed(hierarchy):
            if parent.has_trait(trait):
                return parent, parent.get_trait(trait)
        raise KeyErrorNotFound(f"No parent with trait {trait} found")

    def nearest_common_ancestor(self, *others: "NodeT") -> tuple["NodeT", str] | None:
        """
        Finds the nearest common ancestor of the given nodes, or None if no common
        ancestor exists
        """
        nodes = [self, *others]
        if not nodes:
            return None

        # Get hierarchies for all nodes
        hierarchies = [list(n.get_hierarchy()) for n in nodes]
        min_length = min(len(h) for h in hierarchies)

        # Find the last matching ancestor
        last_match = None
        for i in range(min_length):
            ref_node, ref_name = hierarchies[0][i]
            if any(h[i][0] is not ref_node for h in hierarchies[1:]):
                break
            last_match = (ref_node, ref_name)

        return last_match

    # TODO: remove when get_children() is visitor
    def get_direct_children(self) -> list[tuple[str | None, "Node"]]:
        children: list[tuple[str | None, "Node"]] = []
        fbrk.EdgeComposition.visit_children_edges(
            bound_node=self.instance,
            ctx=children,
            f=lambda ctx, edge: ctx.append(
                (
                    edge.edge().name(),
                    Node(
                        instance=edge.g().bind(
                            node=fbrk.EdgeComposition.get_child_node(edge=edge.edge())
                        )
                    ),
                )
            ),
        )
        return children

    # TODO: convert to visitor pattern
    # TODO: implement in zig
    def get_children[C: Node](
        self,
        direct_only: bool,
        types: type[C] | tuple[type[C], ...],
        include_root: bool = False,
        f_filter: Callable[[C], bool] | None = None,
        sort: bool = True,
        required_trait: "type[NodeT] | tuple[type[NodeT], ...] | None" = None,
    ) -> OrderedSet[C]:
        # copied from old fabll
        type_tuple = types if isinstance(types, tuple) else (types,)
        trait_tuple: tuple[type[NodeT], ...] | None
        if required_trait is None:
            trait_tuple = None
        elif isinstance(required_trait, tuple):
            trait_tuple = required_trait
        else:
            trait_tuple = (required_trait,)

        result: list[C] = []

        def check(node: "NodeT") -> TypeGuard[C]:
            if not node.isinstance(*type_tuple):
                return False
            candidate = cast(C, node)
            if trait_tuple and not any(node.has_trait(trait) for trait in trait_tuple):
                return False
            if f_filter and not f_filter(candidate):
                return False
            return True

        if include_root and check(self):
            result.append(self)

        def _visit(node: "NodeT") -> None:
            for _name, child in node.get_direct_children():
                if check(child):
                    result.append(child)
                if not direct_only:
                    _visit(child)

        _visit(self)

        if sort:
            result.sort(key=lambda n: n.get_name(accept_no_parent=True))

        return OrderedSet(result)

    @deprecated("refactor callers and remove")
    def get_tree[C: Node](
        self,
        types: type[C] | tuple[type[C], ...],
        include_root: bool = True,
        f_filter: Callable[[C], bool] | None = None,
        sort: bool = True,
    ) -> Tree[C]:
        out = self.get_children(
            direct_only=True,
            types=types,
            f_filter=f_filter,
            sort=sort,
        )

        tree = Tree[C](
            {
                n: n.get_tree(
                    types=types,
                    include_root=False,
                    f_filter=f_filter,
                    sort=sort,
                )
                for n in out
            }
        )

        if include_root:
            if not isinstance(types, tuple):
                types = (types,)
            if self.isinstance(*types):
                if not f_filter or f_filter(cast(C, self)):
                    tree = Tree[C]({cast(C, self): tree})

        return tree

    # TODO: get rid of
    def iter_children_with_trait[TR: Node](
        self,
        trait: type[TR],
        include_self: bool = True,
    ) -> Iterator[tuple["NodeT", TR]]:
        for level in self.get_tree(
            types=Node, include_root=include_self
        ).iter_by_depth():
            yield from (
                (child, child.get_trait(trait))
                for child in level
                if child.has_trait(trait)
            )

    @property
    def tg(self) -> fbrk.TypeGraph:
        tg = fbrk.TypeGraph.of_instance(instance_node=self.instance)
        if tg is None:
            raise FabLLException(
                f"Failed to bind typegraph from instance: {self.instance}"
            )
        return tg

    def bind_typegraph_from_self(self) -> "TypeNodeBoundTG[Self, Any]":
        return self.bind_typegraph(tg=self.tg)

    def get_graph(self) -> fbrk.TypeGraph:
        return self.tg

    def get_type_node(self) -> graph.BoundNode | None:
        type_edge = fbrk.EdgeType.get_type_edge(bound_node=self.instance)
        if type_edge is None:
            return None
        return type_edge.g().bind(
            node=fbrk.EdgeType.get_type_node(edge=type_edge.edge())
        )

    def has_same_type_as(self, other: "NodeT") -> bool:
        this_type = self.get_type_node()
        if this_type is None:
            return False
        other_type = other.get_type_node()
        if other_type is None:
            return False
        return this_type.node().is_same(other=other_type.node())

    def get_type_name(self) -> str | None:
        type_node = self.get_type_node()
        if type_node is None:
            return None
        # TODO make zig api for this
        type_identifier = type_node.node().get_attr(key="type_identifier")
        if type_identifier is None:
            return None
        return cast_assert(str, type_identifier)

    def isinstance(self, *type_node: "type[NodeT]") -> bool:
        """
        Wildcard: Node
        """
        if Node in type_node:
            return True
        bound_type_nodes = [
            tn.bind_typegraph_from_instance(self.instance) for tn in type_node
        ]
        return any(tn.isinstance(self) for tn in bound_type_nodes)

    @classmethod
    def istypeof(cls, node: "NodeT") -> bool:
        return node.isinstance(cls)

    def get_hierarchy(self) -> list[tuple["Node", str]]:
        hierarchy: list[tuple["NodeT", str]] = []
        current: NodeT = self
        while True:
            if (parent_entry := current.get_parent()) is None:
                hierarchy.append((current, current.get_root_id()))
                break
            hierarchy.append((current, parent_entry[1]))
            current = parent_entry[0]

        hierarchy.reverse()
        return hierarchy

    def get_full_name(self, types: bool = False) -> str:
        parts: list[str] = []
        if (parent := self.get_parent()) is not None:
            parent_node, name = parent
            if not parent_node.no_include_parents_in_full_name:
                if (parent_full := parent_node.get_full_name(types=False)) is not None:
                    parts.append(parent_full)
            parts.append(name)
        elif not self.no_include_parents_in_full_name:
            parts.append(self.get_root_id())

        base = ".".join(filter(None, parts))
        if types:
            type_name = self.get_type_name() or "<NOTYPE>"
            return f"{base}|{type_name}" if base else type_name
        return base

    @property
    def no_include_parents_in_full_name(self) -> bool:
        return getattr(self, "_no_include_parents_in_full_name", False)

    @no_include_parents_in_full_name.setter
    def no_include_parents_in_full_name(self, value: bool) -> None:
        setattr(self, "_no_include_parents_in_full_name", value)

    def pretty_params(self, solver: Any = None) -> str:
        raise NotImplementedError("pretty_params is not implemented")

    def relative_address(self, root: "Node | None" = None) -> str:
        """Return the address from root to self"""
        if root is None:
            return self.get_full_name()

        root_name = root.get_full_name()
        self_name = self.get_full_name()
        if not self_name.startswith(root_name):
            raise ValueError(f"Root {root_name} is not an ancestor of {self_name}")

        return self_name.removeprefix(root_name + ".")

    def try_get_trait[TR: NodeT](self, trait: type[TR]) -> TR | None:
        impl = fbrk.Trait.try_get_trait(
            target=self.instance,
            trait_type=trait.bind_typegraph(self.tg).get_or_create_type(),
        )
        if impl is None:
            return None
        return trait.bind_instance(instance=impl)

    def get_trait[TR: Node](self, trait: type[TR]) -> TR:
        impl = self.try_get_trait(trait)
        if impl is None:
            raise TraitNotFound(f"No trait {trait} found")
        return impl

    def has_trait(self, trait: type["NodeT"]) -> bool:
        return self.try_get_trait(trait) is not None

    def zip_children_by_name_with[N: Node](
        self, other: "Node", sub_type: type[N]
    ) -> dict[str, tuple[N, N]]:
        nodes = self, other
        children = tuple(
            Node.with_names(
                n.get_children(direct_only=True, include_root=False, types=sub_type)
            )
            for n in nodes
        )
        return zip_dicts_by_key(*children)

    @staticmethod
    def with_names[N: Node](nodes: Iterable[N]) -> dict[str, N]:
        return {n.get_name(): n for n in nodes}

    def cast[N: NodeT](self, t: type[N], check: bool = True) -> N:
        if check and not self.isinstance(t):
            # TODO other exception
            raise FabLLException(f"Node {self} is not an instance of {t}")
        return t.bind_instance(self.instance)

    def try_cast[N: NodeT](self, t: type[N]) -> N | None:
        if not self.isinstance(t):
            return None
        return t.bind_instance(self.instance)

    def __repr__(self) -> str:
        return self.get_full_name()

    def __rich_repr__(self):
        yield self.get_full_name()

    __rich_repr__.angular = True

    def is_same(self, other: "NodeT | graph.Node | graph.BoundNode") -> bool:
        match other:
            case Node():
                other_node = other.instance.node()
            case graph.Node():
                other_node = other
            case graph.BoundNode():
                other_node = other.node()
            case _:
                raise TypeError(f"Invalid type: {type(other)}")

        return self.instance.node().is_same(other=other_node)

    def __eq__(self, other: "NodeT | graph.Node | graph.BoundNode") -> bool:
        return self.is_same(other)

    def __hash__(self) -> int:
        return self.instance.node().get_uuid()

    # instance edges -------------------------------------------------------------------
    def connect(self, to: "NodeT", edge_attrs: fbrk.EdgeCreationAttributes) -> None:
        """
        Low-level edge creation function.
        """
        edge_attrs.insert_edge(
            g=self.instance.g(), source=self.instance.node(), target=to.instance.node()
        )

    # traits ---------------------------------------------------------------------------
    def get_sibling_trait[TR: NodeT](self, trait: type[TR]) -> TR:
        """
        Only call this on traits!
        Convenience function to get a trait of the owner of this trait.
        """
        return Traits(self).get_obj_raw().get_trait(trait)

    def try_get_sibling_trait[TR: NodeT](self, trait: type[TR]) -> TR | None:
        """
        Only call this on traits!
        Convenience function to check if the owner of this trait has the given trait.
        """
        return Traits(self).get_obj_raw().try_get_trait(trait)


type NodeT = Node[Any]


class TypeNodeBoundTG[N: NodeT, A: NodeAttributes]:
    """
    (type[Node], fbrk.TypeGraph)
    Becomes available during stage 1 (typegraph creation)
    """

    def __init__(self, tg: fbrk.TypeGraph, t: type[N]) -> None:
        self.tg = tg
        self.t = t

    # node type methods ----------------------------------------------------------------
    def get_or_create_type(self) -> graph.BoundNode:
        """
        Builds Type node and returns it
        """
        tg = self.tg
        typenode = tg.get_type_by_name(type_identifier=self.t._type_identifier())
        if typenode is not None:
            return typenode
        typenode = tg.add_type(identifier=self.t._type_identifier())
        self.t._create_type(self)
        return typenode

    def create_instance(self, g: graph.GraphView, attributes: A | None = None) -> N:
        """
        Create a node instance for the given type node
        """
        # TODO spawn instance in specified graph g
        # TODO if attributes is not empty enforce not None

        typenode = self.get_or_create_type()
        attrs = attributes.to_dict() if attributes else {}
        instance = self.tg.instantiate_node(type_node=typenode, attributes=attrs)
        return self.t.bind_instance(instance=instance)

    def isinstance(self, instance: NodeT) -> bool:
        return fbrk.EdgeType.is_node_instance_of(
            bound_node=instance.instance,
            node_type=self.get_or_create_type().node(),
        )

    def get_instances(self, g: graph.GraphView | None = None) -> list[N]:
        type_node = self.get_or_create_type()
        if g is not None:
            type_node = g.bind(node=type_node.node())
        instances: list[graph.BoundNode] = []
        fbrk.EdgeType.visit_instance_edges(
            bound_node=type_node,
            ctx=instances,
            f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
        )
        return [self.t(instance=instance) for instance in instances]

    # node type agnostic ---------------------------------------------------------------
    @deprecated("Use Traits.get_implementors instead")
    def nodes_with_trait[T: NodeT](self, trait: type[T]) -> list[tuple["NodeT", T]]:
        return [
            (Traits(impl).get_obj_raw(), impl)
            for impl in Traits.get_implementors(trait=trait.bind_typegraph(self.tg))
        ]

    # TODO: Waiting for python to add support for type mapping
    def nodes_with_traits[*Ts](
        self, traits: tuple[*Ts]
    ):  # -> list[tuple[Node, tuple[*Ts]]]:
        # TODO
        raise NotImplementedError("nodes_with_traits is not implemented")

    @deprecated("Use get_instances instead")
    def nodes_of_type[N2: Node](self, t: type[N2]) -> set[N2]:
        return set(t.bind_typegraph(self.tg).get_instances())

    def nodes_of_types(self, t: tuple[type["Node"], ...]) -> set["Node"]:
        return {n for tn in t for n in tn.bind_typegraph(self.tg).get_instances()}

    # construction ---------------------------------------------------------------------
    def MakeChild[C: NodeT](
        self,
        nodetype: type[C],
        *,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
        attributes: NodeAttributes | None = None,
    ) -> InstanceChildBoundType[C]:
        return InstanceChildBoundType(
            nodetype=nodetype, t=self, identifier=identifier, attributes=attributes
        )

    # TODO
    # RefPath1 = list[str | InstanceChildBoundType[Any]]
    RefPath1 = list[str]

    def MakeEdge(
        self,
        *,
        lhs_reference_path: RefPath1,
        rhs_reference_path: RefPath1,
        edge: fbrk.EdgeCreationAttributes,
    ) -> None:
        tg = self.tg
        type_node = self.get_or_create_type()

        tg.add_make_link(
            type_node=type_node,
            lhs_reference_node=tg.add_reference(
                type_node=type_node,
                path=lhs_reference_path,
            ).node(),
            rhs_reference_node=tg.add_reference(
                type_node=type_node,
                path=rhs_reference_path,
            ).node(),
            edge_attributes=edge,
        )

    def check_if_instance_of_type_has_trait(self, trait: type[NodeT]) -> bool:
        children = Node.bind_instance(instance=self.get_or_create_type()).get_children(
            direct_only=True, types=MakeChild
        )
        bound_trait = trait.bind_typegraph(self.tg).get_or_create_type()
        for child in children:
            if child.get_child_type().node().is_same(other=bound_trait.node()):
                return True
        return False

    def try_get_trait[TR: NodeT](self, trait: type[TR]) -> TR | None:
        impl = fbrk.Trait.try_get_trait(
            target=self.get_or_create_type(),
            trait_type=trait.bind_typegraph(self.tg).get_or_create_type(),
        )
        if impl is None:
            return None
        return trait.bind_instance(instance=impl)

    def get_trait[TR: Node](self, trait: type[TR]) -> TR:
        impl = self.try_get_trait(trait)
        if impl is None:
            raise TraitNotFound(f"No trait {trait} found")
        return impl


# ------------------------------------------------------------


# TODO shouldnt this all be in ImplementsTrait?
class Traits:
    def __init__(self, node: NodeT):
        self.node = node

    @classmethod
    def bind(cls, node: NodeT) -> Self:
        return cls(node)

    def get_obj_raw(self) -> NodeT:
        return Node.bind_instance(
            instance=not_none(
                fbrk.EdgeTrait.get_owner_node_of(bound_node=self.node.instance)
            )
        )

    def get_obj[N: NodeT](self, t: type[N]) -> N:
        return self.get_obj_raw().cast(t)

    @staticmethod
    def add_to(node: NodeT, trait: NodeT) -> None:
        fbrk.Trait.add_trait_to(target=node.instance, trait_type=trait.instance)

    @staticmethod
    def create_and_add_instance_to[T: Node[Any]](node: Node[Any], trait: type[T]) -> T:
        trait_bound = trait.bind_typegraph_from_instance(
            node.instance
        ).get_or_create_type()
        trait_node = Node.bind_instance(instance=trait_bound)
        Traits.add_to(node=node, trait=trait_node)
        return node  # type: ignore

    @staticmethod
    def MakeEdge[T: _ChildField](
        child_field: T, owner: RefPath = SELF_OWNER_PLACEHOLDER
    ) -> T:
        out = child_field
        out.add_dependant(
            MakeEdge(
                owner,
                [child_field],
                edge=fbrk.EdgeTrait.build(),
            )
        )
        return out

    @staticmethod
    def get_implementors[T: NodeT](
        trait: TypeNodeBoundTG[T, Any],
        g: graph.GraphView | None = None,
    ) -> list[T]:
        return trait.get_instances(g=g)

    @staticmethod
    def get_implementor_objects(
        trait: TypeNodeBoundTG[Any, Any], g: graph.GraphView | None = None
    ) -> list[NodeT]:
        return [
            Traits(impl).get_obj_raw() for impl in Traits.get_implementors(trait, g=g)
        ]

    def get_trait_of_obj[T: NodeT](self, t: type[T]) -> T:
        return self.get_obj_raw().get_trait(t)

    def try_get_trait_of_obj[T: NodeT](self, t: type[T]) -> T | None:
        return self.get_obj_raw().try_get_trait(t)


class ImplementsTrait(Node):
    """
    Wrapper around zig trait.
    Matched automatically because of name.
    """


class ImplementsType(Node):
    """
    Wrapper around zig type.
    Matched automatically because of name.
    """


class MakeChild(Node):
    """
    Wrapper around zig make child.
    Matched automatically because of name.
    """

    def get_child_type(self) -> graph.BoundNode:
        return not_none(
            fbrk.EdgePointer.get_referenced_node_from_node(node=self.instance)
        )


class is_module(Node):
    """
    Replaces Module type.
    TODO: Will remove in the future.
    Exists for now as compatibility layer.
    specialization/retyping is removed and done in ast -> typegraph now

    Replacement guide:
    - creation: instead of inherit of Module -> inherit of Node + add is_module trait
    - usage instead of type check, trait check:
        - replace isinstance(node, Module) with node.has_trait(is_module)
        - replace get_children(types=(Module,)) with get_children_with_trait(is_module)
        - ...
    """

    _is_trait = Traits.MakeEdge(ImplementsTrait.MakeChild().put_on_type())

    def get_obj(self) -> NodeT:
        return Traits.get_obj_raw(Traits.bind(self))


class is_interface(Node):
    _is_trait = ImplementsTrait.MakeChild().put_on_type()

    def get_obj(self) -> NodeT:
        return Traits.get_obj_raw(Traits.bind(self))

    def connect_to(self, *others: "NodeT") -> None:
        self_node = self.get_obj()
        for other in others:
            fbrk.EdgeInterfaceConnection.connect(
                bn1=self_node.instance, bn2=other.instance
            )

    def connect_shallow_to(self, *others: "NodeT") -> None:
        self_node = self.get_obj()
        for other in others:
            fbrk.EdgeInterfaceConnection.connect_shallow(
                bn1=self_node.instance, bn2=other.instance
            )

    """
    group_into_buses() clusters the supplied electrical
    interfaces by their shared bus (electrical connectivity) so the exporter can treat
    every bus once; the result is a dict whose keys are the representative bus interfaces
    and whose values are the other Interfaces that belong to the same bus.
    """

    @staticmethod
    def group_into_buses(
        nodes: set["Node[Any]"],
    ) -> dict["Node[Any]", set["Node[Any]"]]:
        remaining = set(nodes)
        buses: dict["Node[Any]", set["Node[Any]"]] = {}

        while remaining:
            interface = remaining.pop()
            connected = set(
                interface.get_trait(is_interface)
                .get_connected(include_self=True)
                .keys()
            )
            buses[interface] = connected
            remaining.difference_update(connected)

        return buses

    def is_connected_to(self, other: "NodeT") -> bool:
        self_node = self.get_obj()
        bfs_path = fbrk.EdgeInterfaceConnection.is_connected_to(
            source=self_node.instance, target=other.instance
        )

        return bfs_path.get_end_node().node().is_same(other=other.instance.node())

    def get_connected(self, include_self: bool = False) -> dict["Node[Any]", Path]:
        self_node = self.get_obj()
        connected_nodes_map = fbrk.EdgeInterfaceConnection.get_connected(
            source=self_node.instance, include_self=include_self
        )
        return {
            Node[Any].bind_instance(instance=node): Path(bfs_path)
            for node, bfs_path in connected_nodes_map.items()
        }


# ------------------------------------------------------------
# TODO move parameter stuff into own file (better into zig)


# --------------------------------------------------------------------------------------
# TODO remove
# re-export graph.GraphView to be used from fabll namespace
Graph = fbrk.TypeGraph
# Node type aliases
Module = Node
type Module = Node


# Going to replace MIF usages
class NodeWithInterface(Node):
    _is_interface = is_interface.MakeChild()


IMPLIED_PATHS = False

# lib fields
rt_field = None
f_field = None
d_field = None
# Param stuff
p_field = None
Range = None
RangeWithGaps = None
Single = None
DiscreteSet = None
EmptySet = None
RelaxedQuantity = None
Expressions = None
Domains = None
Predicates = None

# --------------------------------------------------------------------------------------


def _make_graph_and_typegraph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_fabll_basic():
    @dataclass(frozen=True)
    class FileLocationAttributes(NodeAttributes):
        start_line: int
        start_column: int
        end_line: int
        end_column: int

    class FileLocation(Node[FileLocationAttributes]):
        Attributes = FileLocationAttributes

    class TestNodeWithoutAttr(Node):
        pass

    @dataclass(frozen=True)
    class SliceAttributes(NodeAttributes):
        start: int
        end: int
        step: int

    class Slice(Node[SliceAttributes]):
        Attributes = SliceAttributes
        tnwa = _ChildField(TestNodeWithoutAttr)

    class TestNodeWithChildren(Node):
        tnwa1 = _ChildField(TestNodeWithoutAttr)
        tnwa2 = _ChildField(TestNodeWithoutAttr)
        _edge = _EdgeField(
            lhs=[tnwa1],
            rhs=[tnwa2],
            edge=fbrk.EdgePointer.build(identifier=None, order=None),
        )

    g, tg = _make_graph_and_typegraph()
    fileloc = FileLocation.bind_typegraph(tg).create_instance(
        g=g,
        attributes=FileLocationAttributes(
            start_line=1,
            start_column=1,
            end_line=1,
            end_column=1,
        ),
    )

    print("fileloc.start_column:", fileloc.attributes().start_column)
    print("fileloc:", fileloc.attributes())

    tnwa = TestNodeWithoutAttr.bind_typegraph(tg).create_instance(g=g)
    print("tnwa:", tnwa.instance.node().get_dynamic_attrs())

    slice = Slice.bind_typegraph(tg).create_instance(
        g=g, attributes=SliceAttributes(start=1, end=1, step=1)
    )
    print("Slice:", slice.attributes())
    print("Slice.tnwa:", slice.tnwa.get().attributes())

    tnwc = TestNodeWithChildren.bind_typegraph(tg).create_instance(g=g)
    assert (
        not_none(
            fbrk.EdgePointer.get_referenced_node_from_node(
                node=tnwc.tnwa1.get().instance
            )
        )
        .node()
        .is_same(other=tnwc.tnwa2.get().instance.node())
    )

    tnwc_children = tnwc.get_children(direct_only=False, types=(TestNodeWithoutAttr,))
    assert len(tnwc_children) == 2
    assert tnwc_children[0].get_name() == "tnwa1"
    assert tnwc_children[1].get_name() == "tnwa2"
    print(tnwc_children[0].get_full_name())


def test_typegraph_of_type_and_instance_roundtrip():
    g, tg = _make_graph_and_typegraph()

    class Simple(Node):
        """Minimal node to exercise fbrk.TypeGraph helpers."""

        pass

    bound_simple = Simple.bind_typegraph(tg)
    type_node = bound_simple.get_or_create_type()

    tg_from_type = fbrk.TypeGraph.of_type(type_node=type_node)
    assert tg_from_type is not None
    rebound = tg_from_type.get_type_by_name(type_identifier=Simple._type_identifier())
    assert rebound is not None
    assert rebound.node().is_same(other=type_node.node())

    simple_instance = bound_simple.create_instance(g=g)
    tg_from_instance = fbrk.TypeGraph.of_instance(
        instance_node=simple_instance.instance
    )
    assert tg_from_instance is not None
    rebound_from_instance = tg_from_instance.get_type_by_name(
        type_identifier=Simple._type_identifier()
    )
    assert rebound_from_instance is not None
    assert rebound_from_instance.node().is_same(other=type_node.node())

    root_uuid = simple_instance.instance.node().get_uuid()
    assert simple_instance.get_root_id() == f"0x{root_uuid:X}"


def test_trait_mark_as_trait():
    g, tg = _make_graph_and_typegraph()

    class ExampleTrait(Node):
        _is_trait = ImplementsTrait.MakeChild().put_on_type()

    class ExampleNode(Node):
        example_trait = ExampleTrait.MakeChild()

    node = ExampleNode.bind_typegraph(tg).create_instance(g=g)
    assert node.try_get_trait(ExampleTrait) is not None


def test_set_basic():
    """Test basic Set functionality: append, as_list, as_set."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    # Create a Set and some elements
    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)
    elem3 = Element.bind_typegraph(tg).create_instance(g=g)

    # Test empty set
    assert len(set_node.as_list()) == 0
    assert len(set_node.as_set()) == 0

    # Test single append
    set_node.append(elem1)
    elems = set_node.as_list()
    assert len(elems) == 1
    assert elems[0].instance.node().is_same(other=elem1.instance.node())

    # Test multiple appends
    set_node.append(elem2, elem3)
    elems = set_node.as_list()
    assert len(elems) == 3
    assert elems[0].instance.node().is_same(other=elem1.instance.node())
    assert elems[1].instance.node().is_same(other=elem2.instance.node())
    assert elems[2].instance.node().is_same(other=elem3.instance.node())

    # Test as_set returns correct type and size
    elem_set = set_node.as_set()
    assert isinstance(elem_set, set)
    assert len(elem_set) == 3


def test_set_deduplication():
    """Test that Set correctly deduplicates elements by UUID."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)

    # Append elem1 multiple times
    set_node.append(elem1)
    set_node.append(elem1)
    set_node.append(elem1)

    # Should only have one element
    elems = set_node.as_list()
    assert len(elems) == 1
    assert elems[0].instance.node().is_same(other=elem1.instance.node())

    # Append elem2 and elem1 again
    set_node.append(elem2, elem1)
    elems = set_node.as_list()
    # Should still only have 2 unique elements
    assert len(elems) == 2
    assert elems[0].instance.node().is_same(other=elem1.instance.node())
    assert elems[1].instance.node().is_same(other=elem2.instance.node())


def test_set_order_preservation():
    """Test that Set preserves insertion order of unique elements."""

    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)
    elem3 = Element.bind_typegraph(tg).create_instance(g=g)

    # Append in specific order
    set_node.append(elem2)
    set_node.append(elem1)
    set_node.append(elem3)

    elems = set_node.as_list()
    assert len(elems) == 3
    # Order should be preserved: elem2, elem1, elem3
    assert elems[0].instance.node().is_same(other=elem2.instance.node())
    assert elems[1].instance.node().is_same(other=elem1.instance.node())
    assert elems[2].instance.node().is_same(other=elem3.instance.node())

    # Appending duplicates shouldn't change order
    set_node.append(elem1, elem2)
    elems = set_node.as_list()
    assert len(elems) == 3
    assert elems[0].instance.node().is_same(other=elem2.instance.node())
    assert elems[1].instance.node().is_same(other=elem1.instance.node())
    assert elems[2].instance.node().is_same(other=elem3.instance.node())


def test_set_chaining():
    """Test that Set.append returns self for method chaining."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore
    elem1 = Element.bind_typegraph(tg).create_instance(g=g)
    elem2 = Element.bind_typegraph(tg).create_instance(g=g)
    elem3 = Element.bind_typegraph(tg).create_instance(g=g)

    # Test method chaining
    result = set_node.append(elem1).append(elem2).append(elem3)

    # Result should be the same set_node
    assert result.instance.node().is_same(other=set_node.instance.node())

    # All elements should be in the set
    elems = set_node.as_list()
    assert len(elems) == 3


def test_type_children():
    import faebryk.library._F as F

    g, tg = _make_graph_and_typegraph()
    Resistor = F.Resistor.bind_typegraph(tg=tg)

    children = Node.bind_instance(Resistor.get_or_create_type()).get_children(
        direct_only=True,
        types=Node,
    )
    print(indented_container([c.get_full_name(types=True) for c in children]))


def test_resistor_instantiation():
    import faebryk.library._F as F

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    Resistor = F.Resistor.bind_typegraph(tg=tg)
    res_inst = Resistor.create_instance(g=g)
    assert Resistor.get_trait(F.has_usage_example)
    assert res_inst
    assert res_inst._type_identifier() == "Resistor"
    assert res_inst.unnamed[0].get().get_name() == "unnamed[0]"
    assert res_inst.resistance.get().get_name() == "resistance"
    assert res_inst.resistance.get().get_units().get_type_name() == "Ohm"
    assert res_inst.get_trait(fabll.is_module)
    electricals = (
        res_inst.get_trait(F.can_attach_to_footprint_symmetrically)
        .electricals_.get()
        .as_list()
    )
    assert electricals[0].get_name() == "unnamed[0]"
    assert electricals[1].get_name() == "unnamed[1]"
    assert (
        res_inst._is_pickable.get().get_param("resistance").get_name() == "resistance"
    )


def test_string_param():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    string_p = F.Parameters.StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    string_p.constrain_to_single(value="IG constrained")
    assert string_p.force_extract_literal().get_value() == "IG constrained"

    class ExampleStringParameter(fabll.Node):
        string_p_tg = F.Parameters.StringParameter.MakeChild()
        constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().force_extract_literal().get_value() == "TG constrained"


def test_boolean_param():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    boolean_p = F.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.constrain_to_single(value=True)
    assert boolean_p.force_extract_literal().get_value()

    class ExampleBooleanParameter(fabll.Node):
        boolean_p_tg = F.Parameters.BooleanParameter.MakeChild()
        constraint = F.Literals.Booleans.MakeChild_ConstrainToLiteral(
            [boolean_p_tg], True
        )

    ebp = ExampleBooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert ebp.boolean_p_tg.get().force_extract_literal().get_value()


def test_make_lit():
    import faebryk.library._F as F

    g, tg = _make_graph_and_typegraph()
    assert F.Literals.make_lit(tg, value=True).get_value()
    assert F.Literals.make_lit(tg, value=3).get_value() == 3
    assert F.Literals.make_lit(tg, value="test").get_value() == "test"


def test_kicad_footprint():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    _ = F.Pad.bind_typegraph(tg=tg).get_or_create_type()
    pad1 = F.Pad.bind_typegraph(tg=tg).create_instance(g=g)
    pad2 = F.Pad.bind_typegraph(tg=tg).create_instance(g=g)

    kicad_footprint = (
        F.has_kicad_footprint.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(
            kicad_identifier="libR_0402_1005Metric2",
            pinmap={pad1: "P1", pad2: "P2"},
        )
    )
    print(
        f"kicad_footprint.get_kicad_footprint():"
        f" {kicad_footprint.get_kicad_footprint()}"
    )
    print(f"kicad_footprint.get_pin_names(): {kicad_footprint.get_pin_names()}")


if __name__ == "__main__":
    import typer

    # typer.run(test_fabll_basic)

    # test_manual_resistor_def()

    # typer.run(test_resistor_instantiation)
    typer.run(test_make_lit)
