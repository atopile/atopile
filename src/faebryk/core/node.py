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
from faebryk.libs.util import (
    KeyErrorNotFound,
    Tree,
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


class NodeMeta(type):
    @override
    def __setattr__(cls, name: str, value: Any, /) -> None:
        if isinstance(value, Child) and issubclass(cls, Node):
            value.identifier = name
            cls._add_child(value)
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
                f"NodeType subclasses cannot themselves be subclassed "
                f"more than one level deep (found: {cls.__mro__})"
            )
        super().__init_subclass__()

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
    @deprecated("Use add_instance_child instead")
    def add(self, node: "Node[Any]"):
        self.add_instance_child(node)

    def __setattr__(self, name: str, value: Any, /) -> None:
        if isinstance(value, Node) and not name.startswith("_"):
            self.add_instance_child(value, name=name)
        return super().__setattr__(name, value)

    def add_instance_child(self, node: "Node[Any]", name: str | None = None):
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            # TODO None or empty?
            child_identifier=name or "",
        )

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

    # instance edge sugar --------------------------------------------------------------
    def point_to(self, to_node: "Node[Any]", identifier: str | None = None) -> None:
        EdgePointer.point_to(
            bound_node=self.instance,
            target_node=to_node.instance.node(),
        )

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

    @classmethod
    def __create_instance__(cls, tg: TypeGraph, g: GraphView) -> Self:
        return cls.bind_typegraph(tg=tg).create_instance(g=g)


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
        pass

    @deprecated("Use get_instances instead")
    def nodes_of_type[N2: Node](self, t: type[N2]) -> set[N2]:
        return set(t.bind_typegraph(self.tg).get_instances())

    def nodes_of_types(self, t: tuple[type["Node"], ...]) -> set["Node"]:
        return {n for tn in t for n in tn.bind_typegraph(self.tg).get_instances()}

    # construction ---------------------------------------------------------------------
    def Child[C: Node[Any]](self, nodetype: type[C]) -> Child[C]:
        return Child(nodetype=nodetype, t=self)

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


class Traits:
    def __init__(self, node: Node[Any]):
        self.node = node

    @classmethod
    def bind(cls, node: Node[Any]) -> Self:
        return cls(node)

    def get_obj[N: Node[Any]](self, t: type[N]) -> N:
        return self.node.get_parent_force()[0].cast(t)


# ------------------------------------------------------------


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
                edge=EdgePointer.build(),
            )

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
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


if __name__ == "__main__":
    import typer

    typer.run(test_fabll_basic)
