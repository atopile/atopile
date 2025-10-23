"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Self

from faebryk.core.node import BoundNodeType, Node, Parameter, Sequence, Set
from faebryk.core.zig.gen.graph.graph import GraphView

# TODO: capture dynamic substructure in TypeGraph schema


@dataclass(frozen=True)
class SourceInfo:
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    text: str


class FileLocation(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.start_line = t.Child(Parameter)
        cls.start_col = t.Child(Parameter)
        cls.end_line = t.Child(Parameter)
        cls.end_col = t.Child(Parameter)

    def setup(
        self, g: GraphView, start_line: int, start_col: int, end_line: int, end_col: int
    ) -> Self:
        self.start_line.get().constrain_to_literal(g=g, value=start_line)
        self.start_col.get().constrain_to_literal(g=g, value=start_col)
        self.end_line.get().constrain_to_literal(g=g, value=end_line)
        self.end_col.get().constrain_to_literal(g=g, value=end_col)
        return self


class SourceChunk(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.text = t.Child(Parameter)
        cls.loc = t.Child(FileLocation)

    def setup(self, g: GraphView, source_info: SourceInfo) -> Self:
        self.text.get().constrain_to_literal(g=g, value=source_info.text)
        self.loc.get().setup(
            g=g,
            start_line=source_info.start_line,
            start_col=source_info.start_col,
            end_line=source_info.end_line,
            end_col=source_info.end_col,
        )
        return self


class TypeRef(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.name = t.Child(Parameter)
        cls.source = t.Child(SourceChunk)

    def setup(self, g: GraphView, name: str, source_info: SourceInfo) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.name.get().constrain_to_literal(g=g, value=name)
        return self


class ImportPath(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.path = t.Child(Parameter)

    def setup(self, g: GraphView, path: str, source_info: SourceInfo) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.path.get().constrain_to_literal(g=g, value=path)
        return self


class FieldRefPart(Node):
    @dataclass(frozen=True)
    class Info:
        name: str
        key: int | str | None
        source_info: SourceInfo

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.name = t.Child(Parameter)
        cls.key = t.Child(Parameter)

    def setup(self, g: GraphView, info: Info) -> Self:
        self.source.get().setup(g=g, source_info=info.source_info)
        self.name.get().constrain_to_literal(g=g, value=info.name)

        if info.key is not None:
            self.key.get().constrain_to_literal(g=g, value=info.key)

        return self


class FieldRef(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.pin = t.Child(Parameter)
        cls.parts = t.Child(Sequence)

    def setup(
        self, g: GraphView, source_info: SourceInfo, parts: Iterable[FieldRefPart.Info]
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        for part_info in parts:
            part = FieldRefPart.bind_typegraph(self.tg).create_instance(g=g)
            part.setup(g=g, info=part_info)

            self.compose_with(part)
            self.parts.get().append(part)

        return self


class Number(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.value = t.Child(Parameter)

    def setup(self, g: GraphView, source_info: SourceInfo, value: int | float) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.value.get().constrain_to_literal(g=g, value=value)

        return self


class Boolean(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.value = t.Child(Parameter)

    def setup(self, g: GraphView, source_info: SourceInfo, value: bool) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.value.get().constrain_to_literal(g=g, value=value)
        return self


class Unit(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.symbol = t.Child(Parameter)

    def setup(self, g: GraphView, source_info: SourceInfo, symbol: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.symbol.get().constrain_to_literal(g=g, value=symbol)
        return self


class Quantity(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.number = t.Child(Number)
        cls.unit = t.Child(Unit)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        value: int | float,
        value_source_info: SourceInfo,
        unit: tuple[str, SourceInfo] | None = None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.number.get().setup(g=g, source_info=value_source_info, value=value)

        if unit is not None:
            symbol, unit_source = unit
            self.unit.get().setup(g=g, source_info=unit_source, symbol=symbol)

        return self


class BinaryExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.operator = t.Child(Parameter)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        operator: str,
        lhs: "ArithmeticT",
        rhs: "ArithmeticT",
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.operator.get().constrain_to_literal(g=g, value=operator)

        self.compose_with(lhs, name="lhs")
        self.compose_with(rhs, name="rhs")

        return self


class GroupExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    def setup(
        self, g: GraphView, source_info: SourceInfo, expression: "ArithmeticT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.compose_with(expression, name="expression")
        return self


class ComparisonClause(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.operator = t.Child(Parameter)

    def setup(
        self, g: GraphView, source_info: SourceInfo, operator: str, rhs: "ArithmeticT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.operator.get().constrain_to_literal(g=g, value=operator)
        self.compose_with(rhs, name="rhs")
        return self


class ComparisonExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.rhs_clauses = t.Child(Sequence)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        lhs: "ArithmeticT",
        rhs_clauses: Iterable["ComparisonClause"],
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.compose_with(lhs, name="lhs")

        for clause in rhs_clauses:
            self.compose_with(clause)
            self.rhs_clauses.get().append(clause)

        return self


class BilateralQuantity(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.quantity = t.Child(Quantity)
        cls.tolerance = t.Child(Quantity)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        quantity_value: int | float,
        quantity_value_source_info: SourceInfo,
        quantity_unit: tuple[str, SourceInfo] | None,
        quantity_source_info: SourceInfo,
        tolerance_value: int | float,
        tolerance_value_source_info: SourceInfo,
        tolerance_unit: tuple[str, SourceInfo] | None,
        tolerance_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        self.quantity.get().setup(
            g=g,
            source_info=quantity_source_info,
            value=quantity_value,
            value_source_info=quantity_value_source_info,
            unit=quantity_unit,
        )

        self.tolerance.get().setup(
            g=g,
            source_info=tolerance_source_info,
            value=tolerance_value,
            value_source_info=tolerance_value_source_info,
            unit=tolerance_unit,
        )

        return self


class BoundedQuantity(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.start = t.Child(Quantity)
        cls.end = t.Child(Quantity)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        start_value: int | float,
        start_unit: tuple[str, SourceInfo] | None,
        start_source_info: SourceInfo,
        start_value_source_info: SourceInfo,
        end_value: int | float,
        end_unit: tuple[str, SourceInfo] | None,
        end_source_info: SourceInfo,
        end_value_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        self.start.get().setup(
            g=g,
            source_info=start_source_info,
            value=start_value,
            value_source_info=start_value_source_info,
            unit=start_unit,
        )

        self.end.get().setup(
            g=g,
            source_info=end_source_info,
            value=end_value,
            value_source_info=end_value_source_info,
            unit=end_unit,
        )

        return self


class Scope(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.stmts = t.Child(Set)

    def setup(self, g: GraphView, stmts: Iterable["StatementT"]) -> Self:
        for stmt in stmts:
            self.stmts.get().append(stmt)
            self.compose_with(stmt)

        return self

    # TODO: get_child_stmts -> Iterable[Assignment | ...]


class File(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.scope = t.Child(Scope)
        cls.path = t.Child(Parameter)

    # TODO: optional path
    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        path: str,
        stmts: Iterable["StatementT"],
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.path.get().constrain_to_literal(g=g, value=path)
        self.scope.get().setup(g=g, stmts=stmts)

        return self


class BlockDefinition(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.block_type = t.Child(Parameter)  # TODO: enum domain
        cls.type_ref = t.Child(TypeRef)
        cls.super_type_ref = t.Child(TypeRef)
        cls.scope = t.Child(Scope)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        block_type: str,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        super_type_ref_info: tuple[str, SourceInfo] | None,
        stmts: Iterable["StatementT"],
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.block_type.get().constrain_to_literal(g=g, value=block_type)

        self.type_ref.get().setup(
            g=g, name=type_ref_name, source_info=type_ref_source_info
        )

        if super_type_ref_info is not None:
            self.super_type_ref.get().setup(
                g=g, name=super_type_ref_info[0], source_info=super_type_ref_info[1]
            )

        self.scope.get().setup(g=g, stmts=stmts)

        return self


@dataclass(frozen=True)
class SliceConfig:
    source: SourceInfo
    start: tuple[int, SourceInfo] | None = None
    stop: tuple[int, SourceInfo] | None = None
    step: tuple[int, SourceInfo] | None = None


class Slice(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.start = t.Child(Number)
        cls.stop = t.Child(Number)
        cls.step = t.Child(Number)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        start: tuple[int, SourceInfo] | None = None,
        stop: tuple[int, SourceInfo] | None = None,
        step: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        if start is not None:
            start_value, start_source_info = start
            self.start.get().setup(
                g=g, source_info=start_source_info, value=start_value
            )

        if stop is not None:
            stop_value, stop_source_info = stop
            self.stop.get().setup(g=g, source_info=stop_source_info, value=stop_value)

        if step is not None:
            step_value, step_source_info = step
            self.step.get().setup(g=g, source_info=step_source_info, value=step_value)

        return self


class IterableFieldRef(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.field = t.Child(FieldRef)
        cls.slice = t.Child(Slice)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        field_parts: Iterable[FieldRefPart.Info],
        field_source_info: SourceInfo,
        slice_config: SliceConfig | None = None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.field.get().setup(g=g, source_info=field_source_info, parts=field_parts)

        if slice_config is not None:
            self.slice.get().source.get().setup(g=g, source_info=slice_config.source)

            if slice_config.start is not None:
                start_value, start_source_info = slice_config.start
                self.slice.get().start.get().setup(
                    g=g, source_info=start_source_info, value=start_value
                )

            if slice_config.stop is not None:
                stop_value, stop_source_info = slice_config.stop
                self.slice.get().stop.get().setup(
                    g=g, source_info=stop_source_info, value=stop_value
                )

            if slice_config.step is not None:
                step_value, step_source_info = slice_config.step
                self.slice.get().step.get().setup(
                    g=g, source_info=step_source_info, value=step_value
                )

        return self


class FieldRefList(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.items = t.Child(Sequence)

    def setup(
        self, g: GraphView, source_info: SourceInfo, items: Iterable[FieldRef]
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        for item in items:
            self.items.get().append(item)
            self.compose_with(item)

        return self


class ForStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.scope = t.Child(Scope)
        cls.target = t.Child(Parameter)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        target: str,
        iterable: "IterableFieldRef | FieldRefList",
        stmts: Iterable["StatementT"],
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.target.get().constrain_to_literal(g=g, value=target)
        self.compose_with(iterable, name="iterable")
        self.scope.get().setup(g=g, stmts=stmts)
        return self


class PragmaStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.pragma = t.Child(Parameter)

    def setup(self, g: GraphView, source_info: SourceInfo, pragma: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.pragma.get().constrain_to_literal(g=g, value=pragma)
        return self


class ImportStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.path = t.Child(ImportPath)
        cls.type_ref = t.Child(TypeRef)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        path_info: tuple[str, SourceInfo] | None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.type_ref.get().setup(
            g=g, name=type_ref_name, source_info=type_ref_source_info
        )

        if path_info is not None:
            path, path_source_info = path_info
            self.path.get().setup(g=g, path=path, source_info=path_source_info)

        return self


class TemplateArg(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.name = t.Child(Parameter)
        cls.value = t.Child(Parameter)

    def setup(
        self, g: GraphView, source_info: SourceInfo, name: str, value: "LiteralT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.name.get().constrain_to_literal(g=g, value=name)
        self.value.get().constrain_to_literal(g=g, value=value)
        return self


class Template(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    def setup(
        self, g: GraphView, source_info: SourceInfo, args: Iterable[TemplateArg]
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        for i, arg in enumerate(args):
            self.compose_with(arg, name=f"arg_{i}")

        return self


class NewExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.type_ref = t.Child(TypeRef)
        cls.template = t.Child(Template)
        cls.new_count = t.Child(Number)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        template: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        new_count_info: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.type_ref.get().setup(
            g=g, name=type_ref_name, source_info=type_ref_source_info
        )

        if template is not None:
            template_source, template_args = template
            self.template.get().setup(
                g=g, source_info=template_source, args=template_args
            )

        if new_count_info is not None:
            count, count_source_info = new_count_info
            self.new_count.get().setup(g=g, source_info=count_source_info, value=count)

        return self


class String(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.text = t.Child(Parameter)

    def setup(self, g: GraphView, source_info: SourceInfo, text: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.text.get().constrain_to_literal(g=g, value=text)
        return self


class Assignable(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    def setup(
        self, g: GraphView, source_info: SourceInfo, value: "AssignableT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        # TODO: record in schema: name, expected types, is required
        self.compose_with(value, name="value")
        return self

    # TODO: get_value -> AssignableT


class Assignment(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.target = t.Child(FieldRef)  # TODO: declarations?
        cls.assignable = t.Child(Assignable)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        target_field_ref_parts: list[FieldRefPart.Info],
        target_field_ref_source_info: SourceInfo,
        assignable_value: "AssignableT",
        assignable_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.target.get().setup(
            g=g, source_info=target_field_ref_source_info, parts=target_field_ref_parts
        )
        self.assignable.get().setup(
            g=g, source_info=assignable_source_info, value=assignable_value
        )
        return self


class ConnectStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        lhs: "ConnectableT",
        rhs: "ConnectableT",
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.compose_with(lhs, name="lhs")
        self.compose_with(rhs, name="rhs")
        return self


class DirectedConnectStmt(Node):
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.direction = t.Child(Parameter)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        direction: "DirectedConnectStmt.Direction",
        lhs: "ConnectableT",
        rhs: "ConnectableT | DirectedConnectStmt",
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.direction.get().constrain_to_literal(g=g, value=direction.value)
        self.compose_with(lhs, name="lhs")
        self.compose_with(rhs, name="rhs")
        return self


class RetypeStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.target = t.Child(FieldRef)
        cls.new_type_ref = t.Child(TypeRef)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        target_parts: Iterable[FieldRefPart.Info],
        target_source_info: SourceInfo,
        new_type_name: str,
        new_type_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.target.get().setup(g=g, source_info=target_source_info, parts=target_parts)
        self.new_type_ref.get().setup(
            g=g, name=new_type_name, source_info=new_type_source_info
        )
        return self


class PinDeclaration(Node):
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.kind = t.Child(Parameter)
        cls.label = t.Child(Parameter)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        kind: "PinDeclaration.Kind",
        label_value: "LiteralT | None" = None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.kind.get().constrain_to_literal(g=g, value=kind.value)

        if label_value is not None:
            self.label.get().constrain_to_literal(g=g, value=label_value)

        return self


class SignaldefStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.name = t.Child(Parameter)

    def setup(self, g: GraphView, source_info: SourceInfo, name: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.name.get().constrain_to_literal(g=g, value=name)
        return self


class AssertStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    def setup(
        self, g: GraphView, source_info: SourceInfo, comparison: ComparisonExpression
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.compose_with(comparison, name="comparison")
        return self


class DeclarationStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.field_ref = t.Child(FieldRef)
        cls.unit = t.Child(Unit)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        field_ref_parts: Iterable[FieldRefPart.Info],
        field_ref_source_info: SourceInfo,
        unit_symbol: str,
        unit_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.field_ref.get().setup(
            g=g, source_info=field_ref_source_info, parts=field_ref_parts
        )
        self.unit.get().setup(g=g, source_info=unit_source_info, symbol=unit_symbol)
        return self


class StringStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.string = t.Child(String)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        string_value: str,
        string_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.string.get().setup(g=g, source_info=string_source_info, text=string_value)
        return self


class PassStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    def setup(self, g: GraphView, source_info: SourceInfo) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        return self


class TraitStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.type_ref = t.Child(TypeRef)
        cls.target = t.Child(FieldRef)
        cls.template = t.Child(Template)
        cls.constructor = t.Child(Parameter)

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        target_info: tuple[Iterable[FieldRefPart.Info], SourceInfo] | None = None,
        template_info: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        constructor: str | None = None,
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        self.type_ref.get().setup(
            g=g, name=type_ref_name, source_info=type_ref_source_info
        )

        if target_info is not None:
            target_parts, target_source_info = target_info
            self.target.get().setup(
                g=g, source_info=target_source_info, parts=target_parts
            )

        if template_info is not None:
            template_source, template_args = template_info
            self.template.get().setup(
                g=g, source_info=template_source, args=template_args
            )

        if constructor is not None:
            self.constructor.get().constrain_to_literal(g=g, value=constructor)

        return self


LiteralT = float | int | str | bool

ArithmeticAtomT = (
    FieldRef | Quantity | BilateralQuantity | BoundedQuantity | GroupExpression
)

ArithmeticT = BinaryExpression | ArithmeticAtomT

AssignableT = (
    NewExpression
    | String
    | Boolean
    | Quantity
    | BoundedQuantity
    | BilateralQuantity
    | ArithmeticT
)

ConnectableT = FieldRef | SignaldefStmt | PinDeclaration

StatementT = (
    Assignment
    | AssertStmt
    | BlockDefinition
    | ConnectStmt
    | DeclarationStmt
    | DirectedConnectStmt
    | ForStmt
    | ImportStmt
    | PassStmt
    | PinDeclaration
    | PragmaStmt
    | RetypeStmt
    | SignaldefStmt
    | StringStmt
    | TraitStmt
)
