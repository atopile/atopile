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

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.library import Collections
from faebryk.libs.util import cast_assert, not_none


def _add_anon_child(node: fabll.NodeT, child: fabll.NodeT):
    EdgeComposition.add_child(
        bound_node=node.instance,
        child=child.instance.node(),
        child_identifier=str(id(child)),
    )


class is_assignable(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_arithmetic(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_assignable = fabll.Traits.ImpliedTrait(is_assignable)


class is_arithmetic_atom(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_arithmetic = fabll.Traits.ImpliedTrait(is_arithmetic)


class is_connectable(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_statement(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


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

    def setup(  # type: ignore
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
    text = F.Parameters.StringParameter.MakeChild()
    loc = FileLocation.MakeChild()

    def setup(self, source_info: SourceInfo) -> Self:  # type: ignore
        self.text.get().alias_to_literal(source_info.text, g=self.g)
        self.loc.get().setup(
            start_line=source_info.start_line,
            start_col=source_info.start_col,
            end_line=source_info.end_line,
            end_col=source_info.end_col,
        )
        return self


class TypeRef(fabll.Node):
    name = F.Parameters.StringParameter.MakeChild()
    source = SourceChunk.MakeChild()

    def setup(self, name: str, source_info: SourceInfo) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.name.get().alias_to_literal(name, g=self.g)
        return self


class ImportPath(fabll.Node):
    source = SourceChunk.MakeChild()
    path = F.Parameters.StringParameter.MakeChild()

    def setup(self, path: str, source_info: SourceInfo) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.path.get().alias_to_literal(path, g=self.g)
        return self


class FieldRefPart(fabll.Node):
    @dataclass(frozen=True)
    class Info:
        name: str
        key: int | str | None
        source_info: SourceInfo

    source = SourceChunk.MakeChild()
    name = F.Parameters.StringParameter.MakeChild()
    key = F.Parameters.StringParameter.MakeChild()

    def setup(self, info: Info) -> Self:  # type: ignore
        self.source.get().setup(source_info=info.source_info)
        self.name.get().alias_to_literal(info.name, g=self.g)

        if info.key is not None:
            # TODO: split int and str cases?
            self.key.get().alias_to_literal(str(info.key), g=self.g)

        return self


class FieldRef(fabll.Node):
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())
    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())

    source = SourceChunk.MakeChild()
    pin = F.Parameters.StringParameter.MakeChild()
    parts = Collections.PointerSequence.MakeChild()  # TODO: specify child type

    def setup(  # type: ignore
        self, source_info: SourceInfo, parts: Iterable[FieldRefPart.Info]
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        for part_info in parts:
            part = FieldRefPart.bind_typegraph(self.tg).create_instance(g=self.g)
            part.setup(info=part_info)

            _add_anon_child(self, part)

            self.parts.get().append(part)

        return self


class Decimal(fabll.Node):
    source = SourceChunk.MakeChild()
    # TODO: should this be a Numbers literal?
    value = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless, integer=False, negative=True, zero_allowed=True
    )

    def setup(self, source_info: SourceInfo, value: int | float) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.value.get().alias_to_literal(g=self.g, value=float(value))
        return self


class Integer(fabll.Node):
    source = SourceChunk.MakeChild()
    value = F.Literals.Counts.MakeChild()

    def setup(self, source_info: SourceInfo, value: int) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.value.get().setup_from_values(values=[value])
        return self

    def get_value(self) -> int:
        return self.value.get().get_single()


class Boolean(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())

    source = SourceChunk.MakeChild()
    value = F.Parameters.BooleanParameter.MakeChild()

    def setup(self, source_info: SourceInfo, value: bool) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.value.get().alias_to_single(value=value, g=self.g)
        return self


class Unit(fabll.Node):
    source = SourceChunk.MakeChild()
    symbol = F.Parameters.StringParameter.MakeChild()

    def setup(self, source_info: SourceInfo, symbol: str) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.symbol.get().alias_to_literal(symbol, g=self.g)
        return self


class Quantity(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())
    _is_arithmetic = fabll.Traits.MakeEdge(is_arithmetic.MakeChild())
    _is_arithmetic_atom = fabll.Traits.MakeEdge(is_arithmetic_atom.MakeChild())

    source = SourceChunk.MakeChild()
    number = Decimal.MakeChild()
    unit = Unit.MakeChild()

    def setup(  # type: ignore
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
    operator = F.Parameters.StringParameter.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()  # TODO: reqyired but deferred
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        operator: str,
        lhs: is_arithmetic,
        rhs: is_arithmetic,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.operator.get().alias_to_literal(operator, g=self.g)

        self.lhs.get().point(lhs)
        _add_anon_child(self, lhs)

        self.rhs.get().point(rhs)
        _add_anon_child(self, rhs)

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

    def setup(  # type: ignore
        self, source_info: SourceInfo, expression: is_arithmetic
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.expression.get().point(expression)
        _add_anon_child(self, expression)
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
    operator = F.Parameters.EnumParameter.MakeChild(enum_t=ComparisonOperator)
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
        self, source_info: SourceInfo, operator: str, rhs: is_arithmetic
    ) -> Self:
        operator_ = self.ComparisonOperator(operator)
        self.source.get().setup(source_info=source_info)
        self.operator.get().alias_to_literal(operator_, g=self.g)
        self.rhs.get().point(rhs)
        _add_anon_child(self, rhs)
        return self

    def get_rhs(self) -> is_arithmetic:
        return self.rhs.get().deref().get_trait(is_arithmetic)


class ComparisonExpression(fabll.Node):
    source = SourceChunk.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()
    rhs_clauses = Collections.PointerSequence.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        lhs: is_arithmetic,
        rhs_clauses: Iterable[ComparisonClause],
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.lhs.get().point(lhs)
        _add_anon_child(self, lhs)
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

    def setup(  # type: ignore
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

    def setup(  # type: ignore
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

    def setup(self, stmts: Iterable[is_statement]) -> Self:  # type: ignore
        for stmt in stmts:
            stmt_node = fabll.Traits(stmt).get_obj_raw()
            self.stmts.get().append(stmt_node)

            _add_anon_child(self, stmt)

        return self

    # TODO: get_child_stmts -> Iterable[Assignment | ...]


class File(fabll.Node):
    source = SourceChunk.MakeChild()
    scope = Scope.MakeChild()
    path = F.Parameters.StringParameter.MakeChild()

    # TODO: optional path
    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        path: str,
        stmts: Iterable[is_statement],
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.path.get().alias_to_literal(*path)
        self.scope.get().setup(stmts=stmts)

        return self


class BlockDefinition(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    class BlockType(StrEnum):
        MODULE = "module"
        COMPONENT = "component"
        INTERFACE = "interface"

    source = SourceChunk.MakeChild()
    block_type = F.Parameters.EnumParameter.MakeChild(enum_t=BlockType)
    type_ref = TypeRef.MakeChild()
    super_type_ref = TypeRef.MakeChild()
    scope = Scope.MakeChild()

    def setup(  # type: ignore
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
        self.block_type.get().alias_to_literal(block_type_)

        self.type_ref.get().setup(name=type_ref_name, source_info=type_ref_source_info)

        if super_type_ref_info is not None:
            self.super_type_ref.get().setup(
                name=super_type_ref_info[0], source_info=super_type_ref_info[1]
            )

        self.scope.get().setup(stmts=stmts)

        return self

    def get_block_type(self) -> BlockType:
        block_type_lit = not_none(
            self.block_type.get().try_extract_constrained_literal()
        )
        (block_type,) = block_type_lit.get_values()
        return self.BlockType(block_type)


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

    def setup(  # type: ignore
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

    def get_start(self) -> int:
        return self.start.get().get_value()

    def get_stop(self) -> int:
        return self.stop.get().get_value()

    def get_step(self) -> int:
        return self.step.get().get_value()


class IterableFieldRef(fabll.Node):
    source = SourceChunk.MakeChild()
    field = FieldRef.MakeChild()
    slice = Slice.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        field_parts: Iterable[FieldRefPart.Info],
        field_source_info: SourceInfo,
        slice_config: SliceConfig | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.field.get().setup(source_info=field_source_info, parts=field_parts)

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


class FieldRefList(fabll.Node):
    source = SourceChunk.MakeChild()
    items = Collections.PointerSequence.MakeChild()

    def setup(  # type: ignore
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
    target = F.Parameters.StringParameter.MakeChild()
    iterable = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        target: str,
        iterable: "IterableFieldRef | FieldRefList",
        stmts: Iterable[is_statement],
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.target.get().alias_to_literal(*target)
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
    pragma = F.Parameters.StringParameter.MakeChild()

    def setup(  # type: ignore
        self, source_info: SourceInfo, pragma: str
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.pragma.get().alias_to_literal(pragma)
        return self


class ImportStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    path = ImportPath.MakeChild()
    type_ref = TypeRef.MakeChild()

    def setup(  # type: ignore
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


class TemplateArg(fabll.Node):
    source = SourceChunk.MakeChild()
    name = F.Parameters.StringParameter.MakeChild()
    value = F.Parameters.AnyParameter.MakeChild()

    def setup(  # type: ignore
        self, source_info: SourceInfo, name: str, value: "LiteralT"
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.name.get().alias_to_literal(name)
        self.value.get().setup(value=value)
        return self

    def get_value(self) -> "LiteralT":
        return self.value.get().get_value()


class Template(fabll.Node):
    source = SourceChunk.MakeChild()
    args = Collections.PointerSequence.MakeChild()

    def setup(  # type: ignore
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

    def setup(  # type: ignore
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


class String(fabll.Node):
    _is_assignable = fabll.Traits.MakeEdge(is_assignable.MakeChild())

    source = SourceChunk.MakeChild()
    text = F.Parameters.StringParameter.MakeChild()

    def setup(  # type: ignore
        self, source_info: SourceInfo, text: str
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.text.get().alias_to_literal(text)
        return self


class Assignable(fabll.Node):
    source = SourceChunk.MakeChild()
    value = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
        self, source_info: SourceInfo, value: is_assignable
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.value.get().point(fabll.Traits(value).get_obj_raw())
        _add_anon_child(self, value)
        return self

    def get_value(self) -> is_assignable:
        return self.value.get().deref().get_trait(is_assignable)


class Assignment(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    target = FieldRef.MakeChild()  # TODO: declarations?
    assignable = Assignable.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        target_field_ref_parts: list[FieldRefPart.Info],
        target_field_ref_source_info: SourceInfo,
        assignable_value: is_assignable,
        assignable_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.target.get().setup(
            source_info=target_field_ref_source_info, parts=target_field_ref_parts
        )
        self.assignable.get().setup(
            source_info=assignable_source_info, value=assignable_value
        )
        return self


class ConnectStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    lhs = F.Collections.Pointer.MakeChild()
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        lhs: is_connectable,
        rhs: is_connectable,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.lhs.get().point(lhs)
        _add_anon_child(self, lhs)
        self.rhs.get().point(rhs)
        _add_anon_child(self, rhs)
        return self

    def get_lhs(self) -> is_connectable:
        return self.lhs.get().deref().get_trait(is_connectable)

    def get_rhs(self) -> is_connectable:
        return self.rhs.get().deref().get_trait(is_connectable)


class DirectedConnectStmt(fabll.Node):
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    direction = F.Parameters.EnumParameter.MakeChild(enum_t=Direction)
    lhs = F.Collections.Pointer.MakeChild()
    rhs = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        direction: "DirectedConnectStmt.Direction",
        lhs: is_connectable,
        rhs: "is_connectable | DirectedConnectStmt",
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.direction.get().alias_to_literal(direction)
        self.lhs.get().point(lhs)
        _add_anon_child(self, lhs)
        self.rhs.get().point(rhs)
        _add_anon_child(self, rhs)
        return self

    def get_lhs(self) -> is_connectable:
        return self.lhs.get().deref().get_trait(is_connectable)

    def get_rhs(self) -> "is_connectable | DirectedConnectStmt":
        return self.rhs.get().deref().get_trait(is_connectable)


class RetypeStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    target = FieldRef.MakeChild()
    new_type_ref = TypeRef.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        target_parts: Iterable[FieldRefPart.Info],
        target_source_info: SourceInfo,
        new_type_name: str,
        new_type_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.target.get().setup(source_info=target_source_info, parts=target_parts)
        self.new_type_ref.get().setup(
            name=new_type_name, source_info=new_type_source_info
        )
        return self


class PinDeclaration(fabll.Node):
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())

    source = SourceChunk.MakeChild()
    kind = F.Parameters.EnumParameter.MakeChild(enum_t=Kind)
    label = F.Parameters.AnyParameter.MakeChild()

    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        kind: "PinDeclaration.Kind",
        label_value: "LiteralT | None" = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.kind.get().alias_to_literal(kind)

        if label_value is not None:
            self.label.get().setup(value=label_value)

        return self


class SignaldefStmt(fabll.Node):
    _is_connectable = fabll.Traits.MakeEdge(is_connectable.MakeChild())
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    name = F.Parameters.StringParameter.MakeChild()

    def setup(self, source_info: SourceInfo, name: str) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        self.name.get().alias_to_literal(name)
        return self


class AssertStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    comparison = F.Collections.Pointer.MakeChild()

    def setup(  # type: ignore
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
    field_ref = FieldRef.MakeChild()
    unit = Unit.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        field_ref_parts: Iterable[FieldRefPart.Info],
        field_ref_source_info: SourceInfo,
        unit_symbol: str,
        unit_source_info: SourceInfo,
    ) -> Self:
        self.source.get().setup(source_info=source_info)
        self.field_ref.get().setup(
            source_info=field_ref_source_info, parts=field_ref_parts
        )
        self.unit.get().setup(source_info=unit_source_info, symbol=unit_symbol)
        return self


class StringStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    string = String.MakeChild()

    def setup(  # type: ignore
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

    def setup(self, source_info: SourceInfo) -> Self:  # type: ignore
        self.source.get().setup(source_info=source_info)
        return self


class TraitStmt(fabll.Node):
    _is_statement = fabll.Traits.MakeEdge(is_statement.MakeChild())

    source = SourceChunk.MakeChild()
    type_ref = TypeRef.MakeChild()
    target = FieldRef.MakeChild()
    template = Template.MakeChild()
    constructor = F.Parameters.StringParameter.MakeChild()

    def setup(  # type: ignore
        self,
        source_info: SourceInfo,
        type_ref_name: str,
        type_ref_source_info: SourceInfo,
        target_info: tuple[Iterable[FieldRefPart.Info], SourceInfo] | None = None,
        template_info: tuple[SourceInfo, Iterable[TemplateArg]] | None = None,
        constructor: str | None = None,
    ) -> Self:
        self.source.get().setup(source_info=source_info)

        self.type_ref.get().setup(name=type_ref_name, source_info=type_ref_source_info)

        if target_info is not None:
            target_parts, target_source_info = target_info
            self.target.get().setup(source_info=target_source_info, parts=target_parts)

        if template_info is not None:
            template_source, template_args = template_info
            self.template.get().setup(source_info=template_source, args=template_args)

        if constructor is not None:
            self.constructor.get().alias_to_literal(constructor)

        return self
