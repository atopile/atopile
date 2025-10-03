"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from collections.abc import Mapping
from enum import StrEnum
from re import A
from typing import Literal, NotRequired, TypedDict, cast

from atopile.compiler.graph_mock import (
    BoundNode,
    EdgeComposition,
    EdgeSource,
    EdgeType,
    GraphView,
    LiteralArgs,
    Node,
)

# TODO: Mapping[str, BoundNode] (not supported yet)
ChildrenT = Mapping[str, object]


class ASTType:
    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict): ...

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node.get_attr(key="name"))


def _compose_children(g: GraphView, bound_node: BoundNode, children: ChildrenT) -> None:
    for child_id, child_node in children.items():
        assert isinstance(child_node, BoundNode)
        EdgeComposition.add_child(
            bound_node=bound_node, child=child_node.node, child_identifier=child_id
        )


def _create_subgraph(
    g: GraphView, children: ChildrenT, attrs: LiteralArgs, type_attrs: ASTType.Attrs
) -> BoundNode:
    node = g.insert_node(node=Node(**attrs))
    t = g.insert_node(node=Node(**type_attrs))
    EdgeType.add_type(bound_node=node, type_node=t.node)
    if "source" in children:  # probably the right kind of source
        EdgeSource.add_source(
            bound_node=node, source_node=cast(BoundNode, children["source"]).node
        )
        children.pop("source")
    _compose_children(g, node, children)
    return node


class FileLocation:
    type_attrs: ASTType.Attrs = {"name": "FileLocation"}

    class Attrs(LiteralArgs):
        start_line: int
        start_col: int
        end_line: int
        end_col: int

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**FileLocation.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n


class SourceChunk:
    type_attrs: ASTType.Attrs = {"name": "SourceChunk"}

    class Attrs(LiteralArgs):
        text: str

    class Children(TypedDict):
        loc: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**SourceChunk.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=SourceChunk.type_attrs)

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node.get_attr(key="name"))

    @staticmethod
    def get_text(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node.get_attr(key="text"))


class TypeRef:
    type_attrs: ASTType.Attrs = {"name": "TypeRef"}

    class Attrs(LiteralArgs):
        name: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**TypeRef.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=TypeRef.type_attrs)

    @staticmethod
    def get_name(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node.get_attr(key="name"))


class ImportPath:
    type_attrs: ASTType.Attrs = {"name": "ImportPath"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        string: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**ImportPath.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=ImportPath.type_attrs)


# class FieldRefPart(_Node):
#     __tid__ = _tid("FieldRefPart")

#     @classmethod
#     def create(
#         cls, graph: GraphView, name: str, key: int | str | None = None
#     ) -> "FieldRefPart":
#         attrs: dict[str, Literal] = {"name": name}
#         if key is not None:
#             attrs["key"] = key
#         node = cast(FieldRefPart, super().create(graph, **attrs))
#         if key is None and node.get_attr(key="key") is None:
#             set_attr(node, key=None)
#         return node

#     @property
#     def name(self) -> str:
#         return cast(str, self.get_attr(key="name"))

#     @property
#     def key(self) -> int | str | None:
#         return cast(int | str | None, self.get_attr(key="key"))


# class FieldRef(_Node):
#     __tid__ = _tid("FieldRef")

#     @classmethod
#     def create(cls, graph: GraphView, pin: int | None = None) -> "FieldRef":
#         attrs: dict[str, Literal] = {}
#         if pin is not None:
#             attrs["pin"] = pin
#         node = cast(FieldRef, super().create(graph, **attrs))
#         if pin is None and node.get_attr(key="pin") is None:
#             set_attr(node, pin=None)
#         return node

#     @property
#     def pin(self) -> int | None:
#         return cast(int | None, self.get_attr(key="pin"))


# class Number(_Node):
#     __tid__ = _tid("Number")

#     @classmethod
#     def create(cls, graph: GraphView, value: Decimal) -> "Number":
#         return cast(Number, super().create(graph, value=value))

#     @property
#     def value(self) -> Decimal:
#         return cast(Decimal, self.get_attr(key="value"))


class String:
    type_attrs: ASTType.Attrs = {"name": "String"}

    class Attrs(LiteralArgs):
        string: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**String.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=String.type_attrs)

    @staticmethod
    def get_string(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node.get_attr(key="string"))


# class Boolean(_Node):
#     __tid__ = _tid("Boolean")

#     @classmethod
#     def create(cls, graph: GraphView, value: bool) -> "Boolean":
#         return cast(Boolean, super().create(graph, value=value))

#     @property
#     def value(self) -> bool:
#         return cast(bool, self.get_attr(key="value"))


# class Quantity(_Node):
#     __tid__ = _tid("Quantity")

#     @classmethod
#     def create(cls, graph: GraphView, value: Number, unit: str | None) -> "Quantity":
#         attrs: dict[str, Literal] = {}
#         if unit is not None:
#             attrs["unit"] = unit
#         node = cast(Quantity, super().create(graph, **attrs))
#         if unit is None and node.get_attr(key="unit") is None:
#             set_attr(node, unit=None)
#         add(graph, node, value, "value")
#         return node

#     @property
#     def unit(self) -> str | None:
#         return cast(str | None, self.get_attr(key="unit"))

#     @property
#     def value(self) -> Number:
#         return cast(Number, first_child(self, "value"))


# class BinaryExpression(_Node):
#     __tid__ = _tid("BinaryExpression")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         operator: str,
#         left: Node,
#         right: Node,
#     ) -> "BinaryExpression":
#         node = cast(BinaryExpression, super().create(graph, operator=operator))
#         add(graph, node, left, "left")
#         add(graph, node, right, "right")
#         return node

#     @property
#     def operator(self) -> str:
#         return cast(str, self.get_attr(key="operator"))


# class GroupExpression(_Node):
#     __tid__ = _tid("GroupExpression")

#     @classmethod
#     def create(cls, graph: GraphView, expression: Node) -> "GroupExpression":
#         node = cast(GroupExpression, super().create(graph))
#         add(graph, node, expression, "expression")
#         return node

#     @property
#     def expression(self) -> Node:
#         return first_child(self, "expression")


# class FunctionCall(_Node):
#     __tid__ = _tid("FunctionCall")

#     @classmethod
#     def create(
#         cls, graph: GraphView, name: str, args: Sequence[Node]
#     ) -> "FunctionCall":
#         node = cast(FunctionCall, super().create(graph, name=name))
#         for index, arg in enumerate(args):
#             add(graph, node, arg, f"arg[{index}]")
#         return node

#     @property
#     def name(self) -> str:
#         return cast(str, self.get_attr(key="name"))


# def args(self) -> Iterable[Node]:
#     graph = _graph_for(self)
#     for edge in graph.child_edges(node=self):
#         edge_name = edge.name()
#         if edge_name and edge_name.startswith("arg["):
#             yield edge.target()


# class ComparisonClause(_Node):
#     __tid__ = _tid("ComparisonClause")

#     @classmethod
#     def create(cls, graph: GraphView, operator: str, right: Node) -> "ComparisonClause":
#         node = cast(ComparisonClause, super().create(graph, operator=operator))
#         add(graph, node, right, "right")
#         return node

#     @property
#     def operator(self) -> str:
#         return cast(str, self.get_attr(key="operator"))

#     @property
#     def right(self) -> Node:
#         return first_child(self, "right")


# class ComparisonExpression(_Node):
#     __tid__ = _tid("ComparisonExpression")

#     @classmethod
#     def create(
#         cls, graph: GraphView, left: Node, clauses: Sequence[ComparisonClause]
#     ) -> "ComparisonExpression":
#         node = cast(ComparisonExpression, super().create(graph))
#         add(graph, node, left, "left")
#         for index, clause in enumerate(clauses):
#             add(graph, node, clause, f"clause[{index}]")
#         return node

#     @property
#     def left(self) -> Node:
#         return first_child(self, "left")


# def clauses(self) -> Iterable[ComparisonClause]:
#     graph = _graph_for(self)
#     for edge in graph.child_edges(node=self):
#         edge_name = edge.name()
#         if edge_name and edge_name.startswith("clause["):
#             yield cast(ComparisonClause, edge.target())


# class BilateralQuantity(_Node):
#     __tid__ = _tid("BilateralQuantity")

#     @classmethod
#     def create(
#         cls, graph: GraphView, quantity: Quantity, tolerance: Quantity
#     ) -> "BilateralQuantity":
#         node = cast(BilateralQuantity, super().create(graph))
#         add(graph, node, quantity, "quantity")
#         add(graph, node, tolerance, "tolerance")
#         return node


# class BoundedQuantity(_Node):
#     __tid__ = _tid("BoundedQuantity")

#     @classmethod
#     def create(
#         cls, graph: GraphView, start: Quantity, end: Quantity
#     ) -> "BoundedQuantity":
#         node = cast(BoundedQuantity, super().create(graph))
#         add(graph, node, start, "start")
#         add(graph, node, end, "end")
#         return node


# TODO: does this node still make sense?
class Scope:
    type_attrs: ASTType.Attrs = {"name": "Scope"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict): ...

    @staticmethod
    def create(g: GraphView) -> BoundNode:
        n = g.insert_node(node=Node())
        t = g.insert_node(node=Node(**Scope.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

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
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**File.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=File.type_attrs)


# class TextFragment(_Node):
#     __tid__ = _tid("TextFragment")

#     @classmethod
#     def create(cls, graph: GraphView, scope: Scope | None = None) -> "TextFragment":
#         node = cast(TextFragment, super().create(graph))
#         if scope is None:
#             scope = Scope.create(graph)
#         add(graph, node, scope, "scope")
#         return node

#     @property
#     def scope(self) -> "Scope":
#         return cast(Scope, first_child(self, "scope"))


# class Whitespace(_Node):
#     __tid__ = _tid("Whitespace")

#     @classmethod
#     def create(cls, graph: GraphView) -> "Whitespace":
#         return cast(Whitespace, super().create(graph))


# class Comment(_Node):
#     __tid__ = _tid("Comment")

#     @classmethod
#     def create(cls, graph: GraphView) -> "Comment":
#         return cast(Comment, super().create(graph))


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
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**BlockDefinition.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(
            g, children, attrs, type_attrs=BlockDefinition.type_attrs
        )

    @staticmethod
    def get_block_type(bound_node: BoundNode) -> "BlockDefinition.BlockTypeT":
        return cast(
            "BlockDefinition.BlockTypeT", bound_node.node.get_attr(key="block_type")
        )


# class CompilationUnit(_Node):
#     __tid__ = _tid("CompilationUnit")

#     @classmethod
#     def create(cls, graph: GraphView, context: Node) -> "CompilationUnit":
#         node = cast(CompilationUnit, super().create(graph))
#         add(graph, node, context, "context")
#         return node


# class Slice(_Node):
#     __tid__ = _tid("Slice")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         start: int | None,
#         stop: int | None,
#         step: int | None,
#     ) -> "Slice":
#         attrs: dict[str, Literal] = {}
#         if start is not None:
#             attrs["start"] = start
#         if stop is not None:
#             attrs["stop"] = stop
#         if step is not None:
#             attrs["step"] = step
#         node = cast(Slice, super().create(graph, **attrs))
#         if start is None and node.get_attr(key="start") is None:
#             set_attr(node, start=None)
#         if stop is None and node.get_attr(key="stop") is None:
#             set_attr(node, stop=None)
#         if step is None and node.get_attr(key="step") is None:
#             set_attr(node, step=None)
#         return node

#     @property
#     def start(self) -> int | None:
#         return cast(int | None, self.get_attr(key="start"))

#     @property
#     def stop(self) -> int | None:
#         return cast(int | None, self.get_attr(key="stop"))

#     @property
#     def step(self) -> int | None:
#         return cast(int | None, self.get_attr(key="step"))


# class IterableFieldRef(_Node):
#     __tid__ = _tid("IterableFieldRef")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         field_ref: FieldRef,
#         slice_: Slice | None = None,
#     ) -> "IterableFieldRef":
#         node = cast(IterableFieldRef, super().create(graph))
#         add(graph, node, field_ref, "field")
#         if slice_ is not None:
#             add(graph, node, slice_, "slice")
#         return node


# class FieldRefList(_Node):
#     __tid__ = _tid("FieldRefList")

#     @classmethod
#     def create(cls, graph: GraphView, items: Sequence[FieldRef]) -> "FieldRefList":
#         node = cast(FieldRefList, super().create(graph))
#         for index, item in enumerate(items):
#             add(graph, node, item, f"item[{index}]")
#         return node


# def items(self) -> Iterable[FieldRef]:
#     graph = _graph_for(self)
#     for edge in graph.child_edges(node=self):
#         edge_name = edge.name()
#         if edge_name and edge_name.startswith("item["):
#             yield cast(FieldRef, edge.target())


# class ForStmt(_Node):
#     __tid__ = _tid("ForStmt")

#     @classmethod
#     def create(cls, graph: GraphView, target: str, iterable: Node) -> "ForStmt":
#         node = cast(ForStmt, super().create(graph, target=target))
#         add(graph, node, iterable, "iterable")
#         add(graph, node, Scope.create(graph), "scope")
#         return node

#     @property
#     def target(self) -> str:
#         return cast(str, self.get_attr(key="target"))

#     @property
#     def scope(self) -> Scope:
#         return cast(Scope, first_child(self, "scope"))


class PragmaStmt:
    type_attrs: ASTType.Attrs = {"name": "PragmaStmt"}

    class Attrs(LiteralArgs):
        pragma: str

    class Children(TypedDict):
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**PragmaStmt.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=PragmaStmt.type_attrs)

    @staticmethod
    def get_pragma(bound_node: BoundNode) -> str:
        return cast(str, bound_node.node.get_attr(key="pragma"))


class ImportStmt:
    type_attrs: ASTType.Attrs = {"name": "ImportStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        path: NotRequired[BoundNode]
        type_ref: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**ImportStmt.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=ImportStmt.type_attrs)


class AssignQuantityStmt:
    type_attrs: ASTType.Attrs = {"name": "AssignQuantityStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        target: BoundNode
        quantity: BoundNode
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**AssignQuantityStmt.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(
            g, children, attrs, type_attrs=AssignQuantityStmt.type_attrs
        )


# class TemplateArg(_Node):
#     __tid__ = _tid("TemplateArg")

#     @classmethod
#     def create(cls, graph: GraphView, name: str, value: Node) -> "TemplateArg":
#         node = cast(TemplateArg, super().create(graph, name=name))
#         add(graph, node, value, "value")
#         return node

#     @property
#     def name(self) -> str:
#         return cast(str, self.get_attr(key="name"))


# class Template(_Node):
#     __tid__ = _tid("Template")

#     @classmethod
#     def create(cls, graph: GraphView, args: Sequence[TemplateArg]) -> "Template":
#         node = cast(Template, super().create(graph))
#         for index, arg in enumerate(args):
#             add(graph, node, arg, f"arg[{index}]")
#         return node


class AssignValueStmt:
    type_attrs: ASTType.Attrs = {"name": "AssignValueStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        target: BoundNode
        value: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**AssignValueStmt.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(
            g, children, attrs, type_attrs=AssignValueStmt.type_attrs
        )


class AssignNewStmt:
    type_attrs: ASTType.Attrs = {"name": "AssignNewStmt"}

    class Attrs(LiteralArgs):
        new_count: NotRequired[int]

    class Children(TypedDict):
        target: BoundNode
        type_ref: BoundNode
        template: NotRequired[BoundNode]
        source: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**AssignNewStmt.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=AssignNewStmt.type_attrs)


# class CumAssignStmt(_Node):
#     __tid__ = _tid("CumAssignStmt")

#     @classmethod
#     def create(cls, graph: GraphView) -> "CumAssignStmt":
#         return cast(CumAssignStmt, super().create(graph))


# class SetAssignStmt(_Node):
#     __tid__ = _tid("SetAssignStmt")

#     @classmethod
#     def create(cls, graph: GraphView) -> "SetAssignStmt":
#         return cast(SetAssignStmt, super().create(graph))


# class ConnectStmt(_Node):
#     __tid__ = _tid("ConnectStmt")

#     @classmethod
#     def create(cls, graph: GraphView, left: Node, right: Node) -> "ConnectStmt":
#         node = cast(ConnectStmt, super().create(graph))
#         add(graph, node, left, "left")
#         add(graph, node, right, "right")
#         return node


# class DirectedConnectStmt(_Node):
#     class Direction(StrEnum):
#         RIGHT = "RIGHT"
#         LEFT = "LEFT"

#     __tid__ = _tid("DirectedConnectStmt")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         left: Node,
#         right: Node,
#         direction: "DirectedConnectStmt.Direction",
#     ) -> "DirectedConnectStmt":
#         node = cast(
#             DirectedConnectStmt,
#             super().create(graph, direction=direction.value),
#         )
#         add(graph, node, left, "left")
#         add(graph, node, right, "right")
#         return node

#     @property
#     def direction(self) -> "DirectedConnectStmt.Direction":
#         value = cast(str, self.get_attr(key="direction"))
#         return DirectedConnectStmt.Direction(value)


# class RetypeStmt(_Node):
#     __tid__ = _tid("RetypeStmt")

#     @classmethod
#     def create(
#         cls, graph: GraphView, field_ref: FieldRef, type_ref: TypeRef
#     ) -> "RetypeStmt":
#         node = cast(RetypeStmt, super().create(graph))
#         add(graph, node, field_ref, "field_ref")
#         add(graph, node, type_ref, "type_ref")
#         return node


# class PinDeclaration(_Node):
#     class Kind(StrEnum):
#         NAME = "name"
#         NUMBER = "number"
#         STRING = "string"

#     __tid__ = _tid("PinDeclaration")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         kind: "PinDeclaration.Kind",
#         value: str | int,
#         literal: Node | None = None,
#     ) -> "PinDeclaration":
#         node = cast(
#             PinDeclaration,
#             super().create(graph, kind=kind.value, value=value),
#         )
#         if literal is not None:
#             add(graph, node, literal, "literal")
#         return node

#     @property
#     def kind(self) -> "PinDeclaration.Kind":
#         value = cast(str, self.get_attr(key="kind"))
#         return PinDeclaration.Kind(value)

#     @property
#     def value(self) -> str | int:
#         return cast(str | int, self.get_attr(key="value"))


# class SignaldefStmt(_Node):
#     __tid__ = _tid("SignaldefStmt")

#     @classmethod
#     def create(cls, graph: GraphView, name: str) -> "SignaldefStmt":
#         return cast(SignaldefStmt, super().create(graph, name=name))

#     @property
#     def name(self) -> str:
#         return cast(str, self.get_attr(key="name"))


# class AssertStmt(_Node):
#     __tid__ = _tid("AssertStmt")

#     @classmethod
#     def create(cls, graph: GraphView, comparison: Node) -> "AssertStmt":
#         node = cast(AssertStmt, super().create(graph))
#         add(graph, node, comparison, "comparison")
#         return node


# class DeclarationStmt(_Node):
#     __tid__ = _tid("DeclarationStmt")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         field_ref: FieldRef,
#         type_ref: TypeRef | None = None,
#     ) -> "DeclarationStmt":
#         node = cast(DeclarationStmt, super().create(graph))
#         add(graph, node, field_ref, "field_ref")
#         if type_ref is not None:
#             add(graph, node, type_ref, "type_ref")
#         return node


class StringStmt:
    type_attrs: ASTType.Attrs = {"name": "StringStmt"}

    class Attrs(LiteralArgs): ...

    class Children(TypedDict):
        source: BoundNode
        string: BoundNode

    @staticmethod
    def create(g: GraphView, attrs: Attrs) -> BoundNode:
        n = g.insert_node(node=Node(**attrs))
        t = g.insert_node(node=Node(**StringStmt.type_attrs))
        EdgeType.add_type(bound_node=n, type_node=t.node)
        return n

    @staticmethod
    def create_subgraph(g: GraphView, children: ChildrenT, attrs: Attrs) -> BoundNode:
        return _create_subgraph(g, children, attrs, type_attrs=StringStmt.type_attrs)


# class PassStmt(_Node):
#     __tid__ = _tid("PassStmt")

#     @classmethod
#     def create(cls, graph: GraphView) -> "PassStmt":
#         return cast(PassStmt, super().create(graph))


# class TraitStmt(_Node):
#     __tid__ = _tid("TraitStmt")

#     @classmethod
#     def create(
#         cls,
#         graph: GraphView,
#         type_ref: TypeRef,
#         target: FieldRef | None = None,
#         constructor: str | None = None,
#         template: Template | None = None,
#     ) -> "TraitStmt":
#         attrs: dict[str, Literal] = {}
#         if constructor is not None:
#             attrs["constructor"] = constructor
#         node = cast(TraitStmt, super().create(graph, **attrs))
#         add(graph, node, type_ref, "type_ref")
#         if target is not None:
#             add(graph, node, target, "target")
#         if template is not None:
#             add(graph, node, template, "template")
#         if constructor is None and node.get_attr(key="constructor") is None:
#             set_attr(node, constructor=None)
#         return node
