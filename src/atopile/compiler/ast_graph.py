"""
Generates an AST graph from the ANTLR4-generated AST.

Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
"""

from __future__ import annotations

import itertools
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from antlr4.tree.Tree import TerminalNodeImpl

import atopile.compiler.ast_types as AST
from atopile.compiler.graph_mock import BoundNode, NodeHelpers
from atopile.compiler.parse import parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.core.fabll import NodeType
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import GraphView


class ANTLRVisitor(AtoParserVisitor):
    """
    Generates a native AST graph from the ANTLR4-generated AST, with attached
    source context.
    """

    def __init__(
        self, graph: GraphView, type_graph: TypeGraph, file_path: Path
    ) -> None:
        super().__init__()
        self._graph = graph
        self._type_graph = type_graph
        self._file_path = file_path

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
            start_column=start_token.column,  # type: ignore
            end_line=stop_token.line,  # type: ignore
            end_column=stop_token.column,  # type: ignore
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

    def visitType_reference(self, ctx: AtoParser.Type_referenceContext) -> str:
        return self.visitName(ctx.name())

    def visitArray_index(self, ctx: AtoParser.Array_indexContext) -> str | int | None:
        if key := ctx.key():
            return self.visitKey(key)

    def visitKey(self, ctx: AtoParser.KeyContext) -> int:
        return self.visitNumber_hint_integer(ctx.number_hint_integer())

    def visitStmt(self, ctx: AtoParser.StmtContext) -> Iterable[NodeType]:
        match (ctx.pragma_stmt(), ctx.simple_stmts(), ctx.compound_stmt()):
            case (pragma_stmt, None, None):
                return [self.visitPragma_stmt(pragma_stmt)]
            case (None, simple_stmts, None):
                return self.visitSimple_stmts(simple_stmts)
            case (None, None, compound_stmt):
                return [self.visitCompound_stmt(compound_stmt)]
            case _:
                assert False, f"Unexpected statement: {ctx.getText()}"

    def visitStmts(self, ctx: AtoParser.StmtsContext) -> Iterable[NodeType]:
        return itertools.chain.from_iterable(
            (child for child in self.visitStmt(child) if child is not None)
            for child in ctx
        )

    def visitBlock(self, ctx: AtoParser.BlockContext) -> Iterable[NodeType]:
        stmts = []

        if ctx.stmt() is not None:
            for stmt_ctx in ctx.stmt():
                if stmt_ctx is not None:
                    stmts.extend(self.visitStmt(stmt_ctx))

        if ctx.simple_stmts() is not None:
            for simple_stmt_ctx in ctx.simple_stmts():
                if simple_stmt_ctx is not None:
                    stmts.extend(self.visitSimple_stmts(simple_stmt_ctx))

        # stnts = itertools.chain.from_iterable(
        #     (
        #         (child for child in self.visitStmts(ctx.stmt()) if child is not None),
        #         (
        #             child
        #             for child in (
        #                 self.visitSimple_stmts(ctx.simple_stmts())
        #                 if ctx.simple_stmts()
        #                 else []
        #             )
        #             if child is not None
        #         ),
        #     )
        # )

        # print("block", stnts)
        return stmts

    def visitBlockdef(self, ctx: AtoParser.BlockdefContext) -> NodeType:
        return AST.BlockDefinition.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            block_type=ctx.blocktype().getText(),
            type_ref_name=self.visitType_reference(ctx.type_reference()),
            type_ref_source_info=self._extract_source_info(ctx.type_reference()),
            super_type_ref_name=(
                self.visitType_reference(ctx.blockdef_super().type_reference())
                if ctx.blockdef_super()
                else None
            ),
            super_type_ref_source_info=(
                self._extract_source_info(ctx.blockdef_super().type_reference())
                if ctx.blockdef_super()
                else None
            ),
            child_stmts=self.visitBlock(ctx.block()),
        )

    def visitFile_input(self, ctx: AtoParser.File_inputContext) -> AST.File:
        return AST.File.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            path=str(self._file_path),
            child_stmts=self.visitStmts(ctx.stmt()),
        )

    def visitSimple_stmts(
        self, ctx: AtoParser.Simple_stmtsContext
    ) -> Iterable[NodeType]:
        return itertools.chain.from_iterable(
            (
                child
                if (isinstance(child, Iterable) and not isinstance(child, str))
                else [child]
                for child in (self.visit(child) for child in ctx.simple_stmt())
            )
        )

    def visitSimple_stmt(self, ctx: AtoParser.Simple_stmtContext) -> NodeType:
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

    def visitCompound_stmt(self, ctx: AtoParser.Compound_stmtContext) -> NodeType:
        match (ctx.blockdef(), ctx.for_stmt()):
            case (blockdef_ctx, None):
                return self.visitBlockdef(blockdef_ctx)
            case (None, for_ctx):
                return self.visitFor_stmt(for_ctx)
            case _:
                raise ValueError(f"Unexpected compound statement: {ctx.getText()}")

    def visitPragma_stmt(self, ctx: AtoParser.Pragma_stmtContext) -> AST.PragmaStmt:
        return AST.PragmaStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            pragma=self.visit(ctx.PRAGMA()),
        )

    def visitImport_stmt(self, ctx: AtoParser.Import_stmtContext) -> AST.ImportStmt:
        return AST.ImportStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            path=self.visitString(ctx.string()) if ctx.string() else None,
            path_source_info=self._extract_source_info(ctx.string())
            if ctx.string()
            else None,
            type_ref_name=self.visitType_reference(ctx.type_reference()),
            type_ref_source_info=self._extract_source_info(ctx.type_reference()),
        )

    def visitRetype_stmt(self, ctx: AtoParser.Retype_stmtContext) -> AST.RetypeStmt:
        field_parts, field_source = self._field_ref_parts_from_ctx(
            ctx.field_reference()
        )
        type_ref_ctx = ctx.type_reference()
        return AST.RetypeStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            field_ref_parts=field_parts,
            field_ref_source_info=field_source,
            type_ref_name=self.visitType_reference(type_ref_ctx),
            type_ref_source_info=self._extract_source_info(type_ref_ctx),
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
                label_value = self.visitString(string_ctx)
            case _:
                raise ValueError(f"Unexpected pin statement: {ctx.getText()}")

        return AST.PinDeclaration.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            kind=kind,
            label_value=label_value,
        )

    def visitSignaldef_stmt(
        self, ctx: AtoParser.Signaldef_stmtContext
    ) -> AST.SignaldefStmt:
        return AST.SignaldefStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            name=self.visitName(ctx.name()),
        )

    def visitString_stmt(self, ctx: AtoParser.String_stmtContext) -> AST.StringStmt:
        return AST.StringStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            string_value=self.visitString(ctx.string()),
            string_source_info=self._extract_source_info(ctx.string()),
        )

    def visitField_reference_or_declaration(
        self, ctx: AtoParser.Field_reference_or_declarationContext
    ) -> NodeType:
        if (field_ref_ctx := ctx.field_reference()) is not None:
            return self._build_field_ref(field_ref_ctx)
        if (decl_stmt_ctx := ctx.declaration_stmt()) is not None:
            return self.visitDeclaration_stmt(decl_stmt_ctx)
        raise ValueError(f"Unexpected field reference or declaration: {ctx.getText()}")

    def visitPass_stmt(self, ctx: AtoParser.Pass_stmtContext) -> AST.PassStmt:
        return AST.PassStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
        )

    def visitAssert_stmt(self, ctx: AtoParser.Assert_stmtContext) -> AST.AssertStmt:
        return AST.AssertStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            comparison=self.visitComparison(ctx.comparison()),
        )

    def visitTrait_stmt(self, ctx: AtoParser.Trait_stmtContext) -> AST.TraitStmt:
        target_parts: list[AST.FieldRefPart.Info] | None = None
        target_source_info: AST.SourceInfo | None = None
        if ctx.field_reference() is not None:
            target_parts, target_source_info = self._field_ref_parts_from_ctx(
                ctx.field_reference()
            )

        template_data = (
            self.visitTemplate(ctx.template()) if ctx.template() is not None else None
        )

        constructor = (
            self.visitConstructor(ctx.constructor())
            if ctx.constructor() is not None
            else None
        )

        type_ref_ctx = ctx.type_reference()

        return AST.TraitStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            type_ref_name=self.visitType_reference(type_ref_ctx),
            type_ref_source_info=self._extract_source_info(type_ref_ctx),
            target_parts=target_parts,
            target_source_info=target_source_info,
            template_data=template_data,
            constructor=constructor,
        )

    def visitConstructor(self, ctx: AtoParser.ConstructorContext) -> str:
        return self.visitName(ctx.name())

    def visitFor_stmt(self, ctx: AtoParser.For_stmtContext) -> AST.ForStmt:
        iterable = self.visitIterable_references(ctx.iterable_references())
        body_nodes = list(self.visitBlock(ctx.block()))
        return AST.ForStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            target=self.visitName(ctx.name()),
            iterable=iterable,
            body_stmts=body_nodes,
        )

    def visitIterable_references(
        self, ctx: AtoParser.Iterable_referencesContext
    ) -> NodeType:
        match [ctx.field_reference(), ctx.list_literal_of_field_references()]:
            case [field_ref_ctx, None]:
                field_parts, field_source_info = self._field_ref_parts_from_ctx(
                    field_ref_ctx
                )
                slice_config = (
                    self.visitSlice(ctx.slice_()) if ctx.slice_() is not None else None
                )
                return AST.IterableFieldRef.create_instance(
                    tg=self._type_graph,
                    g=self._graph,
                    source_info=self._extract_source_info(ctx),
                    field_parts=field_parts,
                    field_source_info=field_source_info,
                    slice_config=slice_config,
                )
            case [None, list_literal_ctx]:
                return self.visitList_literal_of_field_references(list_literal_ctx)
            case _:
                raise ValueError(f"Unexpected iterable references: {ctx.getText()}")

    def visitList_literal_of_field_references(
        self, ctx: AtoParser.List_literal_of_field_referencesContext
    ) -> AST.FieldRefList:
        items = [self._build_field_ref(fr) for fr in ctx.field_reference()]
        return AST.FieldRefList.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            items=items,
        )

    def visitSlice(self, ctx: AtoParser.SliceContext) -> AST.SliceConfig:
        start = (
            self.visitSlice_start(ctx.slice_start())
            if ctx.slice_start() is not None
            else None
        )
        stop = (
            self.visitSlice_stop(ctx.slice_stop())
            if ctx.slice_stop() is not None
            else None
        )
        step = (
            self.visitSlice_step(ctx.slice_step())
            if ctx.slice_step() is not None
            else None
        )
        return AST.SliceConfig(
            source=self._extract_source_info(ctx),
            start=start,
            stop=stop,
            step=step,
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

    def _field_ref_parts_from_ctx(
        self, ctx: AtoParser.Field_referenceContext
    ) -> tuple[list[AST.FieldRefPart.Info], AST.SourceInfo]:
        parts = [
            self.visitField_reference_part(part_ctx)
            for part_ctx in ctx.field_reference_part()
        ]
        return parts, self._extract_source_info(ctx)

    def _build_field_ref(self, ctx: AtoParser.Field_referenceContext) -> AST.FieldRef:
        parts, source_info = self._field_ref_parts_from_ctx(ctx)
        return AST.FieldRef.create_instance(
            tg=self._type_graph, g=self._graph, source_info=source_info, parts=parts
        )

    def visitField_reference(
        self, ctx: AtoParser.Field_referenceContext
    ) -> AST.FieldRef:
        return self._build_field_ref(ctx)

    class _AssignableType(StrEnum):
        NEW = "new"
        QUANTITY = "quantity"
        ARITHMETIC = "arithmetic"
        STRING = "string"
        BOOLEAN = "boolean"

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

        return AST.Assignment.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            target_field_ref_parts=field_ref_parts,
            target_field_ref_source_info=field_ref_source_info,  # FIXME
            assignable_value=self.visitAssignable(ctx.assignable()),
            assignable_source_info=self._extract_source_info(ctx.assignable()),
        )

    def visitAssignable(self, ctx: AtoParser.AssignableContext) -> NodeType:
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
                value = AST.String.create_instance(
                    tg=self._type_graph,
                    g=self._graph,
                    source_info=self._extract_source_info(string_ctx),
                    text=self.visitString(string_ctx),
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
        new_count_data = None
        if ctx.new_count() is not None:
            new_count_data = (
                self.visitNumber_hint_natural(ctx.new_count().number_hint_natural()),
                self._extract_source_info(ctx.new_count()),
            )
        return AST.NewExpression.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            type_ref_name=self.visitType_reference(ctx.type_reference()),
            type_ref_source_info=self._extract_source_info(ctx.type_reference()),
            template=template_data,
            new_count=new_count_data,
        )

    def visitLiteral_physical(self, ctx: AtoParser.Literal_physicalContext) -> NodeType:
        match ctx.quantity(), ctx.bilateral_quantity(), ctx.bound_quantity():
            case (quantity_ctx, None, None):
                return self._build_quantity(quantity_ctx)
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
    ) -> NodeType:
        right = self.visitSum(ctx.sum_())

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

            left = self.visitArithmetic_expression(ctx.arithmetic_expression())
            return AST.BinaryExpression.create_instance(
                tg=self._type_graph,
                g=self._graph,
                source_info=self._extract_source_info(ctx),
                operator=operator,
                left=left,
                right=right,
            )

        return right

    def visitSum(self, ctx: AtoParser.SumContext) -> NodeType:
        right = self.visitTerm(ctx.term())

        if ctx.sum_() is not None:
            match [ctx.PLUS(), ctx.MINUS()]:
                case [plus_token, None]:
                    operator = plus_token.getText()
                case [None, minus_token]:
                    operator = minus_token.getText()
                case _:
                    raise ValueError(f"Unexpected sum operator: {ctx.getText()}")

            left = self.visitSum(ctx.sum_())
            return AST.BinaryExpression.create_instance(
                tg=self._type_graph,
                g=self._graph,
                source_info=self._extract_source_info(ctx),
                operator=operator,
                left=left,
                right=right,
            )

        return right

    def visitTerm(self, ctx: AtoParser.TermContext) -> NodeType:
        right = self.visitPower(ctx.power())

        if ctx.term() is not None:
            match [ctx.STAR(), ctx.DIV()]:
                case [star_token, None]:
                    operator = star_token.getText()
                case [None, div_token]:
                    operator = div_token.getText()
                case _:
                    raise ValueError(f"Unexpected term operator: {ctx.getText()}")

            left = self.visitTerm(ctx.term())
            return AST.BinaryExpression.create_instance(
                tg=self._type_graph,
                g=self._graph,
                source_info=self._extract_source_info(ctx),
                operator=operator,
                left=left,
                right=right,
            )

        return right

    def visitPower(self, ctx: AtoParser.PowerContext) -> NodeType:
        atoms = [self.visitAtom(atom_ctx) for atom_ctx in ctx.atom()]
        match atoms:
            case [base, exponent]:
                return AST.BinaryExpression.create_instance(
                    tg=self._type_graph,
                    g=self._graph,
                    source_info=self._extract_source_info(ctx),
                    operator=ctx.POWER().getText(),
                    left=base,
                    right=exponent,
                )
            case [single]:
                return single
            case _:
                raise ValueError(f"Unexpected power context: {ctx.getText()}")

    def visitArithmetic_group(
        self, ctx: AtoParser.Arithmetic_groupContext
    ) -> AST.GroupExpression:
        return AST.GroupExpression.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            expression=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitAtom(self, ctx: AtoParser.AtomContext) -> NodeType:
        if (field_ref_ctx := ctx.field_reference()) is not None:
            return self._build_field_ref(field_ref_ctx)
        if (literal_ctx := ctx.literal_physical()) is not None:
            return self.visitLiteral_physical(literal_ctx)
        if (group_ctx := ctx.arithmetic_group()) is not None:
            return self.visitArithmetic_group(group_ctx)
        raise ValueError(f"Unexpected atom context: {ctx.getText()}")

    def visitComparison(
        self, ctx: AtoParser.ComparisonContext
    ) -> AST.ComparisonExpression:
        clauses = [
            self.visitCompare_op_pair(pair_ctx) for pair_ctx in ctx.compare_op_pair()
        ]
        return AST.ComparisonExpression.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            left=self.visitArithmetic_expression(ctx.arithmetic_expression()),
            clauses=clauses,
        )

    def visitCompare_op_pair(
        self, ctx: AtoParser.Compare_op_pairContext
    ) -> AST.ComparisonClause:
        if (lt_ctx := ctx.lt_arithmetic_or()) is not None:
            return self.visitLt_arithmetic_or(lt_ctx)
        if (gt_ctx := ctx.gt_arithmetic_or()) is not None:
            return self.visitGt_arithmetic_or(gt_ctx)
        if (lt_eq_ctx := ctx.lt_eq_arithmetic_or()) is not None:
            return self.visitLt_eq_arithmetic_or(lt_eq_ctx)
        if (gt_eq_ctx := ctx.gt_eq_arithmetic_or()) is not None:
            return self.visitGt_eq_arithmetic_or(gt_eq_ctx)
        if (in_ctx := ctx.in_arithmetic_or()) is not None:
            return self.visitIn_arithmetic_or(in_ctx)
        if (is_ctx := ctx.is_arithmetic_or()) is not None:
            return self.visitIs_arithmetic_or(is_ctx)
        raise ValueError(f"Unexpected compare op pair context: {ctx.getText()}")

    def visitLt_arithmetic_or(
        self, ctx: AtoParser.Lt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return AST.ComparisonClause.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.LESS_THAN().getText(),
            right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitGt_arithmetic_or(
        self, ctx: AtoParser.Gt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return AST.ComparisonClause.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.GREATER_THAN().getText(),
            right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitLt_eq_arithmetic_or(
        self, ctx: AtoParser.Lt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return AST.ComparisonClause.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.LT_EQ().getText(),
            right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitGt_eq_arithmetic_or(
        self, ctx: AtoParser.Gt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return AST.ComparisonClause.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.GT_EQ().getText(),
            right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitIn_arithmetic_or(
        self, ctx: AtoParser.In_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return AST.ComparisonClause.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.WITHIN().getText(),
            right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitIs_arithmetic_or(
        self, ctx: AtoParser.Is_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return AST.ComparisonClause.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            operator=ctx.IS().getText(),
            right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitQuantity(
        self, ctx: AtoParser.QuantityContext
    ) -> tuple[int | float, str | None]:
        number = self.visitNumber(ctx.number())
        unit = self.visitUnit(ctx.unit()) if ctx.unit() else None
        return number, unit

    def _build_quantity(self, ctx: AtoParser.QuantityContext) -> AST.Quantity:
        value, unit_symbol = self.visitQuantity(ctx)
        unit_data: tuple[str, AST.SourceInfo] | None = None
        if unit_symbol is not None and ctx.unit() is not None:
            unit_data = (unit_symbol, self._extract_source_info(ctx.unit()))
        return AST.Quantity.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            value=value,
            value_source_info=self._extract_source_info(ctx.number()),
            unit=unit_data,
        )

    def visitUnit(self, ctx: AtoParser.UnitContext) -> str:
        return self.visitName(ctx.name())

    def _parse_boolean_literal(self, ctx: AtoParser.Boolean_Context) -> bool:
        if ctx.TRUE() is not None:
            return True
        if ctx.FALSE() is not None:
            return False
        raise ValueError(f"Unexpected boolean literal: {ctx.getText()}")

    def _literal_value(self, ctx: AtoParser.LiteralContext) -> AST.LiteralT:
        if (string_ctx := ctx.string()) is not None:
            return self.visitString(string_ctx)
        if (boolean_ctx := ctx.boolean_()) is not None:
            return self._parse_boolean_literal(boolean_ctx)
        if (number_ctx := ctx.number()) is not None:
            return self.visitNumber(number_ctx)
        raise ValueError(f"Unexpected literal: {ctx.getText()}")

    def visitDeclaration_stmt(
        self, ctx: AtoParser.Declaration_stmtContext
    ) -> AST.DeclarationStmt:
        field_parts, field_source = self._field_ref_parts_from_ctx(
            ctx.field_reference()
        )
        unit_symbol = self.visitUnit(ctx.unit())
        unit_source = self._extract_source_info(ctx.unit())
        return AST.DeclarationStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            field_ref_parts=field_parts,
            field_ref_source_info=field_source,
            unit_symbol=unit_symbol,
            unit_source_info=unit_source,
        )

    def visitBilateral_quantity(
        self, ctx: AtoParser.Bilateral_quantityContext
    ) -> AST.BilateralQuantity:
        quantity_ctx = ctx.quantity()
        quantity_value, quantity_unit = self.visitQuantity(quantity_ctx)
        quantity_value_source = self._extract_source_info(quantity_ctx.number())
        quantity_unit_source = (
            self._extract_source_info(quantity_ctx.unit())
            if quantity_ctx.unit() is not None
            else None
        )

        (
            tolerance_value,
            tolerance_unit,
            tolerance_value_source,
            tolerance_unit_source,
        ) = self.visitBilateral_tolerance(ctx.bilateral_tolerance())

        return AST.BilateralQuantity.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            quantity_value=quantity_value,
            quantity_unit=quantity_unit,
            quantity_source_info=self._extract_source_info(ctx.quantity()),
            quantity_value_source_info=quantity_value_source,
            quantity_unit_source_info=quantity_unit_source,
            tolerance_value=tolerance_value,
            tolerance_unit=tolerance_unit,
            tolerance_source_info=self._extract_source_info(ctx.bilateral_tolerance()),
            tolerance_value_source_info=tolerance_value_source,
            tolerance_unit_source_info=tolerance_unit_source,
        )

    def visitBilateral_tolerance(
        self, ctx: AtoParser.Bilateral_toleranceContext
    ) -> tuple[int | float, str | None, AST.SourceInfo, AST.SourceInfo | None]:
        number = self.visitNumber_signless(ctx.number_signless())
        number_source = self._extract_source_info(ctx.number_signless())

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

        return number, unit, number_source, unit_source

    def visitBound_quantity(
        self, ctx: AtoParser.Bound_quantityContext
    ) -> AST.BoundedQuantity:
        start_ctx, end_ctx = ctx.quantity()
        start_value, start_unit = self.visitQuantity(start_ctx)
        end_value, end_unit = self.visitQuantity(end_ctx)
        start_value_source = self._extract_source_info(start_ctx.number())
        start_unit_source = (
            self._extract_source_info(start_ctx.unit())
            if start_ctx.unit() is not None
            else None
        )
        end_value_source = self._extract_source_info(end_ctx.number())
        end_unit_source = (
            self._extract_source_info(end_ctx.unit())
            if end_ctx.unit() is not None
            else None
        )
        return AST.BoundedQuantity.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            start_value=start_value,
            start_unit=start_unit,
            start_source_info=self._extract_source_info(start_ctx),
            start_value_source_info=start_value_source,
            start_unit_source_info=start_unit_source,
            end_value=end_value,
            end_unit=end_unit,
            end_source_info=self._extract_source_info(end_ctx),
            end_value_source_info=end_value_source,
            end_unit_source_info=end_unit_source,
        )

    def visitTemplate(
        self, ctx: AtoParser.TemplateContext
    ) -> tuple[AST.SourceInfo, list[AST.TemplateArg]]:
        args = [self.visitTemplate_arg(arg_ctx) for arg_ctx in ctx.template_arg()]
        return self._extract_source_info(ctx), args

    def visitTemplate_arg(self, ctx: AtoParser.Template_argContext) -> AST.TemplateArg:
        return AST.TemplateArg.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            name=self.visitName(ctx.name()),
            value=self._literal_value(ctx.literal()),
        )

    def visitTerminal(self, node: TerminalNodeImpl) -> str:
        return node.getText()

    def visitString(self, ctx: AtoParser.StringContext) -> str:
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

        return text

    def visitBoolean_(self, ctx: AtoParser.Boolean_Context) -> AST.Boolean:
        value = self._parse_boolean_literal(ctx)
        return AST.Boolean.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            value=value,
        )

    def visitNumber_signless(
        self, ctx: AtoParser.Number_signlessContext
    ) -> int | float:
        return self._parse_decimal(ctx.getText())

    def visitNumber(self, ctx: AtoParser.NumberContext) -> int | float:
        return self._parse_decimal(ctx.getText())

    def visitNumber_hint_natural(
        self, ctx: AtoParser.Number_hint_naturalContext
    ) -> int:
        return self._parse_int(ctx.getText())

    def visitNumber_hint_integer(
        self, ctx: AtoParser.Number_hint_integerContext
    ) -> int:
        return self._parse_int(ctx.getText())

    def visitMif(self, ctx: AtoParser.MifContext) -> NodeType:
        return self.visitConnectable(ctx.connectable())

    def visitBridgeable(self, ctx: AtoParser.BridgeableContext) -> NodeType:
        return self.visitConnectable(ctx.connectable())

    def visitConnectable(self, ctx: AtoParser.ConnectableContext) -> NodeType:
        match ctx.field_reference(), ctx.signaldef_stmt(), ctx.pindef_stmt():
            case (field_ref_ctx, None, None):
                return self._build_field_ref(field_ref_ctx)
            case (None, signaldef_stmt_ctx, None):
                return self.visitSignaldef_stmt(signaldef_stmt_ctx)
            case (None, None, pindef_stmt_ctx):
                return self.visitPindef_stmt(pindef_stmt_ctx)
            case _:
                raise ValueError(f"Unexpected connectable: {ctx.getText()}")

    def visitConnect_stmt(self, ctx: AtoParser.Connect_stmtContext) -> AST.ConnectStmt:
        left, right = [self.visitMif(mif_ctx) for mif_ctx in ctx.mif()]
        return AST.ConnectStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            left=left,
            right=right,
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
            case [single]:
                nested = ctx.directed_connect_stmt()
                if nested is None:
                    raise ValueError(
                        "Directed connect statement missing RHS for chained syntax"
                    )
                left = single
                right = self.visitDirected_connect_stmt(nested)
            case [first, second]:
                left, right = first, second
            case _:
                raise ValueError(f"Unexpected bridgeables: {ctx.getText()}")

        return AST.DirectedConnectStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            direction=direction,
            left=left,
            right=right,
        )


class DslException(Exception): ...


class ASTVisitor:
    """
    Generates a TypeGraph from the AST.
    """

    @dataclass
    class _ScopeState:
        symbols: set[str] = field(default_factory=set)

    class _ScopeStack:
        stack: list[ASTVisitor._ScopeState]

        def __init__(self) -> None:
            self.stack = []

        @contextmanager
        def enter(self) -> Generator[ASTVisitor._ScopeState, None, None]:
            state = ASTVisitor._ScopeState()
            self.stack.append(state)
            try:
                yield state
            finally:
                self.stack.pop()

        def add_symbol(self, symbol: str) -> None:
            # TODO: think about this

            current_state = self.stack[-1]
            if symbol in current_state.symbols:
                raise DslException(f"Symbol {symbol} already defined in scope")

            current_state.symbols.add(symbol)

            print(f"Added symbol {symbol} to scope")

    class _Pragma(StrEnum):
        EXPERIMENT = "experiment"

    class _Experiments(StrEnum):
        BRIDGE_CONNECT = "BRIDGE_CONNECT"
        FOR_LOOP = "FOR_LOOP"
        TRAITS = "TRAITS"
        MODULE_TEMPLATING = "MODULE_TEMPLATING"
        INSTANCE_TRAITS = "INSTANCE_TRAITS"

    def __init__(self, ast_root: BoundNode) -> None:
        self._ast_root = ast_root
        self._type_graph = TypeGraph.create(g=ast_root.g())
        self._type_nodes: dict[str, BoundNode] = {}
        self._scope_stack = ASTVisitor._ScopeStack()
        self._experiments: set[ASTVisitor._Experiments] = set()

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

    def _enable_experiment(self, experiment: ASTVisitor._Experiments) -> None:
        print(f"Enabling experiment: {experiment}")
        self._experiments.add(experiment)

    def build(self) -> tuple[TypeGraph, dict[str, BoundNode]]:
        # must start with a File (for now)
        assert NodeHelpers.get_type_name(self._ast_root) == AST.File.__qualname__

        self.visit(self._ast_root)
        return self._type_graph, self._type_nodes

    def visit(self, node: BoundNode):
        node_type = NodeHelpers.get_type_name(node)
        print(f"Visiting node of type {node_type}")

        try:
            handler = getattr(self, f"visit_{node_type}")
        except AttributeError:
            raise NotImplementedError(f"No handler for node type: {node_type}")

        return handler(node)

    def visit_File(self, node: BoundNode) -> BoundNode:
        scope_node = NodeHelpers.get_child(node, "scope")
        assert scope_node is not None
        return self.visit(scope_node)

    def visit_Scope(self, node: BoundNode) -> BoundNode:
        with self._scope_stack.enter():
            for scope_child in NodeHelpers.get_children(node).values():
                self.visit(scope_child)

        return node

    def visit_PragmaStmt(self, node: BoundNode) -> BoundNode:
        pragma = AST.PragmaStmt.get_pragma(node)
        name, args = ASTVisitor._parse_pragma(pragma)

        if name == ASTVisitor._Pragma.EXPERIMENT.value:
            if len(args) != 1:
                raise DslException("Experiment pragma takes exactly one argument")
            if not isinstance(args[0], str):
                raise DslException("Experiment pragma takes a single string argument")
            if args[0] not in ASTVisitor._Experiments:
                raise DslException(f"Unknown experiment: {args[0]}")
            self._enable_experiment(ASTVisitor._Experiments(args[0]))
        else:
            raise DslException(f"Unknown pragma: {name}")

        return node


def build_file(source_file: Path) -> tuple[BoundNode, TypeGraph]:
    graph = GraphView.create()
    type_graph = TypeGraph.create(g=graph)

    tree = parse_text_as_file(source_file.read_text(), source_file)
    ast_root = ANTLRVisitor(graph, type_graph, source_file).visit(tree).instance
    # type_graph, type_nodes = ASTVisitor(ast_root).build()

    return ast_root, type_graph
