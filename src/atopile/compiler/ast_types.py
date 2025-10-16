"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, NotRequired, TypedDict, cast

from atopile.compiler.graph_mock import BoundNode, EdgeComposition, LiteralArgs, Node
from faebryk.core.fabll import Child, NodeType, NodeTypeAttributes
from faebryk.core.zig.gen.faebryk.composition import EdgeOperand
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.source import EdgeSource
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundEdge, GraphView

# TODO: Mapping[str, BoundNode] (not supported yet)
ChildrenT = Mapping[str, object]


class ASTType:
    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict): ...

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="name"))


GraphTypeCache = dict[str, BoundNode]


def _create(
    g: GraphView,
    type_cache: GraphTypeCache,
    attrs: LiteralArgs,
    type_attrs: ASTType.Attrs,
) -> BoundNode:
    n = g.insert_node(node=Node.create(**attrs))

    if (name := type_attrs["name"]) in type_cache:
        t = type_cache[name]
    else:
        t = g.insert_node(node=Node.create(**type_attrs))
        type_cache[name] = t

    EdgeType.add_instance(bound_type_node=n, bound_instance_node=t)
    return n


def _create_subgraph(
    g: GraphView,
    type_cache: GraphTypeCache,
    children: ChildrenT,
    attrs: LiteralArgs,
    type_attrs: ASTType.Attrs,
) -> BoundNode:
    n = _create(g, type_cache, attrs, type_attrs)

    for child_id, child_node in children.items():
        assert isinstance(child_node, BoundNode)

        if child_id == "source":  # hopefully the right kind of source
            EdgeSource.add_source(bound_node=n, source_node=child_node.node())
            continue

        EdgeComposition.add_child(
            bound_node=n, child=child_node.node(), child_identifier=child_id
        )

    return n


LiteralT = float | int | str | bool


def constrain_to_literal(
    g: GraphView, tg: TypeGraph, node: Node, value: LiteralT
) -> None:
    text_value = LiteralValue.create_instance(
        tg=tg, g=g, attributes=LiteralValueAttributes(value=value)
    )

    expr = ExpressionAliasIs.create_instance(
        tg=tg, g=g, attributes=ExpressionAliasIsAttributes(constrained=True)
    )

    EdgeOperand.add_operand(
        bound_node=expr.instance, operand=node, operand_identifier="lhs"
    )

    EdgeOperand.add_operand(
        bound_node=expr.instance,
        operand=text_value.instance.node(),
        operand_identifier="rhs",
    )


def try_extract_constrained_literal(node: BoundNode) -> LiteralT | None:
    # TODO: solver? `only_proven=True` parameter?

    if (inbound_expr_edge := EdgeOperand.get_expression_edge(bound_node=node)) is None:
        return None

    expr = inbound_expr_edge.g().bind(node=inbound_expr_edge.edge().source())

    operands: list[BoundNode] = []

    def visit(ctx: None, edge: BoundEdge) -> None:
        operands.append(edge.g().bind(node=edge.edge().target()))

    EdgeOperand.visit_operand_edges(bound_node=expr, ctx=None, f=visit)

    assert len(operands) == 2
    (lit_operand,) = [op for op in operands if not node.node().is_same(other=op.node())]

    return LiteralValue.Attributes.of(node=lit_operand).value


class Parameter(NodeType):
    pass


@dataclass(frozen=True)
class LiteralValueAttributes(NodeTypeAttributes):
    value: float | int | str | bool | None


class LiteralValue(NodeType[LiteralValueAttributes]):
    Attributes = LiteralValueAttributes


@dataclass(frozen=True)
class ExpressionAliasIsAttributes(NodeTypeAttributes):
    constrained: bool  # TODO: principled reason for this not being a Parameter


class ExpressionAliasIs(NodeType[ExpressionAliasIsAttributes]):
    # TODO: constrain operand cardinality?

    Attributes = ExpressionAliasIsAttributes


# @dataclass(frozen=True)
# class FileLocationAttributes(NodeTypeAttributes):
#     start_line: int
#     start_col: int
#     end_line: int
#     end_col: int


class FileLocation(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.start_line = Child(Parameter, tg=tg)
        cls.start_col = Child(Parameter, tg=tg)
        cls.end_line = Child(Parameter, tg=tg)
        cls.end_col = Child(Parameter, tg=tg)


# @dataclass(frozen=True)
# class SourceChunkAttributes(NodeTypeAttributes):
#     text:


class SourceChunk(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.text = Child(Parameter, tg=tg)
        cls.loc = Child(FileLocation, tg=tg)


@dataclass(frozen=True)
class TypeRefAttributes(NodeTypeAttributes):
    name: str


class TypeRef(NodeType[TypeRefAttributes]):
    Attributes = TypeRefAttributes

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)


class ImportPath:
    type_attrs: ASTType.Attrs = {"name": "ImportPath"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        path: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=ImportPath.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=ImportPath.type_attrs
        )


class FieldRefPart:
    type_attrs: ASTType.Attrs = {"name": "FieldRefPart"}

    class Attrs(LiteralArgs):
        name: str
        key: NotRequired[int | str]

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=FieldRefPart.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, dict(children), attrs, FieldRefPart.type_attrs
        )

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="name"))

    @staticmethod
    def get_key(bound_node: BoundNode) -> int | str | None:
        return cast(int | str | None, bound_node.node().get_attr(key="key"))


class FieldRef:
    type_attrs: ASTType.Attrs = {"name": "FieldRef"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        pin: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=FieldRef.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, FieldRef.type_attrs)


class Number:
    type_attrs: ASTType.Attrs = {"name": "Number"}

    class Attrs(LiteralArgs):
        value: float

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Number.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Number.type_attrs)

    @staticmethod
    def get_value(bound_node: BoundNode) -> float:
        return cast(float, bound_node.node().get_attr(key="value"))


class Boolean:
    type_attrs: ASTType.Attrs = {"name": "Boolean"}

    class Attrs(LiteralArgs):
        value: bool

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Boolean.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Boolean.type_attrs)


class Unit:
    type_attrs: ASTType.Attrs = {"name": "Unit"}

    class Attrs(LiteralArgs):
        symbol: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Unit.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Unit.type_attrs)


class Quantity:
    type_attrs: ASTType.Attrs = {"name": "Quantity"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        number: BoundNode
        unit: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Quantity.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Quantity.type_attrs)


class BinaryExpression:
    type_attrs: ASTType.Attrs = {"name": "BinaryExpression"}

    class Attrs(LiteralArgs):
        operator: str

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=BinaryExpression.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, BinaryExpression.type_attrs
        )


class GroupExpression:
    type_attrs: ASTType.Attrs = {"name": "GroupExpression"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        expression: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=GroupExpression.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, GroupExpression.type_attrs
        )


class ComparisonClause:
    type_attrs: ASTType.Attrs = {"name": "ComparisonClause"}

    class Attrs(LiteralArgs):
        operator: str

    class Children(TypedDict):
        source: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=ComparisonClause.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, ComparisonClause.type_attrs
        )


class ComparisonExpression:
    type_attrs: ASTType.Attrs = {"name": "ComparisonExpression"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=ComparisonExpression.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, ComparisonExpression.type_attrs
        )


class BilateralQuantity:
    type_attrs: ASTType.Attrs = {"name": "BilateralQuantity"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        quantity: BoundNode
        tolerance: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=BilateralQuantity.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, BilateralQuantity.type_attrs
        )


class BoundedQuantity:
    type_attrs: ASTType.Attrs = {"name": "BoundedQuantity"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        start: BoundNode
        end: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=BoundedQuantity.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, BoundedQuantity.type_attrs
        )


# TODO: does this node still make sense?
class Scope:
    type_attrs: ASTType.Attrs = {"name": "Scope"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict): ...

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache) -> BoundNode:
        return _create(g, type_cache, attrs=Scope.Attrs(), type_attrs=Scope.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs=Scope.Attrs(), type_attrs=Scope.type_attrs
        )


class File:
    type_attrs: ASTType.Attrs = {"name": "File"}

    class Attrs(LiteralArgs):
        path: str | None

    class Children(TypedDict):
        source: BoundNode
        scope: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=File.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=File.type_attrs
        )


class BlockDefinition:
    BlockTypeT = Literal["component", "module", "interface"]

    type_attrs: ASTType.Attrs = {"name": "BlockDefinition"}

    class Attrs(LiteralArgs):
        block_type: "BlockDefinition.BlockTypeT"

    class Children(TypedDict):
        source: BoundNode
        type_ref: BoundNode
        super_type_ref: NotRequired[BoundNode]
        scope: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=BlockDefinition.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=BlockDefinition.type_attrs
        )

    @staticmethod
    def get_block_type(bound_node: BoundNode) -> "BlockDefinition.BlockTypeT":
        return cast(
            "BlockDefinition.BlockTypeT", bound_node.node().get_attr(key="block_type")
        )


class Slice:
    type_attrs: ASTType.Attrs = {"name": "Slice"}

    class Attrs(LiteralArgs):
        start: NotRequired[int]
        stop: NotRequired[int]
        step: NotRequired[int]

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Slice.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Slice.type_attrs)


class IterableFieldRef:
    type_attrs: ASTType.Attrs = {"name": "IterableFieldRef"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        field: BoundNode
        slice: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=IterableFieldRef.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, IterableFieldRef.type_attrs
        )


class FieldRefList:
    type_attrs: ASTType.Attrs = {"name": "FieldRefList"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=FieldRefList.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, FieldRefList.type_attrs)


class ForStmt:
    type_attrs: ASTType.Attrs = {"name": "ForStmt"}

    class Attrs(LiteralArgs):
        target: str

    class Children(TypedDict):
        source: BoundNode
        iterable: BoundNode
        scope: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=ForStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, ForStmt.type_attrs)


class PragmaStmt:
    type_attrs: ASTType.Attrs = {"name": "PragmaStmt"}

    class Attrs(LiteralArgs):
        pragma: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=PragmaStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=PragmaStmt.type_attrs
        )

    @staticmethod
    def get_pragma(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="pragma"))


class ImportStmt:
    type_attrs: ASTType.Attrs = {"name": "ImportStmt"}

    class Attrs(LiteralArgs):
        path: NotRequired[str]

    class Children(TypedDict):
        source: BoundNode
        path: NotRequired[BoundNode]
        type_ref: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=ImportStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=ImportStmt.type_attrs
        )


class TemplateArg:
    type_attrs: ASTType.Attrs = {"name": "TemplateArg"}

    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict):
        source: BoundNode
        value: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=TemplateArg.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, TemplateArg.type_attrs)


class Template:
    type_attrs: ASTType.Attrs = {"name": "Template"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Template.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Template.type_attrs)


class Assignment:
    type_attrs: ASTType.Attrs = {"name": "Assignment"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        target: BoundNode
        value: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=Assignment.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, Assignment.type_attrs)


class NewExpression:
    type_attrs: ASTType.Attrs = {"name": "NewExpression"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        type_ref: BoundNode
        template: NotRequired[BoundNode]
        new_count: NotRequired[BoundNode]
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=NewExpression.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=NewExpression.type_attrs
        )


class ConnectStmt:
    type_attrs: ASTType.Attrs = {"name": "ConnectStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=ConnectStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, ConnectStmt.type_attrs)


class DirectedConnectStmt:
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    type_attrs: ASTType.Attrs = {"name": "DirectedConnectStmt"}

    class Attrs(LiteralArgs):
        direction: str

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=DirectedConnectStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, DirectedConnectStmt.type_attrs
        )


class RetypeStmt:
    type_attrs: ASTType.Attrs = {"name": "RetypeStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        field_ref: BoundNode
        type_ref: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=RetypeStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, RetypeStmt.type_attrs)


class PinDeclaration:
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    type_attrs: ASTType.Attrs = {"name": "PinDeclaration"}

    class Attrs(LiteralArgs):
        kind: str
        name: NotRequired[str]

    class Children(TypedDict):
        source: BoundNode
        label: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=PinDeclaration.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, PinDeclaration.type_attrs
        )


class SignaldefStmt:
    type_attrs: ASTType.Attrs = {"name": "SignaldefStmt"}

    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=SignaldefStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, SignaldefStmt.type_attrs
        )


class AssertStmt:
    type_attrs: ASTType.Attrs = {"name": "AssertStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        comparison: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=AssertStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, AssertStmt.type_attrs)


class DeclarationStmt:
    type_attrs: ASTType.Attrs = {"name": "DeclarationStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        field_ref: BoundNode
        unit: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=DeclarationStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, DeclarationStmt.type_attrs
        )


class String:
    type_attrs: ASTType.Attrs = {"name": "String"}

    class Attrs(LiteralArgs):
        value: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=String.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=String.type_attrs
        )


class StringStmt:
    type_attrs: ASTType.Attrs = {"name": "StringStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        string: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=StringStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(
            g, type_cache, children, attrs, type_attrs=StringStmt.type_attrs
        )


class PassStmt:
    type_attrs: ASTType.Attrs = {"name": "PassStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=PassStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, PassStmt.type_attrs)


class TraitStmt:
    type_attrs: ASTType.Attrs = {"name": "TraitStmt"}

    class Attrs(LiteralArgs):
        constructor: NotRequired[str]

    class Children(TypedDict):
        source: BoundNode
        type_ref: BoundNode
        target: NotRequired[BoundNode]
        template: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, type_cache: GraphTypeCache, attrs: Attrs) -> BoundNode:
        return _create(g, type_cache, attrs, type_attrs=TraitStmt.type_attrs)

    @staticmethod
    def create_subgraph(
        g: GraphView, type_cache: GraphTypeCache, children: ChildrenT, attrs: Attrs
    ) -> BoundNode:
        return _create_subgraph(g, type_cache, children, attrs, TraitStmt.type_attrs)
