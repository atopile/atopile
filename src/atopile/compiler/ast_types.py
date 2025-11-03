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
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.graph.graph import GraphView
from faebryk.library import Collections


@dataclass(frozen=True)
class SourceInfo:
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    text: str


class FileLocation(fabll.Node):
    start_line = fabll.Parameter.MakeChild()
    start_col = fabll.Parameter.MakeChild()
    end_line = fabll.Parameter.MakeChild()
    end_col = fabll.Parameter.MakeChild()

    def setup(
        self, g: GraphView, start_line: int, start_col: int, end_line: int, end_col: int
    ) -> Self:
        self.start_line.get().constrain_to_literal(g=g, value=start_line)
        self.start_col.get().constrain_to_literal(g=g, value=start_col)
        self.end_line.get().constrain_to_literal(g=g, value=end_line)
        self.end_col.get().constrain_to_literal(g=g, value=end_col)
        return self


class SourceChunk(fabll.Node):
    text = fabll.Parameter.MakeChild()
    loc = FileLocation.MakeChild()

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


class TypeRef(fabll.Node):
    name = fabll.Parameter.MakeChild()
    source = SourceChunk.MakeChild()

    def setup(self, g: GraphView, name: str, source_info: SourceInfo) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.name.get().constrain_to_literal(g=g, value=name)
        return self


class ImportPath(fabll.Node):
    source = SourceChunk.MakeChild()
    path = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, path: str, source_info: SourceInfo) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.path.get().constrain_to_literal(g=g, value=path)
        return self


class FieldRefPart(fabll.Node):
    @dataclass(frozen=True)
    class Info:
        name: str
        key: int | str | None
        source_info: SourceInfo

    source = SourceChunk.MakeChild()
    name = fabll.Parameter.MakeChild()
    key = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, info: Info) -> Self:
        self.source.get().setup(g=g, source_info=info.source_info)
        self.name.get().constrain_to_literal(g=g, value=info.name)

        if info.key is not None:
            self.key.get().constrain_to_literal(g=g, value=info.key)

        return self


class FieldRef(fabll.Node):
    source = SourceChunk.MakeChild()
    pin = fabll.Parameter.MakeChild()
    parts = Collections.PointerSequence.MakeChild()  # TODO: specify child type

    def setup(
        self, g: GraphView, source_info: SourceInfo, parts: Iterable[FieldRefPart.Info]
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        for part_info in parts:
            part = FieldRefPart.bind_typegraph(self.tg).create_instance(g=g)
            part.setup(g=g, info=part_info)

            EdgeComposition.add_child(
                bound_node=self.instance,
                child=part.instance.node(),
                child_identifier=str(id(part)),
            )

            self.parts.get().append(part)

        return self


class Number(fabll.Node):
    source = SourceChunk.MakeChild()
    value = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo, value: int | float) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.value.get().constrain_to_literal(g=g, value=value)
        return self


class Boolean(fabll.Node):
    source = SourceChunk.MakeChild()
    value = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo, value: bool) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.value.get().constrain_to_literal(g=g, value=value)
        return self


class Unit(fabll.Node):
    source = SourceChunk.MakeChild()
    symbol = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo, symbol: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.symbol.get().constrain_to_literal(g=g, value=symbol)
        return self


class Quantity(fabll.Node):
    source = SourceChunk.MakeChild()
    number = Number.MakeChild()
    unit = Unit.MakeChild()

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


class BinaryExpression(fabll.Node):
    source = SourceChunk.MakeChild()
    operator = fabll.Parameter.MakeChild()
    lhs = fabll.Optional.MakeChild()  # TODO: reqyired but deferred
    rhs = fabll.Optional.MakeChild()

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
        self.lhs.get().setup(g=g, value=lhs)
        self.rhs.get().setup(g=g, value=rhs)
        return self

    def get_lhs(self) -> "ArithmeticT":
        return self.lhs.get().get_value()

    def get_rhs(self) -> "ArithmeticT":
        return self.rhs.get().get_value()


class GroupExpression(fabll.Node):
    source = SourceChunk.MakeChild()
    expression = fabll.Optional.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, expression: "ArithmeticT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.expression.get().setup(g=g, value=expression)
        return self

    def get_expression(self) -> "ArithmeticT":
        return self.expression.get().get_value()


class ComparisonClause(fabll.Node):
    source = SourceChunk.MakeChild()
    operator = fabll.Parameter.MakeChild()
    rhs = fabll.Optional.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, operator: str, rhs: "ArithmeticT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.operator.get().constrain_to_literal(g=g, value=operator)
        self.rhs.get().setup(g=g, value=rhs)
        return self

    def get_rhs(self) -> "ArithmeticT":
        return self.rhs.get().get_value()


class ComparisonExpression(fabll.Node):
    source = SourceChunk.MakeChild()
    lhs = fabll.Optional.MakeChild()
    rhs_clauses = Collections.PointerSequence.MakeChild()

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        lhs: "ArithmeticT",
        rhs_clauses: Iterable["ComparisonClause"],
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.lhs.get().setup(g=g, value=lhs)

        for clause in rhs_clauses:
            EdgeComposition.add_child(
                bound_node=self.instance,
                child=clause.instance.node(),
                child_identifier=str(id(clause)),
            )
            self.rhs_clauses.get().append(clause)

        return self

    def get_lhs(self) -> "ArithmeticT":
        return self.lhs.get().get_value()


class BilateralQuantity(fabll.Node):
    source = SourceChunk.MakeChild()
    quantity = Quantity.MakeChild()
    tolerance = Quantity.MakeChild()

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


class BoundedQuantity(fabll.Node):
    source = SourceChunk.MakeChild()
    start = Quantity.MakeChild()
    end = Quantity.MakeChild()

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


class Scope(fabll.Node):
    stmts = Collections.PointerSet.MakeChild()

    def setup(self, g: GraphView, stmts: Iterable["StatementT"]) -> Self:
        for stmt in stmts:
            self.stmts.get().append(stmt)

            EdgeComposition.add_child(
                bound_node=self.instance,
                child=stmt.instance.node(),
                child_identifier=str(id(stmt)),
            )

        return self

    # TODO: get_child_stmts -> Iterable[Assignment | ...]


class File(fabll.Node):
    source = SourceChunk.MakeChild()
    scope = Scope.MakeChild()
    path = fabll.Parameter.MakeChild()

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


class BlockDefinition(fabll.Node):
    class BlockType(StrEnum):
        MODULE = "module"
        COMPONENT = "component"
        INTERFACE = "interface"

    source = SourceChunk.MakeChild()
    block_type = fabll.Parameter.MakeChild()  # TODO: enum domain
    type_ref = TypeRef.MakeChild()
    super_type_ref = TypeRef.MakeChild()
    scope = Scope.MakeChild()

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

    def get_block_type(self) -> BlockType:
        return self.BlockType(self.block_type.get().try_extract_constrained_literal())


@dataclass(frozen=True)
class SliceConfig:
    source: SourceInfo
    start: tuple[int, SourceInfo] | None = None
    stop: tuple[int, SourceInfo] | None = None
    step: tuple[int, SourceInfo] | None = None


class Slice(fabll.Node):
    source = SourceChunk.MakeChild()
    start = Number.MakeChild()
    stop = Number.MakeChild()
    step = Number.MakeChild()

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


class IterableFieldRef(fabll.Node):
    source = SourceChunk.MakeChild()
    field = FieldRef.MakeChild()
    slice = Slice.MakeChild()

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


class FieldRefList(fabll.Node):
    source = SourceChunk.MakeChild()
    items = Collections.PointerSequence.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, items: Iterable[FieldRef]
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        for item in items:
            self.items.get().append(item)
            EdgeComposition.add_child(
                bound_node=self.instance,
                child=item.instance.node(),
                child_identifier=str(id(item)),
            )

        return self


class ForStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    scope = Scope.MakeChild()
    target = fabll.Parameter.MakeChild()
    iterable = fabll.Optional.MakeChild()

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
        self.iterable.get().setup(g=g, value=iterable)
        self.scope.get().setup(g=g, stmts=stmts)
        return self

    def get_iterable(self) -> "IterableFieldRef | FieldRefList":
        return self.iterable.get().get_value()


class PragmaStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    pragma = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo, pragma: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.pragma.get().constrain_to_literal(g=g, value=pragma)
        return self


class ImportStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    path = ImportPath.MakeChild()
    type_ref = TypeRef.MakeChild()

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


class TemplateArg(fabll.Node):
    source = SourceChunk.MakeChild()
    name = fabll.Parameter.MakeChild()
    value = fabll.Parameter.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, name: str, value: "LiteralT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.name.get().constrain_to_literal(g=g, value=name)
        self.value.get().constrain_to_literal(g=g, value=value)
        return self


class Template(fabll.Node):
    source = SourceChunk.MakeChild()
    args = Collections.PointerSequence.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, args: Iterable[TemplateArg]
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        for arg in args:
            self.args.get().append(arg)
            EdgeComposition.add_child(
                bound_node=self.instance,
                child=arg.instance.node(),
                child_identifier=str(id(arg)),
            )

        return self


class NewExpression(fabll.Node):
    source = SourceChunk.MakeChild()
    type_ref = TypeRef.MakeChild()
    template = Template.MakeChild()
    new_count = Number.MakeChild()

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


class String(fabll.Node):
    source = SourceChunk.MakeChild()
    text = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo, text: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.text.get().constrain_to_literal(g=g, value=text)
        return self


class Assignable(fabll.Node):
    source = SourceChunk.MakeChild()
    value = fabll.Optional.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, value: "AssignableT"
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)

        self.value.get().setup(g=g, value=value)
        return self

    def get_value(self) -> "AssignableT":
        return self.value.get().get_value()


class Assignment(fabll.Node):
    source = SourceChunk.MakeChild()
    target = FieldRef.MakeChild()  # TODO: declarations?
    assignable = Assignable.MakeChild()

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


class ConnectStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    lhs = fabll.Optional.MakeChild()
    rhs = fabll.Optional.MakeChild()

    def setup(
        self,
        g: GraphView,
        source_info: SourceInfo,
        lhs: "ConnectableT",
        rhs: "ConnectableT",
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.lhs.get().setup(g=g, value=lhs)
        self.rhs.get().setup(g=g, value=rhs)
        return self

    def _get_operand(self, node: fabll.Node) -> "ConnectableT":
        match node_type := fabll.Node.get_type_name(node):
            case FieldRef.__name__:
                return FieldRef.bind_instance(node.instance)
            case SignaldefStmt.__name__:
                return SignaldefStmt.bind_instance(node.instance)
            case PinDeclaration.__name__:
                return PinDeclaration.bind_instance(node.instance)
            case _:
                raise ValueError(f"Expected ConnectableT, got {node_type}")

    def get_lhs(self) -> "ConnectableT":
        return self._get_operand(self.lhs.get().get_value())

    def get_rhs(self) -> "ConnectableT":
        return self._get_operand(self.rhs.get().get_value())


class DirectedConnectStmt(fabll.Node):
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    source = SourceChunk.MakeChild()
    direction = fabll.Parameter.MakeChild()  # TODO: enum domain
    lhs = fabll.Optional.MakeChild()
    rhs = fabll.Optional.MakeChild()

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
        self.lhs.get().setup(g=g, value=lhs)
        self.rhs.get().setup(g=g, value=rhs)
        return self

    def get_lhs(self) -> "ConnectableT":
        return self.lhs.get().get_value()

    def get_rhs(self) -> "ConnectableT | DirectedConnectStmt":
        return self.rhs.get().get_value()


class RetypeStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    target = FieldRef.MakeChild()
    new_type_ref = TypeRef.MakeChild()

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


class PinDeclaration(fabll.Node):
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    source = SourceChunk.MakeChild()
    kind = fabll.Parameter.MakeChild()
    label = fabll.Parameter.MakeChild()

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


class SignaldefStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    name = fabll.Parameter.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo, name: str) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.name.get().constrain_to_literal(g=g, value=name)
        return self


class AssertStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    comparison = fabll.Optional.MakeChild()

    def setup(
        self, g: GraphView, source_info: SourceInfo, comparison: ComparisonExpression
    ) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        self.comparison.get().setup(g=g, value=comparison)
        return self

    def get_comparison(self) -> "ComparisonExpression":
        return self.comparison.get().get_value()


class DeclarationStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    field_ref = FieldRef.MakeChild()
    unit = Unit.MakeChild()

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


class StringStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    string = String.MakeChild()

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


class PassStmt(fabll.Node):
    source = SourceChunk.MakeChild()

    def setup(self, g: GraphView, source_info: SourceInfo) -> Self:
        self.source.get().setup(g=g, source_info=source_info)
        return self


class TraitStmt(fabll.Node):
    source = SourceChunk.MakeChild()
    type_ref = TypeRef.MakeChild()
    target = FieldRef.MakeChild()
    template = Template.MakeChild()
    constructor = fabll.Parameter.MakeChild()

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
