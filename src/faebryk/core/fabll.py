from dataclasses import dataclass
from typing import Any, Self, cast, override

from typing_extensions import deprecated

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, GraphView
from faebryk.libs.util import dataclass_as_kwargs, not_none


class FaebrykApiException(Exception):
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
    def attributes(self) -> T:
        Attributes = cast(type[T], type(self).Attributes)
        return Attributes.of(self.instance)

    def get_parent(self) -> "Node":
        parent_edge = EdgeComposition.get_parent_edge(bound_node=self.instance)
        if parent_edge is None:
            raise FaebrykApiException("Node has no parent")
        parent_node = parent_edge.g().bind(node=parent_edge.edge().target())
        return Node(instance=parent_node)

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

    def isinstance(self, instance: BoundNode) -> bool:
        return EdgeType.is_node_instance_of(
            bound_node=instance,
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
    def nodes_with_trait[T: Node](self, trait: type[T]) -> list[tuple["Node", T]]:
        impls = trait.bind_typegraph(self.tg).get_instances()
        return [(impl.get_parent(), impl) for impl in impls]

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

        lit: LiteralNode | None = None

        # TODO need better python visitor api
        def visit(ctx: None, edge: BoundEdge) -> None:
            nonlocal lit
            operand = edge.g().bind(node=edge.edge().target())
            tg = not_none(TypeGraph.of_instance(instance_node=operand))
            if LiteralNode.bind_typegraph(tg=tg).isinstance(instance=operand):
                lit = LiteralNode(operand)

        EdgeOperand.visit_operand_edges(bound_node=expr, ctx=None, f=visit)

        if lit is None:
            return None
        return LiteralNode.Attributes.of(node=lit.instance).value


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


if __name__ == "__main__":
    import typer

    typer.run(test_fabll_basic)
