# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from dataclasses import dataclass
from enum import Enum
from textwrap import indent
from tkinter import N
from typing import Any, Iterable, Iterator, Protocol, Self, TypeGuard, cast, override

from ordered_set import OrderedSet
from typing_extensions import Callable, deprecated

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.nodebuilder import NodeCreationAttributes
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.faebryk.trait import Trait
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, GraphView
from faebryk.core.zig.gen.graph.graph import Node as GraphNode
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
    def __init__(self, node: "Node[Any]", message: str):
        self.node = node
        super().__init__(message)


class NodeNoParent(NodeException):
    def __init__(self, node: "Node[Any]"):
        super().__init__(node, "Node has no parent")


class ChildNotFound(NodeException):
    def __init__(self, node: "Node[Any]", identifier: str):
        super().__init__(node, f"Child with identifier {identifier} not found")


class PathNotResolvable(NodeException):
    def __init__(
        self,
        node: "Node[Any]",
        path: "list[str] | RefPath",
        error_node: "Node[Any]",
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


class ChildAccessor[T: Node[Any]](Protocol):
    """
    Protocol to trick python LSP into thinking there is a get() function on Stage 0 & 1
    We replace Stage 0 & 1 with Stage 2 during init, but the LSP doesn't know that
    So we have to pretend there is a get() function on Stage 0 & 1
    """

    def get(self) -> T: ...


class ChildField[T: Node[Any]](Field, ChildAccessor[T]):
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
        self._dependants: list["ChildField[Any] | EdgeField"] = []
        self._prepend_dependants: list["ChildField[Any] | EdgeField"] = []
        self.attributes = attributes
        super().__init__(identifier=identifier)

    def bind_to_parent_type[N: Node[Any]](
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
        *dependant: "ChildField[Any] | EdgeField",
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


class InstanceChildBoundType[T: Node[Any]](ChildAccessor[T]):
    """
    Stage 1: Child on a type node (type graph)
    """

    def __init__[N: Node[Any]](
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

    def cast_to_child_type(self, instance: BoundNode) -> T:
        """
        Casts instance node to the child type
        """
        assert not isinstance(self.identifier, PLACEHOLDER), (
            "Bug: Needs to be set on setattr"
        )

        if self.identifier is None:
            raise FabLLException("Can only be called on named children")

        child_instance = not_none(
            EdgeComposition.get_child_by_identifier(
                bound_node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound

    def get_identifier(self) -> str | None:
        if isinstance(self.identifier, PLACEHOLDER):
            raise FabLLException("Identifier is not set")
        return self.identifier

    def bind_instance(self, instance: BoundNode):
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
        self, nodetype: type[T], identifier: str | None, instance: BoundNode
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
            EdgeComposition.get_child_by_identifier(
                bound_node=self.instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound


class TypeChildBoundInstance[T: Node[Any]]:
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

    def get_unbound(self, instance: BoundNode) -> T:
        assert self.identifier is not None, "Bug: Needs to be set on setattr"

        child_instance = not_none(
            EdgeComposition.get_child_by_identifier(
                bound_node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound


RefPath = list[str | ChildField[Any]]


class EdgeField(Field):
    def __init__(
        self,
        lhs: RefPath,
        rhs: RefPath,
        *,
        edge: EdgeCreationAttributes,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
    ):
        super().__init__(identifier=identifier)
        for arg in [lhs, rhs]:
            for r in arg:
                if not isinstance(r, (ChildField, str)):
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
            not_none(field.get_identifier()) if isinstance(field, ChildField) else field
            for field in path
        ]

    @staticmethod
    def _resolve_path_from_node(
        path: list[str] | RefPath, instance: BoundNode
    ) -> BoundNode:
        target = instance

        for segment in path:
            if not isinstance(segment, str):
                segment = segment.get_identifier()
            child = EdgeComposition.get_child_by_identifier(
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

    def lhs_resolved_on_node(self, instance: BoundNode) -> BoundNode:
        return self._resolve_path_from_node(self.lhs_resolved(), instance)

    def rhs_resolved(self) -> list[str]:
        return self._resolve_path(self.rhs)

    def rhs_resolved_on_node(self, instance: BoundNode) -> BoundNode:
        return self._resolve_path_from_node(self.rhs_resolved(), instance)

    def __repr__(self) -> str:
        return (
            f"EdgeField(lhs={self.lhs_resolved()}, "
            f"rhs={self.rhs_resolved()}, "
            f"edge={self.edge})"
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
    def connect(self, target: "Node[Any]") -> None: ...
    def get_single(self) -> "Node[Any]": ...
    def get_all(self) -> list["Node[Any]"]: ...


class EdgeFactoryField(Field, EdgeFactoryAccessor):
    def __init__(
        self,
        edge_factory: Callable[[str], EdgeCreationAttributes],
        *,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
        single: bool = False,
    ):
        super().__init__(identifier=identifier)
        self.edge_factory = edge_factory
        self.edge_attrs = self.edge_factory(self.get_identifier())
        self.single = single
        raise NotImplementedError("Not sure whether we want to keep this")

    def _connect(self, source: "Node[Any]", target: "Node[Any]"):
        source.connect(target, self.edge_attrs)

    def _get_single(self, source: "Node[Any]") -> "Node[Any]":
        return self._get_all(source)[0]

    def _get_all(self, source: "Node[Any]") -> list["Node[Any]"]:
        class Ctx:
            nodes: list[BoundNode] = []

        source.instance.visit_edges_of_type(
            edge_type=self.edge_attrs.get_tid(),
            ctx=Ctx,
            f=lambda ctx, bound_edge: ctx.nodes.append(
                bound_edge.g().bind(node=bound_edge.edge().target())
            ),
        )
        return [Node.bind_instance(instance=node) for node in Ctx.nodes]

    def connect(self, target: "Node[Any]") -> None:
        raise FabLLException("Wrong stage")

    def get_single(self) -> "Node[Any]":
        raise FabLLException("Wrong stage")

    def get_all(self) -> list["Node[Any]"]:
        raise FabLLException("Wrong stage")


class InstanceBoundEdgeFactory(EdgeFactoryField):
    def __init__(self, instance: "Node[Any]", edge_factory_field: EdgeFactoryField):
        self.instance = instance
        self.edge_factory_field = edge_factory_field

    def connect(self, target: "Node[Any]") -> None:
        self.edge_factory_field._connect(source=self.instance, target=target)

    def get_single(self) -> "Node[Any]":
        return self.edge_factory_field._get_single(source=self.instance)

    def get_all(self) -> list["Node[Any]"]:
        return self.edge_factory_field._get_all(source=self.instance)


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
    def of(cls: type[Self], node: "BoundNode | Node[Any]") -> Self:
        if isinstance(node, Node):
            node = node.instance
        return cls(**node.node().get_dynamic_attrs())

    def to_dict(self) -> dict[str, Literal]:
        return dataclass_as_kwargs(self)

    def to_node_attributes(self) -> NodeCreationAttributes | None:
        attrs = self.to_dict()
        if not attrs:
            return None
        return NodeCreationAttributes.init(dynamic=attrs)


class Node[T: NodeAttributes = NodeAttributes](metaclass=NodeMeta):
    Attributes = NodeAttributes
    __fields: list[Field] = []
    # TODO do we need this?
    # _fields_bound_tg: dict[TypeGraph, list[InstanceChildBoundType]] = {}

    def __init__(self, instance: BoundNode) -> None:
        self.instance = instance

        # setup instance accessors
        # overrides fields in instance
        for field in type(self).__fields:
            if field.locator is None:
                continue
            if isinstance(field, ChildField):
                child = InstanceChildBoundInstance(
                    nodetype=field.nodetype,
                    identifier=field.get_identifier(),
                    instance=instance,
                )
                setattr(self, field.get_locator(), child)
            if isinstance(field, ListField):
                list_attr = list[InstanceChildBoundInstance[Any]]()
                for nested_field in field.get_fields():
                    if isinstance(nested_field, ChildField):
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
        if isinstance(field, ChildField):
            identifier = field.get_identifier()
            for dependant in field._prepend_dependants:
                cls._exec_field(t=t, field=dependant, type_field=type_field)
            if type_field:
                child_nodetype: type[Node[Any]] = field.nodetype
                child_instance = child_nodetype.bind_typegraph(tg=t.tg).create_instance(
                    g=t.tg.get_graph_view(),
                    attributes=field.attributes,
                )
                EdgeComposition.add_child(
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
        elif isinstance(field, EdgeField):
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
    def _create_instance(cls, tg: TypeGraph, g: GraphView) -> Self:
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
    ) -> BoundNode:
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
    ) -> BoundNode:
        tg = child.t.tg
        identifier = child.identifier
        nodetype = child.nodetype

        child_node = nodetype.bind_typegraph(tg).create_instance(g=tg.get_graph_view())
        EdgeComposition.add_child(
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
    def MakeChild(cls) -> ChildField[Any]:
        return ChildField(cls)

    # bindings -------------------------------------------------------------------------
    @classmethod
    def bind_typegraph[N: Node[Any]](
        cls: type[N], tg: TypeGraph
    ) -> "TypeNodeBoundTG[N, T]":
        return TypeNodeBoundTG[N, T](tg=tg, t=cls)

    @classmethod
    def bind_typegraph_from_instance[N: Node[Any]](
        cls: type[N], instance: BoundNode
    ) -> "TypeNodeBoundTG[N, T]":
        return cls.bind_instance(instance=instance).bind_typegraph_from_self()

    @classmethod
    def bind_instance(cls, instance: BoundNode) -> Self:
        return cls(instance=instance)

    # instance methods -----------------------------------------------------------------
    @deprecated("Use compose_with instead")
    def add(self, node: "Node[Any]"):
        # TODO node name
        self.connect(
            to=node, edge_attrs=EdgeComposition.build(child_identifier=f"{id(node)}")
        )

    def __setattr__(self, name: str, value: Any, /) -> None:
        if isinstance(value, Node) and not name.startswith("_"):
            self.connect(
                to=value, edge_attrs=EdgeComposition.build(child_identifier=name)
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
        parent_edge = EdgeComposition.get_parent_edge(bound_node=self.instance)
        if parent_edge is None:
            return None
        parent_node = parent_edge.g().bind(
            node=EdgeComposition.get_parent_node(edge=parent_edge.edge())
        )
        return (
            Node(instance=parent_node),
            EdgeComposition.get_name(edge=parent_edge.edge()),
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
        filter_expr: Callable[["Node[Any]"], bool],
        direct_only: bool = False,
        include_root: bool = True,
    ) -> "Node[Any] | None":
        parents = [p for p, _ in self.get_hierarchy()]
        if not include_root:
            parents = parents[:-1]
        if direct_only:
            parents = parents[-1:]
        for p in reversed(parents):
            if filter_expr(p):
                return p
        return None

    def get_parent_of_type[P: Node[Any]](
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
    ) -> tuple["Node[Any]", TR]:
        hierarchy = self.get_hierarchy()
        if not include_self:
            hierarchy = hierarchy[:-1]
        for parent, _ in reversed(hierarchy):
            if parent.has_trait(trait):
                return parent, parent.get_trait(trait)
        raise KeyErrorNotFound(f"No parent with trait {trait} found")

    def nearest_common_ancestor(
        self, *others: "Node[Any]"
    ) -> tuple["Node[Any]", str] | None:
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
        EdgeComposition.visit_children_edges(
            bound_node=self.instance,
            ctx=children,
            f=lambda ctx, edge: ctx.append(
                (
                    edge.edge().name(),
                    Node(
                        instance=edge.g().bind(
                            node=EdgeComposition.get_child_node(edge=edge.edge())
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
        required_trait: "type[Node[Any]] | None" = None,
    ) -> OrderedSet[C]:
        # copied from old fabll
        type_tuple = types if isinstance(types, tuple) else (types,)

        result: list[C] = []

        def check(node: "Node[Any]") -> TypeGuard[C]:
            if not node.isinstance(*type_tuple):
                return False
            candidate = cast(C, node)
            if required_trait and not node.has_trait(required_trait):
                return False
            if f_filter and not f_filter(candidate):
                return False
            return True

        if include_root and check(self):
            result.append(self)

        def _visit(node: "Node[Any]") -> None:
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
    ) -> Iterator[tuple["Node[Any]", TR]]:
        for level in self.get_tree(
            types=Node, include_root=include_self
        ).iter_by_depth():
            yield from (
                (child, child.get_trait(trait))
                for child in level
                if child.has_trait(trait)
            )

    @property
    def tg(self) -> TypeGraph:
        tg = TypeGraph.of_instance(instance_node=self.instance)
        if tg is None:
            raise FabLLException(
                f"Failed to bind typegraph from instance: {self.instance}"
            )
        return tg

    def bind_typegraph_from_self(self) -> "TypeNodeBoundTG[Self, Any]":
        return self.bind_typegraph(tg=self.tg)

    def get_graph(self) -> TypeGraph:
        return self.tg

    def get_type_node(self) -> BoundNode | None:
        type_edge = EdgeType.get_type_edge(bound_node=self.instance)
        if type_edge is None:
            return None
        return type_edge.g().bind(node=EdgeType.get_type_node(edge=type_edge.edge()))

    def get_type_name(self) -> str | None:
        type_node = self.get_type_node()
        if type_node is None:
            return None
        # TODO make zig api for this
        type_identifier = type_node.node().get_attr(key="type_identifier")
        if type_identifier is None:
            return None
        return cast_assert(str, type_identifier)

    def isinstance(self, *type_node: "type[Node]") -> bool:
        """
        Wildcard: Node
        """
        if Node in type_node:
            return True
        bound_type_nodes = [
            tn.bind_typegraph_from_instance(self.instance) for tn in type_node
        ]
        return any(tn.isinstance(self) for tn in bound_type_nodes)

    def get_hierarchy(self) -> list[tuple["Node", str]]:
        hierarchy: list[tuple["Node[Any]", str]] = []
        current: Node[Any] = self
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

    def try_get_trait[TR: Node[Any]](self, trait: type[TR]) -> TR | None:
        impl = Trait.try_get_trait(
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

    def has_trait(self, trait: type["Node[Any]"]) -> bool:
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

    def cast[N: Node[Any]](self, t: type[N], check: bool = True) -> N:
        if check and not self.isinstance(t):
            # TODO other exception
            raise FabLLException(f"Node {self} is not an instance of {t}")
        return t.bind_instance(self.instance)

    def __repr__(self) -> str:
        return self.get_full_name()

    def __rich_repr__(self):
        yield self.get_full_name()

    __rich_repr__.angular = True

    def __eq__(self, other: object) -> bool:
        match other:
            case Node():
                other_node = other.instance.node()
            case GraphNode():
                other_node = other
            case BoundNode():
                other_node = other.node()
            case _:
                return False

        return self.instance.node().is_same(other=other_node)

    def __hash__(self) -> int:
        return self.instance.node().get_uuid()

    # instance edges -------------------------------------------------------------------
    def connect(self, to: "Node[Any]", edge_attrs: EdgeCreationAttributes) -> None:
        """
        Low-level edge creation function.
        """
        edge_attrs.insert_edge(
            g=self.instance.g(), source=self.instance.node(), target=to.instance.node()
        )


class TypeNodeBoundTG[N: Node[Any], A: NodeAttributes]:
    """
    (type[Node], TypeGraph)
    Becomes available during stage 1 (typegraph creation)
    """

    def __init__(self, tg: TypeGraph, t: type[N]) -> None:
        self.tg = tg
        self.t = t

    # node type methods ----------------------------------------------------------------
    def get_or_create_type(self) -> BoundNode:
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

    def create_instance(self, g: GraphView, attributes: A | None = None) -> N:
        """
        Create a node instance for the given type node
        """
        # TODO spawn instance in specified graph g
        # TODO if attributes is not empty enforce not None

        typenode = self.get_or_create_type()
        attrs = attributes.to_dict() if attributes else {}
        instance = self.tg.instantiate_node(type_node=typenode, attributes=attrs)
        return self.t.bind_instance(instance=instance)

    def isinstance(self, instance: Node[Any]) -> bool:
        return EdgeType.is_node_instance_of(
            bound_node=instance.instance,
            node_type=self.get_or_create_type().node(),
        )

    def get_instances(self) -> list[N]:
        type_node = self.get_or_create_type()
        instances: list[BoundNode] = []
        EdgeType.visit_instance_edges(
            bound_node=type_node,
            ctx=instances,
            f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
        )
        return [self.t(instance=instance) for instance in instances]

    # node type agnostic ---------------------------------------------------------------
    def nodes_with_trait[T: Node[Any]](
        self, trait: type[T]
    ) -> list[tuple["Node[Any]", T]]:
        impls = trait.bind_typegraph(self.tg).get_instances()
        return [(p[0], impl) for impl in impls if (p := impl.get_parent()) is not None]

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
    def MakeChild[C: Node[Any]](
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
        edge: EdgeCreationAttributes,
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


# ------------------------------------------------------------


class Traits:
    def __init__(self, node: Node[Any]):
        self.node = node

    @classmethod
    def bind(cls, node: Node[Any]) -> Self:
        return cls(node)

    def get_obj_raw(self) -> Node[Any]:
        return self.node.get_parent_force()[0]

    def get_obj[N: Node[Any]](self, t: type[N]) -> N:
        return self.get_obj_raw().cast(t)

    @staticmethod
    def add_to(node: Node[Any], trait: Node[Any]) -> None:
        Trait.add_trait_to(target=node.instance, trait_type=trait.instance)


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

    _is_trait = ImplementsTrait.MakeChild().put_on_type()

    def get_obj(self) -> Node[Any]:
        return Traits.get_obj_raw(Traits.bind(self))


class is_interface(Node):
    _is_trait = ImplementsTrait.MakeChild().put_on_type()

    def get_obj(self) -> Node[Any]:
        return Traits.get_obj_raw(Traits.bind(self))

    def connect_to(self, *others: "Node[Any]") -> None:
        self_node = self.get_obj()
        for other in others:
            EdgeInterfaceConnection.connect(bn1=self_node.instance, bn2=other.instance)

    def connect_shallow_to(self, *others: "Node[Any]") -> None:
        self_node = self.get_obj()
        for other in others:
            EdgeInterfaceConnection.connect_shallow(
                bn1=self_node.instance, bn2=other.instance
            )

    def is_connected_to(self, other: "Node[Any]") -> bool:
        self_node = self.get_obj()
        path = EdgeInterfaceConnection.is_connected_to(
            source=self_node.instance, target=other.instance
        )
        return len(path) > 0

    def get_connected(self) -> set["Node[Any]"]:
        self_node = self.get_obj()
        connected_nodes = EdgeInterfaceConnection.get_connected(
            source=self_node.instance
        )
        return {Node[Any].bind_instance(instance=node) for node in connected_nodes}


# ------------------------------------------------------------
# TODO move parameter stuff into own file (better into zig)


class Parameter(Node):
    # TODO consider making a NumericParameter
    domain = ChildField(Node)

    def constrain_to_literal(self, g: GraphView, value: LiteralT) -> None:
        node = self.instance
        tg = not_none(TypeGraph.of_instance(instance_node=node))
        lit = LiteralNode.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=LiteralNodeAttributes(value=value)
        )
        from faebryk.library.Expressions import Is

        Is.bind_typegraph(tg=tg).create_instance(g=g).setup(
            operands=[self, lit], constrain=True
        )

    @classmethod
    def MakeChild_Numeric(cls, unit: type[Node[Any]]) -> ChildField[Any]:
        out = ChildField(Parameter)
        unit_instance = ChildField(unit, identifier=None)
        out.add_dependant(unit_instance)
        out.add_dependant(
            EdgeField(
                [out],
                [unit_instance],
                edge=EdgePointer.build(identifier="unit", order=None),
            )
        )
        return out

    @classmethod
    def MakeChild_String(cls) -> ChildField["Parameter"]:
        pass

    @classmethod
    def MakeChild_Enum(cls, enum_t: type[Enum]) -> ChildField["Parameter"]:
        # TODO: representation of enum values
        pass

    def try_extract_constrained_literal(self) -> LiteralT | None:
        # TODO: solver? `only_proven=True` parameter?
        node = self.instance

        if (
            inbound_expr_edge := EdgeOperand.get_expression_edge(bound_node=node)
        ) is None:
            return None

        expr = inbound_expr_edge.g().bind(node=inbound_expr_edge.edge().source())

        class Ctx:
            lit: LiteralNode | None = None

        def visit(ctx: type[Ctx], edge: BoundEdge) -> None:
            operand = Node[Any].bind_instance(edge.g().bind(node=edge.edge().target()))
            tg = not_none(TypeGraph.of_instance(instance_node=operand.instance))
            if LiteralNode.bind_typegraph(tg=tg).isinstance(instance=operand):
                ctx.lit = LiteralNode.bind_instance(operand.instance)

        EdgeOperand.visit_operand_edges(bound_node=expr, ctx=Ctx, f=visit)

        if Ctx.lit is None:
            return None
        return LiteralNode.Attributes.of(node=Ctx.lit.instance).value

    def force_extract_literal[T: LiteralT](self, t: type[T]) -> T:
        lit = self.try_extract_constrained_literal()
        if lit is None:
            raise FabLLException(f"Parameter {self} has no literal")
        if not isinstance(lit, t):
            raise FabLLException(f"Parameter {self} has no literal of type {t}")
        return lit


@dataclass(frozen=True)
class LiteralNodeAttributes(NodeAttributes):
    value: Literal


class LiteralNode(Node[LiteralNodeAttributes]):
    Attributes = LiteralNodeAttributes

    @classmethod
    def MakeChild(cls, value: LiteralT) -> ChildField[Any]:
        return ChildField(cls, attributes=LiteralNodeAttributes(value=value))

    def get_value(self) -> LiteralT:
        return self.instance.node().get_dynamic_attrs().get("value", "")


# --------------------------------------------------------------------------------------
# TODO remove
# re-export GraphView to be used from fabll namespace
Graph = TypeGraph
# Node type aliases
Module = Node


# Going to replace MIF usages
class GenericNodeWithInterface(Node):
    _is_interface = is_interface.MakeChild()


ModuleInterface = GenericNodeWithInterface
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
    g = GraphView.create()
    tg = TypeGraph.create(g=g)
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
        tnwa = ChildField(TestNodeWithoutAttr)

    class TestNodeWithChildren(Node):
        tnwa1 = ChildField(TestNodeWithoutAttr)
        tnwa2 = ChildField(TestNodeWithoutAttr)
        _edge = EdgeField(
            lhs=[tnwa1],
            rhs=[tnwa2],
            edge=EdgePointer.build(identifier=None, order=None),
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
            EdgePointer.get_referenced_node_from_node(node=tnwc.tnwa1.get().instance)
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
        """Minimal node to exercise TypeGraph helpers."""

        pass

    bound_simple = Simple.bind_typegraph(tg)
    type_node = bound_simple.get_or_create_type()

    tg_from_type = TypeGraph.of_type(type_node=type_node)
    assert tg_from_type is not None
    rebound = tg_from_type.get_type_by_name(type_identifier=Simple._type_identifier())
    assert rebound is not None
    assert rebound.node().is_same(other=type_node.node())

    simple_instance = bound_simple.create_instance(g=g)
    tg_from_instance = TypeGraph.of_instance(instance_node=simple_instance.instance)
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


def test_manual_resistor_def():
    import faebryk.library._F as F

    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # create electrical type node and insert into type graph
    _ = F.Electrical.bind_typegraph(tg=tg).get_or_create_type()

    # create resistor type node and insert into type graph
    # add make child nodes for p1 and p2, insert into type graph
    Resistor = F.Resistor.bind_typegraph(tg=tg)

    resistor_instance = Resistor.create_instance(g=g)
    assert resistor_instance
    print("resistor_instance:", resistor_instance.instance.node().get_dynamic_attrs())
    print(resistor_instance._type_identifier())

    # Electrical make child
    p1 = EdgeComposition.get_child_by_identifier(
        bound_node=resistor_instance.instance, child_identifier="unnamed[0]"
    )
    assert p1 is not None
    p1_fab = resistor_instance.unnamed[0].get()
    assert p1_fab.instance.node().is_same(other=p1.node())
    print("p1:", p1)

    # unconstrained Parameter make child
    resistance = EdgeComposition.get_child_by_identifier(
        bound_node=resistor_instance.instance, child_identifier="resistance"
    )
    assert resistance is not None
    print(
        "resistance is type Parameter:",
        EdgeType.is_node_instance_of(
            bound_node=resistance,
            node_type=Parameter.bind_typegraph(tg=tg).get_or_create_type().node(),
        ),
    )

    # Constrained parameter type child
    designator_prefix = not_none(
        EdgeComposition.get_child_by_identifier(
            bound_node=resistor_instance.instance,
            child_identifier="designator_prefix",
        )
    )
    prefix_param = not_none(
        EdgeComposition.get_child_by_identifier(
            bound_node=designator_prefix,
            child_identifier="prefix_param",
        )
    )
    constraint_edge = not_none(EdgeOperand.get_expression_edge(bound_node=prefix_param))
    expression_node = not_none(
        EdgeOperand.get_expression_node(edge=constraint_edge.edge())
    )
    expression_bnode = g.bind(node=expression_node)

    operands: list[BoundNode] = []
    EdgeOperand.visit_operand_edges(
        bound_node=expression_bnode,
        ctx=operands,
        f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
    )
    for operand in operands:
        attrs = EdgeType.get_type_node(
            edge=not_none(EdgeType.get_type_edge(bound_node=operand)).edge()
        ).get_dynamic_attrs()
        print(f"{attrs} {operand.node().get_dynamic_attrs()}")

    expression_bnode = g.bind(node=expression_node)
    operands2: list[BoundNode] = []
    EdgeOperand.visit_operand_edges(
        bound_node=expression_bnode,
        ctx=operands2,
        f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
    )
    for operand in operands2:
        attrs = EdgeType.get_type_node(
            edge=not_none(EdgeType.get_type_edge(bound_node=operand)).edge()
        ).get_dynamic_attrs()
        print(f"{attrs} {operand.node().get_dynamic_attrs()}")

    # Is pickable by type
    ipbt = not_none(
        EdgeComposition.get_child_by_identifier(
            bound_node=resistor_instance.instance,
            child_identifier="_is_pickable",
        )
    )
    ipbt_params = not_none(
        EdgeComposition.get_child_by_identifier(
            bound_node=ipbt,
            child_identifier="params_",
        )
    )
    variables: list[BoundNode] = []
    ipbt_params.visit_edges_of_type(
        edge_type=EdgePointer.get_tid(),
        ctx=variables,
        f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
    )
    print(
        "ipbt_params:",
        [
            EdgeComposition.get_name(
                edge=not_none(
                    EdgeComposition.get_parent_edge(bound_node=variable)
                ).edge()
            )
            for variable in variables
        ],
    )


def test_lightweight():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    resistor_type_bnode = F.Resistor.bind_typegraph(tg=tg).get_or_create_type()
    resistor_instance = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)

    # Test list fields
    assert resistor_instance.unnamed[0].get().get_name() == "unnamed[0]"
    assert resistor_instance.unnamed[1].get().get_name() == "unnamed[1]"

    # Test is pickable by type
    ipbt = resistor_instance.get_trait(F.is_pickable_by_type)
    sorted_params = sorted(param.get_name() for param in ipbt.params)
    assert sorted_params == ["max_power", "max_voltage", "resistance"]
    # TODO: test endpoint extraction from endpoint property
    # assert endpoint == "resistors"

    # Test has_simple_value_representation_based_on_params_chain
    # hsvprp = resistor_instance.get_trait(
    #     F.has_simple_value_representation_based_on_params_chain
    # )
    # print(hsvprp.get_value())

    _ = F.Resistor.bind_typegraph(tg=tg).get_or_create_type()
    _ = F.BJT.bind_typegraph(tg=tg).get_or_create_type()
    # pat = not_none(
    #     EdgePointer.get_pointed_node_by_identifier(
    #         bound_node=bjt_instance.emitter.get().instance,
    #         identifier="pin_association_table_set",
    #     )
    # )
    # for lit in Set.bind_instance(instance=pat).as_list():
    #     lit = LiteralNode.bind_instance(instance=lit.instance)
    #     print(lit.get_value())

    # print(pah.get_nc_literals())
    resistor_instance = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)
    bjt_instance = F.BJT.bind_typegraph(tg=tg).create_instance(g=g)
    pah = bjt_instance.get_trait(F.has_pin_association_heuristic_lookup_table)
    #
    # print(nc_set)
    # print(pah.nc.get())
    # print(pah.nc.get().as_list())
    # print(pah.get_nc_literals())
    print(pah.get_mapping_as_dict())
    print(pah.get_pins(pins=[("1", "E"), ("2", "Collector"), ("3", "B")]))

    # bjt_type_node = F.BJT.bind_typegraph(tg=tg).get_or_create_type()
    # print(Node.bind_instance(bjt_type_node).get_trait(F.is_pickable_by_type))

    # TODO: Fix this to pull traits from the type node
    # print(resistor_instance.get_trait(F.is_pickable_by_type).endpoint)
    # print(resistor_instance.get_trait(F.has_usage_example).language)

    simple_repr = resistor_instance.get_trait(
        F.has_simple_value_representation_based_on_params_chain
    )
    print(simple_repr.get_specs())
    specs_set = simple_repr.specs_set_.get()
    assert isinstance(specs_set, F.Collections.PointerSet)
    print(simple_repr.get_params())
    print(simple_repr.get_value())

    _ = F.Battery.bind_typegraph(tg=tg).get_or_create_type()
    battery_instance = F.Battery.bind_typegraph(tg=tg).create_instance(g=g)
    ref = battery_instance.get_trait(
        F.has_single_electric_reference_defined
    ).get_reference()
    print(ref)
    assert (
        battery_instance.get_trait(F.has_net_name).level
        == F.has_net_name.Level.SUGGESTED
    )
    assert battery_instance.get_trait(F.has_net_name).name == "BAT_VCC"

    _ = F.OpAmp.bind_typegraph(tg=tg).get_or_create_type()
    op_amp_instance = F.OpAmp.bind_typegraph(tg=tg).create_instance(g=g)
    print(
        op_amp_instance.get_trait(
            F.has_pin_association_heuristic_lookup_table
        ).get_mapping_as_dict()
    )

    _ = F.Footprint.bind_typegraph(tg=tg).get_or_create_type()
    footprint_instance = F.Footprint.bind_typegraph(tg=tg).create_instance(g=g)
    # print(footprint_instance.get_trait(F.has_footprint_impl).get_footprint())

    print(resistor_instance.has_trait(F.has_footprint))


if __name__ == "__main__":
    import typer

    # typer.run(test_fabll_basic)

    # test_manual_resistor_def()

    typer.run(test_lightweight)
