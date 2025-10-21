"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Iterable, Self

from atopile.compiler.graph_mock import BoundNode, EdgeComposition, Node
from faebryk.core.fabll import Child, NodeType, NodeTypeAttributes
from faebryk.core.zig.gen.faebryk.composition import EdgeOperand
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundEdge, GraphView


@dataclass(frozen=True)
class SourceInfo:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    text: str


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

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        parts: Iterable[FieldRefPart.Info],
    ) -> Self:
        field_ref = super().create_instance(tg=tg, g=g)
        field_ref.set_source_info(tg=tg, g=g, source_info=source_info)
        for part_info in parts:
            part = FieldRefPart.create_instance(tg=tg, g=g, info=part_info)
            field_ref.add_part(tg=tg, g=g, part=part)
        return field_ref

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

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

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, value: int | float
    ) -> Self:
        number = super().create_instance(tg=tg, g=g)
        number.set_source_info(tg=tg, g=g, source_info=source_info)
        number.set_value(tg=tg, g=g, value=value)
        return number

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_value(self, tg: TypeGraph, g: GraphView, value: int | float):
        constrain_to_literal(
            g=g, tg=tg, node=self.value.get().instance.node(), value=value
        )


class Boolean(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.value = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, value: bool
    ) -> Self:
        boolean = super().create_instance(tg=tg, g=g)
        boolean.set_source_info(tg=tg, g=g, source_info=source_info)
        boolean.set_value(tg=tg, g=g, value=value)
        return boolean

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_value(self, tg: TypeGraph, g: GraphView, value: bool):
        constrain_to_literal(
            g=g, tg=tg, node=self.value.get().instance.node(), value=value
        )


class Unit(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.symbol = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, symbol: str
    ) -> Self:
        unit = super().create_instance(tg=tg, g=g)
        unit.set_source_info(tg=tg, g=g, source_info=source_info)
        unit.set_symbol(tg=tg, g=g, symbol=symbol)
        return unit

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

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

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        *,
        value: int | float,
        value_source_info: SourceInfo,
        unit: tuple[str, SourceInfo] | None = None,
    ) -> Self:
        quantity = super().create_instance(tg=tg, g=g)
        quantity.set_source_info(tg=tg, g=g, source_info=source_info)
        quantity.set_number(
            tg=tg,
            g=g,
            number=value,
            source_info=value_source_info,
        )
        if unit is not None:
            symbol, unit_source = unit
            quantity.set_unit(
                tg=tg,
                g=g,
                unit=symbol,
                source_info=unit_source,
            )
        return quantity

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_number(
        self,
        tg: TypeGraph,
        g: GraphView,
        number: int | float,
        *,
        source_info: SourceInfo | None = None,
    ):
        number_node = self.number.get()
        number_node.set_value(tg=tg, g=g, value=number)
        if source_info is not None:
            number_node.set_source_info(tg=tg, g=g, source_info=source_info)

    def set_unit(
        self,
        tg: TypeGraph,
        g: GraphView,
        unit: str,
        *,
        source_info: SourceInfo | None = None,
    ):
        unit_node = self.unit.get()
        unit_node.set_symbol(tg=tg, g=g, symbol=unit)
        if source_info is not None:
            unit_node.set_source_info(tg=tg, g=g, source_info=source_info)


class BinaryExpression(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.operator = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        operator: str,
        left: NodeType,
        right: NodeType,
    ) -> Self:
        binary = super().create_instance(tg=tg, g=g)
        binary.set_source_info(tg=tg, g=g, source_info=source_info)
        binary.set_operator(tg=tg, g=g, operator=operator)
        binary.set_left(tg=tg, g=g, node=left)
        binary.set_right(tg=tg, g=g, node=right)
        return binary

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_operator(self, tg: TypeGraph, g: GraphView, operator: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.operator.get().instance.node(), value=operator
        )

    def set_left(self, tg: TypeGraph, g: GraphView, node: NodeType):
        child = Child(type(node), tg=tg).bind(node.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier="left",
        )

    def set_right(self, tg: TypeGraph, g: GraphView, node: NodeType):
        child = Child(type(node), tg=tg).bind(node.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier="right",
        )


class GroupExpression(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, expression: NodeType
    ) -> Self:
        group = super().create_instance(tg=tg, g=g)
        group.set_source_info(tg=tg, g=g, source_info=source_info)
        group.set_expression(tg=tg, g=g, expression=expression)
        return group

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_expression(self, tg: TypeGraph, g: GraphView, expression: NodeType):
        child = Child(type(expression), tg=tg).bind(expression.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=expression.instance.node(),
            child_identifier="expression",
        )


class ComparisonClause(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.operator = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        operator: str,
        right: NodeType,
    ) -> Self:
        clause = super().create_instance(tg=tg, g=g)
        clause.set_source_info(tg=tg, g=g, source_info=source_info)
        clause.set_operator(tg=tg, g=g, operator=operator)
        clause.set_right(tg=tg, g=g, node=right)
        return clause

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_operator(self, tg: TypeGraph, g: GraphView, operator: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.operator.get().instance.node(), value=operator
        )

    def set_right(self, tg: TypeGraph, g: GraphView, node: NodeType):
        child = Child(type(node), tg=tg).bind(node.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier="right",
        )


class ComparisonExpression(NodeType):
    _clause_idx = 0

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        left: NodeType,
        clauses: Iterable[ComparisonClause],
    ) -> Self:
        comparison = super().create_instance(tg=tg, g=g)
        comparison.set_source_info(tg=tg, g=g, source_info=source_info)
        comparison.set_left(tg=tg, g=g, node=left)
        for clause in clauses:
            comparison.add_clause(tg=tg, g=g, clause=clause)
        return comparison

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def set_left(self, tg: TypeGraph, g: GraphView, node: NodeType):
        child = Child(type(node), tg=tg).bind(node.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier="left",
        )

    def add_clause(self, tg: TypeGraph, g: GraphView, clause: ComparisonClause):
        ComparisonExpression._clause_idx += 1
        child = Child(type(clause), tg=tg).bind(clause.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=clause.instance.node(),
            child_identifier=f"clause_{ComparisonExpression._clause_idx}",
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
        quantity_value_source_info: SourceInfo,
        quantity_unit_source_info: SourceInfo | None,
        tolerance_value: int | float,
        tolerance_unit: str | None,
        tolerance_source_info: SourceInfo,
        tolerance_value_source_info: SourceInfo,
        tolerance_unit_source_info: SourceInfo | None,
    ) -> Self:
        bilateral_quantity = super().create_instance(tg=tg, g=g)
        bilateral_quantity.source.get().set_source_info(
            tg=tg, g=g, source_info=source_info
        )
        quantity_node = bilateral_quantity.quantity.get()
        quantity_node.set_source_info(tg=tg, g=g, source_info=quantity_source_info)
        quantity_node.set_number(
            tg=tg,
            g=g,
            number=quantity_value,
            source_info=quantity_value_source_info,
        )
        if quantity_unit is not None:
            quantity_node.set_unit(
                tg=tg,
                g=g,
                unit=quantity_unit,
                source_info=quantity_unit_source_info,
            )

        tolerance_node = bilateral_quantity.tolerance.get()
        tolerance_node.set_source_info(tg=tg, g=g, source_info=tolerance_source_info)
        tolerance_node.set_number(
            tg=tg,
            g=g,
            number=tolerance_value,
            source_info=tolerance_value_source_info,
        )
        if tolerance_unit is not None:
            tolerance_node.set_unit(
                tg=tg,
                g=g,
                unit=tolerance_unit,
                source_info=tolerance_unit_source_info,
            )

        return bilateral_quantity


class BoundedQuantity(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.start = Child(Quantity, tg=tg)
        cls.end = Child(Quantity, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        start_value: int | float,
        start_unit: str | None,
        start_source_info: SourceInfo,
        start_value_source_info: SourceInfo,
        start_unit_source_info: SourceInfo | None,
        end_value: int | float,
        end_unit: str | None,
        end_source_info: SourceInfo,
        end_value_source_info: SourceInfo,
        end_unit_source_info: SourceInfo | None,
    ) -> Self:
        bounded = super().create_instance(tg=tg, g=g)
        bounded.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        start_quantity = bounded.start.get()
        start_quantity.set_source_info(tg=tg, g=g, source_info=start_source_info)
        start_quantity.set_number(
            tg=tg,
            g=g,
            number=start_value,
            source_info=start_value_source_info,
        )
        if start_unit is not None:
            start_quantity.set_unit(
                tg=tg,
                g=g,
                unit=start_unit,
                source_info=start_unit_source_info,
            )

        end_quantity = bounded.end.get()
        end_quantity.set_source_info(tg=tg, g=g, source_info=end_source_info)
        end_quantity.set_number(
            tg=tg,
            g=g,
            number=end_value,
            source_info=end_value_source_info,
        )
        if end_unit is not None:
            end_quantity.set_unit(
                tg=tg,
                g=g,
                unit=end_unit,
                source_info=end_unit_source_info,
            )

        return bounded


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
        cls.block_type = Child(Parameter, tg=tg)
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

        constrain_to_literal(
            g=g,
            tg=tg,
            node=block_definition.block_type.get().instance.node(),
            value=block_type_val,
        )

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


@dataclass(frozen=True)
class SliceConfig:
    source: SourceInfo
    start: tuple[int, SourceInfo] | None = None
    stop: tuple[int, SourceInfo] | None = None
    step: tuple[int, SourceInfo] | None = None


class Slice(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.start = Child(Number, tg=tg)
        cls.stop = Child(Number, tg=tg)
        cls.step = Child(Number, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        *,
        start: tuple[int, SourceInfo] | None = None,
        stop: tuple[int, SourceInfo] | None = None,
        step: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        slice_node = super().create_instance(tg=tg, g=g)
        slice_node.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        if start is not None:
            slice_node.set_start(tg=tg, g=g, value=start[0], source_info=start[1])

        if stop is not None:
            slice_node.set_stop(tg=tg, g=g, value=stop[0], source_info=stop[1])

        if step is not None:
            slice_node.set_step(tg=tg, g=g, value=step[0], source_info=step[1])

        return slice_node

    def set_start(
        self, tg: TypeGraph, g: GraphView, value: int, source_info: SourceInfo
    ):
        number = self.start.get()
        number.set_value(tg=tg, g=g, value=value)
        number.set_source_info(tg=tg, g=g, source_info=source_info)

    def set_stop(
        self, tg: TypeGraph, g: GraphView, value: int, source_info: SourceInfo
    ):
        number = self.stop.get()
        number.set_value(tg=tg, g=g, value=value)
        number.set_source_info(tg=tg, g=g, source_info=source_info)

    def set_step(
        self, tg: TypeGraph, g: GraphView, value: int, source_info: SourceInfo
    ):
        number = self.step.get()
        number.set_value(tg=tg, g=g, value=value)
        number.set_source_info(tg=tg, g=g, source_info=source_info)


class IterableFieldRef(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.field = Child(FieldRef, tg=tg)
        cls.slice = Child(Slice, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        *,
        field_parts: Iterable[FieldRefPart.Info],
        field_source_info: SourceInfo,
        slice_config: SliceConfig | None = None,
    ) -> Self:
        iterable = super().create_instance(tg=tg, g=g)
        iterable.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        field_node = iterable.field.get()
        field_node.set_source_info(tg=tg, g=g, source_info=field_source_info)
        for part in field_parts:
            field_part = FieldRefPart.create_instance(tg=tg, g=g, info=part)
            field_node.add_part(tg=tg, g=g, part=field_part)

        if slice_config is not None:
            slice_node = iterable.slice.get()
            slice_node.source.get().set_source_info(
                tg=tg, g=g, source_info=slice_config.source
            )
            if slice_config.start is not None:
                slice_node.set_start(
                    tg=tg,
                    g=g,
                    value=slice_config.start[0],
                    source_info=slice_config.start[1],
                )
            if slice_config.stop is not None:
                slice_node.set_stop(
                    tg=tg,
                    g=g,
                    value=slice_config.stop[0],
                    source_info=slice_config.stop[1],
                )
            if slice_config.step is not None:
                slice_node.set_step(
                    tg=tg,
                    g=g,
                    value=slice_config.step[0],
                    source_info=slice_config.step[1],
                )
        return iterable


class FieldRefList(NodeType):
    _item_idx = 0

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        items: Iterable[FieldRef],
    ) -> Self:
        fr_list = super().create_instance(tg=tg, g=g)
        fr_list.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        for item in items:
            fr_list.add_item(tg=tg, g=g, item=item)
        return fr_list

    def add_item(self, tg: TypeGraph, g: GraphView, item: FieldRef):
        FieldRefList._item_idx += 1
        child = Child(type(item), tg=tg).bind(item.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=item.instance.node(),
            child_identifier=f"item_{FieldRefList._item_idx}",
        )


class ForStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.scope = Child(Scope, tg=tg)
        cls.target = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        target: str,
        iterable: NodeType,
        body_stmts: Iterable[NodeType],
    ) -> Self:
        for_stmt = super().create_instance(tg=tg, g=g)
        for_stmt.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        for_stmt.set_target(tg=tg, g=g, target=target)
        for_stmt.set_iterable(tg=tg, g=g, iterable=iterable)
        scope_node = for_stmt.scope.get()
        for stmt in body_stmts:
            scope_node.add_stmt(tg=tg, g=g, stmt=stmt)
        return for_stmt

    def set_target(self, tg: TypeGraph, g: GraphView, target: str):
        constrain_to_literal(
            g=g, tg=tg, node=self.target.get().instance.node(), value=target
        )

    def set_iterable(self, tg: TypeGraph, g: GraphView, iterable: NodeType):
        child = Child(type(iterable), tg=tg).bind(iterable.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=iterable.instance.node(),
            child_identifier="iterable",
        )


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

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        name: str,
        value: LiteralT,
    ) -> Self:
        template_arg = super().create_instance(tg=tg, g=g)
        template_arg.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        constrain_to_literal(
            g=g, tg=tg, node=template_arg.name.get().instance.node(), value=name
        )
        constrain_to_literal(
            g=g, tg=tg, node=template_arg.value.get().instance.node(), value=value
        )
        return template_arg


class Template(NodeType):
    _arg_idx = 0

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        args: Iterable[TemplateArg],
    ) -> Self:
        template = super().create_instance(tg=tg, g=g)
        template.set_source_info(tg=tg, g=g, source_info=source_info)
        for arg in args:
            template.add_arg(tg=tg, g=g, arg=arg)
        return template

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

    def add_arg(self, tg: TypeGraph, g: GraphView, arg: TemplateArg):
        Template._arg_idx += 1
        child = Child(TemplateArg, tg=tg).bind(arg.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=arg.instance.node(),
            child_identifier=f"arg_{Template._arg_idx}",
        )


class NewExpression(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.type_ref = Child(TypeRef, tg=tg)
        cls.template = Child(Template, tg=tg)
        cls.new_count = Child(Number, tg=tg)

    def set_new_count(
        self, tg: TypeGraph, g: GraphView, count: int, source_info: SourceInfo
    ):
        number = self.new_count.get()
        number.set_value(tg=tg, g=g, value=count)
        number.set_source_info(tg=tg, g=g, source_info=source_info)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        *,
        template: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        new_count: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        new_expression = super().create_instance(tg=tg, g=g)
        new_expression.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        new_expression.type_ref.get().set_name(tg=tg, g=g, name=type_ref_name)
        new_expression.type_ref.get().set_source(
            tg=tg, g=g, source_info=type_ref_source_info
        )
        if template is not None:
            template_source, template_args = template
            template_node = new_expression.template.get()
            template_node.set_source_info(tg=tg, g=g, source_info=template_source)
            for arg in template_args:
                template_node.add_arg(tg=tg, g=g, arg=arg)

        if new_count is not None:
            count, count_source_info = new_count
            new_expression.set_new_count(
                tg=tg, g=g, count=count, source_info=count_source_info
            )

        return new_expression

    def set_source_info(self, tg: TypeGraph, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(tg=tg, g=g, source_info=source_info)


AssignableT = NewExpression  # FIXME


class Assignable(NodeType):
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
        assignable_value: AssignableT,
        assignable_source_info: SourceInfo,
    ) -> Self:
        assignment = super().create_instance(tg=tg, g=g)
        assignment.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        for part_info in target_field_ref_parts:
            field_ref_part = FieldRefPart.create_instance(tg=tg, g=g, info=part_info)
            assignment.target.get().add_part(tg=tg, g=g, part=field_ref_part)

        assignment.target.get().set_source_info(
            tg=tg, g=g, source_info=target_field_ref_source_info
        )

        assignment.assignable.get().set_value(tg=tg, g=g, value=assignable_value)
        assignment.assignable.get().set_source_info(
            tg=tg, g=g, source_info=assignable_source_info
        )

        return assignment


class ConnectStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        left: NodeType,
        right: NodeType,
    ) -> Self:
        connect = super().create_instance(tg=tg, g=g)
        connect.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        connect._set_endpoint(tg=tg, g=g, identifier="left", node=left)
        connect._set_endpoint(tg=tg, g=g, identifier="right", node=right)
        return connect

    def _set_endpoint(
        self, tg: TypeGraph, g: GraphView, identifier: str, node: NodeType
    ) -> None:
        child = Child(type(node), tg=tg).bind(node.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier=identifier,
        )


class DirectedConnectStmt(NodeType):
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.direction = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        direction: "DirectedConnectStmt.Direction",
        left: NodeType,
        right: NodeType,
    ) -> Self:
        directed = super().create_instance(tg=tg, g=g)
        directed.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        directed.set_direction(tg=tg, g=g, direction=direction)
        directed._set_endpoint(tg=tg, g=g, identifier="left", node=left)
        directed._set_endpoint(tg=tg, g=g, identifier="right", node=right)
        return directed

    def set_direction(
        self, tg: TypeGraph, g: GraphView, direction: "DirectedConnectStmt.Direction"
    ):
        constrain_to_literal(
            g=g,
            tg=tg,
            node=self.direction.get().instance.node(),
            value=direction.value,
        )

    def _set_endpoint(
        self, tg: TypeGraph, g: GraphView, identifier: str, node: NodeType
    ) -> None:
        child = Child(type(node), tg=tg).bind(node.instance)
        self.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=self.instance,
            child=node.instance.node(),
            child_identifier=identifier,
        )


class RetypeStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.field_ref = Child(FieldRef, tg=tg)
        cls.type_ref = Child(TypeRef, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        field_ref_parts: Iterable[FieldRefPart.Info],
        field_ref_source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
    ) -> Self:
        retype = super().create_instance(tg=tg, g=g)
        retype.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        field_node = retype.field_ref.get()
        field_node.set_source_info(tg=tg, g=g, source_info=field_ref_source_info)
        for part in field_ref_parts:
            field_part = FieldRefPart.create_instance(tg=tg, g=g, info=part)
            field_node.add_part(tg=tg, g=g, part=field_part)

        type_node = retype.type_ref.get()
        type_node.set_name(tg=tg, g=g, name=type_ref_name)
        type_node.set_source(tg=tg, g=g, source_info=type_ref_source_info)

        return retype


class PinDeclaration(NodeType):
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.kind = Child(Parameter, tg=tg)
        cls.label = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        kind: "PinDeclaration.Kind",
        *,
        label_value: LiteralT | None = None,
    ) -> Self:
        pin = super().create_instance(tg=tg, g=g)
        pin.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        pin.set_kind(tg=tg, g=g, kind=kind)
        if label_value is not None:
            pin.set_label(tg=tg, g=g, value=label_value)
        return pin

    def set_kind(self, tg: TypeGraph, g: GraphView, kind: "PinDeclaration.Kind"):
        constrain_to_literal(
            g=g, tg=tg, node=self.kind.get().instance.node(), value=kind.value
        )

    def set_label(self, tg: TypeGraph, g: GraphView, value: LiteralT):
        constrain_to_literal(
            g=g, tg=tg, node=self.label.get().instance.node(), value=value
        )


class SignaldefStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.name = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, name: str
    ) -> Self:
        signal = super().create_instance(tg=tg, g=g)
        signal.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        constrain_to_literal(
            g=g, tg=tg, node=signal.name.get().instance.node(), value=name
        )
        return signal


class AssertStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        comparison: ComparisonExpression,
    ) -> Self:
        assert_stmt = super().create_instance(tg=tg, g=g)
        assert_stmt.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        child = Child(type(comparison), tg=tg).bind(comparison.instance)
        assert_stmt.add_anon_child(child)
        EdgeComposition.add_child(
            bound_node=assert_stmt.instance,
            child=comparison.instance.node(),
            child_identifier="comparison",
        )
        return assert_stmt


class DeclarationStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.field_ref = Child(FieldRef, tg=tg)
        cls.unit = Child(Unit, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        field_ref_parts: Iterable[FieldRefPart.Info],
        field_ref_source_info: SourceInfo,
        unit_symbol: str,
        unit_source_info: SourceInfo,
    ) -> Self:
        declaration = super().create_instance(tg=tg, g=g)
        declaration.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        field_node = declaration.field_ref.get()
        field_node.set_source_info(tg=tg, g=g, source_info=field_ref_source_info)
        for part in field_ref_parts:
            field_part = FieldRefPart.create_instance(tg=tg, g=g, info=part)
            field_node.add_part(tg=tg, g=g, part=field_part)

        unit_node = declaration.unit.get()
        unit_node.set_source_info(tg=tg, g=g, source_info=unit_source_info)
        unit_node.set_symbol(tg=tg, g=g, symbol=unit_symbol)

        return declaration


class String(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.text = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, text: str
    ) -> Self:
        string = super().create_instance(tg=tg, g=g)
        string.set_source_info(tg=tg, g=g, source_info=source_info)
        string.set_text(tg=tg, g=g, text=text)
        return string

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


class PassStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo
    ) -> Self:
        stmt = super().create_instance(tg=tg, g=g)
        stmt.source.get().set_source_info(tg=tg, g=g, source_info=source_info)
        return stmt


class TraitStmt(NodeType):
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        cls.source = Child(SourceChunk, tg=tg)
        cls.type_ref = Child(TypeRef, tg=tg)
        cls.target = Child(FieldRef, tg=tg)
        cls.template = Child(Template, tg=tg)
        cls.constructor = Child(Parameter, tg=tg)

    @classmethod
    def create_instance(
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        *,
        target_parts: Iterable[FieldRefPart.Info] | None = None,
        target_source_info: SourceInfo | None = None,
        template_data: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        constructor: str | None = None,
    ) -> Self:
        trait = super().create_instance(tg=tg, g=g)
        trait.source.get().set_source_info(tg=tg, g=g, source_info=source_info)

        type_node = trait.type_ref.get()
        type_node.set_name(tg=tg, g=g, name=type_ref_name)
        type_node.set_source(tg=tg, g=g, source_info=type_ref_source_info)

        if target_parts is not None and target_source_info is not None:
            target_node = trait.target.get()
            target_node.set_source_info(tg=tg, g=g, source_info=target_source_info)
            for part in target_parts:
                target_node.add_part(
                    tg=tg,
                    g=g,
                    part=FieldRefPart.create_instance(tg=tg, g=g, info=part),
                )

        if template_data is not None:
            template_source, template_args = template_data
            template_node = trait.template.get()
            template_node.set_source_info(tg=tg, g=g, source_info=template_source)
            for arg in template_args:
                template_node.add_arg(tg=tg, g=g, arg=arg)

        if constructor is not None:
            trait.set_constructor(tg=tg, g=g, constructor=constructor)

        return trait

    def set_constructor(self, tg: TypeGraph, g: GraphView, constructor: str):
        constrain_to_literal(
            g=g,
            tg=tg,
            node=self.constructor.get().instance.node(),
            value=constructor,
        )
