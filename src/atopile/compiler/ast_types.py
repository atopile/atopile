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

from faebryk.core.node import BoundNodeType, Node, Parameter
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import GraphView

# TODO: remove `set_*` methods that could be incorporated into `setup`
# TODO: capture dynamic substructure in TypeGraph schema
# TODO: standardize on rhs/lhs instead of left/right for expressions


@dataclass(frozen=True)
class SourceInfo:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    text: str


LiteralT = float | int | str | bool


class FileLocation(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.start_line = t.Child(Parameter)
        cls.start_col = t.Child(Parameter)
        cls.end_line = t.Child(Parameter)
        cls.end_col = t.Child(Parameter)

    def set_start_line(self, g: GraphView, value: int):
        self.start_line.get().constrain_to_literal(g=g, value=value)

    def set_start_col(self, g: GraphView, value: int):
        self.start_col.get().constrain_to_literal(g=g, value=value)

    def set_end_line(self, g: GraphView, value: int):
        self.end_line.get().constrain_to_literal(g=g, value=value)

    def set_end_col(self, g: GraphView, value: int):
        self.end_col.get().constrain_to_literal(g=g, value=value)


class SourceChunk(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.text = t.Child(Parameter)
        cls.loc = t.Child(FileLocation)

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.text.get().constrain_to_literal(g=g, value=source_info.text)
        self.loc.get().set_start_line(g=g, value=source_info.start_line)
        self.loc.get().set_start_col(g=g, value=source_info.start_column)
        self.loc.get().set_end_line(g=g, value=source_info.end_line)
        self.loc.get().set_end_col(g=g, value=source_info.end_column)


class TypeRef(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.name = t.Child(Parameter)
        cls.source = t.Child(SourceChunk)

    def set_name(self, g: GraphView, name: str):
        self.name.get().constrain_to_literal(g=g, value=name)

    def set_source(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)


class ImportPath(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.path = t.Child(Parameter)

    def set_path(self, g: GraphView, path: str):
        self.path.get().constrain_to_literal(g=g, value=path)

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    # TODO: get_path -> str | None


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

    @classmethod
    def __create_instance__(cls, tg: TypeGraph, g: GraphView, info: Info) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        field_ref_part = super().__create_instance__(tg=tg, g=g)
        field_ref_part.source.get().set_source_info(g=g, source_info=info.source_info)
        field_ref_part.name.get().constrain_to_literal(g=g, value=info.name)

        if info.key is not None:
            field_ref_part.key.get().constrain_to_literal(g=g, value=info.key)

        return field_ref_part


class FieldRef(Node):
    _part_idx = 0

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.pin = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        parts: Iterable[FieldRefPart.Info],
    ) -> Self:
        field_ref = super().__create_instance__(tg=tg, g=g)
        field_ref.set_source_info(g=g, source_info=source_info)

        for part_info in parts:
            part = FieldRefPart.__create_instance__(tg=tg, g=g, info=part_info)
            field_ref.add_part(g=g, part=part)

        return field_ref

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def add_part(self, g: GraphView, part: FieldRefPart):
        # TODO: store as Sequence
        self._part_idx += 1
        self.add_instance_child(part, name=f"part_{self._part_idx}")


class Number(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.value = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, value: int | float
    ) -> Self:
        number = super().__create_instance__(tg=tg, g=g)
        number.set_source_info(g=g, source_info=source_info)
        number.set_value(g=g, value=value)
        return number

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_value(self, g: GraphView, value: int | float):
        self.value.get().constrain_to_literal(g=g, value=value)


class Boolean(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.value = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, value: bool
    ) -> Self:
        boolean = super().__create_instance__(tg=tg, g=g)
        boolean.set_source_info(g=g, source_info=source_info)
        boolean.set_value(g=g, value=value)
        return boolean

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_value(self, g: GraphView, value: bool):
        self.value.get().constrain_to_literal(g=g, value=value)


class Unit(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.symbol = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, symbol: str
    ) -> Self:
        unit = super().__create_instance__(tg=tg, g=g)
        unit.set_source_info(g=g, source_info=source_info)
        unit.set_symbol(g=g, symbol=symbol)
        return unit

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_symbol(self, g: GraphView, symbol: str):
        self.symbol.get().constrain_to_literal(g=g, value=symbol)


class Quantity(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.number = t.Child(Number)
        cls.unit = t.Child(Unit)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        value: int | float,
        value_source_info: SourceInfo,
        unit: tuple[str, SourceInfo] | None = None,
    ) -> Self:
        quantity = super().__create_instance__(tg=tg, g=g)
        quantity.set_source_info(g=g, source_info=source_info)
        quantity.set_number(g=g, value=value, source_info=value_source_info)
        if unit is not None:
            symbol, unit_source = unit
            quantity.set_unit(g=g, symbol=symbol, source_info=unit_source)
        return quantity

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_number(self, g: GraphView, value: int | float, source_info: SourceInfo):
        number = self.number.get()
        number.set_value(g=g, value=value)
        number.set_source_info(g=g, source_info=source_info)

    def set_unit(self, g: GraphView, symbol: str, source_info: SourceInfo):
        unit = self.unit.get()
        unit.set_symbol(g=g, symbol=symbol)
        unit.set_source_info(g=g, source_info=source_info)


class BinaryExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.operator = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        operator: str,
        lhs: Node,
        rhs: Node,  # TODO: restrict types
    ) -> Self:
        binary = super().__create_instance__(tg=tg, g=g)
        binary.set_source_info(g=g, source_info=source_info)
        binary.operator.get().constrain_to_literal(g=g, value=operator)
        binary.add_instance_child(lhs, name="lhs")
        binary.add_instance_child(rhs, name="rhs")
        return binary

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)


# FIXME: do we need this?
class GroupExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        expression: Node,  # FIXME: typing
    ) -> Self:
        group = super().__create_instance__(tg=tg, g=g)
        group.set_source_info(g=g, source_info=source_info)
        group.add_instance_child(expression, name="expression")
        return group

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)


class ComparisonClause(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.operator = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        operator: str,
        right: Node,
    ) -> Self:
        clause = super().__create_instance__(tg=tg, g=g)
        clause.set_source_info(g=g, source_info=source_info)
        clause.set_operator(g=g, operator=operator)
        clause.set_right(g=g, node=right)
        return clause

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_operator(self, g: GraphView, operator: str):
        self.operator.get().constrain_to_literal(g=g, value=operator)

    def set_right(self, g: GraphView, node: Node):
        # FIXME
        self.add_instance_child(node, name="right")


class ComparisonExpression(Node):
    _clause_idx = 0

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        left: Node,
        clauses: Iterable[ComparisonClause],
    ) -> Self:
        comparison = super().__create_instance__(tg=tg, g=g)
        comparison.set_source_info(g=g, source_info=source_info)
        comparison.set_left(g=g, node=left)
        for clause in clauses:
            comparison.add_clause(g=g, clause=clause)
        return comparison

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_left(self, g: GraphView, node: Node):
        # FIXME: static?
        self.add_instance_child(node, name="left")

    def add_clause(self, g: GraphView, clause: ComparisonClause):
        ComparisonExpression._clause_idx += 1
        # FIXME
        self.add_instance_child(
            clause, name=f"clause_{ComparisonExpression._clause_idx}"
        )


class BilateralQuantity(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.quantity = t.Child(Quantity)
        cls.tolerance = t.Child(Quantity)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
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
        bilateral_quantity = super().__create_instance__(tg=tg, g=g)
        bilateral_quantity.source.get().set_source_info(g=g, source_info=source_info)
        quantity_node = bilateral_quantity.quantity.get()
        quantity_node.set_source_info(g=g, source_info=quantity_source_info)
        quantity_node.set_number(
            g=g, value=quantity_value, source_info=quantity_value_source_info
        )
        if quantity_unit is not None:
            quantity_node.set_unit(
                g=g, symbol=quantity_unit, source_info=quantity_unit_source_info
            )

        tolerance_node = bilateral_quantity.tolerance.get()
        tolerance_node.set_source_info(g=g, source_info=tolerance_source_info)
        tolerance_node.set_number(
            g=g, value=tolerance_value, source_info=tolerance_value_source_info
        )
        if tolerance_unit is not None:
            tolerance_node.set_unit(
                g=g, symbol=tolerance_unit, source_info=tolerance_unit_source_info
            )

        return bilateral_quantity


class BoundedQuantity(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.start = t.Child(Quantity)
        cls.end = t.Child(Quantity)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
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
        bounded = super().__create_instance__(tg=tg, g=g)
        bounded.source.get().set_source_info(g=g, source_info=source_info)

        start_quantity = bounded.start.get()
        start_quantity.set_source_info(g=g, source_info=start_source_info)
        start_quantity.set_number(
            g=g, value=start_value, source_info=start_value_source_info
        )
        if start_unit is not None:
            start_quantity.set_unit(
                g=g, symbol=start_unit, source_info=start_unit_source_info
            )

        end_quantity = bounded.end.get()
        end_quantity.set_source_info(g=g, source_info=end_source_info)
        end_quantity.set_number(g=g, value=end_value, source_info=end_value_source_info)
        if end_unit is not None:
            end_quantity.set_unit(
                g=g, symbol=end_unit, source_info=end_unit_source_info
            )

        return bounded


class Scope(Node):
    _stmt_idx: ClassVar[int] = 0

    # TODO: constrain stmt types
    def add_stmt(self, g: GraphView, stmt: Node):
        # TODO: capture order independent from child_id
        Scope._stmt_idx += 1
        self.add_instance_child(
            stmt,
            name=f"stmt_{Scope._stmt_idx}",  # TODO: anonymous children
        )

    # TODO: get_child_stmts -> Iterable[Assignment | ...]


class File(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.scope = t.Child(Scope)
        cls.path = t.Child(Parameter)

    # TODO: optional path
    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        path: str,
        child_stmts: Iterable[Node],
    ) -> Self:
        file = super().__create_instance__(tg=tg, g=g)
        file.source.get().set_source_info(g=g, source_info=source_info)
        file.set_path(g=g, path=path)

        for child_node in child_stmts:
            if child_node is not None:  # FIXME
                file.scope.get().add_stmt(g=g, stmt=child_node)

        return file

    def set_path(self, g: GraphView, path: str):
        self.path.get().constrain_to_literal(g=g, value=path)


class BlockDefinition(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.block_type = t.Child(Parameter)  # TODO: enum domain
        cls.type_ref = t.Child(TypeRef)
        cls.super_type_ref = t.Child(TypeRef)
        cls.scope = t.Child(Scope)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        block_type: str,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        super_type_ref_name: str | None,
        super_type_ref_source_info: SourceInfo | None,
        child_stmts: Iterable[Node],
    ) -> Self:
        block_definition = super().__create_instance__(tg=tg, g=g)
        block_definition.source.get().set_source_info(g=g, source_info=source_info)
        block_definition.block_type.get().constrain_to_literal(g=g, value=block_type)

        block_definition.type_ref.get().set_name(g=g, name=type_ref_name)
        block_definition.type_ref.get().set_source(
            g=g, source_info=type_ref_source_info
        )

        if super_type_ref_name is not None:
            block_definition.super_type_ref.get().set_name(
                g=g, name=super_type_ref_name
            )

        if super_type_ref_source_info is not None:
            block_definition.super_type_ref.get().set_source(
                g=g, source_info=super_type_ref_source_info
            )

        for child_node in child_stmts:
            if child_node is not None:  # FIXME
                block_definition.scope.get().add_stmt(g=g, stmt=child_node)

        return block_definition


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

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        start: tuple[int, SourceInfo] | None = None,
        stop: tuple[int, SourceInfo] | None = None,
        step: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        slice_node = super().__create_instance__(tg=tg, g=g)
        slice_node.source.get().set_source_info(g=g, source_info=source_info)

        if start is not None:
            slice_node.set_start(g=g, value=start[0], source_info=start[1])

        if stop is not None:
            slice_node.set_stop(g=g, value=stop[0], source_info=stop[1])

        if step is not None:
            slice_node.set_step(g=g, value=step[0], source_info=step[1])

        return slice_node

    def set_start(self, g: GraphView, value: int, source_info: SourceInfo):
        number = self.start.get()
        number.set_value(g=g, value=value)
        number.set_source_info(g=g, source_info=source_info)

    def set_stop(self, g: GraphView, value: int, source_info: SourceInfo):
        number = self.stop.get()
        number.set_value(g=g, value=value)
        number.set_source_info(g=g, source_info=source_info)

    def set_step(self, g: GraphView, value: int, source_info: SourceInfo):
        number = self.step.get()
        number.set_value(g=g, value=value)
        number.set_source_info(g=g, source_info=source_info)


class IterableFieldRef(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.field = t.Child(FieldRef)
        cls.slice = t.Child(Slice)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        field_parts: Iterable[FieldRefPart.Info],
        field_source_info: SourceInfo,
        slice_config: SliceConfig | None = None,
    ) -> Self:
        iterable = super().__create_instance__(tg=tg, g=g)
        iterable.source.get().set_source_info(g=g, source_info=source_info)

        field_node = iterable.field.get()
        field_node.set_source_info(g=g, source_info=field_source_info)
        for part in field_parts:
            field_part = FieldRefPart.__create_instance__(tg=tg, g=g, info=part)
            field_node.add_part(g=g, part=field_part)

        if slice_config is not None:
            slice_node = iterable.slice.get()
            slice_node.source.get().set_source_info(
                g=g, source_info=slice_config.source
            )
            if slice_config.start is not None:
                start_value, start_source_info = slice_config.start
                slice_node.set_start(
                    g=g, value=start_value, source_info=start_source_info
                )
            if slice_config.stop is not None:
                stop_value, stop_source_info = slice_config.stop
                slice_node.set_stop(g=g, value=stop_value, source_info=stop_source_info)
            if slice_config.step is not None:
                step_value, step_source_info = slice_config.step
                slice_node.set_step(g=g, value=step_value, source_info=step_source_info)
        return iterable


class FieldRefList(Node):
    _item_idx = 0

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        items: Iterable[FieldRef],
    ) -> Self:
        fr_list = super().__create_instance__(tg=tg, g=g)
        fr_list.source.get().set_source_info(g=g, source_info=source_info)
        for item in items:
            fr_list.add_item(g=g, item=item)
        return fr_list

    def add_item(self, g: GraphView, item: FieldRef):
        FieldRefList._item_idx += 1
        self.add_instance_child(item, name=f"item_{FieldRefList._item_idx}")


class ForStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.scope = t.Child(Scope)
        cls.target = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        target: str,
        iterable: Node,
        body_stmts: Iterable[Node],
    ) -> Self:
        for_stmt = super().__create_instance__(tg=tg, g=g)
        for_stmt.source.get().set_source_info(g=g, source_info=source_info)
        for_stmt.set_target(g=g, target=target)
        for_stmt.set_iterable(g=g, iterable=iterable)
        scope_node = for_stmt.scope.get()
        for stmt in body_stmts:
            scope_node.add_stmt(g=g, stmt=stmt)
        return for_stmt

    def set_target(self, g: GraphView, target: str):
        self.target.get().constrain_to_literal(g=g, value=target)

    def set_iterable(self, g: GraphView, iterable: Node):
        # TODO: should this be dynamic?
        self.add_instance_child(iterable, name="iterable")


class PragmaStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.pragma = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, pragma: str
    ) -> Self:
        pragma_stmt = super().__create_instance__(tg=tg, g=g)
        pragma_stmt.source.get().set_source_info(g=g, source_info=source_info)
        pragma_stmt.pragma.get().constrain_to_literal(g=g, value=pragma)

        return pragma_stmt


class ImportStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.path = t.Child(ImportPath)
        cls.type_ref = t.Child(TypeRef)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        path: str | None,
        path_source_info: SourceInfo | None,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
    ) -> Self:
        import_stmt = super().__create_instance__(tg=tg, g=g)
        import_stmt.source.get().set_source_info(g=g, source_info=source_info)

        if path is not None:
            import_stmt.path.get().set_path(g=g, path=path)

        if path_source_info is not None:
            import_stmt.path.get().set_source_info(g=g, source_info=path_source_info)

        import_stmt.type_ref.get().set_name(g=g, name=type_ref_name)
        import_stmt.type_ref.get().set_source(g=g, source_info=type_ref_source_info)

        return import_stmt


class TemplateArg(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.name = t.Child(Parameter)
        cls.value = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        name: str,
        value: LiteralT,
    ) -> Self:
        template_arg = super().__create_instance__(tg=tg, g=g)
        template_arg.source.get().set_source_info(g=g, source_info=source_info)
        template_arg.name.get().constrain_to_literal(g=g, value=name)
        template_arg.value.get().constrain_to_literal(g=g, value=value)
        return template_arg


class Template(Node):
    _arg_idx = 0

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        args: Iterable[TemplateArg],
    ) -> Self:
        template = super().__create_instance__(tg=tg, g=g)
        template.set_source_info(g=g, source_info=source_info)
        for arg in args:
            template.add_arg(g=g, arg=arg)
        return template

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def add_arg(self, g: GraphView, arg: TemplateArg):
        Template._arg_idx += 1
        # TODO: provide at construction?
        self.add_instance_child(arg, name=f"arg_{Template._arg_idx}")


class NewExpression(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.type_ref = t.Child(TypeRef)
        cls.template = t.Child(Template)
        cls.new_count = t.Child(Number)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        template: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        new_count: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        new_expression = super().__create_instance__(tg=tg, g=g)
        new_expression.source.get().set_source_info(g=g, source_info=source_info)
        new_expression.type_ref.get().set_name(g=g, name=type_ref_name)
        new_expression.type_ref.get().set_source(g=g, source_info=type_ref_source_info)

        if template is not None:
            template_source, template_args = template
            template_node = new_expression.template.get()
            template_node.set_source_info(g=g, source_info=template_source)
            for arg in template_args:
                template_node.add_arg(g=g, arg=arg)

        if new_count is not None:
            count, count_source_info = new_count
            new_expression.set_new_count(
                g=g, count=count, source_info=count_source_info
            )

        return new_expression

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_new_count(self, g: GraphView, count: int, source_info: SourceInfo):
        number = self.new_count.get()
        number.set_value(g=g, value=count)
        number.set_source_info(g=g, source_info=source_info)


class String(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.text = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, text: str
    ) -> Self:
        string = super().__create_instance__(tg=tg, g=g)
        string.set_source_info(g=g, source_info=source_info)
        string.set_text(g=g, text=text)
        return string

    def set_text(self, g: GraphView, text: str):
        self.text.get().constrain_to_literal(g=g, value=text)

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)


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


class Assignable(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        # cls.value = t.Child(NewExpression)  #  TODO: other options

    def set_source_info(self, g: GraphView, source_info: SourceInfo):
        self.source.get().set_source_info(g=g, source_info=source_info)

    def set_value(self, g: GraphView, value: AssignableT):
        # TODO: guard
        self.add_instance_child(value, name="value")

    # TODO: get_value -> AssignableT


class Assignment(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.target = t.Child(FieldRef)  # TODO: declarations?
        cls.assignable = t.Child(Assignable)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        target_field_ref_parts: list[FieldRefPart.Info],
        target_field_ref_source_info: SourceInfo,
        assignable_value: AssignableT,
        assignable_source_info: SourceInfo,
    ) -> Self:
        assignment = super().__create_instance__(tg=tg, g=g)
        assignment.source.get().set_source_info(g=g, source_info=source_info)

        for part_info in target_field_ref_parts:
            field_ref_part = FieldRefPart.__create_instance__(
                tg=tg, g=g, info=part_info
            )
            assignment.target.get().add_part(g=g, part=field_ref_part)

        assignment.target.get().set_source_info(
            g=g, source_info=target_field_ref_source_info
        )

        assignment.assignable.get().set_value(g=g, value=assignable_value)
        assignment.assignable.get().set_source_info(
            g=g, source_info=assignable_source_info
        )

        return assignment


class ConnectStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        left: Node,
        right: Node,
    ) -> Self:
        connect = super().__create_instance__(tg=tg, g=g)
        connect.source.get().set_source_info(g=g, source_info=source_info)

        for node, identifier in [(left, "left"), (right, "right")]:
            connect.add_instance_child(node, name=identifier)

        return connect


class DirectedConnectStmt(Node):
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.direction = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        direction: "DirectedConnectStmt.Direction",
        left: Node,
        right: Node,
    ) -> Self:
        directed = super().__create_instance__(tg=tg, g=g)
        directed.source.get().set_source_info(g=g, source_info=source_info)
        directed.set_direction(g=g, direction=direction)

        for node, identifier in [(left, "left"), (right, "right")]:
            directed.add_instance_child(node, name=identifier)

        return directed

    def set_direction(self, g: GraphView, direction: "DirectedConnectStmt.Direction"):
        self.direction.get().constrain_to_literal(g=g, value=direction.value)


class RetypeStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.field_ref = t.Child(FieldRef)
        cls.type_ref = t.Child(TypeRef)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        field_ref_parts: Iterable[FieldRefPart.Info],
        field_ref_source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
    ) -> Self:
        retype = super().__create_instance__(tg=tg, g=g)
        retype.source.get().set_source_info(g=g, source_info=source_info)

        field_node = retype.field_ref.get()
        field_node.set_source_info(g=g, source_info=field_ref_source_info)

        # FIXME
        for part in field_ref_parts:
            field_part = FieldRefPart.__create_instance__(tg=tg, g=g, info=part)
            field_node.add_part(g=g, part=field_part)

        type_node = retype.type_ref.get()
        type_node.set_name(g=g, name=type_ref_name)
        type_node.set_source(g=g, source_info=type_ref_source_info)

        return retype


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

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        kind: "PinDeclaration.Kind",
        label_value: LiteralT | None = None,
    ) -> Self:
        pin = super().__create_instance__(tg=tg, g=g)
        pin.source.get().set_source_info(g=g, source_info=source_info)
        pin.set_kind(g=g, kind=kind)
        if label_value is not None:
            pin.set_label(g=g, value=label_value)
        return pin

    def set_kind(self, g: GraphView, kind: "PinDeclaration.Kind"):
        self.kind.get().constrain_to_literal(g=g, value=kind.value)

    def set_label(self, g: GraphView, value: LiteralT):
        self.label.get().constrain_to_literal(g=g, value=value)


class SignaldefStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.name = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo, name: str
    ) -> Self:
        signal = super().__create_instance__(tg=tg, g=g)
        signal.source.get().set_source_info(g=g, source_info=source_info)
        signal.name.get().constrain_to_literal(g=g, value=name)
        return signal


class AssertStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        comparison: ComparisonExpression,
    ) -> Self:
        assert_stmt = super().__create_instance__(tg=tg, g=g)
        assert_stmt.source.get().set_source_info(g=g, source_info=source_info)
        assert_stmt.add_instance_child(comparison, name="comparison")

        return assert_stmt


class DeclarationStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.field_ref = t.Child(FieldRef)
        cls.unit = t.Child(Unit)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        field_ref_parts: Iterable[FieldRefPart.Info],
        field_ref_source_info: SourceInfo,
        unit_symbol: str,
        unit_source_info: SourceInfo,
    ) -> Self:
        declaration = super().__create_instance__(tg=tg, g=g)
        declaration.source.get().set_source_info(g=g, source_info=source_info)

        field_node = declaration.field_ref.get()
        field_node.set_source_info(g=g, source_info=field_ref_source_info)
        # FIXME
        for part in field_ref_parts:
            field_part = FieldRefPart.__create_instance__(tg=tg, g=g, info=part)
            field_node.add_part(g=g, part=field_part)

        unit_node = declaration.unit.get()
        unit_node.set_source_info(g=g, source_info=unit_source_info)
        unit_node.set_symbol(g=g, symbol=unit_symbol)

        return declaration


class StringStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.string = t.Child(String)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        string_value: str,
        string_source_info: SourceInfo,
    ) -> Self:
        string_stmt = super().__create_instance__(tg=tg, g=g)
        string_stmt.source.get().set_source_info(g=g, source_info=source_info)
        string_stmt.string.get().set_text(g=g, text=string_value)
        string_stmt.string.get().set_source_info(g=g, source_info=string_source_info)
        return string_stmt


class PassStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, tg: TypeGraph, g: GraphView, source_info: SourceInfo
    ) -> Self:
        stmt = super().__create_instance__(tg=tg, g=g)
        stmt.source.get().set_source_info(g=g, source_info=source_info)
        return stmt


class TraitStmt(Node):
    @classmethod
    def __create_type__(cls, t: BoundNodeType) -> None:
        cls.source = t.Child(SourceChunk)
        cls.type_ref = t.Child(TypeRef)
        cls.target = t.Child(FieldRef)
        cls.template = t.Child(Template)
        cls.constructor = t.Child(Parameter)

    @classmethod
    def __create_instance__(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        tg: TypeGraph,
        g: GraphView,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        target_parts: Iterable[FieldRefPart.Info] | None = None,
        target_source_info: SourceInfo | None = None,
        template_data: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        constructor: str | None = None,
    ) -> Self:
        trait = super().__create_instance__(tg=tg, g=g)
        trait.source.get().set_source_info(g=g, source_info=source_info)

        type_node = trait.type_ref.get()
        type_node.set_name(g=g, name=type_ref_name)
        type_node.set_source(g=g, source_info=type_ref_source_info)

        if target_parts is not None and target_source_info is not None:
            target_node = trait.target.get()
            target_node.set_source_info(g=g, source_info=target_source_info)
            for part in target_parts:
                target_node.add_part(
                    g=g, part=FieldRefPart.__create_instance__(tg=tg, g=g, info=part)
                )

        if template_data is not None:
            template_source, template_args = template_data
            template_node = trait.template.get()
            template_node.set_source_info(g=g, source_info=template_source)
            for arg in template_args:
                template_node.add_arg(g=g, arg=arg)

        if constructor is not None:
            trait.set_constructor(g=g, constructor=constructor)

        return trait

    def set_constructor(self, g: GraphView, constructor: str):
        self.constructor.get().constrain_to_literal(g=g, value=constructor)
