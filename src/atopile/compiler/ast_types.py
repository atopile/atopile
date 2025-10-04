"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal, NotRequired, TypedDict, cast

from atopile.compiler.graph_mock import (
    BoundNode,
    EdgeComposition,
    LiteralArgs,
    Node,
    NodeHelpers,
)
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.source import EdgeSource
from faebryk.core.zig.gen.graph.graph import GraphView

# TODO: Mapping[str, BoundNode] (not supported yet)
ChildrenT = Mapping[str, object]


class ASTType:
    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict): ...

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="name"))


def _create(g: GraphView, attrs: LiteralArgs, type_attrs: ASTType.Attrs) -> BoundNode:
    n = g.insert_node(node=Node.create(**attrs))
    t = g.insert_node(node=Node.create(**type_attrs))
    EdgeType.add_instance(bound_type_node=n, bound_instance_node=t)
    return n


def _create_subgraph(
    g: GraphView, children: ChildrenT, attrs: LiteralArgs, type_attrs: ASTType.Attrs
) -> BoundNode:
    n = _create(g, attrs, type_attrs)

    for child_id, child_node in children.items():
        assert isinstance(child_node, BoundNode)

        if child_id == "source":  # hopefully the right kind of source
            EdgeSource.add_source(bound_node=n, source_node=child_node.node())
            continue

        EdgeComposition.add_child(
            bound_node=n, child=child_node.node(), child_identifier=child_id
        )

    return n


class FileLocation:
    type_attrs: ASTType.Attrs = {"name": "FileLocation"}

    class Attrs(LiteralArgs):
        start_line: int
        start_col: int
        end_line: int
        end_col: int

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=FileLocation.type_attrs)


class SourceChunk:
    type_attrs: ASTType.Attrs = {"name": "SourceChunk"}

    class Attrs(LiteralArgs):
        text: str

    class Children(TypedDict):
        loc: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=SourceChunk.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=SourceChunk.type_attrs)

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="name"))

    @staticmethod
    def get_text(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="text"))


class TypeRef:
    type_attrs: ASTType.Attrs = {"name": "TypeRef"}

    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=TypeRef.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=TypeRef.type_attrs)

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node().get_attr(key="name"))


class ImportPath:
    type_attrs: ASTType.Attrs = {"name": "ImportPath"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        path: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=ImportPath.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=ImportPath.type_attrs)


class FieldRefPart:
    type_attrs: ASTType.Attrs = {"name": "FieldRefPart"}

    class Attrs(LiteralArgs):
        name: str
        key: NotRequired[int | str]

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=FieldRefPart.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, FieldRefPart.type_attrs)

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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=FieldRef.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, FieldRef.type_attrs)


class Number:
    type_attrs: ASTType.Attrs = {"name": "Number"}

    class Attrs(LiteralArgs):
        value: float

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Number.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Number.type_attrs)

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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Boolean.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Boolean.type_attrs)


class Unit:
    type_attrs: ASTType.Attrs = {"name": "Unit"}

    class Attrs(LiteralArgs):
        symbol: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Unit.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Unit.type_attrs)


class Quantity:
    type_attrs: ASTType.Attrs = {"name": "Quantity"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        number: BoundNode
        unit: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Quantity.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Quantity.type_attrs)


class BinaryExpression:
    type_attrs: ASTType.Attrs = {"name": "BinaryExpression"}

    class Attrs(LiteralArgs):
        operator: str

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=BinaryExpression.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, BinaryExpression.type_attrs)


class GroupExpression:
    type_attrs: ASTType.Attrs = {"name": "GroupExpression"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        expression: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=GroupExpression.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, GroupExpression.type_attrs)


class ComparisonClause:
    type_attrs: ASTType.Attrs = {"name": "ComparisonClause"}

    class Attrs(LiteralArgs):
        operator: str

    class Children(TypedDict):
        source: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=ComparisonClause.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, ComparisonClause.type_attrs)


class ComparisonExpression:
    type_attrs: ASTType.Attrs = {"name": "ComparisonExpression"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=ComparisonExpression.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(
            g, dict(children), attrs, ComparisonExpression.type_attrs
        )


class BilateralQuantity:
    type_attrs: ASTType.Attrs = {"name": "BilateralQuantity"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        quantity: BoundNode
        tolerance: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=BilateralQuantity.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, BilateralQuantity.type_attrs)


class BoundedQuantity:
    type_attrs: ASTType.Attrs = {"name": "BoundedQuantity"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        start: BoundNode
        end: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=BoundedQuantity.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, BoundedQuantity.type_attrs)


# TODO: does this node still make sense?
class Scope:
    type_attrs: ASTType.Attrs = {"name": "Scope"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict): ...

    @staticmethod
    def create(g: GraphView) -> BoundNode:
        return _create(g, attrs=Scope.Attrs(), type_attrs=Scope.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT) -> BoundNode:
        return _create_subgraph(
            g, children, attrs=Scope.Attrs(), type_attrs=Scope.type_attrs
        )


class File:
    type_attrs: ASTType.Attrs = {"name": "File"}

    class Attrs(LiteralArgs):
        path: str | None

    class Children(TypedDict):
        source: BoundNode
        scope: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=File.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=File.type_attrs)


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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=BlockDefinition.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(
            g, children, attrs, type_attrs=BlockDefinition.type_attrs
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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Slice.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Slice.type_attrs)


class IterableFieldRef:
    type_attrs: ASTType.Attrs = {"name": "IterableFieldRef"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        field: BoundNode
        slice: NotRequired[BoundNode]

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=IterableFieldRef.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, IterableFieldRef.type_attrs)


class FieldRefList:
    type_attrs: ASTType.Attrs = {"name": "FieldRefList"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=FieldRefList.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=ForStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, ForStmt.type_attrs)


class PragmaStmt:
    type_attrs: ASTType.Attrs = {"name": "PragmaStmt"}

    class Attrs(LiteralArgs):
        pragma: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=PragmaStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=PragmaStmt.type_attrs)

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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=ImportStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=ImportStmt.type_attrs)


class TemplateArg:
    type_attrs: ASTType.Attrs = {"name": "TemplateArg"}

    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict):
        source: BoundNode
        value: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=TemplateArg.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, TemplateArg.type_attrs)


class Template:
    type_attrs: ASTType.Attrs = {"name": "Template"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Template.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Template.type_attrs)


class Assignment:
    type_attrs: ASTType.Attrs = {"name": "Assignment"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        target: BoundNode
        value: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=Assignment.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, Assignment.type_attrs)


class NewExpression:
    type_attrs: ASTType.Attrs = {"name": "NewExpression"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        type_ref: BoundNode
        template: NotRequired[BoundNode]
        new_count: NotRequired[BoundNode]
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=NewExpression.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=NewExpression.type_attrs)


class ConnectStmt:
    type_attrs: ASTType.Attrs = {"name": "ConnectStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        left: BoundNode
        right: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=ConnectStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, ConnectStmt.type_attrs)


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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=DirectedConnectStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(
            g, dict(children), attrs, DirectedConnectStmt.type_attrs
        )


class RetypeStmt:
    type_attrs: ASTType.Attrs = {"name": "RetypeStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        field_ref: BoundNode
        type_ref: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=RetypeStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, RetypeStmt.type_attrs)


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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=PinDeclaration.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, PinDeclaration.type_attrs)


class SignaldefStmt:
    type_attrs: ASTType.Attrs = {"name": "SignaldefStmt"}

    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=SignaldefStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, SignaldefStmt.type_attrs)


class AssertStmt:
    type_attrs: ASTType.Attrs = {"name": "AssertStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        comparison: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=AssertStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, AssertStmt.type_attrs)


class DeclarationStmt:
    type_attrs: ASTType.Attrs = {"name": "DeclarationStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        field_ref: BoundNode
        unit: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=DeclarationStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, DeclarationStmt.type_attrs)


class String:
    type_attrs: ASTType.Attrs = {"name": "String"}

    class Attrs(LiteralArgs):
        value: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=String.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=String.type_attrs)


class StringStmt:
    type_attrs: ASTType.Attrs = {"name": "StringStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        string: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=StringStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=StringStmt.type_attrs)


class PassStmt:
    type_attrs: ASTType.Attrs = {"name": "PassStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=PassStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, PassStmt.type_attrs)


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
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        return _create(g, attrs, type_attrs=TraitStmt.type_attrs)

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, dict(children), attrs, TraitStmt.type_attrs)


# TODO: generic get_attrs in API
def get_attrs(bound_node: BoundNode) -> dict[str, int | float | str | bool]:
    attrs_class_by_type_name = {
        "FileLocation": FileLocation.Attrs,
        "SourceChunk": SourceChunk.Attrs,
        "TypeRef": TypeRef.Attrs,
        "ImportPath": ImportPath.Attrs,
        "FieldRefPart": FieldRefPart.Attrs,
        "FieldRef": FieldRef.Attrs,
        "Number": Number.Attrs,
        "Boolean": Boolean.Attrs,
        "Unit": Unit.Attrs,
        "Quantity": Quantity.Attrs,
        "BinaryExpression": BinaryExpression.Attrs,
        "GroupExpression": GroupExpression.Attrs,
        "ComparisonClause": ComparisonClause.Attrs,
        "ComparisonExpression": ComparisonExpression.Attrs,
        "BilateralQuantity": BilateralQuantity.Attrs,
        "BoundedQuantity": BoundedQuantity.Attrs,
        "Scope": Scope.Attrs,
        "File": File.Attrs,
        "BlockDefinition": BlockDefinition.Attrs,
        "Slice": Slice.Attrs,
        "IterableFieldRef": IterableFieldRef.Attrs,
        "FieldRefList": FieldRefList.Attrs,
        "ForStmt": ForStmt.Attrs,
        "PragmaStmt": PragmaStmt.Attrs,
        "ImportStmt": ImportStmt.Attrs,
        "TemplateArg": TemplateArg.Attrs,
        "Template": Template.Attrs,
        "Assignment": Assignment.Attrs,
        "NewExpression": NewExpression.Attrs,
        "ConnectStmt": ConnectStmt.Attrs,
        "DirectedConnectStmt": DirectedConnectStmt.Attrs,
        "RetypeStmt": RetypeStmt.Attrs,
        "PinDeclaration": PinDeclaration.Attrs,
        "SignaldefStmt": SignaldefStmt.Attrs,
        "AssertStmt": AssertStmt.Attrs,
        "DeclarationStmt": DeclarationStmt.Attrs,
        "String": String.Attrs,
        "StringStmt": StringStmt.Attrs,
        "PassStmt": PassStmt.Attrs,
        "TraitStmt": TraitStmt.Attrs,
    }

    attrs_class = attrs_class_by_type_name[NodeHelpers.get_type_name(bound_node)]
    required_keys = attrs_class.__required_keys__
    optional_keys = attrs_class.__optional_keys__

    out = {k: bound_node.node().get_attr(key=k) for k in required_keys}
    for k in optional_keys:
        if v := bound_node.node().get_attr(key=k):
            out[k] = v

    return attrs_class(**out)
