"""
Generates an AST graph from the ANTLR4-generated AST.

Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
"""

from __future__ import annotations

import itertools
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from antlr4.tree.Tree import TerminalNodeImpl

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.Collections as Collections
from atopile.compiler.parse import parse_file, parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.linker import Linker as _Linker
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph, TypeGraphPathError
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView
from faebryk.library.Expressions import Is
from faebryk.libs.util import cast_assert, not_none

STDLIB_ALLOWLIST = {
    "Resistor": F.Resistor,
}


class ANTLRVisitor(AtoParserVisitor):
    """
    Generates a native AST graph from the ANTLR4-generated AST, with attached
    source context.
    """

    def __init__(
        self, graph: GraphView, type_graph: TypeGraph, file_path: Path | None
    ) -> None:
        super().__init__()
        self._graph = graph
        self._type_graph = type_graph
        self._file_path = file_path

    def _new[T: fabll.Node](self, type: type[T]) -> T:
        return type.bind_typegraph(self._type_graph).create_instance(g=self._graph)

    def _extract_source_info(self, ctx: ParserRuleContext) -> AST.SourceInfo:
        start_token = ctx.start
        stop_token = ctx.stop
        token_stream = ctx.parser.getInputStream()  # type: ignore
        text = AtoRewriter(token_stream).getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start_token.tokenIndex,  # type: ignore
            stop_token.tokenIndex,  # type: ignore
        )
        return AST.SourceInfo(
            start_line=start_token.line,  # type: ignore
            start_col=start_token.column,  # type: ignore
            end_line=stop_token.line,  # type: ignore
            end_col=stop_token.column,  # type: ignore
            text=text,
        )

    @staticmethod
    def _parse_int(text: str) -> int:
        normalized = text.replace("_", "")
        return int(normalized, 0)

    @staticmethod
    def _parse_decimal(text: str) -> int | float:
        normalized = text.replace("_", "")
        try:
            return float(Decimal(normalized))
        except InvalidOperation:
            return int(normalized, 0)

    def visitName(self, ctx: AtoParser.NameContext) -> str:
        return ctx.getText()

    def visitType_reference(
        self, ctx: AtoParser.Type_referenceContext
    ) -> tuple[str, AST.SourceInfo]:
        return (self.visitName(ctx.name()), self._extract_source_info(ctx))

    def visitArray_index(self, ctx: AtoParser.Array_indexContext) -> str | int | None:
        if (key_ctx := ctx.key()) is not None:
            return self.visitKey(key_ctx)

    def visitKey(self, ctx: AtoParser.KeyContext) -> int:
        return self.visitNumber_hint_integer(ctx.number_hint_integer())

    def visitStmt(self, ctx: AtoParser.StmtContext) -> Iterable[AST.StatementT]:
        match (ctx.pragma_stmt(), ctx.simple_stmts(), ctx.compound_stmt()):
            case (pragma_stmt, None, None):
                return [self.visitPragma_stmt(pragma_stmt)]
            case (None, simple_stmts, None):
                return self.visitSimple_stmts(simple_stmts)
            case (None, None, compound_stmt):
                return [self.visitCompound_stmt(compound_stmt)]
            case _:
                assert False, f"Unexpected statement: {ctx.getText()}"

    def visitStmts(self, ctx: AtoParser.StmtsContext) -> Iterable[AST.StatementT]:
        return itertools.chain.from_iterable(
            (child for child in self.visitStmt(child) if child is not None)
            for child in ctx
        )

    def visitBlock(self, ctx: AtoParser.BlockContext) -> Iterable[AST.StatementT]:
        stmts_children = (
            child for child in self.visitStmts(ctx.stmt()) if child is not None
        )

        simple_stmts_children = (
            self.visitSimple_stmts(ctx.simple_stmts())
            if ctx.simple_stmts() is not None
            else []
        )

        return itertools.chain.from_iterable((stmts_children, simple_stmts_children))

    def visitBlockdef(self, ctx: AtoParser.BlockdefContext) -> AST.BlockDefinition:
        type_ref_name, type_ref_source_info = self.visitType_reference(
            ctx.type_reference()
        )

        return self._new(AST.BlockDefinition).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            block_type=ctx.blocktype().getText(),
            type_ref_name=type_ref_name,
            type_ref_source_info=type_ref_source_info,
            super_type_ref_info=(
                self.visitType_reference(ctx.blockdef_super().type_reference())
                if ctx.blockdef_super() is not None
                else None
            ),
            stmts=self.visitBlock(ctx.block()),
        )

    def visitFile_input(self, ctx: AtoParser.File_inputContext) -> AST.File:
        return self._new(AST.File).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            path=str(self._file_path) if self._file_path is not None else "",
            stmts=self.visitStmts(ctx.stmt()),
        )

    def visitSimple_stmts(
        self, ctx: AtoParser.Simple_stmtsContext
    ) -> Iterable[AST.StatementT]:
        return itertools.chain.from_iterable(
            (
                child
                if (isinstance(child, Iterable) and not isinstance(child, str))
                else [child]
                for child in (self.visit(child) for child in ctx.simple_stmt())
            )
        )

    def visitSimple_stmt(self, ctx: AtoParser.Simple_stmtContext) -> AST.StatementT:
        (stmt_ctx,) = [
            stmt_ctx
            for stmt_ctx in [
                ctx.import_stmt(),
                ctx.assign_stmt(),
                ctx.connect_stmt(),
                ctx.directed_connect_stmt(),
                ctx.retype_stmt(),
                ctx.pin_declaration(),
                ctx.signaldef_stmt(),
                ctx.assert_stmt(),
                ctx.declaration_stmt(),
                ctx.string_stmt(),
                ctx.pass_stmt(),
                ctx.trait_stmt(),
            ]
            if stmt_ctx is not None
        ]

        return self.visit(stmt_ctx)

    def visitCompound_stmt(
        self, ctx: AtoParser.Compound_stmtContext
    ) -> AST.BlockDefinition | AST.ForStmt:
        match (ctx.blockdef(), ctx.for_stmt()):
            case (blockdef_ctx, None):
                return self.visitBlockdef(blockdef_ctx)
            case (None, for_ctx):
                return self.visitFor_stmt(for_ctx)
            case _:
                raise ValueError(f"Unexpected compound statement: {ctx.getText()}")

    def visitPragma_stmt(self, ctx: AtoParser.Pragma_stmtContext) -> AST.PragmaStmt:
        return self._new(AST.PragmaStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            pragma=self.visit(ctx.PRAGMA()),
        )

    def visitImport_stmt(self, ctx: AtoParser.Import_stmtContext) -> AST.ImportStmt:
        type_ref_name, type_ref_source_info = self.visitType_reference(
            ctx.type_reference()
        )
        return self._new(AST.ImportStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            type_ref_name=type_ref_name,
            type_ref_source_info=type_ref_source_info,
            path_info=self.visitString(ctx.string()) if ctx.string() else None,
        )

    def visitRetype_stmt(self, ctx: AtoParser.Retype_stmtContext) -> AST.RetypeStmt:
        field_parts, field_source = self._field_ref_parts_from_ctx(
            ctx.field_reference()
        )
        type_ref_name, type_ref_source_info = self.visitType_reference(
            ctx.type_reference()
        )
        return self._new(AST.RetypeStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            target_parts=field_parts,
            target_source_info=field_source,
            new_type_name=type_ref_name,
            new_type_source_info=type_ref_source_info,
        )

    def visitPin_declaration(
        self, ctx: AtoParser.Pin_declarationContext
    ) -> AST.PinDeclaration:
        return self.visitPin_stmt(ctx.pin_stmt())

    def visitPindef_stmt(self, ctx: AtoParser.Pindef_stmtContext) -> AST.PinDeclaration:
        return self.visitPin_stmt(ctx.pin_stmt())

    def visitPin_stmt(self, ctx: AtoParser.Pin_stmtContext) -> AST.PinDeclaration:
        match (ctx.name(), ctx.number_hint_natural(), ctx.string()):
            case (name_ctx, None, None):
                kind = AST.PinDeclaration.Kind.NAME
                label_value: AST.LiteralT | None = self.visitName(name_ctx)
            case (None, number_ctx, None):
                kind = AST.PinDeclaration.Kind.NUMBER
                label_value = self.visitNumber_hint_natural(number_ctx)
            case (None, None, string_ctx):
                kind = AST.PinDeclaration.Kind.STRING
                label_value, _ = self.visitString(string_ctx)
            case _:
                raise ValueError(f"Unexpected pin statement: {ctx.getText()}")

        return self._new(AST.PinDeclaration).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            kind=kind,
            label_value=label_value,
        )

    def visitSignaldef_stmt(
        self, ctx: AtoParser.Signaldef_stmtContext
    ) -> AST.SignaldefStmt:
        return self._new(AST.SignaldefStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            name=self.visitName(ctx.name()),
        )

    def visitString_stmt(self, ctx: AtoParser.String_stmtContext) -> AST.StringStmt:
        text, source_info = self.visitString(ctx.string())
        return self._new(AST.StringStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            string_value=text,
            string_source_info=source_info,
        )

    def visitField_reference_or_declaration(
        self, ctx: AtoParser.Field_reference_or_declarationContext
    ) -> AST.FieldRef | AST.DeclarationStmt:
        match [ctx.field_reference(), ctx.declaration_stmt()]:
            case [field_ref_ctx, None]:
                return self.visitField_reference(field_ref_ctx)
            case [None, decl_stmt_ctx]:
                return self.visitDeclaration_stmt(decl_stmt_ctx)
            case _:
                raise ValueError(
                    f"Unexpected field reference or declaration: {ctx.getText()}"
                )

    def visitPass_stmt(self, ctx: AtoParser.Pass_stmtContext) -> AST.PassStmt:
        return self._new(AST.PassStmt).setup(
            g=self._graph, source_info=self._extract_source_info(ctx)
        )

    def visitAssert_stmt(self, ctx: AtoParser.Assert_stmtContext) -> AST.AssertStmt:
        return self._new(AST.AssertStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            comparison=self.visitComparison(ctx.comparison()),
        )

    def visitTrait_stmt(self, ctx: AtoParser.Trait_stmtContext) -> AST.TraitStmt:
        target_info = (
            self._field_ref_parts_from_ctx(ctx.field_reference())
            if ctx.field_reference() is not None
            else None
        )

        template_info = (
            self.visitTemplate(ctx.template()) if ctx.template() is not None else None
        )

        constructor = (
            self.visitConstructor(ctx.constructor())
            if ctx.constructor() is not None
            else None
        )

        type_ref_name, type_ref_source_info = self.visitType_reference(
            ctx.type_reference()
        )

        return self._new(AST.TraitStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            type_ref_name=type_ref_name,
            type_ref_source_info=type_ref_source_info,
            target_info=target_info,
            template_info=template_info,
            constructor=constructor,
        )

    def visitConstructor(self, ctx: AtoParser.ConstructorContext) -> str:
        return self.visitName(ctx.name())

    def visitFor_stmt(self, ctx: AtoParser.For_stmtContext) -> AST.ForStmt:
        return self._new(AST.ForStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            target=self.visitName(ctx.name()),
            iterable=self.visitIterable_references(ctx.iterable_references()),
            stmts=self.visitBlock(ctx.block()),
        )

    def visitIterable_references(
        self, ctx: AtoParser.Iterable_referencesContext
    ) -> AST.IterableFieldRef | AST.FieldRefList:
        match [ctx.field_reference(), ctx.list_literal_of_field_references()]:
            case [field_ref_ctx, None]:
                field_parts, field_source_info = self._field_ref_parts_from_ctx(
                    field_ref_ctx
                )
                return self._new(AST.IterableFieldRef).setup(
                    g=self._graph,
                    source_info=self._extract_source_info(ctx),
                    field_parts=field_parts,
                    field_source_info=field_source_info,
                    slice_config=self.visitSlice(ctx.slice_())
                    if ctx.slice_() is not None
                    else None,
                )
            case [None, list_literal_ctx]:
                return self.visitList_literal_of_field_references(list_literal_ctx)
            case _:
                raise ValueError(f"Unexpected iterable references: {ctx.getText()}")

    def visitList_literal_of_field_references(
        self, ctx: AtoParser.List_literal_of_field_referencesContext
    ) -> AST.FieldRefList:
        return self._new(AST.FieldRefList).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            items=map(self.visitField_reference, ctx.field_reference()),
        )

    def visitSlice(self, ctx: AtoParser.SliceContext) -> AST.SliceConfig:
        return AST.SliceConfig(
            source=self._extract_source_info(ctx),
            start=(
                self.visitSlice_start(ctx.slice_start())
                if ctx.slice_start() is not None
                else None
            ),
            stop=(
                self.visitSlice_stop(ctx.slice_stop())
                if ctx.slice_stop() is not None
                else None
            ),
            step=(
                self.visitSlice_step(ctx.slice_step())
                if ctx.slice_step() is not None
                else None
            ),
        )

    def visitSlice_start(
        self, ctx: AtoParser.Slice_startContext
    ) -> tuple[int, AST.SourceInfo]:
        return (
            self.visitNumber_hint_integer(ctx.number_hint_integer()),
            self._extract_source_info(ctx),
        )

    def visitSlice_stop(
        self, ctx: AtoParser.Slice_stopContext
    ) -> tuple[int, AST.SourceInfo]:
        return (
            self.visitNumber_hint_integer(ctx.number_hint_integer()),
            self._extract_source_info(ctx),
        )

    def visitSlice_step(
        self, ctx: AtoParser.Slice_stepContext
    ) -> tuple[int, AST.SourceInfo]:
        return (
            self.visitNumber_hint_integer(ctx.number_hint_integer()),
            self._extract_source_info(ctx),
        )

    def visitField_reference_part(
        self, ctx: AtoParser.Field_reference_partContext
    ) -> AST.FieldRefPart.Info:
        return AST.FieldRefPart.Info(
            name=self.visitName(ctx.name()),
            key=(
                self.visitArray_index(ctx.array_index())
                if ctx.array_index() is not None
                else None
            ),
            source_info=self._extract_source_info(ctx),
        )

    # TODO: consolidate with visitField_reference?
    def _field_ref_parts_from_ctx(
        self, ctx: AtoParser.Field_referenceContext
    ) -> tuple[list[AST.FieldRefPart.Info], AST.SourceInfo]:
        return [
            self.visitField_reference_part(part_ctx)
            for part_ctx in ctx.field_reference_part()
        ], self._extract_source_info(ctx)

    def visitField_reference(
        self, ctx: AtoParser.Field_referenceContext
    ) -> AST.FieldRef:
        parts, source_info = self._field_ref_parts_from_ctx(ctx)
        return self._new(AST.FieldRef).setup(
            g=self._graph, source_info=source_info, parts=parts
        )

    def visitAssign_stmt(self, ctx: AtoParser.Assign_stmtContext) -> AST.Assignment:
        field_ref_ctx = ctx.field_reference_or_declaration().field_reference()
        decl_stmt_ctx = ctx.field_reference_or_declaration().declaration_stmt()

        match (field_ref_ctx, decl_stmt_ctx):
            case (field_ref_ctx, None):
                field_ref_parts = [
                    self.visitField_reference_part(part)
                    for part in field_ref_ctx.field_reference_part()
                ]

                # FIXME: not working?
                field_ref_source_info = self._extract_source_info(field_ref_ctx)

                # TODO: support final pin?

            case (None, decl_stmt_ctx):
                raise NotImplementedError(
                    "Declaration statements are not supported yet"
                )  # TODO
            case _:
                raise ValueError(
                    f"Unexpected field reference or declaration: {ctx.getText()}"
                )

        return self._new(AST.Assignment).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            target_field_ref_parts=field_ref_parts,
            target_field_ref_source_info=field_ref_source_info,
            assignable_value=self.visitAssignable(ctx.assignable()),
            assignable_source_info=self._extract_source_info(ctx.assignable()),
        )

    def visitAssignable(self, ctx: AtoParser.AssignableContext) -> AST.AssignableT:
        match (
            ctx.new_stmt(),
            ctx.literal_physical(),
            ctx.arithmetic_expression(),
            ctx.string(),
            ctx.boolean_(),
        ):
            case (new_stmt_ctx, None, None, None, None):
                value = self.visitNew_stmt(new_stmt_ctx)
            case (None, literal_physical_ctx, None, None, None):
                value = self.visitLiteral_physical(literal_physical_ctx)
            case (None, None, arithmetic_expression_ctx, None, None):
                value = self.visitArithmetic_expression(arithmetic_expression_ctx)
            case (None, None, None, string_ctx, None):
                text, source_info = self.visitString(string_ctx)
                value = self._new(AST.String).setup(
                    g=self._graph, source_info=source_info, text=text
                )
            case (None, None, None, None, boolean_ctx):
                value = self.visitBoolean_(boolean_ctx)
            case _:
                raise ValueError(f"Unexpected assignable: {ctx.getText()}")

        return value

    def visitNew_stmt(self, ctx: AtoParser.New_stmtContext) -> AST.NewExpression:
        template_data = (
            self.visitTemplate(ctx.template()) if ctx.template() is not None else None
        )

        new_count_info = (
            (
                self.visitNumber_hint_natural(ctx.new_count().number_hint_natural()),
                self._extract_source_info(ctx.new_count()),
            )
            if ctx.new_count() is not None
            else None
        )

        type_ref_name, type_ref_source_info = self.visitType_reference(
            ctx.type_reference()
        )

        return self._new(AST.NewExpression).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            type_ref_name=type_ref_name,
            type_ref_source_info=type_ref_source_info,
            template=template_data,
            new_count_info=new_count_info,
        )

    def visitLiteral_physical(
        self, ctx: AtoParser.Literal_physicalContext
    ) -> AST.Quantity | AST.BilateralQuantity | AST.BoundedQuantity:
        match ctx.quantity(), ctx.bilateral_quantity(), ctx.bound_quantity():
            case (quantity_ctx, None, None):
                value, unit_symbol, unit_source = self.visitQuantity(quantity_ctx)

                return self._new(AST.Quantity).setup(
                    g=self._graph,
                    source_info=self._extract_source_info(quantity_ctx),
                    value=value,
                    value_source_info=self._extract_source_info(quantity_ctx.number()),
                    unit=(
                        (unit_symbol, unit_source)
                        if (quantity_ctx.unit() is not None and unit_symbol is not None)
                        else None
                    ),
                )
            case (None, bilateral_quantity_ctx, None):
                return self.visitBilateral_quantity(bilateral_quantity_ctx)
            case (None, None, bound_quantity_ctx):
                return self.visitBound_quantity(bound_quantity_ctx)
            case _:
                raise ValueError(
                    f"Unexpected literal physical context: {ctx.getText()}"
                )

    def visitArithmetic_expression(
        self, ctx: AtoParser.Arithmetic_expressionContext
    ) -> AST.ArithmeticT:
        rhs = self.visitSum(ctx.sum_())

        if ctx.arithmetic_expression() is not None:
            match [ctx.OR_OP(), ctx.AND_OP()]:
                case [or_op, None]:
                    operator = or_op.getText()
                case [None, and_op]:
                    operator = and_op.getText()
                case _:
                    raise ValueError(
                        f"Unexpected operator in arithmetic expression: {ctx.getText()}"
                    )

            lhs = self.visitArithmetic_expression(ctx.arithmetic_expression())
            return self._new(AST.BinaryExpression).setup(
                g=self._graph,
                source_info=self._extract_source_info(ctx),
                operator=operator,
                lhs=lhs,
                rhs=rhs,
            )

        return rhs

    def visitSum(self, ctx: AtoParser.SumContext) -> AST.ArithmeticT:
        rhs = self.visitTerm(ctx.term())

        if ctx.sum_() is not None:
            match [ctx.PLUS(), ctx.MINUS()]:
                case [plus_token, None]:
                    operator = self.visitTerminal(plus_token)
                case [None, minus_token]:
                    operator = self.visitTerminal(minus_token)
                case _:
                    raise ValueError(f"Unexpected sum operator: {ctx.getText()}")

            return self._new(AST.BinaryExpression).setup(
                g=self._graph,
                source_info=self._extract_source_info(ctx),
                operator=operator,
                lhs=self.visitSum(ctx.sum_()),
                rhs=rhs,
            )

        return rhs

    def visitTerm(self, ctx: AtoParser.TermContext) -> AST.ArithmeticT:
        rhs = self.visitPower(ctx.power())

        if ctx.term() is not None:
            match [ctx.STAR(), ctx.DIV()]:
                case [star_token, None]:
                    operator = star_token.getText()
                case [None, div_token]:
                    operator = div_token.getText()
                case _:
                    raise ValueError(f"Unexpected term operator: {ctx.getText()}")

            lhs = self.visitTerm(ctx.term())
            return self._new(AST.BinaryExpression).setup(
                g=self._graph,
                source_info=self._extract_source_info(ctx),
                operator=operator,
                lhs=lhs,
                rhs=rhs,
            )

        return rhs

    def visitPower(self, ctx: AtoParser.PowerContext) -> AST.ArithmeticT:
        atoms = [self.visitAtom(atom_ctx) for atom_ctx in ctx.atom()]
        match atoms:
            case [base, exponent]:
                return self._new(AST.BinaryExpression).setup(
                    g=self._graph,
                    source_info=self._extract_source_info(ctx),
                    operator=ctx.POWER().getText(),
                    lhs=base,
                    rhs=exponent,
                )
            case [single]:
                return single
            case _:
                raise ValueError(f"Unexpected power context: {ctx.getText()}")

    def visitArithmetic_group(
        self, ctx: AtoParser.Arithmetic_groupContext
    ) -> AST.GroupExpression:
        return self._new(AST.GroupExpression).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            expression=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitAtom(self, ctx: AtoParser.AtomContext) -> AST.ArithmeticAtomT:
        match ctx.field_reference(), ctx.literal_physical(), ctx.arithmetic_group():
            case (field_ref_ctx, None, None):
                return self.visitField_reference(field_ref_ctx)
            case (None, literal_ctx, None):
                return self.visitLiteral_physical(literal_ctx)
            case (None, None, group_ctx):
                return self.visitArithmetic_group(group_ctx)
            case _:
                raise ValueError(f"Unexpected atom context: {ctx.getText()}")

    def visitComparison(
        self, ctx: AtoParser.ComparisonContext
    ) -> AST.ComparisonExpression:
        return self._new(AST.ComparisonExpression).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            lhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
            rhs_clauses=[
                self.visitCompare_op_pair(pair_ctx)
                for pair_ctx in ctx.compare_op_pair()
            ],
        )

    def visitCompare_op_pair(
        self, ctx: AtoParser.Compare_op_pairContext
    ) -> AST.ComparisonClause:
        match [
            ctx.lt_arithmetic_or(),
            ctx.gt_arithmetic_or(),
            ctx.lt_eq_arithmetic_or(),
            ctx.gt_eq_arithmetic_or(),
            ctx.in_arithmetic_or(),
            ctx.is_arithmetic_or(),
        ]:
            case [lt_ctx, None, None, None, None, None]:
                return self.visitLt_arithmetic_or(lt_ctx)
            case [None, gt_ctx, None, None, None, None]:
                return self.visitGt_arithmetic_or(gt_ctx)
            case [None, None, lt_eq_ctx, None, None, None]:
                return self.visitLt_eq_arithmetic_or(lt_eq_ctx)
            case [None, None, None, gt_eq_ctx, None, None]:
                return self.visitGt_eq_arithmetic_or(gt_eq_ctx)
            case [None, None, None, None, in_ctx, None]:
                return self.visitIn_arithmetic_or(in_ctx)
            case [None, None, None, None, None, is_ctx]:
                return self.visitIs_arithmetic_or(is_ctx)
            case _:
                raise ValueError(f"Unexpected compare op pair context: {ctx.getText()}")

    def visitLt_arithmetic_or(
        self, ctx: AtoParser.Lt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.LESS_THAN().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitGt_arithmetic_or(
        self, ctx: AtoParser.Gt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.GREATER_THAN().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitLt_eq_arithmetic_or(
        self, ctx: AtoParser.Lt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.LT_EQ().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitGt_eq_arithmetic_or(
        self, ctx: AtoParser.Gt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.GT_EQ().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitIn_arithmetic_or(
        self, ctx: AtoParser.In_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.WITHIN().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitIs_arithmetic_or(
        self, ctx: AtoParser.Is_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.IS().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitQuantity(
        self, ctx: AtoParser.QuantityContext
    ) -> tuple[int | float, str | None, AST.SourceInfo]:
        number, _ = self.visitNumber(ctx.number())
        unit = self.visitUnit(ctx.unit()) if ctx.unit() else None
        return number, unit, self._extract_source_info(ctx)

    def visitUnit(self, ctx: AtoParser.UnitContext) -> str:
        return self.visitName(ctx.name())

    def visitDeclaration_stmt(
        self, ctx: AtoParser.Declaration_stmtContext
    ) -> AST.DeclarationStmt:
        field_parts, field_source = self._field_ref_parts_from_ctx(
            ctx.field_reference()
        )

        return self._new(AST.DeclarationStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            field_ref_parts=field_parts,
            field_ref_source_info=field_source,
            unit_symbol=self.visitUnit(ctx.unit()),
            unit_source_info=self._extract_source_info(ctx.unit()),
        )

    def visitBilateral_quantity(
        self, ctx: AtoParser.Bilateral_quantityContext
    ) -> AST.BilateralQuantity:
        quantity_ctx = ctx.quantity()
        quantity_value, quantity_unit, quantity_source = self.visitQuantity(
            quantity_ctx
        )

        (
            tolerance_value,
            tolerance_unit,
            tolerance_value_source,
            tolerance_unit_source,
        ) = self.visitBilateral_tolerance(ctx.bilateral_tolerance())

        return self._new(AST.BilateralQuantity).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            quantity_value=quantity_value,
            quantity_value_source_info=self._extract_source_info(quantity_ctx.number()),
            quantity_unit=(
                (quantity_unit, quantity_source) if quantity_unit is not None else None
            ),
            quantity_source_info=self._extract_source_info(ctx.quantity()),
            tolerance_value=tolerance_value,
            tolerance_value_source_info=tolerance_value_source,
            tolerance_unit=(
                (tolerance_unit, tolerance_unit_source)
                if tolerance_unit is not None and tolerance_unit_source is not None
                else None
            ),
            tolerance_source_info=self._extract_source_info(ctx.bilateral_tolerance()),
        )

    def visitBilateral_tolerance(
        self, ctx: AtoParser.Bilateral_toleranceContext
    ) -> tuple[int | float, str | None, AST.SourceInfo, AST.SourceInfo | None]:
        match [ctx.unit(), ctx.PERCENT()]:
            case [unit_ctx, None]:
                unit = self.visitUnit(unit_ctx)
                unit_source = self._extract_source_info(unit_ctx)
            case [None, percent_token]:
                unit = self.visitTerminal(percent_token)
                unit_source = self._extract_source_info(ctx)
            case _:
                raise ValueError(
                    f"Unexpected bilateral tolerance context: {ctx.getText()}"
                )

        return (
            self.visitNumber_signless(ctx.number_signless()),
            unit,
            self._extract_source_info(ctx.number_signless()),
            unit_source,
        )

    def visitBound_quantity(
        self, ctx: AtoParser.Bound_quantityContext
    ) -> AST.BoundedQuantity:
        start_ctx, end_ctx = ctx.quantity()
        start_value, start_unit, start_source = self.visitQuantity(start_ctx)
        end_value, end_unit, end_source = self.visitQuantity(end_ctx)

        return self._new(AST.BoundedQuantity).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            start_value=start_value,
            start_unit=(start_unit, start_source) if start_unit is not None else None,
            start_source_info=start_source,
            start_value_source_info=self._extract_source_info(start_ctx.number()),
            end_value=end_value,
            end_unit=(end_unit, end_source) if end_unit is not None else None,
            end_source_info=end_source,
            end_value_source_info=self._extract_source_info(end_ctx.number()),
        )

    def visitTemplate(
        self, ctx: AtoParser.TemplateContext
    ) -> tuple[AST.SourceInfo, list[AST.TemplateArg]]:
        args = [self.visitTemplate_arg(arg_ctx) for arg_ctx in ctx.template_arg()]
        return self._extract_source_info(ctx), args

    def visitTemplate_arg(self, ctx: AtoParser.Template_argContext) -> AST.TemplateArg:
        match [
            ctx.literal().string(),
            ctx.literal().boolean_(),
            ctx.literal().number(),
        ]:
            case [string_ctx, None, None]:
                value, _ = self.visitString(string_ctx)
            case [None, boolean_ctx, None]:
                match [boolean_ctx.TRUE(), boolean_ctx.FALSE()]:
                    case [_, None]:
                        value = True
                    case [None, _]:
                        value = False
                    case _:
                        raise ValueError(f"Unexpected boolean literal: {ctx.getText()}")
            case [None, None, number_ctx]:
                value, _ = self.visitNumber(number_ctx)
            case _:
                raise ValueError(f"Unexpected literal: {ctx.getText()}")

        return self._new(AST.TemplateArg).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            name=self.visitName(ctx.name()),
            value=value,
        )

    def visitTerminal(self, node: TerminalNodeImpl) -> str:
        return node.getText()

    def visitString(self, ctx: AtoParser.StringContext) -> tuple[str, AST.SourceInfo]:
        # TODO: parser should give us the text without quotes

        text = self.visitTerminal(ctx.STRING())
        if text.startswith(r'"""') and text.endswith(r'"""'):
            text = text.removeprefix(r'"""').removesuffix(r'"""')
        elif text.startswith(r"'") and text.endswith(r"'"):
            text = text.removeprefix(r"'").removesuffix(r"'")
        elif text.startswith(r'"') and text.endswith(r'"'):
            text = text.removeprefix(r'"').removesuffix(r'"')
        else:
            raise ValueError(f"Unexpected string context: {ctx.getText()}")

        return text, self._extract_source_info(ctx)

    def visitBoolean_(self, ctx: AtoParser.Boolean_Context) -> AST.Boolean:
        match [ctx.TRUE(), ctx.FALSE()]:
            case [_, None]:
                value = True
            case [None, _]:
                value = False
            case _:
                raise ValueError(f"Unexpected boolean literal: {ctx.getText()}")

        return self._new(AST.Boolean).setup(
            g=self._graph, source_info=self._extract_source_info(ctx), value=value
        )

    def visitNumber_signless(
        self, ctx: AtoParser.Number_signlessContext
    ) -> int | float:
        return self._parse_decimal(ctx.getText())

    def visitNumber(
        self, ctx: AtoParser.NumberContext
    ) -> tuple[int | float, AST.SourceInfo]:
        number = self._parse_decimal(ctx.getText())
        return number, self._extract_source_info(ctx)

    def visitNumber_hint_natural(
        self, ctx: AtoParser.Number_hint_naturalContext
    ) -> int:
        return self._parse_int(ctx.getText())

    def visitNumber_hint_integer(
        self, ctx: AtoParser.Number_hint_integerContext
    ) -> int:
        return self._parse_int(ctx.getText())

    def visitMif(self, ctx: AtoParser.MifContext) -> AST.ConnectableT:
        return self.visitConnectable(ctx.connectable())

    def visitBridgeable(self, ctx: AtoParser.BridgeableContext) -> AST.ConnectableT:
        return self.visitConnectable(ctx.connectable())

    def visitConnectable(self, ctx: AtoParser.ConnectableContext) -> AST.ConnectableT:
        match ctx.field_reference(), ctx.signaldef_stmt(), ctx.pindef_stmt():
            case (field_ref_ctx, None, None):
                return self.visitField_reference(field_ref_ctx)
            case (None, signaldef_stmt_ctx, None):
                return self.visitSignaldef_stmt(signaldef_stmt_ctx)
            case (None, None, pindef_stmt_ctx):
                return self.visitPindef_stmt(pindef_stmt_ctx)
            case _:
                raise ValueError(f"Unexpected connectable: {ctx.getText()}")

    def visitConnect_stmt(self, ctx: AtoParser.Connect_stmtContext) -> AST.ConnectStmt:
        lhs, rhs = [self.visitMif(mif_ctx) for mif_ctx in ctx.mif()]

        return self._new(AST.ConnectStmt).setup(
            g=self._graph, source_info=self._extract_source_info(ctx), lhs=lhs, rhs=rhs
        )

    def visitDirected_connect_stmt(
        self, ctx: AtoParser.Directed_connect_stmtContext
    ) -> AST.DirectedConnectStmt:
        match [ctx.SPERM(), ctx.LSPERM()]:
            case [_, None]:
                direction = AST.DirectedConnectStmt.Direction.RIGHT
            case [None, _]:
                direction = AST.DirectedConnectStmt.Direction.LEFT
            case _:
                raise ValueError(
                    f"Unexpected directed connect statement: {ctx.getText()}"
                )

        match [self.visitBridgeable(b) for b in ctx.bridgeable()]:
            case [lhs]:
                if (nested_ctx := ctx.directed_connect_stmt()) is None:
                    raise ValueError(
                        "Directed connect statement missing RHS for chained syntax"
                    )
                rhs = self.visitDirected_connect_stmt(nested_ctx)
            case [first, second]:
                lhs, rhs = first, second
            case _:
                raise ValueError(f"Unexpected bridgeables: {ctx.getText()}")

        return self._new(AST.DirectedConnectStmt).setup(
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            direction=direction,
            lhs=lhs,
            rhs=rhs,
        )


class DslException(Exception):
    """
    Exceptions arising from user's DSL code.
    """


class CompilerException(Exception):
    """
    Exceptions arising from internal compiler failures.
    """


@dataclass
class BuildState:
    type_graph: TypeGraph
    type_roots: dict[str, BoundNode]
    external_type_refs: list[tuple[BoundNode, GenTypeGraphIR.ImportRef]]
    file_path: Path | None


class GenTypeGraphIR:
    @dataclass(frozen=True)
    class ImportRef:
        name: str
        path: str | None = None

        def __repr__(self) -> str:
            path_part = f', path="{self.path}"' if self.path else ""
            return f"ImportRef(name={self.name}{path_part})"

    @dataclass(frozen=True)
    class Symbol:
        name: str
        import_ref: GenTypeGraphIR.ImportRef | None = None
        type_node: BoundNode | None = None

        def __repr__(self) -> str:
            return (
                f"Symbol(name={self.name}, import_ref={self.import_ref}, "
                f"type_node={self.type_node})"
            )

    @dataclass(frozen=True)
    class FieldPath:
        @dataclass(frozen=True)
        class Segment:
            identifier: str
            is_index: bool = False

        segments: tuple["GenTypeGraphIR.FieldPath.Segment", ...]

        def __post_init__(self) -> None:
            if not self.segments:
                raise ValueError("FieldPath cannot be empty")

        @property
        def parent_segments(self) -> Sequence["GenTypeGraphIR.FieldPath.Segment"]:
            *head, _ = self.segments
            return head

        @property
        def leaf(self) -> "GenTypeGraphIR.FieldPath.Segment":
            *_, tail = self.segments
            return tail

        def is_singleton(self) -> bool:
            return len(self.segments) == 1

        def __str__(self) -> str:
            parts: list[str] = []

            for segment in self.segments:
                if segment.is_index:
                    parts[-1] = f"{parts[-1]}[{segment.identifier}]"
                else:
                    parts.append(segment.identifier)

            return ".".join(parts)

        def identifiers(self) -> tuple[str, ...]:
            return tuple(segment.identifier for segment in self.segments)

    @dataclass(frozen=True)
    class NewChildSpec:
        symbol: GenTypeGraphIR.Symbol | None = None
        type_identifier: str | None = None
        type_node: BoundNode | None = None
        count: int | None = None

    @dataclass(frozen=True)
    class AddMakeChildAction:
        target_path: GenTypeGraphIR.FieldPath
        child_spec: GenTypeGraphIR.NewChildSpec
        parent_reference: BoundNode | None
        parent_path: GenTypeGraphIR.FieldPath | None

    @dataclass(frozen=True)
    class AddMakeLinkAction:
        lhs_ref: BoundNode
        rhs_ref: BoundNode

    @dataclass
    class ScopeState:
        symbols: dict[str, GenTypeGraphIR.Symbol] = field(default_factory=dict)
        fields: set[str] = field(default_factory=set)
        # Aliases allow temporarily binding a loop variable name to a concrete
        # field path during `for` iteration. Only used within the current
        # lexical scope and intended to be short-lived.
        aliases: dict[str, GenTypeGraphIR.FieldPath] = field(default_factory=dict)


class _ScopeStack:
    stack: list[GenTypeGraphIR.ScopeState]

    def __init__(self) -> None:
        self.stack = []

    @contextmanager
    def enter(self) -> Generator[GenTypeGraphIR.ScopeState, None, None]:
        state = GenTypeGraphIR.ScopeState()
        self.stack.append(state)
        try:
            yield state
        finally:
            self.stack.pop()

    @property
    def current(self) -> GenTypeGraphIR.ScopeState:
        return self.stack[-1]

    def add_symbol(self, symbol: GenTypeGraphIR.Symbol) -> None:
        current_state = self.current
        if symbol.name in current_state.symbols:
            raise DslException(f"Symbol `{symbol.name}` already defined in scope")

        current_state.symbols[symbol.name] = symbol

        print(f"Added symbol {symbol} to scope")

    def add_field(self, path: GenTypeGraphIR.FieldPath) -> None:
        current_state = self.current
        if (key := str(path)) in current_state.fields:
            raise DslException(f"Field `{key}` already defined in scope")

        current_state.fields.add(key)

        print(f"Added field {key} to scope")

    def has_field(self, path: GenTypeGraphIR.FieldPath) -> bool:
        return any(str(path) in state.fields for state in reversed(self.stack))

    def resolve_symbol(self, name: str) -> GenTypeGraphIR.Symbol:
        for state in reversed(self.stack):
            if name in state.symbols:
                return state.symbols[name]

        raise DslException(f"Symbol `{name}` is not available in this scope")

    @contextmanager
    def temporary_alias(self, name: str, path: GenTypeGraphIR.FieldPath):
        assert self.stack, "Alias cannot be installed without an active scope"

        if self.is_symbol_defined(name):
            raise DslException(
                f"Alias `{name}` would shadow an existing symbol in scope"
            )

        state = self.current
        had_existing = name in state.aliases
        previous = state.aliases.get(name)
        state.aliases[name] = path
        try:
            yield
        finally:
            if had_existing:
                assert previous is not None
                state.aliases[name] = previous
            else:
                state.aliases.pop(name, None)

    def resolve_alias(self, name: str) -> GenTypeGraphIR.FieldPath | None:
        return self.current.aliases.get(name)

    @property
    def depth(self) -> int:
        return len(self.stack)

    def is_symbol_defined(self, name: str) -> bool:
        return any(name in state.symbols for state in self.stack)


class _TypeContextStack:
    """
    Maintains the current TypeGraph context while emitting IR.

    All structural lookups are delegated back to the TypeGraph so mounts, pointer
    sequences, and other graph semantics are resolved in one place.

    Translates any `TypeGraphPathError` into a user-facing `DslException` that
    preserves the enriched error metadata.
    """

    def __init__(
        self, graph: GraphView, type_graph: TypeGraph, state: BuildState
    ) -> None:
        self._stack: list[BoundNode] = []
        self._graph = graph
        self._type_graph = type_graph
        self._state = state

    @contextmanager
    def enter(self, type_node: BoundNode) -> Generator[None, None, None]:
        self._stack.append(type_node)
        try:
            yield
        finally:
            self._stack.pop()

    def current(self) -> BoundNode:
        if not self._stack:
            raise DslException("Type context is not available")
        return self._stack[-1]

    def apply_action(self, action) -> None:
        match action:
            case GenTypeGraphIR.AddMakeChildAction() as action:
                self._add_child(type_node=self.current(), action=action)
            case GenTypeGraphIR.AddMakeLinkAction() as action:
                self._add_link(type_node=self.current(), action=action)
            case list() | tuple() as actions:
                for a in actions:
                    self.apply_action(a)
                return
            case None:  # TODO: why would this be None?
                return
            case _:
                raise NotImplementedError(f"Unhandled action: {action}")

    def resolve_reference(
        self, path: GenTypeGraphIR.FieldPath, validate: bool = True
    ) -> BoundNode:
        return self._ensure_field_path(
            type_node=self.current(), field_path=path, validate=validate
        )

    @staticmethod
    def _format_path_error(
        field_path: GenTypeGraphIR.FieldPath, error: TypeGraphPathError
    ) -> str:
        full_path = ".".join(error.path) if error.path else str(field_path)

        match error.kind:
            # FIXME: enum or different types or format on Zig side
            case "missing_parent":
                prefix = error.path[: error.failing_segment_index]
                joined = ".".join(prefix) if prefix else full_path
                return f"Field `{joined}` is not defined in scope"
            case "invalid_index":
                container_segments = error.path[: error.failing_segment_index]
                container = ".".join(container_segments)
                index_value = (
                    error.index_value
                    if error.index_value is not None
                    else error.failing_segment
                )
                if container:
                    return f"Field `{container}[{index_value}]` is not defined in scope"
                return f"Field `[ {index_value} ]` is not defined in scope"
            case _:
                return f"Field `{full_path}` is not defined in scope"

    def _ensure_field_path(
        self,
        type_node: BoundNode,
        field_path: GenTypeGraphIR.FieldPath,
        validate: bool = True,
    ) -> BoundNode:
        identifiers = list(field_path.identifiers())
        try:
            return self._type_graph.ensure_child_reference(
                type_node=type_node,
                path=identifiers,
                validate=validate,
            )
        except TypeGraphPathError as exc:
            raise DslException(self._format_path_error(field_path, exc)) from exc

    def _add_child(
        self, type_node: BoundNode, action: GenTypeGraphIR.AddMakeChildAction
    ) -> None:
        if (parent_reference := action.parent_reference) is None and (
            parent_path := action.parent_path
        ) is not None:
            parent_reference = self._ensure_field_path(
                type_node=type_node, field_path=parent_path
            )

        child_spec = action.child_spec
        symbol = child_spec.symbol

        if (
            child_type_identifier := child_spec.type_identifier
        ) is None and symbol is not None:
            child_type_identifier = symbol.name

        assert child_type_identifier is not None

        make_child = self._type_graph.add_make_child(
            type_node=type_node,
            child_type_identifier=child_type_identifier,
            identifier=action.target_path.leaf.identifier,
            node_attributes=None,
            mount_reference=parent_reference,
        )

        type_reference = not_none(
            self._type_graph.get_make_child_type_reference(make_child=make_child)
        )

        if symbol is not None and symbol.import_ref:
            self._state.external_type_refs.append((type_reference, symbol.import_ref))
            return

        if (
            target := symbol.type_node if symbol is not None else child_spec.type_node
        ) is None:
            raise DslException(
                f"Type `{child_type_identifier}` is not defined in scope"
            )

        _Linker.link_type_reference(
            g=self._graph,
            type_reference=type_reference,
            target_type_node=target,
        )

    def _add_link(
        self, type_node: BoundNode, action: GenTypeGraphIR.AddMakeLinkAction
    ) -> None:
        self._type_graph.add_make_link(
            type_node=type_node,
            lhs_reference=action.lhs_ref,
            rhs_reference=action.rhs_ref,
            edge_attributes=EdgeInterfaceConnection.build(shallow=False),
        )


class BlockType(StrEnum):
    MODULE = "module"
    COMPONENT = "component"
    INTERFACE = "interface"


class is_ato_block(fabll.Node):
    """
    Indicates type origin and originating block type (module, component, interface)
    """

    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()
    block_type = fabll.Parameter.MakeChild()  # TODO: enum domain

    @classmethod
    def MakeChild_Module(cls) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            Is.MakeChild_ConstrainToLiteral(
                ref=[out, cls.block_type], value=BlockType.MODULE
            )
        )
        return out

    @classmethod
    def MakeChild_Component(cls) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            Is.MakeChild_ConstrainToLiteral([out, cls.block_type], BlockType.COMPONENT)
        )
        return out

    @classmethod
    def MakeChild_Interface(cls) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            Is.MakeChild_ConstrainToLiteral([out, cls.block_type], BlockType.INTERFACE)
        )
        return out


class ASTVisitor:
    """
    Generates a TypeGraph from the AST.

    Error handling strategy:
    - Fail early (TODO: revisit — return list of errors and let caller decide impact)
    - Use DslException for errors arising from code contents

    Responsibilities & boundaries:
    - Translate parsed AST nodes into high-level TypeGraph actions (e.g.
      creating fields, wiring connections, recording imports) without peeking
      into fabll/node semantics or mutating the TypeGraph directly.
    - Maintain only minimal lexical bookkeeping (detecting redeclarations,
      ensuring names are declared before reuse); structural validation and path
      resolution are delegated to the TypeGraph.
    - Defer cross-file linkage, stdlib loading, and part selection to the
      surrounding build/linker code. The visitor produces a `BuildState` that
      higher layers consume to finish linking.

    TODO: store graph references instead of reifying as IR?
    """

    class _Pragma(StrEnum):
        EXPERIMENT = "experiment"

    class _Experiments(StrEnum):
        BRIDGE_CONNECT = "BRIDGE_CONNECT"
        FOR_LOOP = "FOR_LOOP"
        TRAITS = "TRAITS"
        MODULE_TEMPLATING = "MODULE_TEMPLATING"
        INSTANCE_TRAITS = "INSTANCE_TRAITS"

    def __init__(
        self, ast_root: AST.File, graph: GraphView, file_path: Path | None
    ) -> None:
        self._ast_root = ast_root
        self._graph = graph
        self._type_graph = TypeGraph.create(g=graph)
        self._state = BuildState(
            type_graph=self._type_graph,
            type_roots={},
            external_type_refs=[],
            file_path=file_path,
        )

        # TODO: from "system" type graph
        pointer_sequence_type = Collections.PointerSequence.bind_typegraph(
            self._type_graph
        ).get_or_create_type()
        self._pointer_sequence_type = pointer_sequence_type
        self._pointer_sequence_type_identifier = Collections.PointerSequence.__name__
        self._experiments: set[ASTVisitor._Experiments] = set()
        self._scope_stack = _ScopeStack()
        self._type_stack = _TypeContextStack(
            graph=self._graph,
            type_graph=self._type_graph,
            state=self._state,
        )

    @staticmethod
    def _parse_pragma(pragma_text: str) -> tuple[str, list[str | int | float | bool]]:
        """
        pragma_stmt: '#pragma' function_call
        function_call: NAME '(' argument (',' argument)* ')'
        argument: literal
        literal: STRING | NUMBER | BOOLEAN

        returns (name, [arg1, arg2, ...])
        """
        import re

        _pragma = "#pragma"
        _function_name = r"(?P<function_name>\w+)"
        _string = r'"([^"]*)"'
        _int = r"(\d+)"
        _args_str = r"(?P<args_str>.*?)"

        pragma_syntax = re.compile(
            rf"^{_pragma}\s+{_function_name}\(\s*{_args_str}\s*\)$"
        )
        _individual_arg_pattern = re.compile(rf"{_string}|{_int}")
        match = pragma_syntax.match(pragma_text)

        if match is None:
            raise DslException(f"Malformed pragma: '{pragma_text}'")

        data = match.groupdict()
        name = data["function_name"]
        args_str = data["args_str"]
        found_args = _individual_arg_pattern.findall(args_str)
        arguments = [
            string_arg if string_arg is not None else int(int_arg)
            for string_arg, int_arg in found_args
        ]
        return name, arguments

    def enable_experiment(self, experiment: ASTVisitor._Experiments) -> None:
        print(f"Enabling experiment: {experiment}")
        self._experiments.add(experiment)

    def ensure_experiment(self, experiment: ASTVisitor._Experiments) -> None:
        if experiment not in self._experiments:
            raise DslException(f"Experiment {experiment} is not enabled")

    def build(self) -> BuildState:
        # must start with a File (for now)
        assert self._ast_root.isinstance(AST.File)
        self.visit(self._ast_root)
        return self._state

    def visit(self, node: fabll.Node):
        # TODO: less magic dispatch

        node_type = cast_assert(str, node.get_type_name())
        print(f"Visiting node of type {node_type}")

        try:
            handler = getattr(self, f"visit_{node_type}")
        except AttributeError:
            print(f"No handler for node type: {node_type}")
            # raise NotImplementedError(f"No handler for node type: {node_type}")
            return None

        bound_node = getattr(AST, node_type).bind_instance(node.instance)
        return handler(bound_node)

    def visit_File(self, node: AST.File):
        self.visit(node.scope.get())

    def visit_Scope(self, node: AST.Scope):
        with self._scope_stack.enter():
            for scope_child in node.stmts.get().as_list():
                self.visit(scope_child)

    def visit_PragmaStmt(self, node: AST.PragmaStmt):
        if (pragma_text := node.pragma.get().try_extract_constrained_literal()) is None:
            raise DslException(f"Pragma statement has no pragma text: {node}")

        pragma_text = cast_assert(str, pragma_text)
        pragma_func_name, pragma_args = self._parse_pragma(pragma_text)

        match pragma_func_name:
            case ASTVisitor._Pragma.EXPERIMENT.value:
                match pragma_args:
                    case [ASTVisitor._Experiments.BRIDGE_CONNECT]:
                        self.enable_experiment(ASTVisitor._Experiments.BRIDGE_CONNECT)
                    case [ASTVisitor._Experiments.FOR_LOOP]:
                        self.enable_experiment(ASTVisitor._Experiments.FOR_LOOP)
                    case [ASTVisitor._Experiments.TRAITS]:
                        self.enable_experiment(ASTVisitor._Experiments.TRAITS)
                    case [ASTVisitor._Experiments.MODULE_TEMPLATING]:
                        self.enable_experiment(
                            ASTVisitor._Experiments.MODULE_TEMPLATING
                        )
                    case [ASTVisitor._Experiments.INSTANCE_TRAITS]:
                        self.enable_experiment(ASTVisitor._Experiments.INSTANCE_TRAITS)
                    case _:
                        raise DslException(
                            f"Experiment not recognized: `{pragma_text}`"
                        )
            case _:
                raise DslException(f"Pragma function not recognized: `{pragma_text}`")

    def visit_ImportStmt(self, node: AST.ImportStmt):
        type_ref_name = cast_assert(
            str, node.type_ref.get().name.get().try_extract_constrained_literal()
        )

        path_literal = node.path.get().path.get().try_extract_constrained_literal()
        path = cast_assert(str, path_literal) if path_literal is not None else None
        import_ref = GenTypeGraphIR.ImportRef(name=type_ref_name, path=path)

        if path is None and type_ref_name not in STDLIB_ALLOWLIST:
            raise DslException(f"Standard library import not found: {type_ref_name}")

        self._scope_stack.add_symbol(
            GenTypeGraphIR.Symbol(name=type_ref_name, import_ref=import_ref)
        )

    def visit_BlockDefinition(self, node: AST.BlockDefinition):
        if self._scope_stack.depth != 1:
            raise DslException("Nested block definitions are not permitted")

        module_name = cast_assert(
            str,
            node.type_ref.get().name.get().try_extract_constrained_literal(),
        )

        if self._scope_stack.is_symbol_defined(module_name):
            raise DslException(f"Symbol `{module_name}` already defined in scope")

        match node.get_block_type():
            case AST.BlockDefinition.BlockType.MODULE:

                class _Module(fabll.Node):
                    is_ato_block = (
                        # TODO: link from other typegraph
                        is_ato_block.MakeChild_Module()
                    )

                _Block = _Module

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    is_ato_block = is_ato_block.MakeChild_Component()

                _Block = _Component

            case AST.BlockDefinition.BlockType.INTERFACE:

                class _Interface(fabll.Node):
                    is_ato_block = is_ato_block.MakeChild_Interface()

                _Block = _Interface

        _Block.__name__ = module_name
        _Block.__qualname__ = module_name

        type_node = _Block.bind_typegraph(self._type_graph).get_or_create_type()
        self._state.type_roots[module_name] = type_node

        with self._scope_stack.enter():
            with self._type_stack.enter(type_node):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))

        self._scope_stack.add_symbol(
            GenTypeGraphIR.Symbol(name=module_name, type_node=type_node)
        )

    def visit_PassStmt(self, node: AST.PassStmt):
        pass

    def visit_StringStmt(self, node: AST.StringStmt):
        # TODO: add docstring trait to preceding node
        pass

    def visit_FieldRef(self, node: AST.FieldRef) -> GenTypeGraphIR.FieldPath:
        segments: list[GenTypeGraphIR.FieldPath.Segment] = []

        for part_node in node.parts.get().as_list():
            part = part_node.cast(t=AST.FieldRefPart)
            name_literal = part.name.get().try_extract_constrained_literal()
            segments.append(
                GenTypeGraphIR.FieldPath.Segment(
                    identifier=cast_assert(str, name_literal)
                )
            )

            if (
                key_literal := part.key.get().try_extract_constrained_literal()
            ) is not None:
                if isinstance(key_literal, float):
                    assert key_literal.is_integer()
                    key_literal = int(key_literal)

                segments.append(
                    GenTypeGraphIR.FieldPath.Segment(
                        identifier=str(key_literal), is_index=True
                    )
                )

        if node.pin.get().try_extract_constrained_literal() is not None:
            raise NotImplementedError(
                "Field references with pin suffixes are not supported yet"
            )

        if not segments:
            raise DslException("Empty field reference encountered")

        # Alias rewrite (for-loop variable): if the root segment is an alias,
        # expand it to the aliased field path.
        if (
            aliased := self._scope_stack.resolve_alias(segments[0].identifier)
        ) is not None:
            # Replace root with alias path
            segments = list(aliased.segments) + segments[1:]

        return GenTypeGraphIR.FieldPath(segments=tuple(segments))

    def _handle_new_child(
        self,
        target_path: GenTypeGraphIR.FieldPath,
        new_spec: GenTypeGraphIR.NewChildSpec,
        parent_reference: BoundNode | None,
        parent_path: GenTypeGraphIR.FieldPath | None,
    ) -> list[GenTypeGraphIR.AddMakeChildAction] | GenTypeGraphIR.AddMakeChildAction:
        self._scope_stack.add_field(target_path)

        if new_spec.count is None:
            # TODO: review
            if target_path.leaf.is_index and parent_path is not None:
                try:
                    pointer_members = self._type_graph.iter_pointer_members(
                        type_node=self._type_stack.current(),
                        container_path=list(parent_path.identifiers()),
                    )
                except TypeGraphPathError as exc:
                    raise DslException(
                        self._type_stack._format_path_error(parent_path, exc)
                    ) from exc

                member_identifiers = {
                    identifier
                    for identifier, _ in pointer_members
                    if identifier is not None
                }

                if target_path.leaf.identifier not in member_identifiers:
                    raise DslException(f"Field `{target_path}` is not defined in scope")

            return GenTypeGraphIR.AddMakeChildAction(
                target_path=target_path,
                child_spec=new_spec,
                parent_reference=parent_reference,
                parent_path=parent_path,
            )

        pointer_action = GenTypeGraphIR.AddMakeChildAction(
            target_path=target_path,
            child_spec=GenTypeGraphIR.NewChildSpec(
                type_identifier=self._pointer_sequence_type_identifier,
                type_node=self._pointer_sequence_type,
            ),
            parent_reference=parent_reference,
            parent_path=parent_path,
        )

        element_spec = replace(new_spec, count=None)

        element_actions: list[GenTypeGraphIR.AddMakeChildAction] = []

        for idx in range(new_spec.count):
            element_path = GenTypeGraphIR.FieldPath(
                segments=(
                    *target_path.segments,
                    GenTypeGraphIR.FieldPath.Segment(
                        identifier=str(idx), is_index=True
                    ),
                )
            )

            self._scope_stack.add_field(element_path)
            element_actions.append(
                GenTypeGraphIR.AddMakeChildAction(
                    target_path=element_path,
                    child_spec=element_spec,
                    parent_reference=None,
                    parent_path=GenTypeGraphIR.FieldPath(segments=target_path.segments),
                )
            )

        return [pointer_action, *element_actions]

    def visit_Assignment(self, node: AST.Assignment):
        # TODO: broaden assignable support and handle keyed/pin field references

        target_path = self.visit_FieldRef(node.target.get())
        assignable = self.visit(node.assignable.get().get_value())

        parent_path: GenTypeGraphIR.FieldPath | None = None
        parent_reference: BoundNode | None = None

        if target_path.parent_segments:
            parent_path = GenTypeGraphIR.FieldPath(
                segments=tuple(target_path.parent_segments)
            )

            if not self._scope_stack.has_field(parent_path):
                raise DslException(f"Field `{parent_path}` is not defined in scope")

            parent_reference = self._type_stack.resolve_reference(parent_path)

        if self._scope_stack.has_field(target_path):
            raise DslException(
                f"Field `{target_path}` is already defined in this scope"
            )

        match assignable:
            case GenTypeGraphIR.NewChildSpec() as new_spec:
                return self._handle_new_child(
                    target_path, new_spec, parent_reference, parent_path
                )
            case _:
                raise NotImplementedError(f"Unhandled assignable type: {assignable}")

    def visit_NewExpression(self, node: AST.NewExpression):
        type_name = cast_assert(
            str, node.type_ref.get().name.get().try_extract_constrained_literal()
        )
        symbol = self._scope_stack.resolve_symbol(type_name)
        count: int | None = None

        if (
            count_literal := node.new_count.get()
            .value.get()
            .try_extract_constrained_literal()
        ) is not None:
            assert count_literal.is_integer()
            count = int(count_literal)

        return GenTypeGraphIR.NewChildSpec(
            symbol=symbol,
            type_identifier=symbol.name,
            type_node=symbol.type_node,
            count=count,
        )

        # TODO: handle template args

    def visit_ConnectStmt(self, node: AST.ConnectStmt):
        lhs, rhs = node.get_lhs(), node.get_rhs()

        # TODO: handle connectables other than field refs
        if not lhs.isinstance(AST.FieldRef):
            raise NotImplementedError("Unhandled connectable type for LHS")
        if not rhs.isinstance(AST.FieldRef):
            raise NotImplementedError("Unhandled connectable type for RHS")

        lhs_path = self.visit_FieldRef(lhs.cast(t=AST.FieldRef))
        rhs_path = self.visit_FieldRef(rhs.cast(t=AST.FieldRef))

        def _ensure_reference(path: GenTypeGraphIR.FieldPath) -> BoundNode:
            (root, *_) = path.segments
            root_path = GenTypeGraphIR.FieldPath(segments=(root,))

            if not self._scope_stack.has_field(root_path):
                raise DslException(f"Field `{root_path}` is not defined in scope")

            return self._type_stack.resolve_reference(path, validate=False)

        lhs_ref = _ensure_reference(lhs_path)
        rhs_ref = _ensure_reference(rhs_path)

        return GenTypeGraphIR.AddMakeLinkAction(lhs_ref=lhs_ref, rhs_ref=rhs_ref)

    @staticmethod
    def _select_elements(
        iterable_field: AST.IterableFieldRef,
        sequence_elements: list[GenTypeGraphIR.FieldPath],
    ) -> list[GenTypeGraphIR.FieldPath]:
        def _extract_slice_value(attr: fabll.ChildField[AST.Number]) -> int | None:
            if (
                value_literal := attr.get()
                .value.get()
                .try_extract_constrained_literal()
            ) is None:
                return None

            return int(value_literal)

        if (slice_node := iterable_field.slice.get()) is None:
            return sequence_elements

        start_idx, stop_idx, step_idx = (
            _extract_slice_value(slice_node.start),
            _extract_slice_value(slice_node.stop),
            _extract_slice_value(slice_node.step),
        )

        if step_idx == 0:
            raise DslException("Slice step cannot be zero")

        return sequence_elements[slice(start_idx, stop_idx, step_idx)]

    def _pointer_member_paths(
        self, container_path: GenTypeGraphIR.FieldPath
    ) -> list[GenTypeGraphIR.FieldPath]:
        try:
            pointer_members = self._type_graph.iter_pointer_members(
                type_node=self._type_stack.current(),
                container_path=list(container_path.identifiers()),
            )
        except TypeGraphPathError as exc:
            raise DslException(
                self._type_stack._format_path_error(container_path, exc)
            ) from exc

        return [
            GenTypeGraphIR.FieldPath(
                segments=(
                    *container_path.segments,
                    GenTypeGraphIR.FieldPath.Segment(
                        identifier=identifier,
                        is_index=identifier.isdigit(),
                    ),
                )
            )
            for identifier in [
                identifier
                for identifier, _ in pointer_members
                if identifier is not None
            ]
        ]

    def visit_ForStmt(self, node: AST.ForStmt):
        self.ensure_experiment(ASTVisitor._Experiments.FOR_LOOP)

        iterable_node = node.iterable.get().get_value()
        item_paths: list[GenTypeGraphIR.FieldPath]

        if iterable_node.isinstance(AST.FieldRefList):
            list_node = iterable_node.cast(t=AST.FieldRefList)
            items = list_node.items.get().as_list()
            item_paths = [
                self.visit_FieldRef(item_ref.cast(t=AST.FieldRef)) for item_ref in items
            ]

        elif iterable_node.isinstance(AST.IterableFieldRef):
            iterable_field = iterable_node.cast(t=AST.IterableFieldRef)
            container_path = self.visit_FieldRef(iterable_field.field.get())
            member_paths = self._pointer_member_paths(container_path)

            selected = self._select_elements(iterable_field, member_paths)
            item_paths = list(selected)
        else:
            raise DslException("Unexpected iterable type")

        target_literal = node.target.get().try_extract_constrained_literal()
        loop_var = cast_assert(str, target_literal)

        # Execute body for each item by aliasing the loop var to the item's path
        for item_path in item_paths:
            with self._scope_stack.temporary_alias(loop_var, item_path):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))


@dataclass
class BuildFileResult:
    ast_root: AST.File
    state: BuildState


def _build_from_ctx(
    graph: GraphView, root_ctx: AtoParser.File_inputContext, file_path: Path | None
) -> BuildFileResult:
    ast_type_graph = TypeGraph.create(g=graph)
    ast_root = ANTLRVisitor(graph, ast_type_graph, file_path).visit(root_ctx)
    assert isinstance(ast_root, AST.File)
    build_state = ASTVisitor(ast_root, graph, file_path).build()
    return BuildFileResult(ast_root=ast_root, state=build_state)


def build_file(graph: GraphView, path: Path) -> BuildFileResult:
    # TODO: per-file caching
    return _build_from_ctx(graph, parse_file(path), path)


def build_source(graph: GraphView, source: str) -> BuildFileResult:
    return _build_from_ctx(graph, parse_text_as_file(source), file_path=None)


class Linker:
    @staticmethod
    def _resolve_import_path(base_file: Path | None, raw_path: str) -> Path:
        # TODO: include all search paths
        # TODO: get base dirs from config
        search_paths = [
            *([base_file.parent] if base_file is not None else []),
            Path(".ato/modules"),
        ]

        for search_path in search_paths:
            if (candidate := search_path / raw_path).exists():
                return candidate

        raise DslException(f"Import path not found: `{raw_path}`")

    @staticmethod
    def link_imports(
        graph: GraphView,
        build_state: BuildState,
        stdlib_registry: dict[str, BoundNode],
        stdlib_tg: TypeGraph,
    ) -> None:
        # TODO: handle cycles

        for type_reference, import_ref in build_state.external_type_refs:
            if import_ref.path is None:
                target_type_node = stdlib_registry[import_ref.name]

            else:
                source_path = Linker._resolve_import_path(
                    base_file=build_state.file_path, raw_path=import_ref.path
                )
                assert source_path.exists()

                child_result = build_file(graph, source_path)
                Linker.link_imports(
                    graph, child_result.state, stdlib_registry, stdlib_tg
                )
                target_type_node = child_result.state.type_roots[import_ref.name]

            _Linker.link_type_reference(
                g=graph,
                type_reference=type_reference,
                target_type_node=target_type_node,
            )

        if build_state.type_graph.collect_unresolved_type_references():
            raise DslException("Unresolved type references remaining after linking")


def build_stdlib(graph: GraphView) -> tuple[TypeGraph, dict[str, BoundNode]]:
    tg = TypeGraph.create(g=graph)
    registry: dict[str, BoundNode] = {}

    for name, obj in STDLIB_ALLOWLIST.items():
        type_node = obj.bind_typegraph(tg).get_or_create_type()
        registry[name] = type_node

    return tg, registry
