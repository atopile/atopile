"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless of
  syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Iterable, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library import Collections
from faebryk.libs.util import cast_assert


def _add_anon_child(node: fabll.NodeT, child: fabll.NodeT):
    fbrk.EdgeComposition.add_anon_child(
        bound_node=node.instance, child=child.instance.node()
    )


class is_assignable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_arithmetic(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_assignable = fabll.Traits.ImpliedTrait(is_assignable)


class is_arithmetic_atom(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_arithmetic = fabll.Traits.ImpliedTrait(is_arithmetic)


class is_connectable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_statement(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_path(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    path = F.Literals.Strings.MakeChild()

    def setup(self, path: str) -> Self:  # type: ignore[invalid-method-override]
        self.path.get().setup_from_values(path)
        return self

    def get_path(self) -> str:
        return self.path.get().get_single()


LiteralT = float | int | str | bool


@dataclass(frozen=True)
class SourceInfo:
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    text: str


class FileLocation(fabll.Node):
    start_line = F.Literals.Counts.MakeChild()
    start_col = F.Literals.Counts.MakeChild()
    end_line = F.Literals.Counts.MakeChild()
    end_col = F.Literals.Counts.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, start_line: int, start_col: int, end_line: int, end_col: int
    ) -> Self:
        self.start_line.get().setup_from_values(values=[start_line])
        self.start_col.get().setup_from_values(values=[start_col])
        self.end_line.get().setup_from_values(values=[end_line])
        self.end_col.get().setup_from_values(values=[end_col])
        return self

    def get_start_line(self) -> int:
        return self.start_line.get().get_single()

    def get_start_col(self) -> int:
        return self.start_col.get().get_single()

    def get_end_line(self) -> int:
        return self.end_line.get().get_single()

    def get_end_col(self) -> int:
        return self.end_col.get().get_single()


class SourceChunk(fabll.Node):
    text = F.Literals.Strings.MakeChild()
    loc = FileLocation.MakeChild()

    def setup(self, source_info: SourceInfo) -> Self:  # type: ignore[invalid-method-override]
        self.text.get().setup_from_values(source_info.text)
        self.loc.get().setup(
            start_line=source_info.start_line,
            start_col=source_info.start_col,
            end_line=source_info.end_line,
            end_col=source_info.end_col,
        )
        return self


class TypeRef(fabll.Node):
    name = F.Literals.Strings.MakeChild()
    source = SourceChunk.MakeChild()

    def setup(self, name: str, source_info: SourceInfo) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.name.get().setup_from_values(name)
        return self


class ImportPath(fabll.Node):
    source = SourceChunk.MakeChild()
    path = F.Literals.Strings.MakeChild()

    def setup(self, path: str, source_info: SourceInfo) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.path.get().setup_from_values(path)
        return self


class FieldRefPart(fabll.Node):
    @dataclass(frozen=True)
    class Info:
        name: str
        key: int | str | None
        source_info: SourceInfo

    source = SourceChunk.MakeChild()
    name = F.Literals.Strings.MakeChild()
    key = F.Literals.Strings.MakeChild()

    def setup(self, info: Info) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=info.source_info)
        self.name.get().setup_from_values(info.name)

        if info.key is not None:
            # TODO: split int and str cases?
            self.key.get().setup_from_values(str(info.key))

        return self

    def get_key(self) -> int | str | None:
        if len(key_values := self.key.get().get_values()) == 0:
            return None
        (key,) = key_values
        return key


class FieldRef(fabll.Node):
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())
    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())

    source = SourceChunk.MakeChild()
    pin = F.Literals.Strings.MakeChild()
    parts = Collections.PointerSequence.MakeChild()  # TODO: specify child type

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, parts: Iterable[FieldRefPart.Info]
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        for part_info in parts:
            part = FieldRefPart.bind_typegraph(self.tg).create_instance(g=self.g)
            part.setup(info=part_info)

            _add_anon_child(self, part)

            self.parts.get().append(part)

        return self

    def get_pin(self) -> str | None:
        if len(pin_values := self.pin.get().get_values()) == 0:
            return None
        (pin,) = pin_values
        return pin


class Decimal(fabll.Node):
    source = SourceChunk.MakeChild()
    value = F.Literals.NumericSet.MakeChild_Empty()

    def setup(self, source_info: SourceInfo, value: int | float) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.value.get().setup_from_singleton(float(value))
        return self


class Integer(fabll.Node):
    source = SourceChunk.MakeChild()
    value = F.Literals.Counts.MakeChild()

    def setup(self, source_info: SourceInfo, value: int) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.value.get().setup_from_values(values=[value])
        return self

    def get_value(self) -> int | None:
        values = self.value.get().get_values()
        if not values:
            return None
        (value,) = values
        return value


class Boolean(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())

    source = SourceChunk.MakeChild()
    value = F.Literals.Booleans.MakeChild()

    def setup(self, source_info: SourceInfo, value: bool) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.value.get().setup_from_values(value)
        return self


class Unit(fabll.Node):
    source = SourceChunk.MakeChild()
    symbol = F.Literals.Strings.MakeChild()

    def setup(self, source_info: SourceInfo, symbol: str) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.symbol.get().setup_from_values(symbol)
        return self


class Quantity(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())

    source = SourceChunk.MakeChild()
    number = Decimal.MakeChild()
    unit = Unit.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        value: int | float,
        value_source_info: SourceInfo,
        unit: tuple[str, SourceInfo] | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.number.get().setup(source_info=value_source_info, value=value)

        if unit is not None:
            symbol, unit_source = unit
            self.unit.get().setup(source_info=unit_source, symbol=symbol)

        return self


class BinaryExpression(fabll.Node):
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())

    source = SourceChunk.MakeChild()
    operator = F.Literals.Strings.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()  # TODO: required but deferred
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        operator: str,
        lhs: is_arithmetic,
        rhs: is_arithmetic,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.operator.get().setup_from_values(operator)

        lhs_node = fabll.Traits(lhs).get_obj_raw()
        self.lhs.get().point(lhs_node)
        _add_anon_child(self, lhs_node)

        rhs_node = fabll.Traits(rhs).get_obj_raw()
        self.rhs.get().point(rhs_node)
        _add_anon_child(self, rhs_node)

        return self

    def get_lhs(self) -> is_arithmetic:
        return self.lhs.get().deref().get_trait(is_arithmetic)

    def get_rhs(self) -> is_arithmetic:
        return self.rhs.get().deref().get_trait(is_arithmetic)


class GroupExpression(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())

    source = SourceChunk.MakeChild()
    expression = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, expression: is_arithmetic
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        expression_node = fabll.Traits(expression).get_obj_raw()
        self.expression.get().point(expression_node)
        _add_anon_child(self, expression_node)
        return self

    def get_expression(self) -> is_arithmetic:
        return self.expression.get().deref().get_trait(is_arithmetic)


class ComparisonClause(fabll.Node):
    class ComparisonOperator(StrEnum):
        LESS_THAN = "<"
        GREATER_THAN = ">"
        LT_EQ = "<="
        GT_EQ = ">="
        WITHIN = "within"
        IS = "is"

    source = SourceChunk.MakeChild()
    operator = F.Literals.EnumsFactory(ComparisonOperator).MakeChild(
        *ComparisonOperator.__members__.values()
    )
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, operator: str, rhs: is_arithmetic
    ) -> Self:
        operator_ = self.ComparisonOperator(operator)
        self.source.get().setup(source_info=source_info)
        self.operator.get().setup(operator_)
        rhs_node = fabll.Traits(rhs).get_obj_raw()
        self.rhs.get().point(rhs_node)
        _add_anon_child(self, rhs_node)
        return self

    def get_rhs(self) -> is_arithmetic:
        return self.rhs.get().deref().get_trait(is_arithmetic)


class ComparisonExpression(fabll.Node):
    source = SourceChunk.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()
    rhs_clauses = Collections.PointerSequence.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        lhs: is_arithmetic,
        rhs_clauses: Iterable[ComparisonClause],
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        lhs_node = fabll.Traits(lhs).get_obj_raw()
        self.lhs.get().point(lhs_node)
        _add_anon_child(self, lhs_node)
        for clause in rhs_clauses:
            _add_anon_child(self, clause)
            self.rhs_clauses.get().append(clause)

        return self

    def get_lhs(self) -> is_arithmetic:
        return self.lhs.get().deref().get_trait(is_arithmetic)


class BilateralQuantity(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())

    source = SourceChunk.MakeChild()
    quantity = Quantity.MakeChild()
    tolerance = Quantity.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
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
        self.source.get().setup(source_info=source_info)

        self.quantity.get().setup(
            source_info=quantity_source_info,
            value=quantity_value,
            value_source_info=quantity_value_source_info,
            unit=quantity_unit,
        )

        self.tolerance.get().setup(
            source_info=tolerance_source_info,
            value=tolerance_value,
            value_source_info=tolerance_value_source_info,
            unit=tolerance_unit,
        )

        return self


class BoundedQuantity(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())

    source = SourceChunk.MakeChild()
    start = Quantity.MakeChild()
    end = Quantity.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
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
        self.source.get().setup(source_info=source_info)

        self.start.get().setup(
            source_info=start_source_info,
            value=start_value,
            value_source_info=start_value_source_info,
            unit=start_unit,
        )

        self.end.get().setup(
            source_info=end_source_info,
            value=end_value,
            value_source_info=end_value_source_info,
            unit=end_unit,
        )

        return self


class Scope(fabll.Node):
    stmts = Collections.PointerSet.MakeChild()

    def setup(self, stmts: Iterable[is_statement]) -> Self:  # type: ignore[invalid-method-override]
        for stmt in stmts:
            stmt_node = fabll.Traits(stmt).get_obj_raw()
            self.stmts.get().append(stmt_node)

            _add_anon_child(self, stmt_node)

        return self

    def get_child_stmts(self) -> Iterable[is_statement]:
        return (stmt.get_trait(is_statement) for stmt in self.stmts.get().as_list())


class File(fabll.Node):
    source = SourceChunk.MakeChild()
    scope = Scope.MakeChild()
    _has_path = fabll.Traits.MakeEdge(has_path.MakeChild())

    # TODO: optional path
    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        path: str,
        stmts: Iterable[is_statement],
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self._has_path.get().setup(path=path)
        self.scope.get().setup(stmts=stmts)

        return self


class BlockDefinition(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    class BlockType(StrEnum):
        MODULE = "module"
        COMPONENT = "component"
        INTERFACE = "interface"

    source = SourceChunk.MakeChild()
    block_type = F.Literals.EnumsFactory(BlockType).MakeChild(
        *BlockType.__members__.values()
    )
    type_ref = TypeRef.MakeChild()
    super_type_ref = TypeRef.MakeChild()
    scope = Scope.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        block_type: str,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        super_type_ref_info: tuple[str, SourceInfo] | None,
        stmts: Iterable[is_statement],
    ) -> Self:
        block_type_ = self.BlockType(block_type)
        self.source.get().setup(source_info=source_info)
        self.block_type.get().setup(block_type_)

        self.type_ref.get().setup(name=type_ref_name, source_info=type_ref_source_info)

        if super_type_ref_info is not None:
            self.super_type_ref.get().setup(
                name=super_type_ref_info[0], source_info=super_type_ref_info[1]
            )

        self.scope.get().setup(stmts=stmts)

        return self

    def get_block_type(self) -> BlockType:
        block_type = self.block_type.get().get_single_value()
        return self.BlockType(block_type)

    def get_type_ref_name(self) -> str:
        (type_ref_name,) = self.type_ref.get().name.get().get_values()
        return type_ref_name

    def get_super_type_ref_name(self) -> str | None:
        if len(values := self.super_type_ref.get().name.get().get_values()) == 0:
            return None
        (name,) = values
        return name


@dataclass(frozen=True)
class SliceConfig:
    source: SourceInfo
    start: tuple[int, SourceInfo] | None = None
    stop: tuple[int, SourceInfo] | None = None
    step: tuple[int, SourceInfo] | None = None


class Slice(fabll.Node):
    source = SourceChunk.MakeChild()
    start = Integer.MakeChild()
    stop = Integer.MakeChild()
    step = Integer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        start: tuple[int, SourceInfo] | None = None,
        stop: tuple[int, SourceInfo] | None = None,
        step: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        if start is not None:
            start_value, start_source_info = start
            self.start.get().setup(source_info=start_source_info, value=start_value)

        if stop is not None:
            stop_value, stop_source_info = stop
            self.stop.get().setup(source_info=stop_source_info, value=stop_value)

        if step is not None:
            step_value, step_source_info = step
            self.step.get().setup(source_info=step_source_info, value=step_value)

        return self

    def get_values(self) -> tuple[int | None, int | None, int | None]:
        return (
            self.start.get().get_value(),
            self.stop.get().get_value(),
            self.step.get().get_value(),
        )


class IterableFieldRef(fabll.Node):
    source = SourceChunk.MakeChild()
    field = F.Collections.Pointer.MakeChild()
    slice = Slice.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        field_ref: FieldRef,
        slice_config: SliceConfig | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.field.get().point(field_ref)
        _add_anon_child(self, field_ref)

        if slice_config is not None:
            self.slice.get().source.get().setup(source_info=slice_config.source)

            if slice_config.start is not None:
                start_value, start_source_info = slice_config.start
                self.slice.get().start.get().setup(
                    source_info=start_source_info, value=start_value
                )

            if slice_config.stop is not None:
                stop_value, stop_source_info = slice_config.stop
                self.slice.get().stop.get().setup(
                    source_info=stop_source_info, value=stop_value
                )

            if slice_config.step is not None:
                step_value, step_source_info = slice_config.step
                self.slice.get().step.get().setup(
                    source_info=step_source_info, value=step_value
                )

        return self

    def get_field(self) -> FieldRef:
        return self.field.get().deref().cast(t=FieldRef)


class FieldRefList(fabll.Node):
    source = SourceChunk.MakeChild()
    items = Collections.PointerSequence.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, items: Iterable[FieldRef]
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        for item in items:
            self.items.get().append(item)
            _add_anon_child(self, item)

        return self


class ForStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    scope = Scope.MakeChild()
    target = F.Literals.Strings.MakeChild()
    iterable = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        target: str,
        iterable: "IterableFieldRef | FieldRefList",
        stmts: Iterable[is_statement],
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.target.get().setup_from_values(target)
        self.iterable.get().point(iterable)
        _add_anon_child(self, iterable)
        self.scope.get().setup(stmts=stmts)
        return self

    def get_iterable(self) -> IterableFieldRef | FieldRefList:
        return cast_assert(
            (IterableFieldRef, FieldRefList), self.iterable.get().deref()
        )


class PragmaStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    pragma = F.Literals.Strings.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, pragma: str
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.pragma.get().setup_from_values(pragma)
        return self

    def get_pragma(self) -> str | None:
        if len(pragma_values := self.pragma.get().get_values()) == 0:
            return None
        (pragma,) = pragma_values
        return pragma


class ImportStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    path = ImportPath.MakeChild()
    type_ref = TypeRef.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        path_info: tuple[str, SourceInfo] | None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.type_ref.get().setup(name=type_ref_name, source_info=type_ref_source_info)

        if path_info is not None:
            path, path_source_info = path_info
            self.path.get().setup(path=path, source_info=path_source_info)

        return self

    def get_type_ref_name(self) -> str:
        (type_ref_name,) = self.type_ref.get().name.get().get_values()
        return type_ref_name

    def get_path(self) -> str | None:
        if len(path_values := self.path.get().path.get().get_values()) == 0:
            return None
        (path,) = path_values
        return path


class TemplateArg(fabll.Node):
    source = SourceChunk.MakeChild()
    name = F.Literals.Strings.MakeChild()
    value = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, name: str, value: "LiteralT"
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.name.get().setup_from_values(name)
        lit = F.Literals.make_simple_lit_singleton(g=self.g, tg=self.tg, value=value)
        self.value.get().point(lit)
        _add_anon_child(self, lit)
        return self

    def get_value(self) -> str | bool | float | None:
        return (
            self.value.get()
            .deref()
            .get_trait(F.Literals.is_literal)
            .switch_cast()
            .get_single()
        )


class Template(fabll.Node):
    source = SourceChunk.MakeChild()
    args = Collections.PointerSequence.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, args: Iterable[TemplateArg]
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        for arg in args:
            self.args.get().append(arg)
            _add_anon_child(self, arg)

        return self


class NewExpression(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())

    source = SourceChunk.MakeChild()
    type_ref = TypeRef.MakeChild()
    template = Template.MakeChild()
    new_count = Integer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        template: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        new_count_info: tuple[int, SourceInfo] | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.type_ref.get().setup(name=type_ref_name, source_info=type_ref_source_info)

        if template is not None:
            template_source, template_args = template
            self.template.get().setup(source_info=template_source, args=template_args)

        if new_count_info is not None:
            count, count_source_info = new_count_info
            self.new_count.get().setup(source_info=count_source_info, value=count)

        return self

    def get_type_ref_name(self) -> str:
        (type_ref_name,) = self.type_ref.get().name.get().get_values()
        return type_ref_name

    def get_new_count(self) -> int | None:
        if len(count_values := self.new_count.get().value.get().get_values()) == 0:
            return None
        (count,) = count_values
        return count


class String(fabll.Node):
    @classmethod
    def _type_identifier(cls) -> str:
        # disambiguate from F.Literals.String
        return "AstString"

    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())

    source = SourceChunk.MakeChild()
    text = F.Literals.Strings.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, text: str
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.text.get().setup_from_values(text)
        return self


class Assignable(fabll.Node):
    source = SourceChunk.MakeChild()
    value = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, value: is_assignable
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        value_node = fabll.Traits(value).get_obj_raw()
        self.value.get().point(value_node)
        _add_anon_child(self, value_node)
        return self

    def get_value(self) -> is_assignable:
        return self.value.get().deref().get_trait(is_assignable)


class Assignment(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    target = F.Collections.Pointer.MakeChild()
    assignable = Assignable.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        target_field_ref: FieldRef,
        assignable_value: is_assignable,
        assignable_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.target.get().point(target_field_ref)
        _add_anon_child(self, target_field_ref)
        self.assignable.get().setup(
            source_info=assignable_source_info, value=assignable_value
        )
        return self

    def get_target(self) -> FieldRef:
        return self.target.get().deref().cast(t=FieldRef)


class ConnectStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, lhs: is_connectable, rhs: is_connectable
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        # Store the is_connectable trait directly (not the raw host object)
        self.lhs.get().point(lhs)
        _add_anon_child(self, lhs)
        self.rhs.get().point(rhs)
        _add_anon_child(self, rhs)
        return self

    def get_lhs(self) -> is_connectable:
        return self.lhs.get().deref().cast(is_connectable)

    def get_rhs(self) -> is_connectable:
        return self.rhs.get().deref().cast(is_connectable)


class DirectedConnectStmt(fabll.Node):
    class Direction(StrEnum):
        RIGHT = "RIGHT"  # ~> arrow points right
        LEFT = "LEFT"  # <~ arrow points left

    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())
    _direction_identifier: ClassVar[str] = "direction"

    source = SourceChunk.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        direction: "DirectedConnectStmt.Direction",
        lhs: is_connectable,
        rhs: "is_connectable | DirectedConnectStmt",
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        # Create direction literal dynamically and add as named child
        direction_literal = (
            F.Literals.Strings.bind_typegraph(tg=self.tg)
            .create_instance(g=self.instance.g())
            .setup_from_values(direction.value)
        )
        fbrk.EdgeComposition.add_child(
            bound_node=self.instance,
            child=direction_literal.instance.node(),
            child_identifier=self._direction_identifier,
        )

        # Store the is_connectable trait directly (not the raw host object)
        self.lhs.get().point(lhs)
        _add_anon_child(self, lhs)
        # rhs can be either is_connectable trait or DirectedConnectStmt
        self.rhs.get().point(rhs)
        _add_anon_child(self, rhs)
        return self

    def get_lhs(self) -> is_connectable:
        return self.lhs.get().deref().cast(t=is_connectable)

    def get_rhs(self) -> "is_connectable | DirectedConnectStmt":
        node = self.rhs.get().deref()
        if node.isinstance(DirectedConnectStmt):
            return node.cast(t=DirectedConnectStmt)
        return node.cast(t=is_connectable)

    def get_direction(self) -> "Direction":
        """Get the direction enum value from the dynamically created literal."""
        direction_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance,
            child_identifier=self._direction_identifier,
        )
        if direction_node is None:
            raise ValueError("Direction not set")
        direction_literal = fabll.Node(instance=direction_node).cast(F.Literals.Strings)
        return DirectedConnectStmt.Direction(direction_literal.get_single())


class RetypeStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    target = F.Collections.Pointer.MakeChild()
    new_type_ref = TypeRef.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        target_field_ref: FieldRef,
        new_type_name: str,
        new_type_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.target.get().point(target_field_ref)
        _add_anon_child(self, target_field_ref)
        self.new_type_ref.get().setup(
            name=new_type_name, source_info=new_type_source_info
        )
        return self

    def get_target(self) -> FieldRef:
        return self.target.get().deref().cast(t=FieldRef)


class PinDeclaration(fabll.Node):
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())

    source = SourceChunk.MakeChild()
    kind = F.Literals.EnumsFactory(Kind).MakeChild(*Kind.__members__.values())
    label = F.Collections.Pointer.MakeChild()

    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        kind: "PinDeclaration.Kind",
        label_value: "LiteralT | None" = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.kind.get().setup(kind)

        if label_value is not None:
            lit = F.Literals.make_simple_lit_singleton(
                g=self.g, tg=self.tg, value=label_value
            )
            self.label.get().point(lit)
            _add_anon_child(self, lit)

        return self

    def get_label(self) -> str | bool | float | None:
        return (
            self.label.get()
            .deref()
            .get_trait(F.Literals.is_literal)
            .switch_cast()
            .get_single()
        )


class SignaldefStmt(fabll.Node):
    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    name = F.Literals.Strings.MakeChild()

    def setup(self, source_info: SourceInfo, name: str) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        self.name.get().setup_from_values(name)
        return self


class AssertStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    comparison = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self, source_info: SourceInfo, comparison: ComparisonExpression
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.comparison.get().point(comparison)
        _add_anon_child(self, comparison)
        return self

    def get_comparison(self) -> "ComparisonExpression":
        return cast_assert(ComparisonExpression, self.comparison.get().deref())


class DeclarationStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    field_ref = F.Collections.Pointer.MakeChild()
    unit = Unit.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        field_ref: FieldRef,
        unit_symbol: str,
        unit_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.field_ref.get().point(field_ref)
        _add_anon_child(self, field_ref)
        self.unit.get().setup(source_info=unit_source_info, symbol=unit_symbol)
        return self

    def get_field_ref(self) -> FieldRef:
        return self.field_ref.get().deref().cast(t=FieldRef)


class StringStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    string = String.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        string_value: str,
        string_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.string.get().setup(source_info=string_source_info, text=string_value)
        return self


class PassStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()

    def setup(self, source_info: SourceInfo) -> Self:  # type: ignore[invalid-method-override]
        self.source.get().setup(source_info=source_info)
        return self


class TraitStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    type_ref = TypeRef.MakeChild()
    target = F.Collections.Pointer.MakeChild()
    template = Template.MakeChild()
    constructor = F.Literals.Strings.MakeChild()

    def setup(  # type: ignore[invalid-method-override]
        self,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        target_field_ref: FieldRef | None = None,
        template_info: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        constructor: str | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        self.type_ref.get().setup(name=type_ref_name, source_info=type_ref_source_info)

        if target_field_ref is not None:
            self.target.get().point(target_field_ref)
            _add_anon_child(self, target_field_ref)

        if template_info is not None:
            template_source, template_args = template_info
            self.template.get().setup(source_info=template_source, args=template_args)

        if constructor is not None:
            self.constructor.get().setup_from_values(constructor)

        return self

    def get_target(self) -> FieldRef | None:
        return self.target.get().deref().cast(t=FieldRef)
