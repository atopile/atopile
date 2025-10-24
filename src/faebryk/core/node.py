# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Self, cast, override

from ordered_set import OrderedSet
from typing_extensions import Callable, deprecated

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.faebryk.next import EdgeNext
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
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
    not_none,
    zip_dicts_by_key,
)


class FaebrykApiException(Exception):
    pass


class TraitNotFound(FaebrykApiException):
    pass


class Child[T: Node[Any]]:
    def __init__[N: Node](self, nodetype: type[T], t: "BoundNodeType[N, Any]") -> None:
        self.nodetype = nodetype
        self.t = t
        self.identifier: str = None  # type: ignore

        if nodetype.Attributes is not NodeAttributes:
            raise FaebrykApiException(
                f"Can't have Child with custom Attributes: {nodetype.__name__}"
            )

    def get(self) -> T:
        raise FaebrykApiException(
            "Called on class child instead of bound instance child"
        )

    def get_unbound(self, instance: BoundNode) -> T:
        assert self.identifier is not None, "Bug: Needs to be set on setattr"

        child_instance = not_none(
            EdgeComposition.get_child_by_identifier(
                node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound

    def bind(self, node: BoundNode):
        return BoundChild(child=self, instance=node)


class BoundChild[T: Node](Child[T]):
    def __init__(self, child: Child, instance: BoundNode) -> None:
        self.nodetype = child.nodetype
        self.node = child.nodetype
        self.identifier = child.identifier
        self.t = child.t
        self._instance = instance

    def get(self) -> T:
        return self.get_unbound(instance=self._instance)


class BoundChildOfType[T: Node[Any]]:
    """
    Child of type
    Adds child directly to type node, will not create child in every instance
    Inherintly bound to the type node by definition, therefore no unbound version
    """

    def __init__[N: Node](self, nodetype: type[T], t: "BoundNodeType[N, Any]") -> None:
        # TODO: why so many nodetype references
        self.nodetype = nodetype
        self.t = t
        self.identifier: str = None  # type: ignore
        self._instance = t.get_or_create_type()

        if nodetype.Attributes is not NodeAttributes:
            raise FaebrykApiException(
                f"Can't have Child with custom Attributes: {nodetype.__name__}"
            )

    def get(self) -> T:
        return self.get_unbound(instance=self._instance)

    def get_unbound(self, instance: BoundNode) -> T:
        assert self.identifier is not None, "Bug: Needs to be set on setattr"

        child_instance = not_none(
            EdgeComposition.get_child_by_identifier(
                node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound


class NodeMeta(type):
    @override
    def __setattr__(cls, name: str, value: Any, /) -> None:
        if isinstance(value, Child) and issubclass(cls, Node):
            value.identifier = name
            cls._add_child(value)
        if isinstance(value, BoundChildOfType) and issubclass(cls, Node):
            value.identifier = name
            cls._add_child_to_type(child=value)
        return super().__setattr__(name, value)


@dataclass(frozen=True)
class NodeAttributes:
    def __init_subclass__(cls) -> None:
        # TODO collect all fields (like dataclasses)
        # TODO check Attributes is dataclass and frozen
        pass

    @classmethod
    def of(cls: type[Self], node: "BoundNode | Node[Any]") -> Self:
        if isinstance(node, Node):
            node = node.instance
        return cls(**node.node().get_dynamic_attrs())

    def to_dict(self) -> dict[str, Any]:
        return dataclass_as_kwargs(self)


class Node[T: NodeAttributes = NodeAttributes](metaclass=NodeMeta):
    Attributes = NodeAttributes

    def __init__(self, instance: BoundNode) -> None:
        self.instance = instance
        for name, child in vars(type(self)).items():
            if not isinstance(child, Child):
                continue
            setattr(self, name, child.bind(instance))

    def __init_subclass__(cls) -> None:
        # Ensure single-level inheritance: NodeType subclasses should not themselves
        # be subclassed further.
        if len(cls.__mro__) > len(Node.__mro__) + 1:
            # mro(): [Leaf, NodeType, object] is allowed (len==3),
            # deeper (len>3) is forbidden
            raise FaebrykApiException(
                f"{cls.__qualname__} subclasses cannot themselves be subclassed "
                f"more than one level deep (found: {cls.__mro__})"
            )
        super().__init_subclass__()

    @classmethod
    def __create_instance__(cls, tg: TypeGraph, g: GraphView) -> Self:
        """DO NOT OVERRIDE!"""

        return cls.bind_typegraph(tg=tg).create_instance(g=g)

    @classmethod
    def _type_identifier(cls) -> str:
        return cls.__name__

    # type construction ----------------------------------------------------------------
    @classmethod
    def _add_child(
        cls,
        child: Child,
    ) -> BoundNode:
        tg = child.t.tg
        identifier = child.identifier
        nodetype = child.nodetype

        child_type_node = nodetype.bind_typegraph(tg).get_or_create_type()
        return tg.add_make_child(
            type_node=cls.bind_typegraph(tg).get_or_create_type(),
            child_type_node=child_type_node,
            identifier=identifier,
        )

    @classmethod
    def _add_child_to_type(
        cls,
        child: BoundChildOfType,
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
        child: Child[Any],
    ):
        cls._add_child(child)

    # bindings -------------------------------------------------------------------------
    @classmethod
    def bind_typegraph[N: Node[Any]](
        cls: type[N], tg: TypeGraph
    ) -> "BoundNodeType[N, T]":
        return BoundNodeType[N, T](tg=tg, t=cls)

    @classmethod
    def bind_typegraph_from_instance[N: Node[Any]](
        cls: type[N], instance: BoundNode
    ) -> "BoundNodeType[N, T]":
        return cls.bind_instance(instance=instance).bind_typegraph_from_self()

    @classmethod
    def bind_instance(cls, instance: BoundNode) -> Self:
        return cls(instance=instance)

    # instance methods -----------------------------------------------------------------
    @deprecated("Use compose_with instead")
    def add(self, node: "Node[Any]"):
        self.compose_with(node)

    def __setattr__(self, name: str, value: Any, /) -> None:
        if isinstance(value, Node) and not name.startswith("_"):
            self.compose_with(value, name=name)
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
            raise FaebrykApiException("Node has no parent")
        return parent[1]

    def get_type_name(self) -> str | None:
        # TODO: move to EdgeType

        if (type_edge := EdgeType.get_type_edge(bound_node=self.instance)) is None:
            return None

        type_node = EdgeType.get_type_node(edge=type_edge.edge())
        type_bound = type_edge.g().bind(node=type_node)
        type_name = type_bound.node().get_attr(key="type_identifier")
        return cast_assert(str, type_name)

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
            raise FaebrykApiException("Node has no parent")
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

    def get_child(self, name: str) -> "Node[Any]":
        # TODO: improve this implementation
        children: list["Node[Any]"] = []

        def collect(ctx: list["Node[Any]"], edge: BoundEdge) -> None:
            if edge.edge().name() == name:
                ctx.append(
                    Node(
                        instance=edge.g().bind(
                            node=EdgeComposition.get_child_node(edge=edge.edge())
                        )
                    )
                )

        EdgeComposition.visit_children_edges(
            bound_node=self.instance, ctx=children, f=collect
        )

        (child,) = children
        return child

    # TODO: convert to visitor pattern
    # TODO: implement in zig
    def get_children[C: Node](
        self,
        direct_only: bool,
        types: type[C] | tuple[type[C], ...],
        include_root: bool = False,
        f_filter: Callable[[C], bool] | None = None,
        sort: bool = True,
    ) -> OrderedSet[C]:
        # copied from old fabll
        type_tuple = types if isinstance(types, tuple) else (types,)

        result: list[C] = []

        if include_root and self.isinstance(*type_tuple):
            self_c = cast(C, self)
            if not f_filter or f_filter(self_c):
                result.append(self_c)

        def _visit(node: "Node[Any]") -> None:
            for _name, child in node.get_direct_children():
                if child.isinstance(*type_tuple):
                    candidate = cast(C, child)
                    if not f_filter or f_filter(candidate):
                        result.append(candidate)
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
            raise FaebrykApiException(
                f"Failed to bind typegraph from instance: {self.instance}"
            )
        return tg

    def bind_typegraph_from_self(self) -> "BoundNodeType[Self, Any]":
        return self.bind_typegraph(tg=self.tg)

    def isinstance(self, *type_node: "type[Node]") -> bool:
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
            type_name = self.__class__.__qualname__
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
            raise FaebrykApiException(f"Node {self} is not an instance of {t}")
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

    # instance edge sugar --------------------------------------------------------------
    def compose_with(self, node: "Node[Any]", name: str | None = None):
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            # TODO None or empty?
            child_identifier=name or "",
        )

    # Get compositions with the get_children functions

    def point_to(
        self,
        to_node: "Node[Any]",
        identifier: str | None = None,
        order: int | None = None,
    ) -> None:
        EdgePointer.point_to(
            bound_node=self.instance,
            target_node=to_node.instance.node(),
            identifier=identifier,
            order=order,
        )

    def get_references(self, identifier: str | None = None) -> "list[Node[Any]]":
        references: list[tuple[int | None, BoundNode]] = []

        def _collect(
            ctx: list[tuple[int | None, BoundNode]], bound_edge: BoundEdge
        ) -> None:
            edge_name = bound_edge.edge().name()
            if identifier is not None and edge_name != identifier:
                return
            target = EdgePointer.get_referenced_node(edge=bound_edge.edge())
            if target is None:
                return
            edge_order = EdgePointer.get_order(edge=bound_edge.edge())
            node = bound_edge.g().bind(node=target)
            ctx.append((edge_order, node))

        if identifier is None:
            EdgePointer.visit_pointed_edges(
                bound_node=self.instance,
                ctx=references,
                f=_collect,
            )
        else:
            EdgePointer.visit_pointed_edges_with_identifier(
                bound_node=self.instance,
                identifier=identifier,
                ctx=references,
                f=_collect,
            )
        return [
            Node(instance=instance)
            for _, instance in sorted(references, key=lambda x: x[0] or 0)
        ]

    def chain_to(self, to_node: "Node[Any]") -> None:
        EdgeNext.add_next(
            previous_node=self.instance,
            next_node=to_node.instance,
        )

    # overrides ------------------------------------------------------------------------
    @classmethod
    def __create_type__[N: Node[Any]](cls: type[N], t: "BoundNodeType[N, T]") -> None:
        """
        Override this to add children to the type.
        """
        pass


class BoundNodeType[N: Node[Any], A: NodeAttributes]:
    """
    (type[Node], TypeGraph)
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
        bound_type = self.t.bind_typegraph(tg=tg)
        self.t.__create_type__(bound_type)
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
    def Child[C: Node[Any]](self, nodetype: type[C]) -> Child[C]:
        return Child(nodetype=nodetype, t=self)

    def BoundChildOfType[C: Node[Any]](self, nodetype: type[C]) -> BoundChildOfType[C]:
        return BoundChildOfType(nodetype=nodetype, t=self)

    def _add_link(
        self,
        *,
        lhs_reference_path: list[str],
        rhs_reference_path: list[str],
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

    def add_link_pointer(
        self,
        *,
        lhs_reference_path: list[str],
        rhs_reference_path: list[str],
        identifier: str | None = None,
    ) -> None:
        self._add_link(
            lhs_reference_path=lhs_reference_path,
            rhs_reference_path=rhs_reference_path,
            edge=EdgePointer.build(identifier=identifier, order=None),
        )


# ------------------------------------------------------------
# TODO move parameter stuff into own file (better into zig)


LiteralT = float | int | str | bool
Literal = LiteralT  # Type alias for compatibility with generated types


class Parameter(Node):
    def constrain_to_literal(self, g: GraphView, value: LiteralT) -> None:
        node = self.instance
        tg = not_none(TypeGraph.of_instance(instance_node=node))
        lit = LiteralNode.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=LiteralNodeAttributes(value=value)
        )

        ExpressionAliasIs.alias_is(tg=tg, g=g, operands=[node, lit.instance])

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
            raise FaebrykApiException(f"Parameter {self} has no literal")
        if not isinstance(lit, t):
            raise FaebrykApiException(f"Parameter {self} has no literal of type {t}")
        return lit


@dataclass(frozen=True)
class LiteralNodeAttributes(NodeAttributes):
    value: Literal


class LiteralNode(Node[LiteralNodeAttributes]):
    Attributes = LiteralNodeAttributes


@dataclass(frozen=True)
class ExpressionAliasIsAttributes(NodeAttributes):
    constrained: bool  # TODO: principled reason for this not being a Parameter


class ExpressionAliasIs(Node[ExpressionAliasIsAttributes]):
    # TODO: constrain operand cardinality?

    Attributes = ExpressionAliasIsAttributes

    @classmethod
    def alias_is(
        cls, tg: TypeGraph, g: GraphView, operands: list[BoundNode]
    ) -> BoundNode:
        expr = cls.bind_typegraph(tg=tg).create_instance(
            g=g, attributes=cls.Attributes(constrained=True)
        )
        for operand in operands:
            EdgeOperand.add_operand(
                bound_node=expr.instance,
                operand=operand.node(),
                operand_identifier=None,
            )
        return expr.instance


# ------------------------------------------------------------
class Sequence(Node):
    """
    A sequence of (non-unique) elements.
    Sorted by insertion order.
    """

    _elem_identifier = "e"

    def append(self, *elems: Node[Any]) -> Self:
        cur_len = len(self.as_list())
        for i, elem in enumerate(elems):
            self.point_to(elem, self._elem_identifier, order=cur_len + i)
        return self

    def as_list(self) -> list[Node[Any]]:
        return self.get_references(self._elem_identifier)


class Set(Node):
    """
    A set of unique elements.
    Sorted by insertion order.
    """

    _elem_identifier = "e"

    def append(self, *elems: Node[Any]) -> Self:
        by_uuid = {elem.instance.node().get_uuid(): elem for elem in elems}
        cur = self.as_list()
        cur_len = len(cur)
        for node in cur:
            by_uuid.pop(node.instance.node().get_uuid(), None)

        for i, elem in enumerate(by_uuid.values()):
            self.point_to(elem, self._elem_identifier, order=cur_len + i)

        return self

    def as_list(self) -> list[Node[Any]]:
        return self.get_references(self._elem_identifier)

    def as_set(self) -> set[Node[Any]]:
        return set(self.as_list())


class Traits:
    def __init__(self, node: Node[Any]):
        self.node = node

    @classmethod
    def bind(cls, node: Node[Any]) -> Self:
        return cls(node)

    def get_obj[N: Node[Any]](self, t: type[N]) -> N:
        return self.node.get_parent_force()[0].cast(t)

    @staticmethod
    def mark_as_trait(t: BoundNodeType[Any, Any]) -> None:
        Trait.mark_as_trait(trait_type=t.get_or_create_type())

    @staticmethod
    def add_to(node: Node[Any], trait: Node[Any]) -> None:
        Trait.add_trait_to(target=node.instance, trait_type=trait.instance)


# ------------------------------------------------------------


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

    @dataclass(frozen=True)
    class SliceAttributes(NodeAttributes):
        start: int
        end: int
        step: int

    class Slice(Node[SliceAttributes]):
        Attributes = SliceAttributes

        @classmethod
        def __create_type__(cls, t: "BoundNodeType[Slice, Any]") -> None:
            cls.tnwa = t.Child(TestNodeWithoutAttr)

    class TestNodeWithoutAttr(Node):
        pass

    class TestNodeWithChildren(Node):
        @classmethod
        def __create_type__(cls, t: "BoundNodeType[TestNodeWithoutAttr, Any]") -> None:
            cls.tnwa1 = t.Child(TestNodeWithoutAttr)
            cls.tnwa2 = t.Child(TestNodeWithoutAttr)

            t._add_link(
                lhs_reference_path=["tnwa1"],
                rhs_reference_path=["tnwa2"],
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
        @classmethod
        def __create_type__(cls, t: "BoundNodeType[ExampleTrait, Any]") -> None:
            Traits.mark_as_trait(t=t)

    class ExampleNode(Node):
        @classmethod
        def __create_type__(cls, t: "BoundNodeType[ExampleNode, Any]") -> None:
            cls.example_trait = t.Child(ExampleTrait)

    node = ExampleNode.bind_typegraph(tg).create_instance(g=g)
    assert node.try_get_trait(ExampleTrait) is not None


def test_pointer_helpers():
    g, tg = _make_graph_and_typegraph()

    class Leaf(Node):
        pass

    class Parent(Node):
        @classmethod
        def __create_type__(cls, t: "BoundNodeType[Parent, Any]") -> None:
            cls.left = t.Child(Leaf)
            cls.right = t.Child(Leaf)

    parent = Parent.bind_typegraph(tg).create_instance(g=g)
    left_child = parent.left.get()
    right_child = parent.right.get()

    parent.point_to(left_child, identifier="left_ptr")
    parent.point_to(right_child, identifier="right_ptr")

    pointed_edges: list[str | None] = []

    def _collect(names: list[str | None], edge: BoundEdge):
        names.append(edge.edge().name())

    EdgePointer.visit_pointed_edges(
        bound_node=parent.instance,
        ctx=pointed_edges,
        f=_collect,
    )
    assert pointed_edges.count("left_ptr") == 1
    assert pointed_edges.count("right_ptr") == 1

    left = EdgePointer.get_pointed_node_by_identifier(
        bound_node=parent.instance,
        identifier="left_ptr",
    )
    assert left is not None
    assert left.node().is_same(other=left_child.instance.node())

    right = EdgePointer.get_pointed_node_by_identifier(
        bound_node=parent.instance,
        identifier="right_ptr",
    )
    assert right is not None
    assert right.node().is_same(other=right_child.instance.node())

    parent.point_to(left_child, identifier="shared")
    parent.point_to(right_child, identifier="shared")

    shared_edges: list[BoundEdge] = []

    def _collect_shared(ctx: list[BoundEdge], edge: BoundEdge):
        ctx.append(edge)

    EdgePointer.visit_pointed_edges_with_identifier(
        bound_node=parent.instance,
        identifier="shared",
        ctx=shared_edges,
        f=_collect_shared,
    )
    assert len(shared_edges) == 2

    shared_nodes = parent.get_references(identifier="shared")
    uuids = {node.instance.node().get_uuid() for node in shared_nodes}
    assert uuids == {
        left_child.instance.node().get_uuid(),
        right_child.instance.node().get_uuid(),
    }


def test_set_basic():
    """Test basic Set functionality: append, as_list, as_set."""
    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    # Create a Set and some elements
    set_node = Set.bind_typegraph(tg).create_instance(g=g)
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
    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Set.bind_typegraph(tg).create_instance(g=g)
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
    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Set.bind_typegraph(tg).create_instance(g=g)
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
    g, tg = _make_graph_and_typegraph()

    class Element(Node):
        pass

    set_node = Set.bind_typegraph(tg).create_instance(g=g)
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


def test_manual_resistor_def():
    from faebryk.library.Electrical import Electrical
    from faebryk.library.has_usage_example import has_usage_example
    from faebryk.library.Resistor import Resistor

    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    # create electrical type node and insert into type graph
    _ = Electrical.bind_typegraph(tg=tg).get_or_create_type()

    # create resistor type node and insert into type graph
    # add make child nodes for p1 and p2, insert into type graph
    _ = Resistor.bind_typegraph(tg=tg).get_or_create_type()

    resistor_instance = Resistor.bind_typegraph(tg=tg).create_instance(g=g)
    assert resistor_instance
    print("resistor_instance:", resistor_instance.instance.node().get_dynamic_attrs())
    print(resistor_instance._type_identifier())

    # Electrical make child
    p1 = EdgeComposition.get_child_by_identifier(
        node=resistor_instance.instance, child_identifier="p1"
    )
    assert p1 is not None
    print("p1:", p1)

    # unconstrained Parameter make child
    resistance = EdgeComposition.get_child_by_identifier(
        node=resistor_instance.instance, child_identifier="resistance"
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
            node=Resistor.bind_typegraph(tg=tg).get_or_create_type(),
            child_identifier="designator_prefix",
        )
    )
    prefix_param = not_none(
        EdgeComposition.get_child_by_identifier(
            node=designator_prefix,
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
        print(
            f"{EdgeType.get_type_node(edge=not_none(EdgeType.get_type_edge(bound_node=operand)).edge()).get_dynamic_attrs()} {operand.node().get_dynamic_attrs()}"
        )

    # Constrained trait with type child parameters to be constrained to literals
    usage_example = not_none(
        EdgeComposition.get_child_by_identifier(
            node=Resistor.bind_typegraph(tg=tg).get_or_create_type(),
            child_identifier="usage_example",
        )
    )
    example_bnode = g.bind(
        node=has_usage_example.bind_instance(usage_example)
        .example.get()
        .instance.node()
    )
    expression_edge = not_none(
        EdgeOperand.get_expression_edge(bound_node=example_bnode)
    )
    expression_node = not_none(
        EdgeOperand.get_expression_node(edge=expression_edge.edge())
    )
    expression_bnode = g.bind(node=expression_node)
    operands2: list[BoundNode] = []
    EdgeOperand.visit_operand_edges(
        bound_node=expression_bnode,
        ctx=operands2,
        f=lambda ctx, edge: ctx.append(edge.g().bind(node=edge.edge().target())),
    )
    for operand in operands2:
        print(
            f"{EdgeType.get_type_node(edge=not_none(EdgeType.get_type_edge(bound_node=operand)).edge()).get_dynamic_attrs()} {operand.node().get_dynamic_attrs()}"
        )

    # Is pickable by type
    ipbt = not_none(
        EdgeComposition.get_child_by_identifier(
            node=resistor_instance.instance,
            child_identifier="is_pickable_by_type",
        )
    )
    ipbt_params = not_none(
        EdgeComposition.get_child_by_identifier(
            node=ipbt,
            child_identifier="params_",
        )
    )
    resistance_node_from_pointer = not_none(
        EdgePointer.get_pointed_node_by_identifier(
            bound_node=ipbt_params, identifier="resistance"
        )
    )
    assert resistance.node().is_same(other=resistance_node_from_pointer.node())


if __name__ == "__main__":
    # import typer

    # typer.run(test_fabll_basic)

    test_manual_resistor_def()
