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
from typing import ClassVar, Iterable, Literal, NotRequired, Self, TypedDict, cast

from atopile.compiler.graph_mock import BoundNode, EdgeComposition, LiteralArgs, Node
from faebryk.core.fabll import Child, NodeType, NodeTypeAttributes
from faebryk.core.zig.gen.faebryk.composition import EdgeOperand
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.source import EdgeSource
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundEdge, GraphView

# TODO: Mapping[str, BoundNode] (not supported yet)
ChildrenT = Mapping[str, object]


@dataclass(frozen=True)
class SourceInfo:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    text: str


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


class FileLocation(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.start_line = Child(Parameter, tg=tg)
        cls.start_col = Child(Parameter, tg=tg)
        cls.end_line = Child(Parameter, tg=tg)
        cls.end_col = Child(Parameter, tg=tg)

    def set_start_line(self, tg: TypeGraph, g: GraphView, value: int):
        constrain_to_literal(
            g=g, tg=tg, node=self.start_line.get().instance.node(), value=value
        )

    def set_start_col(self, tg: TypeGraph, g: GraphView, value: int):
        constrain_to_literal(
            g=g, tg=tg, node=self.start_col.get().instance.node(), value=value
        )

    def set_end_line(self, tg: TypeGraph, g: GraphView, value: int):
        constrain_to_literal(
            g=g, tg=tg, node=self.end_line.get().instance.node(), value=value
        )

    def set_end_col(self, tg: TypeGraph, g: GraphView, value: int):
        constrain_to_literal(
            g=g, tg=tg, node=self.end_col.get().instance.node(), value=value
        )


class SourceChunk(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.text = Child(Parameter, tg=tg)
        cls.loc = Child(FileLocation, tg=tg)

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        constrain_to_literal(
            g=g, tg=tg, node=self.text.get().instance.node(), value=source_info.text
        )

        self.loc.get().set_start_line(tg=tg, g=g, value=source_info.start_line)
        self.loc.get().set_start_col(tg=tg, g=g, value=source_info.start_column)
        self.loc.get().set_end_line(tg=tg, g=g, value=source_info.end_line)
        self.loc.get().set_end_col(tg=tg, g=g, value=source_info.end_column)


class TypeRef(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.name = Child(Parameter, tg=tg)
        cls.source = Child(SourceChunk, tg=tg)

    def set_name(self, tg: TypeGraph, g: GraphView, name: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.name.get().instance.node(), value=name
        )

    def set_source(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)


class ImportPath(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.path = Child(Parameter, tg=tg)

    def set_path(self, tg: TypeGraph, g: GraphView, path: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.path.get().instance.node(), value=path
        )

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    # TODO: get_path -> str | None


class FieldRefPart(NodeType):
    @dataclass(frozen=True)
    class Info:
        name: str
        key: int | str | None
        source_info: SourceInfo

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.name = Child(Parameter, tg=tg)
        cls.key = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(cls, tg: TypeGraph, g: GraphView, info: Info) -> Self:
        field_ref_part = super().create_instance(tg=tg, g=g)
        field_ref_part.source.get().set_source_info(
            tg=tg, g=g, source_info=info.source_info
        )
        constrain_to_literal(
            g=g, tg=tg, node=field_ref_part.name.get().instance.node(), value=info.name
        )

        if info.key is not None:
            constrain_to_literal(
                g=g,
                tg=tg,
                node=field_ref_part.key.get().instance.node(),
                value=info.key,
            )

        return field_ref_part


class FieldRef(NodeType):
    _part_idx = 0

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.pin = Child(Parameter, tg=tg)

    def add_part(self, tg: TypeGraph, g: GraphView, part: FieldRefPart):
        # TODO: capture sequencing
        self._part_idx += 1

        child = Child(FieldRefPart, tg=tg).bind(part.instance)
        self.add_anon_child(child)

        EdgeComposition.add_child(
            bound_node=self.instance,
            child=part.instance.node(),
            child_identifier=f"part_{self._part_idx}",
        )


class Number(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.value = Child(Parameter, tg=tg)

    def set_value(self, tg: TypeGraph, g: GraphView, value: int | float):
        constrain_to_literal(
            g=g, tg=tg, node=self.value.get().instance.node(), value=value
        )


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


class Unit(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.symbol = Child(Parameter, tg=tg)

    def set_symbol(self, tg: TypeGraph, g: GraphView, symbol: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.symbol.get().instance.node(), value=symbol
        )


class Quantity(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.number = Child(Number, tg=tg)
        cls.unit = Child(Unit, tg=tg)

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_number(self, tg: TypeGraph, g: GraphView, number: int | float):
        self.number.get().set_value(tg=tg, g=g, value=number)

    def set_unit(self, tg: TypeGraph, g: GraphView, unit: str):
        self.unit.get().set_symbol(tg=tg, g=g, symbol=unit)


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


class BilateralQuantity(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.quantity = Child(Quantity, tg=tg)
        cls.tolerance = Child(Quantity, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        quantity_value: int | float,
        quantity_unit: str | None,
        quantity_source_info: SourceInfo,
        tolerance_value: int | float,
        tolerance_unit: str | None,
        tolerance_source_info: SourceInfo,
    ) -> Self:
        bilateral_quantity = super().create_instance(tg=tg, g=g)
        bilateral_quantity.source.get().set_source_info(
            tg=tg, g=g, source_info=source_info
        )
        bilateral_quantity.quantity.get().set_source_info(
            tg=tg, g=g, source_info=quantity_source_info
        )
        bilateral_quantity.quantity.get().set_number(tg=tg, g=g, number=quantity_value)

        if quantity_unit is not None:
            bilateral_quantity.quantity.get().set_unit(tg=tg, g=g, unit=quantity_unit)

        bilateral_quantity.tolerance.get().set_source_info(
            tg=tg, g=g, source_info=tolerance_source_info
        )
        bilateral_quantity.tolerance.get().set_number(
            tg=tg, g=g, number=tolerance_value
        )

        if tolerance_unit is not None:
            bilateral_quantity.tolerance.get().set_unit(tg=tg, g=g, unit=tolerance_unit)

        return bilateral_quantity


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


class Scope(NodeType):
    _stmt_idx: ClassVar[int] = 0

    # TODO: constrain stmt types
    def add_stmt(self, tg: TypeGraph, g: GraphView, stmt: NodeType):
        # TODO: capture order independent from child_id
        Scope._stmt_idx += 1

        child = Child(type(stmt), tg=tg).bind(stmt.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=stmt.instance.node(),
            child_identifier=f"stmt_{Scope._stmt_idx}",  # TODO: anonymous children
        )

    # TODO: get_child_stmts -> Iterable[Assignment | ...]


class File(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.scope = Child(Scope, tg=tg)
        cls.path = Child(Parameter, tg=tg)

    # TODO: optional path
    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        path: str,
        child_stmts: Iterable[NodeType],
    ) -> Self:
        file = super().create_instance(tg=tg, g=g)
        file.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        file.set_path(tg=tg, g=g, path=path)

        for child_node in child_stmts:
            if child_node is not None:  # FIXME
                file.scope.get().add_stmt(tg=tg, g=g, stmt=child_node)

        return file

    def set_path(self, tg: TypeGraph, g: GraphView, path: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.path.get().instance.node(), value=path
        )


class BlockType(NodeType):
    class Types(StrEnum):
        COMPONENT = "component"
        MODULE = "module"
        INTERFACE = "interface"

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.type = Child(Parameter, tg=tg)

    def set_type(self, tg: TypeGraph, g: GraphView, type: "BlockType.Types"):
        constrain_to_literal(
            g=g, tg=tg, node=self.type.get().instance.node(), value=type.value
        )


class BlockDefinition(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.block_type = Child(BlockType, tg=tg)
        cls.type_ref = Child(TypeRef, tg=tg)
        cls.super_type_ref = Child(TypeRef, tg=tg)
        cls.scope = Child(Scope, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        block_type: str,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        super_type_ref_name: str | None,
        super_type_ref_source_info: SourceInfo | None,
        child_stmts: Iterable[NodeType],
    ) -> Self:
        block_definition = super().create_instance(tg=tg, g=g)
        block_definition.source.get().set_source_info(
            tg=tg, g=g, source_info=source_info
        )

        try:
            block_type_val = BlockType.Types(block_type)
        except ValueError:
            raise ValueError(f"Invalid block type: {block_type}")

        block_definition.block_type.get().set_type(tg=tg, g=g, type=block_type_val)

        block_definition.type_ref.get().set_name(tg=tg, g=g, name=type_ref_name)
        block_definition.type_ref.get().set_source(
            tg=tg, g=g, source_info=type_ref_source_info
        )

        if super_type_ref_name is not None:
            block_definition.super_type_ref.get().set_name(
                tg=tg, g=g, name=super_type_ref_name
            )

        if super_type_ref_source_info is not None:
            block_definition.super_type_ref.get().set_source(
                tg=tg, g=g, source_info=super_type_ref_source_info
            )

        for child_node in child_stmts:
            if child_node is not None:  # FIXME
                block_definition.scope.get().add_stmt(tg=tg, g=g, stmt=child_node)

        return block_definition


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


class PragmaStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.pragma = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, pragma: str
    ) -> Self:
        pragma_stmt = super().create_instance(tg=tg, g=g)
        pragma_stmt.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        constrain_to_literal(
            g=g, tg=tg, node=pragma_stmt.pragma.get().instance.node(), value=pragma
        )

        return pragma_stmt


class ImportStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.path = Child(ImportPath, tg=tg)
        cls.type_ref = Child(TypeRef, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        path: str | None,
        path_source_info: SourceInfo | None,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
    ) -> Self:
        import_stmt = super().create_instance(tg=tg, g=g)
        import_stmt.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        if path is not None:
            import_stmt.path.get().set_path(tg=tg, g=g, path=path)

        if path_source_info is not None:
            import_stmt.path.get().set_source_info(
                tg=tg, g=g, source_info=path_source_info
            )

        import_stmt.type_ref.get().set_name(tg=tg, g=g, name=type_ref_name)
        import_stmt.type_ref.get().set_source(
            tg=tg, g=g, source_info=type_ref_source_info
        )

        return import_stmt


class TemplateArg(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.name = Child(Parameter, tg=tg)
        cls.value = Child(Parameter, tg=tg)


class Template(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)


class NewExpression(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.type_ref = Child(TypeRef, tg=tg)
        cls.template = Child(Template, tg=tg)
        cls.new_count = Child(Number, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
    ) -> Self:
        new_expression = super().create_instance(tg=tg, g=g)
        new_expression.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        new_expression.type_ref.get().set_name(tg=tg, g=g, name=type_ref_name)
        new_expression.type_ref.get().set_source(
            tg=tg, g=g, source_info=type_ref_source_info
        )
        # TODO:template, new_count

        return new_expression

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)


AssignableT = NewExpression


class Assignable(NodeType):
    # @dataclass(frozen=True)
    # class Info:
    #     value: NewExpression.Info
    #     value_source_info: SourceInfo

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        # cls.value = Child(NewExpression, tg=tg)  #  TODO: other options

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_value(self, tg: TypeGraph, g: GraphView, value: AssignableT):
        child = Child(type(value), tg=tg).bind(value.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=value.instance.node(),
            child_identifier="value",
        )

    # TODO: get_value -> AssignableT


class Assignment(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.target = Child(FieldRef, tg=tg)  # TODO: declarations?
        cls.assignable = Child(Assignable, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        target_field_ref_parts: list[FieldRefPart.Info],
        target_field_ref_source_info: SourceInfo,
        assignable_value: NewExpression,
        assignable_source_info: SourceInfo,
    ) -> Self:
        assignment = super().create_instance(tg=tg, g=g)
        assignment.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        for part_info in target_field_ref_parts:
            field_ref_part = FieldRefPart.create_instance(tg=tg, g=g, info=part_info)
            assignment.target.get().add_part(tg=tg, g=g, part=field_ref_part)

        assignment.assignable.get().set_value(tg=tg, g=g, value=assignable_value)
        assignment.assignable.get().set_source_info(
            tg=tg, g=g, source_info=assignable_source_info
        )

        return assignment


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


class String(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.text = Child(Parameter, tg=tg)

    def set_text(self, tg: TypeGraph, g: GraphView, text: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.text.get().instance.node(), value=text
        )

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)


class StringStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.string = Child(String, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        string_value: str,
        string_source_info: SourceInfo,
    ) -> Self:
        string_stmt = super().create_instance(tg=tg, g=g)
        string_stmt.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        string_stmt.string.get().set_text(tg=tg, g=g, text=string_value)
        string_stmt.string.get().set_source_info(
            tg=tg, g=g, source_info=string_source_info
        )
        return string_stmt


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
