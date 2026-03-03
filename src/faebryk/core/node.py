# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import itertools
import logging
import re
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from dataclasses import fields as dataclass_fields
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Iterable,
    Iterator,
    Protocol,
    Self,
    Sequence,
    cast,
    override,
)

import pytest
from typing_extensions import Callable, deprecated

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
from faebryk.libs.util import (
    KeyErrorNotFound,
    OrderedSet,
    indented_container,
    not_none,
    once,
    zip_dicts_by_key,
)

if TYPE_CHECKING:
    from faebryk.core.solver.solver import Solver


class _UniqueKey:
    """Globally-unique key generator to prevent locator / identifier collisions."""

    # TODO: consider using UUIDs instead
    _counter: ClassVar[Iterator[int]] = itertools.count()

    @classmethod
    def get(cls) -> int:
        return next(cls._counter)

    @classmethod
    def get_str(cls) -> str:
        return f"{cls.get():04x}"


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
        path: "list[str | fbrk.EdgeTraversal] | RefPath",
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
            _t_id = (
                (
                    self.nodetype
                    if isinstance(self.nodetype, str)
                    else self.nodetype.__name__
                )
                if isinstance(self, _ChildField)
                else f"{_UniqueKey.get():x}"
            )
            identifier = f"anon{_UniqueKey.get_str()}_{_t_id}"
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
        nodetype: type[T] | str,
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
        assert not isinstance(self.nodetype, str), "Function must be run after linker"
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
                d._set_locator(f"{identifier}_{_UniqueKey.get_str()}")
            else:
                d._set_locator(None)
            if before:
                self._prepend_dependants.append(d)
            else:
                self._dependants.append(d)

    def add_as_dependant(
        self,
        to: "_ChildField[Any]",
        identifier: str | None = None,
        before: bool = False,
    ) -> Self:
        to.add_dependant(self, identifier=identifier, before=before)
        return self

    def __repr__(self) -> str:
        nodetype_name = (
            self.nodetype.__qualname__
            if isinstance(self.nodetype, type)
            else self.nodetype
        )
        return (
            f"ChildField(nodetype={nodetype_name},"
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
        nodetype: type[T] | str,
        t: "TypeNodeBoundTG[N, Any]",
        attributes: "NodeAttributes | None" = None,
        identifier: str | None | PLACEHOLDER = None,
    ) -> None:
        self.nodetype = nodetype
        self.t = t
        self.identifier = identifier
        self.attributes = attributes

        if isinstance(nodetype, str):
            # TODO: Add checking similar to below for prelinked childfields
            return
        if nodetype.Attributes is not NodeAttributes and not isinstance(
            attributes, nodetype.Attributes
        ):
            raise FabLLException(
                f"Attributes mismatch: {nodetype.__name__} expects"
                f" {nodetype.Attributes} but got {type(attributes)}"
            )

    def _add_to_typegraph(self) -> graph.BoundNode:
        identifier = self.identifier
        if isinstance(identifier, PLACEHOLDER):
            raise FabLLException("Placeholder identifier not allowed")

        if isinstance(self.nodetype, str):
            mc = self.t.tg.add_make_child_deferred(
                type_node=self.t.get_or_create_type(),
                child_type_identifier=self.nodetype,
                identifier=identifier,
                node_attributes=self.attributes.to_node_attributes()
                if self.attributes is not None
                else None,
            )
        else:
            child_type_node = self.nodetype.bind_typegraph(
                self.t.tg
            ).get_or_create_type()
            mc = self.t.tg.add_make_child(
                type_node=self.t.get_or_create_type(),
                child_type=child_type_node,
                identifier=identifier,
                node_attributes=self.attributes.to_node_attributes()
                if self.attributes is not None
                else None,
            )
        return mc

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
    def _resolve_path(path: "RefPath") -> list[str | fbrk.EdgeTraversal]:
        # TODO dont think we can assert here, raise FabLLException
        resolved_path: list[str | fbrk.EdgeTraversal] = []
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
        path: "list[str | fbrk.EdgeTraversal] | RefPath",
        instance: graph.BoundNode,
        tg: fbrk.TypeGraph,
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

    def lhs_resolved(self) -> list[str | fbrk.EdgeTraversal]:
        return self._resolve_path(self.lhs)

    def lhs_resolved_on_node(
        self, instance: graph.BoundNode, tg: fbrk.TypeGraph
    ) -> graph.BoundNode:
        return self._resolve_path_from_node(self.lhs_resolved(), instance, tg)

    def rhs_resolved(self) -> list[str | fbrk.EdgeTraversal]:
        return self._resolve_path(self.rhs)

    def rhs_resolved_on_node(
        self, instance: graph.BoundNode, tg: fbrk.TypeGraph
    ) -> graph.BoundNode:
        return self._resolve_path_from_node(self.rhs_resolved(), instance, tg)

    def __repr__(self) -> str:
        try:
            lhs = self.lhs_resolved()
        except FabLLException:
            lhs = "<unresolvable>"
        try:
            rhs = self.rhs_resolved()
        except FabLLException:
            rhs = "<unresolvable>"
        return f"EdgeField(lhs={lhs}, rhs={rhs}, edge={self.edge})"


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
    def edges(self) -> list[graph.Edge]:
        return self._bfs_path.get_edges()

    def get_start_node(self) -> "Node[Any]":
        return Node[Any].bind_instance(instance=self.start_node)

    def get_end_node(self) -> "Node[Any]":
        return Node[Any].bind_instance(instance=self.end_node)

    def _get_nodes_in_order(self) -> list["Node[Any]"]:
        nodes = [self.get_start_node()]
        current_bound = nodes[0].instance
        g = current_bound.g()

        for edge in self.edges:
            current_node = current_bound.node()

            if current_node.is_same(other=edge.source()):
                next_node = edge.target()
            elif current_node.is_same(other=edge.target()):
                next_node = edge.source()
            else:
                break

            current_bound = g.bind(node=next_node)
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

    def pretty_repr(self) -> str:
        return " -> ".join(
            re.sub(
                r"[^|]*?\.ato::",
                "",
                node.get_full_name(types=True, include_uuid=False),
            )
            for node in self._get_nodes_in_order()
        )


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


_ATTR_UNSET = object()


@dataclass(kw_only=True)
class NodeAttributes:
    _loaded_from: "graph.Node | None" = dataclass_field(
        default=None, repr=False, compare=False, hash=False
    )

    def __init_subclass__(cls) -> None:
        # TODO collect all fields (like dataclasses)
        # TODO check Attributes is dataclass and not frozen
        # TODO check all values are literals
        pass

    @classmethod
    def of(cls: type[Self], node: "graph.BoundNode | NodeT") -> Self:
        if isinstance(node, Node):
            node = node.instance
        return cls(
            _loaded_from=node.node(),
            **{
                f.name: _ATTR_UNSET
                for f in dataclass_fields(cls)
                if f.name != "_loaded_from"
            },
        )

    def __getattribute__(self, name: str) -> Any:
        out = super().__getattribute__(name)
        if out is _ATTR_UNSET and self._loaded_from is not None:
            resolved = self._loaded_from.get_attr(key=name)
            setattr(self, name, resolved)
            return resolved
        return out

    def to_dict(self) -> dict[str, Literal]:
        return {
            f.name: getattr(self, f.name)
            for f in dataclass_fields(type(self))
            if f.name != "_loaded_from"
        }

    def to_node_attributes(self) -> fbrk.NodeCreationAttributes | None:
        attrs = self.to_dict()
        if not attrs:
            return None
        return fbrk.NodeCreationAttributes.init(dynamic=attrs)


class _LazyProxyPerf:
    slots = ("__parent",)

    def __init__(self, parent: Any) -> None:
        self.__parent = parent

    def __get_and_set(self):
        f = Node._load_fields
        parent = self.__parent
        f(parent)
        return getattr(parent, type(self).__name__)

    @override
    def __getattribute__(self, name: str, /) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        return getattr(self.__get_and_set(), name)

    def __contains__(self, value: Any) -> bool:
        return value in self.__get_and_set()

    def __iter__(self) -> Iterator[Any]:
        return iter(self.__get_and_set())

    def __getitem__(self, key: Any) -> Any:
        return self.__get_and_set()[key]

    def __repr__(self) -> str:
        return f"_LazyProxy({type(self).__name__},{self.__parent})"


def lazy_proxy(f: Callable[[Any], Any], name: str) -> type[_LazyProxyPerf]:
    class _(_LazyProxyPerf):
        pass

    out = _
    out.__name__ = name
    return out


class Node[T: NodeAttributes = NodeAttributes](metaclass=NodeMeta):
    Attributes = NodeAttributes
    _type_cache: dict[tuple[int, int], graph.BoundNode] = {}
    __fields: dict[str, Field] = {}
    __proxys: list[type[_LazyProxyPerf]] = []
    _seen_types = dict[str, type["NodeT"]]()
    _override_type_identifier: str | None = None

    def __init__(self, instance: graph.BoundNode) -> None:
        self.instance = instance

        # setup instance accessors
        # perfomance optimization: only load fields when needed
        # self._load_fields()
        for pt in type(self).__proxys:
            p = pt(self)
            super().__setattr__(pt.__name__, p)

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
        cls._type_cache = {}
        cls.__fields = {}
        cls.__proxys = []

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

        cls._register_type()

    @classmethod
    def _type_identifier(cls) -> str:
        if cls._override_type_identifier:
            return cls._override_type_identifier

        module = cls.__module__
        # reverse for strcmp efficiency
        modname = ".".join(reversed(module.split(".")))
        clsname = cls.__name__
        # TODO dont hardcode lib name
        # don't prefix library types, so ato can import them by name
        if module.startswith("faebryk.library.") or not (
            module.startswith("faebryk.") or module.startswith("atopile.")
        ):
            # anonymous temporary test classes can be randomized
            if clsname.startswith("_"):
                clsname = f"{clsname}{id(cls):X}"

            return clsname

        return clsname + "." + modname

    @classmethod
    def _register_type(cls) -> None:
        t_id = cls._type_identifier()
        if (existing_type := cls._seen_types.get(t_id)) and existing_type != cls:
            raise FabLLException(
                f"Type {t_id} already registered for "
                f"{existing_type}({id(existing_type):X}) "
                f"cannot register {cls}({id(cls):X})"
            )
        cls._seen_types[t_id] = cls

    @classmethod
    def _rename_type(cls, name: str) -> None:
        # delete registration
        old_t_id = cls._type_identifier()
        del cls._seen_types[old_t_id]

        # reregister
        cls._override_type_identifier = name
        cls._register_type()

    @staticmethod
    def _copy_type[U: "type[NodeT]"](to_copy: U, name: str) -> U:
        class _Copy(to_copy):
            __COPY_TYPE__ = True
            _override_type_identifier = name

        _Copy.__name__ = name

        return cast(U, _Copy)

    @classmethod
    def _exec_field(
        cls,
        t: "TypeNodeBoundTG[Self, T]",
        field: Field,
        type_field: bool = False,
        source_chunk_node: "Node | None" = None,
    ) -> None:
        type_field = type_field or field._type_child
        if isinstance(field, _ChildField):
            identifier = field.get_identifier()
            for dependant in field._prepend_dependants:
                cls._exec_field(
                    t=t,
                    field=dependant,
                    type_field=type_field,
                    source_chunk_node=source_chunk_node,
                )
            if type_field:
                if isinstance(field.nodetype, str):
                    raise FabLLException(
                        f"Type reference not resolved for child {identifier}"
                    )
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
                if source_chunk_node is not None:
                    child_instance.add_source_chunk_trait(source_chunk_node)
            else:
                mc = t.MakeChild(
                    nodetype=field.nodetype,
                    identifier=identifier,
                    attributes=cast(NodeAttributes, field.attributes),
                )
                makechild = mc._add_to_typegraph()
                if source_chunk_node is not None:
                    cls(makechild).set_source_pointer(source_chunk_node)
            for dependant in field._dependants:
                cls._exec_field(
                    t=t,
                    field=dependant,
                    type_field=type_field,
                    source_chunk_node=source_chunk_node,
                )
        elif isinstance(field, ListField):
            for nested_field in field.get_fields():
                cls._exec_field(
                    t=t,
                    field=nested_field,
                    type_field=type_field,
                    source_chunk_node=source_chunk_node,
                )
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
                make_link = t.MakeEdge(
                    lhs_reference_path=field.lhs_resolved(),
                    rhs_reference_path=field.rhs_resolved(),
                    edge=field.edge,
                )
                if source_chunk_node is not None:
                    cls(make_link).set_source_pointer(source_chunk_node)

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
        if isinstance(value, list) and len(value):
            # Flatten nested lists (e.g., from multiple MakeConnectionEdge calls)
            # MakeConnectionEdge returns list[_EdgeField], so a list of those calls
            # produces list[list[_EdgeField]] which needs flattening
            flattened: list[Field] = []
            for item in value:
                if isinstance(item, Field):
                    flattened.append(item)
                elif isinstance(item, list) and all(isinstance(c, Field) for c in item):
                    flattened.extend(item)
            if flattened and all(isinstance(c, Field) for c in flattened):
                cls._add_field(locator=name, field=ListField(fields=flattened))

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
        cls.__proxys.append(lazy_proxy(f=cls._load_fields, name=locator))

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
            bound_node=fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg, cls),
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
        return TypeNodeBoundTG(tg=tg, t=cls)

    @classmethod
    def bind_typegraph_from_instance[N: NodeT](
        cls: type[N], instance: graph.BoundNode
    ) -> "TypeNodeBoundTG[N, T]":
        return cls.bind_instance(instance=instance).bind_typegraph_from_self()

    @classmethod
    def bind_instance(cls, instance: graph.BoundNode) -> Self:
        return cls(instance=instance)

    # instance methods -----------------------------------------------------------------
    def add_child(self, node: "NodeT", identifier: str | None = None):
        assert node.get_parent() is None, "Node already has a parent"
        fbrk.EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier=identifier or f"{_UniqueKey.get():x}",
        )

    # TODO this is soooo slow
    # def __setattr__(self, name: str, value: Any, /) -> None:
    #    if not name.startswith("_") and isinstance(value, Node):
    #        self.add(value, identifier=name)
    #    return super().__setattr__(name, value)

    @once
    def attributes(self) -> T:
        Attributes = cast(type[T], type(self).Attributes)
        return Attributes.of(self.instance)

    def get_root_id(self) -> str:
        return f"0x{self.instance.node().get_uuid():X}"

    def get_name(self, accept_no_parent: bool = True, with_detail: bool = False) -> str:
        from faebryk.library.has_name_override import has_name_override

        if (has_name := self.try_get_trait(has_name_override)) is not None:
            return has_name.get_name(with_detail=with_detail)
        elif (parent := self.get_parent()) is not None:
            return parent[1]
        elif accept_no_parent:
            return self.get_root_id()
        else:
            raise FabLLException("Node has no parent")

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
            if any(not ref_node.is_same(h[i][0]) for h in hierarchies[1:]):
                break
            last_match = (ref_node, ref_name)

        return last_match

    def get_children[C: Node](
        self,
        direct_only: bool,
        types: type[C] | tuple[type[C], ...],
        include_root: bool = False,
        f_filter: Callable[[C], bool] | None = None,
        sort: bool = True,
        required_trait: "type[NodeT] | tuple[type[NodeT], ...] | None" = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> list[C]:
        # This function is optimized to basically 0 overhead in python

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
                TypeNodeBoundTG.get_or_create_type_in_tg(tg, t).node()
                for t in type_tuple
            ]

        # Convert Python trait types to Zig trait type nodes
        zig_traits: list[graph.Node] | None = None
        if trait_tuple:
            zig_traits = [
                TypeNodeBoundTG.get_or_create_type_in_tg(tg, t).node()
                for t in trait_tuple
            ]

        # Call Zig get_children_query
        bound_nodes = fbrk.EdgeComposition.get_children_query(
            bound_node=self.instance,
            direct_only=direct_only,
            types=zig_types,
            include_root=include_root,
            sort=sort,
            required_traits=zig_traits,
        )

        # fast cast
        if zig_types and len(zig_types) == 1:
            tp = type_tuple[0]

            def _cast(n: graph.BoundNode) -> C:
                return tp.bind_instance(n)
        elif zig_types:
            paired = list(zip(type_tuple, zig_types, strict=True))
            type_dict = {zigt.get_uuid(): pyt for pyt, zigt in paired}

            def _cast(n: graph.BoundNode) -> C:
                node_typenode = fbrk.EdgeType.get_type_node(
                    edge=not_none(fbrk.EdgeType.get_type_edge(bound_node=n)).edge()
                )
                return type_dict[node_typenode.get_uuid()].bind_instance(n)
        else:

            def _cast(n: graph.BoundNode) -> C:
                return cast(C, Node.bind_instance(instance=n))

        # Convert BoundNode results back to Python Node objects
        nodes = (_cast(n) for n in bound_nodes)
        if f_filter:
            result: list[C] = [node for node in nodes if f_filter(node)]
        else:
            result = list(nodes)

        return result

    @property
    def tg(self) -> fbrk.TypeGraph:
        tg = fbrk.TypeGraph.of_instance(instance_node=self.instance)
        if tg is None:
            tg = fbrk.TypeGraph.of_type(type_node=self.instance)
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
        return fbrk.TypeGraph.get_type_name(type_node=type_node)

    def isinstance(self, *type_node: "type[NodeT]") -> bool:
        """
        Wildcard: Node
        """
        if Node in type_node:
            return True
        tn = self.get_type_name()
        if not tn:
            return False
        # a bit of a hack, but this should be fast
        # also internally thats exactly what would happen
        return any(tn == t._type_identifier() for t in type_node)

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

    def get_path_from_ancestor(self, ancestor: "NodeT") -> list[str]:
        """
        Get the composition-edge path from an ancestor to this node.

        Returns an empty list if the ancestor is this node or is not in the
        hierarchy.
        """
        hierarchy = self.get_hierarchy()
        for idx, (node, _name) in enumerate(hierarchy):
            if node.is_same(ancestor):
                return [name for _node, name in hierarchy[idx + 1 :]]
        return []

    def is_in_graph(self, g: graph.GraphView) -> bool:
        return Node.graphs_match(self.g, g)

    def is_in_typegraph(self, tg: fbrk.TypeGraph) -> bool:
        return self.nodes_match(self.tg.get_self_node(), tg.get_self_node())

    @staticmethod
    def nodes_match(*ns: graph.BoundNode) -> bool:
        return len(set(n.node().get_uuid() for n in ns)) == 1 and Node.graphs_match(
            *[n.g() for n in ns]
        )

    @staticmethod
    def graphs_match(*gs: graph.GraphView) -> bool:
        return len(set(g.get_self_node().node().get_uuid() for g in gs)) == 1

    def copy_into(self, g: graph.GraphView) -> Self:
        """
        Copy all nodes in hierarchy and edges between them and their types
        """
        if (
            self.g.get_self_node().node().get_uuid()
            == g.get_self_node().node().get_uuid()
        ):
            return self
        fbrk.TypeGraph.copy_node_into(start_node=self.instance, target_graph=g)
        return self.bind_instance(instance=g.bind(node=self.instance.node()))

    def get_full_name(
        self, types: bool = False, include_uuid: bool = True, with_detail: bool = False
    ) -> str:
        """
        Returns node name + heirarchy
        """
        from faebryk.library.has_name_override import has_name_override

        # Try to get name override, but gracefully handle missing TypeGraph
        # (can happen during solver mutation when nodes are in copied graphs)
        try:
            if (has_name := self.try_get_trait(has_name_override)) is not None:
                return has_name.get_name(with_detail=with_detail)
        except FabLLException:
            pass  # No TypeGraph available, fall through to default naming

        parts: list[str] = []
        if (parent := self.get_parent()) is not None:
            parent_node, name = parent
            if not parent_node.no_include_parents_in_full_name:
                if parent_full := parent_node.get_full_name(
                    types=types, include_uuid=include_uuid, with_detail=with_detail
                ):
                    parts.append(parent_full)
            if name:
                parts.append(name)
            elif include_uuid:
                parts.append(self.get_root_id())
        elif not self.no_include_parents_in_full_name:
            if include_uuid:
                parts.append(self.get_root_id())

        base = ".".join(parts)
        if types:
            type_name = self.get_type_name() or "<NOTYPE>"
            return f"{base}|{type_name}" if base else type_name
        return base

    def pretty_repr(self) -> str:
        return re.sub(
            r"[^|]*?\.ato::",
            "",
            self.get_full_name(types=True, include_uuid=False),
        )

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
                solver.extract_superset(
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

    def try_get_trait[TR: NodeT](self, trait: type[TR], required=False) -> TR | None:
        trait_type = TypeNodeBoundTG.get_or_create_type_in_tg(self.tg, trait)
        impl = fbrk.Trait.try_get_trait(
            target=self.instance,
            trait_type=trait_type,
        )
        if impl is None:
            # just for better debugging
            if required:
                raise TraitNotFound(f"No trait {trait} found on {self}")
            return None
        return trait(impl)

    def get_trait[TR: Node](self, trait: type[TR]) -> TR:
        return cast(TR, self.try_get_trait(trait, required=True))

    def has_trait(self, trait: type["NodeT"]) -> bool:
        return self.try_get_trait(trait) is not None

    def try_get_traits(
        self, *traits: type["NodeT"]
    ) -> dict[type["NodeT"], "Node | None"]:
        """
        Batch lookup of multiple traits on this node.
        Returns a dict mapping each trait type to its instance (or None if not found).
        More efficient than calling try_get_trait multiple times due to reduced
        Python-Zig boundary crossings.
        """
        if not traits:
            return {}

        # Prepare trait type nodes for batch lookup
        trait_type_nodes = [
            TypeNodeBoundTG.get_or_create_type_in_tg(tg=self.tg, t=trait)
            for trait in traits
        ]

        # Batch call to Zig
        results = fbrk.Trait.try_get_traits(
            target=self.instance,
            trait_types=trait_type_nodes,
        )

        # Convert results to dict with proper binding
        return {
            trait: (trait.bind_instance(instance=impl) if impl is not None else None)
            for trait, impl in zip(traits, results)
        }

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
        return t(self.instance)

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
        return f"<{cls_id} '{self.get_full_name()}'{suffix}>"

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

    # debug ----------------------------------------------------------------------------
    def debug_print_tree(
        self,
        show_composition: bool = True,
        show_traits: bool = True,
        show_connections: bool = True,
        show_operands: bool = True,
        show_pointers: bool = True,
    ) -> None:
        from faebryk.core.graph_render import GraphRenderer

        print(
            GraphRenderer().render(
                self.instance,
                show_composition=show_composition,
                show_pointers=show_pointers,
                show_operands=show_operands,
                show_traits=show_traits,
                show_connections=show_connections,
            )
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

    def try_get_trait_of_type[TR: NodeT](self, trait: type[TR]) -> TR | None:
        type_node = self.get_type_node()
        if type_node is None:
            return None
        return TypeNodeBoundTG.try_get_trait_of_type(trait=trait, type_node=type_node)

    def set_source_pointer(self, source_chunk_node: "Node") -> None:
        """Set source pointer on MakeChild for typegraph to read during instantiation"""
        fbrk.EdgePointer.point_to(
            bound_node=self.instance,
            target_node=source_chunk_node.instance.node(),
            identifier="source",
            index=None,
        )

    def add_source_chunk_trait(self, source_chunk_node: "Node") -> None:
        import faebryk.library._F as F

        Traits.create_and_add_instance_to(node=self, trait=F.has_source_chunk).setup(
            source_chunk_node=source_chunk_node.instance.node()
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

    @staticmethod
    def _get_tg_hash(tg: fbrk.TypeGraph) -> tuple[int, int]:
        tg_bnode = tg.get_self_node()
        return (
            tg_bnode.node().get_uuid(),
            tg_bnode.g().get_self_node().node().get_uuid(),
        )

    # node type methods ----------------------------------------------------------------
    @staticmethod
    def get_or_create_type_in_tg(tg: fbrk.TypeGraph, t: type[NodeT]) -> graph.BoundNode:
        # this is some optimization to avoid binding
        # you would think bind is fast, but python works in mysterious ways

        if typenode := t._type_cache.get(TypeNodeBoundTG._get_tg_hash(tg)):
            return typenode
        return t.bind_typegraph(tg).get_or_create_type()

    def get_or_create_type(self) -> graph.BoundNode:
        """
        Builds Type node and returns it
        """
        tg = self.tg
        tg_hash = TypeNodeBoundTG._get_tg_hash(tg)
        if typenode := self.t._type_cache.get(tg_hash):
            return typenode
        typenode = tg.get_type_by_name(type_identifier=self.t._type_identifier())
        if typenode is not None:
            self.t._type_cache[tg_hash] = typenode
            return typenode
        typenode = tg.add_type(identifier=self.t._type_identifier())
        self.t._type_cache[tg_hash] = typenode
        TypeNodeBoundTG.__TYPE_NODE_MAP__[typenode] = self
        self.t._create_type(self)
        tg.mark_constructable(type_node=typenode)
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
        out = self.t.bind_instance(instance=instance)
        # little optimization, only useful for heavy read after creation
        # pretty useless for creation heavy
        # if attributes is not None:
        #    out.attributes = lambda: attributes
        return out

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
        return [self.t(instance) for instance in instances]

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
    def nodes_of_type[N2: Node](self, t: type[N2]) -> OrderedSet[N2]:
        return OrderedSet(t.bind_typegraph(self.tg).get_instances())

    def nodes_of_types(self, t: tuple[type["Node"], ...]) -> OrderedSet["Node"]:
        out: OrderedSet[Node] = OrderedSet()
        for tn in t:
            out.update(tn.bind_typegraph(self.tg).get_instances())
        return out

    # construction ---------------------------------------------------------------------
    def MakeChild[C: NodeT](
        self,
        nodetype: type[C] | str,
        *,
        identifier: str | None | PLACEHOLDER = PLACEHOLDER(),
        attributes: NodeAttributes | None = None,
    ) -> InstanceChildBoundType[C]:
        return InstanceChildBoundType(
            nodetype=nodetype,
            t=self,
            identifier=identifier,
            attributes=attributes,
        )

    def MakeEdge(
        self,
        *,
        lhs_reference_path: list[str | fbrk.EdgeTraversal],
        rhs_reference_path: list[str | fbrk.EdgeTraversal],
        edge: fbrk.EdgeCreationAttributes,
    ) -> graph.BoundNode:
        tg = self.tg
        type_node = self.get_or_create_type()

        def normalize_path(
            path: list[str | fbrk.EdgeTraversal],
        ) -> list[str | fbrk.EdgeTraversal]:
            """Convert self-reference markers to proper EdgeTraversal.

            The zig layer uses EdgeComposition.traverse("") to represent "self".
            Convert:
            - [] (empty list) -> self reference
            - [""] (SELF_OWNER_PLACEHOLDER) -> self reference
            """
            if not path or path == SELF_OWNER_PLACEHOLDER:
                return [fbrk.EdgeComposition.traverse(identifier="")]
            return path

        lhs_path = normalize_path(lhs_reference_path)
        rhs_path = normalize_path(rhs_reference_path)

        lhs_ref = tg.ensure_child_reference(
            type_node=type_node, path=lhs_path, validate=False
        )
        rhs_ref = tg.ensure_child_reference(
            type_node=type_node, path=rhs_path, validate=False
        )

        return tg.add_make_link(
            type_node=type_node,
            lhs_reference=lhs_ref,
            rhs_reference=rhs_ref,
            edge_attributes=edge,
        )

    @staticmethod
    def has_instance_of_type_has_trait(
        type_node: graph.BoundNode, trait: type[NodeT]
    ) -> bool:
        tg = fbrk.TypeGraph.of_type(type_node=type_node)
        assert tg
        children = Node.bind_instance(instance=type_node).get_children(
            direct_only=True, types=MakeChild, tg=tg
        )
        bound_trait = TypeNodeBoundTG.get_or_create_type_in_tg(tg, trait)
        for child in children:
            child_type = child.get_child_type()
            if child_type.node().is_same(other=bound_trait.node()):
                return True
        return False

    def check_if_instance_of_type_has_trait(self, trait: type[NodeT]) -> bool:
        return self.has_instance_of_type_has_trait(
            type_node=self.get_or_create_type(), trait=trait
        )

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
            trait_type=TypeNodeBoundTG.get_or_create_type_in_tg(self.tg, trait),
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
        trait_bound = trait.bind_typegraph(node.tg).get_or_create_type()
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

    @staticmethod
    def is_trait_type(type_: type[NodeT]) -> bool:
        for attr in type_.__dict__.values():
            if isinstance(attr, _ChildField) and attr.nodetype == ImplementsTrait:
                return True
        return False

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

        @deprecated("Use try_get or force_get instead")
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

    _override_type_identifier = "ImplementsTrait"


class ImplementsType(Node):
    """
    Wrapper around zig type.
    Matched automatically because of name.
    """

    _override_type_identifier = "ImplementsType"


class MakeChild(Node):
    """
    Wrapper around zig make child.
    Matched automatically because of name.
    """

    _override_type_identifier = "MakeChild"

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

    def get_module_locator(self) -> str:
        return self.get_obj().get_full_name(include_uuid=False, types=True)


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
            source=self.get_obj().instance, target=other.instance
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
    def group_into_buses[N: NodeT](nodes: Iterable[N]) -> dict[N, set[N]]:
        remaining = set(nodes)
        buses: dict[N, set[N]] = {}

        logger = logging.getLogger(__name__)

        while remaining:
            interface = remaining.pop()
            logger.info(f"Grouping bus: {interface.get_full_name()}")
            connected = cast(
                set[N],
                interface.get_trait(is_interface)
                .get_connected(include_self=True)
                .keys(),
            )
            logger.info(f"Grouping complete. Elements: {len(connected)}")
            logger.info({i.get_full_name() for i in connected})
            buses[interface] = connected
            remaining.difference_update(connected)

        return buses

    @staticmethod
    def MakeConnectionEdge(*nodes: RefPath, shallow: bool = False) -> list[_EdgeField]:
        if not len(nodes) >= 2:
            return []
        src = nodes[0]
        return [
            MakeEdge(
                src,
                dst,
                edge=fbrk.EdgeInterfaceConnection.build(shallow=shallow),
            )
            for dst in nodes[1:]
        ]


class is_abstract(Node):
    is_trait = ImplementsTrait.MakeChild().put_on_type()


class is_immutable(Node):
    is_trait = ImplementsTrait.MakeChild().put_on_type()


# --------------------------------------------------------------------------------------
# TODO remove
# re-export graph.GraphView to be used from fabll namespace
Graph = fbrk.TypeGraph
# Node type aliases
Module = Node
type Module = Node


# --------------------------------------------------------------------------------------
# Rendering


# TODO merge with/move to graph_render.py
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
    def collect_interface_connections(
        node: graph.BoundNode, root: "Node", edge_type: int
    ) -> list[str]:
        """Collect interface connection descriptions for a node."""
        interface_edges: list[graph.BoundEdge] = []
        node.visit_edges_of_type(
            edge_type=edge_type,
            ctx=interface_edges,
            f=lambda acc, bound_edge: acc.append(bound_edge),
        )

        if edge_type == fbrk.EdgeOperand.get_tid():
            edgechar = "op>"
        elif edge_type == fbrk.EdgeInterfaceConnection.get_tid():
            edgechar = "~"
        elif edge_type == fbrk.EdgeTrait.get_tid():
            edgechar = "t~"
        else:
            raise ValueError(f"Assign edgechar for edge type: {edge_type}")
        connections = []
        for bound_edge in interface_edges:
            if bound_edge.edge().source().is_same(other=node.node()):
                partner_ref = bound_edge.edge().target()
            elif bound_edge.edge().target().is_same(other=node.node()):
                partner_ref = bound_edge.edge().source()
            else:
                continue

            partner_node = Node.bind_instance(bound_edge.g().bind(node=partner_ref))
            connections.append(f"{edgechar} {partner_node.relative_address(root=root)}")

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
    @dataclass
    class FileLocationAttributes(NodeAttributes):
        start_line: int
        start_column: int
        end_line: int
        end_column: int

    class FileLocation(Node[FileLocationAttributes]):
        Attributes = FileLocationAttributes

    class TestNodeWithoutAttr(Node):
        pass

    @dataclass
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
            edge=fbrk.EdgePointer.build(identifier=None, index=None),
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
    fileloc_from_graph = FileLocation.bind_instance(fileloc.instance)
    print("fileloc_from_graph:", fileloc_from_graph.attributes())

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
    assert res_inst.resistance.get().force_get_units().get_symbols()[0] == "Ω"
    assert res_inst.resistance.get().force_get_units().get_symbols()[1] == "ohm"
    assert res_inst.get_trait(is_module)
    leads = [
        n.get_trait(F.Lead.is_lead)
        for n in res_inst.get_children(
            direct_only=False, types=Node, required_trait=F.Lead.is_lead
        )
    ]
    assert leads[0].get_lead_name() == "unnamed[0]"
    assert leads[1].get_lead_name() == "unnamed[1]"
    assert (
        Traits(res_inst._is_pickable.get().get_param("resistance"))
        .get_obj_raw()
        .get_name()
        == "resistance"
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
    string_p.set_singleton(value="IG constrained")
    assert string_p.extract_singleton() == "IG constrained"

    class ExampleStringParameter(Node):
        string_p_tg = F.Parameters.StringParameter.MakeChild()
        constraint = F.Literals.Strings.MakeChild_SetSuperset(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().extract_singleton() == "TG constrained"


def test_boolean_param():
    g, tg = _make_graph_and_typegraph()
    import faebryk.library._F as F

    boolean_p = F.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.set_singleton(value=True)
    assert boolean_p.force_extract_superset().get_values()

    class ExampleBooleanParameter(Node):
        boolean_p_tg = F.Parameters.BooleanParameter.MakeChild()
        constraint = F.Literals.Booleans.MakeChild_SetSuperset([boolean_p_tg], True)

    ebp = ExampleBooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert ebp.boolean_p_tg.get().force_extract_superset().get_values()


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
    class NewType(Node):
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

    class _M(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())

    class _App(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())
        m = _M.MakeChild()

    app = _App.bind_typegraph(tg).create_instance(g=g)
    m = app.m.get()

    mods = app.get_children(direct_only=False, types=Node, required_trait=is_module)
    assert mods == [m]


def test_get_children_modules_hard():
    import faebryk.library._F as F
    from faebryk.libs.util import duplicates

    g, tg = _make_graph_and_typegraph()

    class _App(Node):
        resistors = [F.Resistor.MakeChild() for _ in range(2)]
        _is_module = Traits.MakeEdge(is_module.MakeChild())

    app = _App.bind_typegraph(tg).create_instance(g=g)

    rs = app.get_children(direct_only=False, types=F.Resistor)
    assert rs == [app.resistors[0].get(), app.resistors[1].get()]

    elec = app.get_children(direct_only=False, types=F.Electrical)
    assert elec == [
        app.resistors[0].get().unnamed[0].get(),
        app.resistors[0].get().unnamed[1].get(),
        app.resistors[1].get().unnamed[0].get(),
        app.resistors[1].get().unnamed[1].get(),
    ]

    mods = app.get_children(
        direct_only=False,
        types=Node,
        required_trait=is_module,
        include_root=True,
        sort=True,
    )
    # print(GraphRenderer.render(app.instance))
    assert mods == [app, app.resistors[0].get(), app.resistors[1].get()]

    all_nodes = app.get_children(
        direct_only=False, types=Node, include_root=True, sort=True
    )
    assert all_nodes
    dups = duplicates(all_nodes, lambda x: x.instance.node().get_uuid())
    for _, v in dups.items():
        print(f"dup: {len(v):2d}: {v[0].get_full_name(types=True)}")
    assert not len(dups)


def test_get_children_modules_tree():
    g, tg = _make_graph_and_typegraph()

    class Capacitor(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())

    class CapacitorContainer(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())
        cap1 = Capacitor.MakeChild()
        cap2 = Capacitor.MakeChild()

    class _App(Node):
        _is_module = Traits.MakeEdge(is_module.MakeChild())
        container1 = CapacitorContainer.MakeChild()
        container2 = CapacitorContainer.MakeChild()

    app = _App.bind_typegraph(tg).create_instance(g=g)
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
    assert mods == [cap1, cap2]

    mods = app.get_children(
        direct_only=False,
        types=Capacitor,
        required_trait=is_module,
    )
    assert mods == [cap1, cap2, cap3, cap4]


def test_copy_into_basic():
    g, tg = _make_graph_and_typegraph()
    g_new = graph.GraphView.create()

    class _Inner(Node):
        pass

    class _N(Node):
        inner = _Inner.MakeChild()

    class _Outer(Node):
        n = _N.MakeChild()
        m = _N.MakeChild()
        o = _N.MakeChild()

    outer = _Outer.bind_typegraph(tg).create_instance(g=g)
    m = outer.m.get()
    n = outer.n.get()
    o = outer.o.get()
    m.connect(to=n, edge_attrs=fbrk.EdgePointer.build(identifier=None, index=None))
    n.connect(to=o, edge_attrs=fbrk.EdgePointer.build(identifier=None, index=None))

    assert fbrk.EdgePointer.get_referenced_node_from_node(node=n.instance) == o.instance
    assert fbrk.EdgePointer.get_referenced_node_from_node(node=m.instance) == n.instance

    n2 = n.copy_into(g=g_new)
    n.debug_print_tree()
    n2.debug_print_tree()

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
        f = Node.bind_instance(instance=n)
        return repr(f)

    def _container(ns: Iterable[Node]) -> str:
        return indented_container(
            sorted(ns, key=lambda x: repr(x)), compress_large=1000
        )

    g_nodes = {
        n.node().get_uuid(): Node.bind_instance(instance=n) for n in g.get_nodes()
    }
    g_new_nodes = {
        n.node().get_uuid(): Node.bind_instance(instance=n) for n in g_new.get_nodes()
    }
    g_diff_new = {v for k, v in g_new_nodes.items() if k not in g_nodes}
    g_diff_old = {v for k, v in g_nodes.items() if k not in g_new_nodes}
    # tg.self & g_new.self

    print("g", _container(g_nodes.values()))
    print("g_new", _container(g_new_nodes.values()))
    print("g_diff", _container(g_diff_old))
    print("g_diff_new", _container(g_diff_new))

    # only new graph self node
    assert len(g_diff_new) == 1, f"g_diff_new: {_container(g_diff_new)}"

    assert n2.is_same(n, allow_different_graph=True)
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
    assert inner2.is_same(n.inner.get(), allow_different_graph=True)

    assert n2.isinstance(_N)
    assert inner2.isinstance(_Inner)


def test_type_name_collision_raises_error():
    """
    Test that registering two different classes with the same name raises an error.

    The collision is detected at class definition time via __init_subclass__ ->
    _register_type().
    """

    class MyType(Node):  # type: ignore[no-redef]
        pass

    # Second class definition with same name should raise immediately
    with pytest.raises(FabLLException, match="already registered"):

        class MyType(Node):  # noqa: F811
            some_field: int = 42


def test_same_class_multiple_get_or_create_type_succeeds():
    """Test that calling get_or_create_type multiple times on the same class works."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _MyType(Node):
        pass

    bound = _MyType.bind_typegraph(tg)

    # Multiple calls should return the same type node
    type1 = bound.get_or_create_type()
    type2 = bound.get_or_create_type()
    assert type1.node().is_same(other=type2.node())


def test_tg_merge_copy():
    from faebryk.core.graph_render import GraphRenderer

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _MyType(Node):
        pass

    class _MyType2(Node):
        pass

    mytype = _MyType.bind_typegraph(tg)
    inst1 = mytype.create_instance(g=g)

    g2 = graph.GraphView.create()
    # this will copy MyType to the new tg and create it there
    copy_inst1 = inst1.copy_into(g=g2)
    tg2 = fbrk.TypeGraph.of_instance(instance_node=copy_inst1.instance)
    assert tg2
    assert tg2.get_self_node().node().is_same(other=tg.get_self_node().node())
    print(tg2.get_type_instance_overview())
    print(GraphRenderer().render(tg2.get_self_node()))

    mytype2 = _MyType2.bind_typegraph(tg)
    inst2 = mytype2.create_instance(g=g)

    # this will create a new type node in the new tg that doesnt mirror the one in g
    inst3 = _MyType2.bind_typegraph(tg2).create_instance(g=g2)
    print(tg2.get_type_instance_overview())
    print(GraphRenderer().render(tg2.get_self_node()))

    # this should cause a panic, because the type name collision is not handled yet
    copy_inst2 = inst2.copy_into(g=g2)
    print(tg2.get_type_instance_overview())
    print(inst3.get_type_node())
    print(copy_inst2.get_type_node())
    print(GraphRenderer().render(tg2.get_self_node()))

    assert dict(tg2.get_type_instance_overview())[_MyType2._type_identifier()] == 2


if __name__ == "__main__":
    import typer

    import faebryk.core.node as fabll
    # typer.run(test_fabll_basic)

    # test_manual_resistor_def()

    # typer.run(test_resistor_instantiation)
    typer.run(fabll.test_get_children_modules_hard)
