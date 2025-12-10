# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import re
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Iterator,
    Protocol,
    Self,
    Sequence,
    cast,
    override,
)

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
    once,
    zip_dicts_by_key,
)

if TYPE_CHECKING:
    from faebryk.core.solver.solver import Solver

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
        self._is_dependant = False  # Set when added as a dependant of another field

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
        """
        Attach additional fields (children or edges) to this field that will be
        created when this field is instantiated.

        ### Args
        - dependant: One or more _ChildField or _EdgeField to create alongside
                this field.
        - identifier: Optional identifier prefix for the dependant's locator.
        - before: If True, prepend to dependants list (created first).

        ### Example
            - Add a trait to a child electrical

            unnamed[0].add_dependant(
                fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [unnamed[0]])
            )
        """
        for d in dependant:
            d._is_dependant = (
                True  # Mark as dependant to prevent duplicate registration
            )
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

        child_type_node = self.nodetype.bind_typegraph(self.t.tg).get_or_create_type()

        self.t.tg.add_make_child(
            type_node=self.t.get_or_create_type(),
            child_type=child_type_node,
            identifier=identifier,
            node_attributes=self.attributes.to_node_attributes()
            if self.attributes is not None
            else None,
            mount_reference=None,
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

    def __repr__(self) -> str:
        return (
            f"InstanceChildBoundInstance(nodetype={self.nodetype.__qualname__},"
            f" identifier={self.identifier},"
            f" instance={self.instance})"
        )


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


class _EdgeField(Field):
    def __init__(
        self,
        lhs: "RefPath",
        rhs: "RefPath",
        *,
        edge: fbrk.EdgeCreationAttributes,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
    ):
        super().__init__(identifier=identifier)
        for arg in [lhs, rhs]:
            for r in arg:
                if not (isinstance(r, (_ChildField, str))) and not (
                    isinstance(r, type) and issubclass(r, Node)
                ):
                    raise FabLLException(
                        f"Only ChildFields and strings are allowed, got {type(r)}"
                    )
        self.lhs = lhs
        self.rhs = rhs
        self.edge = edge

    @staticmethod
    def _resolve_path(path: "RefPath") -> list[str]:
        # TODO dont think we can assert here, raise FabLLException
        resolved_path = []
        for field in path:
            if isinstance(field, _ChildField):
                resolved_path.append(not_none(field.get_identifier()))
            elif isinstance(field, type) and issubclass(field, Node):
                resolved_path.append(f"<<{field._type_identifier()}")
            else:
                resolved_path.append(field)
        return resolved_path

    @staticmethod
    def _resolve_path_from_node(
        path: "list[str] | RefPath", instance: graph.BoundNode, tg: fbrk.TypeGraph
    ) -> graph.BoundNode:
        target = instance
        # TODO: consolidate resolution logic between type_fields and instance_fields

        for segment in path:
            if isinstance(segment, _ChildField):
                segment = segment.get_identifier()
            elif isinstance(segment, type) and issubclass(segment, Node):
                segment = f"<<{segment._type_identifier()}"
            elif segment == SELF_OWNER_PLACEHOLDER[0]:
                # keep target unchanged (self-reference)
                continue
            else:
                segment = str(segment)

            if segment.startswith("<<"):
                segment = segment[2:]
                target = tg.get_type_by_name(type_identifier=segment)
                if target is None:
                    raise PathNotResolvable(
                        node=Node.bind_instance(instance),
                        path=path,
                        error_node=Node.bind_instance(instance),
                        error_identifier=segment,
                    )
            else:
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

    def lhs_resolved_on_node(
        self, instance: graph.BoundNode, tg: fbrk.TypeGraph
    ) -> graph.BoundNode:
        return self._resolve_path_from_node(self.lhs_resolved(), instance, tg)

    def rhs_resolved(self) -> list[str]:
        return self._resolve_path(self.rhs)

    def rhs_resolved_on_node(
        self, instance: graph.BoundNode, tg: fbrk.TypeGraph
    ) -> graph.BoundNode:
        return self._resolve_path_from_node(self.rhs_resolved(), instance, tg)

    def __repr__(self) -> str:
        return (
            f"EdgeField(lhs={self.lhs_resolved()}, "
            f"rhs={self.rhs_resolved()}, "
            f"edge={self.edge})"
        )


def MakeEdge(
    lhs: "RefPath",
    rhs: "RefPath",
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

    def _get_nodes_in_order(self) -> list["Node[Any]"]:
        nodes = [self.get_start_node()]
        current_bound = nodes[0].instance

        for bound_edge in self.edges:
            edge = bound_edge.edge()
            graph_view = bound_edge.g()
            current_node = current_bound.node()

            if current_node.is_same(other=edge.source()):
                next_node = edge.target()
            elif current_node.is_same(other=edge.target()):
                next_node = edge.source()
            else:
                break

            current_bound = graph_view.bind(node=next_node)
            nodes.append(Node[Any].bind_instance(instance=current_bound))

        end_node = self.get_end_node()
        if not nodes[-1].is_same(end_node):
            nodes.append(end_node)

        return nodes

    def __iter__(self) -> Iterator["Node[Any]"]:
        return iter(self._get_nodes_in_order())

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
        node_names = [
            node.get_full_name(types=True) for node in self._get_nodes_in_order()
        ]
        return f"Path({', '.join(node_names)})"


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


class _LazyProxy:
    def __init__(self, f: Callable[[], None], parent: Any, name: str) -> None:
        self.___f = f
        self.___parent = parent
        self.___name = name

    def ___get_and_set(self):
        self.___f()
        return getattr(self.___parent, self.___name)

    @override
    def __getattribute__(self, name: str, /) -> Any:
        if "___" in name:
            return super().__getattribute__(name)
        return getattr(self.___get_and_set(), name)

    @override
    def __setattr__(self, name: str, value: Any, /) -> None:
        if "___" in name:
            return super().__setattr__(name, value)
        setattr(self.___get_and_set(), name, value)

    def __contains__(self, value: Any) -> bool:
        return value in self.___get_and_set()

    def __iter__(self) -> Iterator[Any]:
        return iter(self.___get_and_set())

    def __getitem__(self, key: Any) -> Any:
        return self.___get_and_set()[key]

    def __repr__(self) -> str:
        return f"_LazyProxy({self.___f}, {self.___parent})"


class Node[T: NodeAttributes = NodeAttributes](metaclass=NodeMeta):
    Attributes = NodeAttributes
    __fields: dict[str, Field] = {}
    # TODO do we need this?
    # _fields_bound_tg: dict[fbrk.TypeGraph, list[InstanceChildBoundType]] = {}

    def __init__(self, instance: graph.BoundNode) -> None:
        self.instance = instance

        # setup instance accessors
        # perfomance optimization: only load fields when needed
        # self._load_fields()
        fs = type(self).__fields
        for name in fs:
            p = _LazyProxy(self._load_fields, self, name)
            super().__setattr__(name, p)

    @once
    def _load_fields(self) -> None:
        instance = self.instance
        # overrides fields in instance
        for locator, field in type(self).__fields.items():
            if isinstance(field, _ChildField):
                child = InstanceChildBoundInstance(
                    nodetype=field.nodetype,
                    identifier=field.get_identifier(),
                    instance=instance,
                )
                setattr(self, locator, child)
            elif isinstance(field, Traits.ImpliedTrait):
                bound_implied_trait = field.bind(node=self)
                setattr(self, field.get_locator(), bound_implied_trait)
            elif isinstance(field, Traits.OptionalImpliedTrait):
                bound_optional_trait = field.bind(node=self)
                setattr(self, field.get_locator(), bound_optional_trait)
            elif isinstance(field, ListField):
                list_attr = list[InstanceChildBoundInstance[Any]]()
                for nested_field in field.get_fields():
                    if isinstance(nested_field, _ChildField):
                        child = InstanceChildBoundInstance(
                            nodetype=nested_field.nodetype,
                            identifier=nested_field.get_identifier(),
                            instance=instance,
                        )
                        list_attr.append(child)
                setattr(self, locator, list_attr)
            elif isinstance(field, EdgeFactoryField):
                edge_factory_field = InstanceBoundEdgeFactory(
                    instance=self,
                    edge_factory_field=field,
                )
                setattr(self, locator, edge_factory_field)

    def __init_subclass__(cls) -> None:
        # Ensure single-level inheritance: NodeType subclasses should not themselves
        # be subclassed further.
        if len(cls.__mro__) > len(Node.__mro__) + 1 and not getattr(
            cls, "__COPY_TYPE__", False
        ):
            # mro(): [Leaf, NodeType, object] is allowed (len==3),
            # deeper (len>3) is forbidden
            raise FabLLException(
                f"NodeType subclasses cannot themselves be subclassed "
                f"more than one level deep (found: {cls.__mro__})"
            )
        super().__init_subclass__()
        cls.__fields = {}

        # Scan through class fields and add handle ChildFields
        # e.g ```python
        # class Resistor(Node):
        #     resistance = InstanceChildField(Parameter)
        # ```
        attrs = dict(vars(cls))
        if "__COPY_TYPE__" in attrs:
            # python classes dont inherit the dict from their base classes
            # in the copy case we need to add the attrs from above
            attrs = dict(vars(cls.__mro__[1])) | attrs
        for name, child in attrs.items():
            cls._handle_cls_attr(name, child)

    @staticmethod
    def _copy_type[U: "type[NodeT]"](to_copy: U) -> U:
        class _Copy(to_copy):
            __COPY_TYPE__ = True
            pass

        return cast(U, _Copy)

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
                    attributes=cast(NodeAttributes, field.attributes),
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
                    source=field.lhs_resolved_on_node(
                        instance=type_node, tg=t.tg
                    ).node(),
                    target=field.rhs_resolved_on_node(
                        instance=type_node, tg=t.tg
                    ).node(),
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
        for field in cls.__fields.values():
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
            # Skip fields that are already registered (e.g., loop variables pointing
            # to fields already in a list). This prevents the same _ChildField from
            # being registered twice under different locators.
            if cls._is_field_registered(value):
                return
            cls._add_field(locator=name, field=value)
        if (
            isinstance(value, list)
            and len(value)
            and all(isinstance(c, Field) for c in value)
        ):
            cls._add_field(locator=name, field=ListField(fields=value))

    @classmethod
    def _is_field_registered(cls, field: Field) -> bool:
        """
        Check if a field is already registered, either directly, as part of a list,
        or as a dependant of another field.
        This prevents duplicate registration when loop variables reference existing
        fields.
        """
        # Fast path: field was already added as a dependant
        if field._is_dependant:
            return True
        for registered in cls.__fields.values():
            if registered is field:
                return True
            # Check if field is inside a ListField
            if isinstance(registered, ListField) and field in registered:
                return True
        return False

    @classmethod
    def _add_field(cls, locator: str, field: Field):
        # TODO check if identifier is already in use
        assert locator not in cls.__fields, f"Field {locator} already exists"
        field._set_locator(locator=locator)
        cls.__fields[locator] = field

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

    # TODO this is soooo slow
    # def __setattr__(self, name: str, value: Any, /) -> None:
    #    if not name.startswith("_") and isinstance(value, Node):
    #        self.connect(
    #            to=value, edge_attrs=fbrk.EdgeComposition.build(child_identifier=name)
    #        )
    #    return super().__setattr__(name, value)

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
        if p := self.get_parent_f(
            filter_expr=lambda p: p.isinstance(parent_type),
            direct_only=direct_only,
            include_root=include_root,
        ):
            return p.cast(parent_type)
        return None

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

    def is_descendant_of(self, ancestor: "NodeT") -> bool:
        """Check if this node is a descendant of ancestor."""
        current = self
        while True:
            parent_info = current.get_parent()
            if parent_info is None:
                return False
            parent, _ = parent_info
            if parent.is_same(ancestor):
                return True
            current = parent

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

    def get_children[C: Node](
        self,
        direct_only: bool,
        types: type[C] | tuple[type[C], ...],
        include_root: bool = False,
        f_filter: Callable[[C], bool] | None = None,
        sort: bool = True,
        required_trait: "type[NodeT] | tuple[type[NodeT], ...] | None" = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> OrderedSet[C]:
        type_tuple = types if isinstance(types, tuple) else (types,)
        trait_tuple: tuple[type[NodeT], ...] | None
        if required_trait is None:
            trait_tuple = None
        elif isinstance(required_trait, tuple):
            trait_tuple = required_trait
        else:
            trait_tuple = (required_trait,)

        tg = tg or self.tg

        # Convert Python types to Zig type nodes
        # Use Node as wildcard - if Node is in types, don't filter by type
        if Node in type_tuple:
            zig_types: list[graph.Node] | None = None
        else:
            zig_types = [
                t.bind_typegraph(tg).get_or_create_type().node() for t in type_tuple
            ]

        # Convert Python trait types to Zig trait type nodes
        zig_traits: list[graph.Node] | None = None
        if trait_tuple:
            zig_traits = [
                t.bind_typegraph_from_instance(self.instance)
                .get_or_create_type()
                .node()
                for t in trait_tuple
            ]

        # Call Zig get_children_query
        bound_nodes = fbrk.EdgeComposition.get_children_query(
            bound_node=self.instance,
            direct_only=direct_only,
            types=zig_types,
            include_root=include_root,
            sort=False,  # We'll sort in Python since Zig doesn't implement it yet
            required_traits=zig_traits,
        )

        # Convert BoundNode results back to Python Node objects
        result: list[C] = []
        for bound_node in bound_nodes:
            node = Node(instance=bound_node)
            # Cast to the correct type
            if len(type_tuple) == 1:
                candidate = node.try_cast(type_tuple[0])
                if candidate is None:
                    continue
            else:
                candidate = cast(C, node)

            # Apply f_filter if provided (Zig doesn't support this)
            if f_filter and not f_filter(candidate):
                continue

            result.append(candidate)

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

    @property
    def g(self) -> graph.GraphView:
        return self.instance.g()

    def bind_typegraph_from_self(self) -> "TypeNodeBoundTG[Self, Any]":
        return self.bind_typegraph(tg=self.tg)

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

    def copy_into(self, g: graph.GraphView) -> Self:
        """
        Copy all nodes in hierarchy and edges between them and their types
        """
        g_sub = fbrk.TypeGraph.get_subgraph_of_node(start_node=self.instance)
        g.insert_subgraph(subgraph=g_sub)
        return self.bind_instance(instance=g.bind(node=self.instance.node()))

    def get_full_name(self, types: bool = False) -> str:
        parts: list[str] = []
        if (parent := self.get_parent()) is not None:
            parent_node, name = parent
            if not parent_node.no_include_parents_in_full_name:
                if (parent_full := parent_node.get_full_name(types=False)) is not None:
                    parts.append(parent_full)
            parts.append(name or self.get_root_id())
        elif not self.no_include_parents_in_full_name:
            parts.append(self.get_root_id())

        base = ".".join(parts)
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

    def pretty_params(self, solver: "Solver | None" = None) -> str:
        import faebryk.library.Parameters as Parameters

        params = {
            not_none(p.get_parent())[1]: p
            for p in self.get_children(
                direct_only=True, types=Node, required_trait=Parameters.is_parameter
            )
        }

        def _to_str(p: NodeT) -> str:
            return (
                solver.inspect_get_known_supersets(
                    p.get_trait(Parameters.is_parameter)
                ).pretty_str()
                if solver
                else str(p)
            )

        return "\n".join(f"{k}: {_to_str(v)}" for k, v in params.items())

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
            raise TraitNotFound(f"No trait {trait} found on {self}")
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
        cls_name = type(self).__name__
        if type(self) is Node:
            cls_id = f"{cls_name}[{self.get_type_name()}]"
        else:
            cls_id = cls_name
        suffix = ""
        if traits := Traits.is_trait(self):
            suffix = traits.trait_repr()
        return f"<{cls_id} '{self.get_full_name()})'{suffix}>"

    # def __rich_repr__(self):
    #    yield self.get_full_name()

    # __rich_repr__.angular = True

    def is_same(
        self,
        other: "NodeT | graph.Node | graph.BoundNode",
        allow_different_graph: bool = False,
    ) -> bool:
        match other:
            case Node():
                other_node = other.instance.node()
                if (
                    not allow_different_graph
                    and not other.g.get_self_node()
                    .node()
                    .is_same(other=self.g.get_self_node().node())
                ):
                    return False
            case graph.Node():
                other_node = other
            case graph.BoundNode():
                other_node = other.node()
                if (
                    not allow_different_graph
                    and not other.g()
                    .get_self_node()
                    .node()
                    .is_same(other=self.g.get_self_node().node())
                ):
                    return False
            case _:
                raise TypeError(f"Invalid type: {type(other)}")

        return self.instance.node().is_same(other=other_node)

    def __eq__(self, other: "NodeT | graph.Node | graph.BoundNode") -> bool:
        """
        DO NOT USE THIS! Use is_same instead!
        ONLY HERE FOR set AND dict behavior!
        """
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

    def create_instance_of_same_type(self) -> "graph.BoundNode":
        return self.tg.instantiate_node(
            type_node=not_none(self.get_type_node()), attributes={}
        )


type NodeT = Node[Any]
RefPath = list[str | _ChildField[Any] | type[NodeT]]

SELF_OWNER_PLACEHOLDER: RefPath = [""]
"""
When creating trait, default reference path to self is [""].
"""


class TypeNodeBoundTG[N: NodeT, A: NodeAttributes]:
    """
    (type[Node], fbrk.TypeGraph)
    Becomes available during stage 1 (typegraph creation)
    """

    # TODO REMOVE THIS HACK
    # currently needed for solver to make factories from expression instances
    __TYPE_NODE_MAP__: dict[graph.BoundNode, "TypeNodeBoundTG[Any, Any]"] = {}

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
        TypeNodeBoundTG.__TYPE_NODE_MAP__[typenode] = self
        self.t._create_type(self)
        return typenode

    def get_type_name(self) -> str:
        return fbrk.EdgeComposition.get_name(
            edge=not_none(
                fbrk.EdgeComposition.get_parent_edge(
                    bound_node=self.get_or_create_type()
                )
            ).edge()
        )

    def as_type_node(self) -> "NodeT":
        return self.t.bind_instance(instance=self.get_or_create_type())

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
            lhs_reference=tg.ensure_child_reference(
                type_node=type_node, path=lhs_reference_path, validate=False
            ),
            rhs_reference=tg.ensure_child_reference(
                type_node=type_node, path=rhs_reference_path, validate=False
            ),
            edge_attributes=edge,
        )

    def check_if_instance_of_type_has_trait(self, trait: type[NodeT]) -> bool:
        children = Node.bind_instance(instance=self.get_or_create_type()).get_children(
            direct_only=True, types=MakeChild, tg=self.tg
        )
        bound_trait = trait.bind_typegraph(self.tg).get_or_create_type()
        for child in children:
            child_type = child.get_child_type()
            if child_type.node().is_same(other=bound_trait.node()):
                return True
        return False

    @staticmethod
    def try_get_trait_of_type[T: NodeT](
        trait: type[T], type_node: graph.BoundNode
    ) -> "T | None":
        tg = fbrk.TypeGraph.of_type(type_node=type_node)
        assert tg
        trait_type = trait.bind_typegraph(tg=tg)
        out = fbrk.Trait.try_get_trait(
            target=type_node,
            trait_type=trait_type.get_or_create_type(),
        )
        if not out:
            return None
        return trait.bind_instance(instance=out)

    def try_get_type_trait[T: NodeT](self, trait: type[T]) -> T | None:
        return self.try_get_trait_of_type(
            trait=trait, type_node=self.get_or_create_type()
        )

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
    def add_to(node: NodeT, trait: NodeT) -> graph.BoundNode:
        return fbrk.Trait.add_trait_to(target=node.instance, trait_type=trait.instance)

    @staticmethod
    def add_instance_to(node: NodeT, trait_instance: NodeT) -> graph.BoundNode:
        return fbrk.Trait.add_trait_instance_to(
            target=node.instance, trait_instance=trait_instance.instance
        )

    @staticmethod
    def create_and_add_instance_to[T: Node[Any]](node: Node[Any], trait: type[T]) -> T:
        trait_bound = trait.bind_typegraph_from_instance(
            node.instance
        ).get_or_create_type()
        trait_type_node = Node.bind_instance(instance=trait_bound)
        trait_instance_node = Traits.add_to(node=node, trait=trait_type_node)
        return trait.bind_instance(instance=trait_instance_node)

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
    def get_implementor_siblings[T: NodeT](
        trait: TypeNodeBoundTG[Any, Any],
        sibling_trait: type[T],
        g: graph.GraphView | None = None,
    ) -> list[T]:
        return [n.get_sibling_trait(sibling_trait) for n in trait.get_instances(g=g)]

    @staticmethod
    def get_implementor_objects(
        trait: TypeNodeBoundTG[Any, Any], g: graph.GraphView | None = None
    ) -> list[NodeT]:
        return [
            Traits(impl).get_obj_raw() for impl in Traits.get_implementors(trait, g=g)
        ]

    @staticmethod
    def is_trait(node: NodeT) -> "Traits | None":
        type_node = node.get_type_node()
        if type_node is None:
            return None
        if TypeNodeBoundTG.try_get_trait_of_type(ImplementsTrait, type_node):
            return Traits.bind(node)
        return None

    def trait_repr(self):
        return f" on {self.get_obj_raw()!r}"

    class _BoundImpliedTrait[T: NodeT](ChildAccessor[T]):
        def __init__(self, sibling_type: type[T], node: NodeT):
            self._sibling_type = sibling_type
            self._node = node

        def get(self) -> T:
            return self._node.get_sibling_trait(self._sibling_type)

    class ImpliedTrait[T: NodeT](Field, ChildAccessor[T]):
        def __init__(
            self,
            sibling_type: type[T],
            *,
            identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
        ):
            super().__init__(identifier=identifier)
            self._sibling_type = sibling_type

        def get(self) -> T:
            raise ValueError("SiblingField is not bound to a node")

        def bind(self, node: NodeT) -> "Traits._BoundImpliedTrait[T]":
            return Traits._BoundImpliedTrait(sibling_type=self._sibling_type, node=node)

    # Lazy trait reference for OptionalImpliedTrait: direct type or lambda
    LazyTraitRef = type[NodeT] | Callable[[], type[NodeT]]

    @staticmethod
    def _resolve_ref(ref: "Traits.LazyTraitRef") -> type[NodeT]:
        """Resolve a trait reference: if callable, call it; otherwise return as-is."""
        return ref() if callable(ref) and not isinstance(ref, type) else ref

    class _BoundOptionalImpliedTrait[T: NodeT](ChildAccessor[T]):
        def __init__(self, trait_type: "Traits.LazyTraitRef", node: NodeT):
            self._trait_type_ref = trait_type
            self._node = node

        def try_get(self) -> T | None:
            trait_type = Traits._resolve_ref(self._trait_type_ref)
            return cast(T, self._node.try_get_sibling_trait(trait_type))

        def force_get(self) -> T:
            return not_none(self.try_get())

        def get(self) -> T:
            raise ValueError("Unhandled conditional, use try_get or force_get instead")

    class OptionalImpliedTrait[T: NodeT](Field, ChildAccessor[T]):
        def __init__(
            self,
            trait_type: "Traits.LazyTraitRef",
            *,
            identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
        ):
            super().__init__(identifier=identifier)
            self._trait_type_ref = trait_type

        def try_get(self) -> T | None:
            raise ValueError("SiblingField is not bound to a node")

        def force_get(self) -> T:
            raise ValueError("SiblingField is not bound to a node")

        def get(self) -> T:
            raise ValueError("Unhandled conditional, use try_get or force_get instead")

        def bind(self, node: NodeT) -> "Traits._BoundOptionalImpliedTrait[T]":
            return Traits._BoundOptionalImpliedTrait(
                trait_type=self._trait_type_ref, node=node
            )


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
        # TODO expose the zig function instead
        typeref = not_none(
            fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=self.instance, child_identifier="type_ref"
            )
        )
        resolved_type = fbrk.Linker.get_resolved_type(type_reference=typeref)
        if not resolved_type:
            raise ValueError("Type not linked yet")
        return resolved_type


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

    is_trait = Traits.MakeEdge(ImplementsTrait.MakeChild().put_on_type())

    def get_obj(self) -> NodeT:
        return Traits.get_obj_raw(Traits.bind(self))


class is_interface(Node):
    is_trait = ImplementsTrait.MakeChild().put_on_type()

    def get_obj(self) -> NodeT:
        return Traits.get_obj_raw(Traits.bind(self))

    def connect_to(self, *others: "NodeT") -> None:
        self_node = self.get_obj()

        for other in others:
            if isinstance(other, is_interface):
                raise ValueError("Don't call on the interface, just pass the node thx")
            fbrk.EdgeInterfaceConnection.connect(
                bn1=self_node.instance, bn2=other.instance
            )

    def connect_shallow_to(self, *others: "NodeT") -> None:
        self_node = self.get_obj()
        for other in others:
            fbrk.EdgeInterfaceConnection.connect_shallow(
                bn1=self_node.instance, bn2=other.instance
            )

    def is_connected_to(self, other: "NodeT") -> bool:
        bfs_path = fbrk.EdgeInterfaceConnection.is_connected_to(
            source=self.get_obj().instance,
            target=other.instance
        )
        return bfs_path.get_end_node().node().is_same(other=other.instance.node())

    def get_connected(self, include_self: bool = False) -> dict["Node[Any]", Path]:
        connected_nodes_map = fbrk.EdgeInterfaceConnection.get_connected(
            source=self.get_obj().instance, include_self=include_self
        )
        return {
            Node[Any].bind_instance(instance=node): Path(bfs_path)
            for node, bfs_path in connected_nodes_map.items()
        }

    @staticmethod
    def group_into_buses[N: NodeT](nodes: set[N],) -> dict[N, set[N]]:
        remaining = set(nodes)
        buses: dict[N, set[N]] = {}

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


# --------------------------------------------------------------------------------------
# TODO remove
# re-export graph.GraphView to be used from fabll namespace
Graph = fbrk.TypeGraph
# Node type aliases
Module = Node
type Module = Node


# --------------------------------------------------------------------------------------
# Rendering


class TreeRenderer:
    """Renders graph trees, following composition edges."""

    MAX_VALUE_LENGTH = 40  # characters

    @dataclass
    class NodeContext:
        """Context for rendering a single node in the tree."""

        inbound_edge: graph.BoundEdge | None
        node: graph.BoundNode

    @staticmethod
    def truncate_text(text: str, max_length: int | None = None) -> str:
        if max_length is None:
            max_length = TreeRenderer.MAX_VALUE_LENGTH
        if "\n" in text:
            text = text.split("\n")[0] + "..."
        if len(text) > max_length:
            return text[: max_length - 3] + "..."
        return text

    @staticmethod
    def format_edge_label(
        edge: graph.BoundEdge | None,
        *,
        prefix_on_name: bool = True,
        prefix_on_anonymous: bool = True,
    ) -> str:
        edge_name = fbrk.EdgeComposition.get_name(edge=edge.edge()) if edge else None
        if edge_name:
            return f".{edge_name}" if prefix_on_name else edge_name
        return ".<anonymous>" if prefix_on_anonymous else "<anonymous>"

    @staticmethod
    def collect_interface_connections(node: graph.BoundNode, root: "Node") -> list[str]:
        """Collect interface connection descriptions for a node."""
        interface_edges: list[graph.BoundEdge] = []
        node.visit_edges_of_type(
            edge_type=fbrk.EdgeInterfaceConnection.get_tid(),
            ctx=interface_edges,
            f=lambda acc, bound_edge: acc.append(bound_edge),
        )

        connections = []
        for bound_edge in interface_edges:
            if bound_edge.edge().source().is_same(other=node.node()):
                partner_ref = bound_edge.edge().target()
            elif bound_edge.edge().target().is_same(other=node.node()):
                partner_ref = bound_edge.edge().source()
            else:
                continue

            partner_node = Node.bind_instance(bound_edge.g().bind(node=partner_ref))
            connections.append(f"~ {partner_node.relative_address(root=root)}")

        return connections

    @staticmethod
    def format_list(values: list, max_items: int = 3, quote: str = "") -> str:
        """Format a list of values for display."""
        formatted = ", ".join(f"{quote}{v}{quote}" for v in values[:max_items])
        suffix = "..." if len(values) > max_items else ""
        return f"[{formatted}{suffix}]"

    @staticmethod
    def extract_literal_value(node: graph.BoundNode, type_name: str) -> str | None:
        """Extract display value from faebryk literal types."""
        import faebryk.library._F as F

        match type_name:
            case "Strings":
                values = F.Literals.Strings.bind_instance(node).get_values()
                if len(values) == 1:
                    return f'"{TreeRenderer.truncate_text(values[0])}"'
                elif values:
                    return TreeRenderer.format_list(
                        [TreeRenderer.truncate_text(v) for v in values],
                        max_items=3,
                        quote='"',
                    )
            case "Counts":
                values = F.Literals.Counts.bind_instance(node).get_values()
                if len(values) == 1:
                    return str(values[0])
                elif values:
                    return TreeRenderer.format_list(values, max_items=5)
            case "Booleans":
                values = F.Literals.Booleans.bind_instance(node).get_values()
                if len(values) == 1:
                    return str(values[0])
                elif values:
                    return TreeRenderer.format_list(values)
            case "NumericSet":
                numeric_set = F.Literals.NumericSet.bind_instance(node)
                try:
                    values = list(numeric_set.get_values())
                    if len(values) == 1:
                        return str(values[0])
                    elif values:
                        return TreeRenderer.format_list(values)
                except F.Literals.NotSingletonError:
                    intervals = numeric_set.get_intervals()
                    if len(intervals) == 1:
                        i = intervals[0]
                        return f"[{i.get_min_value()}, {i.get_max_value()}]"
                    return TreeRenderer.format_list(
                        [
                            f"[{i.get_min_value()}, {i.get_max_value()}]"
                            for i in intervals
                        ]
                    )
            case "AnyLiteral":
                value = F.Literals.AnyLiteral.bind_instance(node).get_value()
                if isinstance(value, str):
                    return f'"{TreeRenderer.truncate_text(value)}"'
                return str(value)
            case _ if type_name.endswith("Enums") or type_name == "AbstractEnums":
                bound = F.Literals.AbstractEnums.bind_instance(node)
                values = bound.get_values()
                if len(values) == 1:
                    return f"'{values[0]}'"
                elif values:
                    return TreeRenderer.format_list(values, quote="'")

    @staticmethod
    def describe_node(
        ctx: "TreeRenderer.NodeContext",
        *,
        value_extractor: Callable[[graph.BoundNode, str], str | None] | None = None,
    ) -> str:
        """
        Build a description string for a node.

        Args:
            ctx: The render context containing the node.
            value_extractor: Optional function to extract display values from nodes.
                Takes (node, type_name) and returns a display string or None.
        """
        type_name = Node.bind_instance(ctx.node).get_type_name() or "<anonymous>"

        attrs = ctx.node.node().get_dynamic_attrs()
        attrs_parts = [
            f"{k}={TreeRenderer.truncate_text(str(v))}" for k, v in attrs.items()
        ]
        attrs_text = f"<{', '.join(attrs_parts)}>" if attrs_parts else ""

        result = f"{type_name}{attrs_text}"

        if value_extractor:
            if value := value_extractor(ctx.node, type_name):
                result += f" = {value}"

        return result

    @staticmethod
    def _edge_type_ids(edge_types: Sequence[type]) -> list[int]:
        ids: list[int] = []
        for edge_type_cls in edge_types:
            get_tid = getattr(edge_type_cls, "get_tid", None)
            if not callable(get_tid):
                raise AttributeError(
                    f"{edge_type_cls!r} must expose a callable get_tid()"
                )
            ids.append(get_tid())  # type: ignore
        return ids

    @staticmethod
    def _excluded_names(exclude_node_types: Sequence[type] | None) -> frozenset[str]:
        if not exclude_node_types:
            return frozenset()
        return frozenset(t.__qualname__ for t in exclude_node_types)

    @staticmethod
    def _is_excluded(node: graph.BoundNode, excluded: frozenset[str]) -> bool:
        if not excluded:
            return False
        type_name = Node.bind_instance(node).get_type_name()
        return type_name is not None and type_name in excluded

    @staticmethod
    def _child_contexts(
        parent: graph.BoundNode,
        *,
        edge_type_ids: Sequence[int],
        excluded: frozenset[str],
    ) -> list["TreeRenderer.NodeContext"]:
        children: list[TreeRenderer.NodeContext] = []

        def add_child(acc: list, bound_edge: graph.BoundEdge) -> None:
            edge = bound_edge.edge()
            if not edge.source().is_same(other=parent.node()):
                return

            child_node = parent.g().bind(node=edge.target())
            if TreeRenderer._is_excluded(child_node, excluded):
                return

            acc.append(
                TreeRenderer.NodeContext(inbound_edge=bound_edge, node=child_node)
            )

        for edge_type_id in edge_type_ids:
            parent.visit_edges_of_type(
                edge_type=edge_type_id,
                ctx=children,
                f=add_child,
            )

        return children

    @staticmethod
    def print_tree(
        bound_node: graph.BoundNode,
        *,
        renderer: Callable[["TreeRenderer.NodeContext"], str],
        edge_types: Sequence[type] | None = None,
        exclude_node_types: Sequence[type[NodeT]] | None = None,
    ) -> None:
        """
        Print a tree visualization of a faebryk graph starting from the given node.

        Args:
            bound_node: The root node to start traversal from.
            renderer: A function that converts a NodeContext into a display string.
            edge_types: Edge types to follow when traversing children.
                        Defaults to (EdgeComposition,).
            exclude_node_types: Node types to exclude from the output.
        """
        if edge_types is None:
            edge_types = (fbrk.EdgeComposition,)

        edge_type_ids = TreeRenderer._edge_type_ids(edge_types)
        excluded = TreeRenderer._excluded_names(exclude_node_types)

        root_node = bound_node
        if TreeRenderer._is_excluded(root_node, excluded):
            return

        visited: set[int] = set()

        def walk(ctx: TreeRenderer.NodeContext, prefix: str, is_last: bool) -> None:
            node_uuid = ctx.node.node().get_uuid()
            is_cycle = node_uuid in visited

            line = renderer(ctx)
            if is_cycle:
                line += " ↺"

            if prefix:
                connector = "└─ " if is_last else "├─ "
                print(f"{prefix}{connector}{line}")
            else:
                print(line)

            if is_cycle:
                return

            visited.add(node_uuid)

            child_prefix = prefix + ("   " if is_last else "│  ")
            children = TreeRenderer._child_contexts(
                ctx.node, edge_type_ids=edge_type_ids, excluded=excluded
            )
            for index, child_ctx in enumerate(children):
                walk(child_ctx, child_prefix, index == len(children) - 1)

            visited.remove(node_uuid)

        root_ctx = TreeRenderer.NodeContext(inbound_edge=None, node=root_node)
        walk(root_ctx, prefix="", is_last=True)


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
        is_trait = Traits.MakeEdge(ImplementsTrait.MakeChild().put_on_type())

    class ExampleNode(Node):
        example_trait = Traits.MakeEdge(ExampleTrait.MakeChild())

    node = ExampleNode.bind_typegraph(tg).create_instance(g=g)
    assert node.try_get_trait(ExampleTrait) is not None


def test_set_basic():
    """Test basic Set functionality: append, as_list, as_set."""
    import faebryk.library.Collections as Collections

    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    # Create a Set and some elements
    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore[arg-type]
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

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore[arg-type]
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

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore[arg-type]
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

    set_node = Collections.PointerSet.bind_typegraph(tg).create_instance(g=g)  # type: ignore[arg-type]
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
        tg=tg,
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
    assert res_inst.resistance.get().get_units().get_symbols()[0] == "Ω"
    assert res_inst.resistance.get().get_units().get_symbols()[1] == "Ohm"
    assert res_inst.get_trait(fabll.is_module)
    leads = [
        n.get_trait(F.Lead.is_lead)
        for n in res_inst.get_children(
            direct_only=False, types=Node, required_trait=F.Lead.is_lead
        )
    ]
    assert leads[0].get_lead_name() == "unnamed[0]"
    assert leads[1].get_lead_name() == "unnamed[1]"
    assert (
        res_inst._is_pickable.get().get_param("resistance").get_name() == "resistance"
    )
    assert (
        res_inst.get_trait(F.has_designator_prefix).get_prefix()
        == F.has_designator_prefix.Prefix.R
    )


def test_string_param():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    ctx = F.Parameters.BoundParameterContext(tg=tg, g=g)

    string_p = ctx.StringParameter
    string_p.alias_to_single(value="IG constrained")
    assert string_p.force_extract_literal().get_values()[0] == "IG constrained"

    class ExampleStringParameter(fabll.Node):
        string_p_tg = F.Parameters.StringParameter.MakeChild()
        constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert (
        esp.string_p_tg.get().force_extract_literal().get_values()[0]
        == "TG constrained"
    )


def test_boolean_param():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    boolean_p = F.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.alias_to_single(value=True)
    assert boolean_p.force_extract_literal().get_values()

    class ExampleBooleanParameter(fabll.Node):
        boolean_p_tg = F.Parameters.BooleanParameter.MakeChild()
        constraint = F.Literals.Booleans.MakeChild_ConstrainToLiteral(
            [boolean_p_tg], True
        )

    ebp = ExampleBooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert ebp.boolean_p_tg.get().force_extract_literal().get_values()


def test_node_equality():
    g, tg = _make_graph_and_typegraph()

    NT1 = Node.bind_typegraph(tg=tg)
    n1 = NT1.create_instance(g=g)
    n2 = NT1.create_instance(g=g)

    assert n1 != n2
    assert n1 == n1
    assert n1 is n1
    n1_1 = Node.bind_instance(n1.instance)
    assert n1_1 == n1
    assert n1_1 is not n1

    # equal with different type
    class NewType(fabll.Node):
        pass

    NT2 = NewType.bind_typegraph(tg=tg)
    n2 = NT2.create_instance(g=g)
    n2_1 = NewType.bind_instance(n2.instance)
    assert n2_1 == n2

    n2_2 = Node.bind_instance(n2.instance)
    assert n2_2 == n2_1

    # dict behavior
    node_set = {n1}
    assert n1 in node_set
    assert n2 not in node_set
    assert n1_1 in node_set

    node_set.add(n2)
    assert n2 in node_set
    assert n2_1 in node_set
    assert n2_2 in node_set

    node_set.add(n2_1)
    assert len(node_set) == 2


def test_chain_names():
    import re

    g, tg = _make_graph_and_typegraph()

    class N(Node):
        pass

    root = N.bind_typegraph(tg).create_instance(g=g)
    x = root
    for i in range(10):
        y = N.bind_typegraph(tg).create_instance(g=g)
        # Add y as child of x with name "i{i}"
        fbrk.EdgeComposition.add_child(
            bound_node=x.instance,
            child=y.instance.node(),
            child_identifier=f"i{i}",
        )
        x = y

    assert re.search(
        r"0x[0-9A-F]+\.i0\.i1\.i2\.i3\.i4\.i5\.i6\.i7\.i8\.i9", x.get_full_name()
    )


def test_chain_tree():
    g, tg = _make_graph_and_typegraph()

    class N(Node):
        pass

    root = N.bind_typegraph(tg).create_instance(g=g)
    x = root
    for i in range(10):
        y = N.bind_typegraph(tg).create_instance(g=g)
        z = N.bind_typegraph(tg).create_instance(g=g)
        fbrk.EdgeComposition.add_child(
            bound_node=x.instance,
            child=y.instance.node(),
            child_identifier=f"i{i}",
        )
        fbrk.EdgeComposition.add_child(
            bound_node=x.instance,
            child=z.instance.node(),
            child_identifier=f"j{i}",
        )
        x = y

    assert re.search(
        r"0x[0-9A-F]+\.i0\.i1\.i2\.i3\.i4\.i5\.i6\.i7\.i8\.i9", x.get_full_name()
    )


def test_chain_tree_with_root():
    g, tg = _make_graph_and_typegraph()

    class N(Node):
        pass

    root = N.bind_typegraph(tg).create_instance(g=g)
    root.no_include_parents_in_full_name = True
    x = root
    for i in range(10):
        y = N.bind_typegraph(tg).create_instance(g=g)
        z = N.bind_typegraph(tg).create_instance(g=g)
        fbrk.EdgeComposition.add_child(
            bound_node=x.instance,
            child=y.instance.node(),
            child_identifier=f"i{i}",
        )
        fbrk.EdgeComposition.add_child(
            bound_node=x.instance,
            child=z.instance.node(),
            child_identifier=f"j{i}",
        )
        x = y

    assert re.search(
        r"0x[0-9A-F]+\.i0\.i1\.i2\.i3\.i4\.i5\.i6\.i7\.i8\.i9", x.get_full_name()
    )


def test_get_children_modules_simple():
    g, tg = _make_graph_and_typegraph()

    class M(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())

    class App(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())
        m = M.MakeChild()

    app = App.bind_typegraph(tg).create_instance(g=g)
    m = app.m.get()

    mods = app.get_children(direct_only=False, types=Node, required_trait=is_module)
    assert mods == {m}


def test_get_children_modules_tree():
    g, tg = _make_graph_and_typegraph()

    class Capacitor(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())

    class CapacitorContainer(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())
        cap1 = Capacitor.MakeChild()
        cap2 = Capacitor.MakeChild()

    class App(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())
        container1 = CapacitorContainer.MakeChild()
        container2 = CapacitorContainer.MakeChild()

    app = App.bind_typegraph(tg).create_instance(g=g)
    container1 = app.container1.get()
    container2 = app.container2.get()

    cap1 = container1.cap1.get()
    cap2 = container1.cap2.get()
    cap3 = container2.cap1.get()
    cap4 = container2.cap2.get()

    mods = container1.get_children(
        direct_only=False,
        types=Capacitor,
        required_trait=is_module,
    )
    assert mods == {cap1, cap2}

    mods = app.get_children(
        direct_only=False,
        types=Capacitor,
        required_trait=is_module,
    )
    assert mods == {cap1, cap2, cap3, cap4}


def test_copy_into_basic():
    g, tg = _make_graph_and_typegraph()
    g_new = graph.GraphView.create()

    class Inner(Node):
        pass

    class N(Node):
        inner = Inner.MakeChild()

    class Outer(Node):
        n = N.MakeChild()
        m = N.MakeChild()
        o = N.MakeChild()

    outer = Outer.bind_typegraph(tg).create_instance(g=g)
    m = outer.m.get()
    n = outer.n.get()
    o = outer.o.get()
    m.connect(to=n, edge_attrs=fbrk.EdgePointer.build(identifier=None, order=None))
    n.connect(to=o, edge_attrs=fbrk.EdgePointer.build(identifier=None, order=None))

    assert fbrk.EdgePointer.get_referenced_node_from_node(node=n.instance) == o.instance
    assert fbrk.EdgePointer.get_referenced_node_from_node(node=m.instance) == n.instance

    n2 = n.copy_into(g=g_new)

    tg_new = fbrk.TypeGraph.of_instance(instance_node=n2.instance)
    assert tg_new is not None
    print(
        "tg:",
        indented_container(
            dict(sorted(tg.get_type_instance_overview(), key=lambda x: x[0]))
        ),
    )
    print(
        "tg_new:",
        indented_container(
            dict(sorted(tg_new.get_type_instance_overview(), key=lambda x: x[0]))
        ),
    )

    def _get_name(n: graph.BoundNode) -> str:
        f = fabll.Node.bind_instance(instance=n)
        return repr(f)

    def _container(ns: Iterable[fabll.Node]) -> str:
        return indented_container(
            sorted(ns, key=lambda x: repr(x)), compress_large=1000
        )

    g_nodes = {fabll.Node.bind_instance(instance=n) for n in g.get_nodes()}
    g_new_nodes = {fabll.Node.bind_instance(instance=n) for n in g_new.get_nodes()}
    g_diff_new = g_new_nodes - g_nodes
    # tg.self & g_new.self
    assert len(g_diff_new) == 2, f"g_diff_new: {_container(g_diff_new)}"

    print("g", _container(g_nodes))
    print("g_new", _container(g_new_nodes))
    print("g_diff", _container(g_nodes - g_new_nodes))
    print("g_diff_new", _container(g_diff_new))

    assert n2.is_same(n)
    assert n2 is not n
    assert n2.g != n.g

    # check o is in the new graph (because we pointed to it)
    assert (
        not_none(fbrk.EdgePointer.get_referenced_node_from_node(node=n2.instance))
        .node()
        .is_same(other=o.instance.node())
    )

    # check m is not in the new graph
    g_new_nodes = g_new.get_nodes()
    assert not any(m.instance.node().is_same(other=node.node()) for node in g_new_nodes)

    inner2 = n2.inner.get()
    assert inner2.is_same(n.inner.get())

    assert n2.isinstance(N)
    assert inner2.isinstance(Inner)


def test_type_name_collision_raises_error():
    """
    Test that registering two different classes with the same name raises an error.
    """

    import pytest

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class MyType(Node):  # type: ignore[no-redef]
        pass

    # First registration should succeed
    MyType.bind_typegraph(tg).get_or_create_type()

    # Define a different class with the same __name__
    class MyType(Node):  # noqa: F811
        some_field: int = 42

    # Second registration with same name but different class should raise
    with pytest.raises(FabLLException, match="Type name collision"):
        MyType.bind_typegraph(tg).get_or_create_type()


def test_same_class_multiple_get_or_create_type_succeeds():
    """Test that calling get_or_create_type multiple times on the same class works."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class MyType(Node):
        pass

    bound = MyType.bind_typegraph(tg)

    # Multiple calls should return the same type node
    type1 = bound.get_or_create_type()
    type2 = bound.get_or_create_type()
    assert type1.node().is_same(other=type2.node())


if __name__ == "__main__":
    import typer

    # typer.run(test_fabll_basic)

    # test_manual_resistor_def()

    # typer.run(test_resistor_instantiation)
    typer.run(test_copy_into_basic)
