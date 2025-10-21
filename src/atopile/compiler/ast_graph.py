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
from typing import cast

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from antlr4.tree.Tree import TerminalNodeImpl

import atopile.compiler.ast_types as AST
from atopile.compiler.graph_mock import BoundNode, NodeHelpers
from atopile.compiler.parse import parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.core.fabll import Child, NodeType, NodeTypeAttributes
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
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
        self._type_cache: AST.GraphTypeCache = {}
        self._file_path = file_path

    def _constrain_is_literal(
        self, node: BoundNode, value: int | float | str | bool
    ) -> None:
        AST.constrain_to_literal(
            g=self._graph, tg=self._type_graph, node=node.node(), value=value
        )

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
        print("visitStmt", ctx.getText())
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
        stnts = itertools.chain.from_iterable(
            (
                (child for child in self.visitStmts(ctx.stmt()) if child is not None),
                (
                    child
                    for child in (
                        self.visitSimple_stmts(ctx.simple_stmts())
                        if ctx.simple_stmts()
                        else []
                    )
                    if child is not None
                ),
            )
        )

        print("block", stnts)
        return stnts

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

    # def visitRetype_stmt(self, ctx: AtoParser.Retype_stmtContext) -> BoundNode:
    #     return AST.RetypeStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.RetypeStmt.Children(
    #             source=self._extract_source(ctx),
    #             field_ref=self.visitField_reference(ctx.field_reference()),
    #             type_ref=self.visitType_reference(ctx.type_reference()),
    #         ),
    #         attrs=AST.RetypeStmt.Attrs(),
    #     )

    # def visitPin_declaration(self, ctx: AtoParser.Pin_declarationContext) -> BoundNode:
    #     return self.visitPin_stmt(ctx.pin_stmt())

    # def visitPindef_stmt(self, ctx: AtoParser.Pindef_stmtContext) -> BoundNode:
    #     return self.visitPin_stmt(ctx.pin_stmt())

    # def visitPin_stmt(self, ctx: AtoParser.Pin_stmtContext) -> BoundNode:
    #     children = AST.PinDeclaration.Children(source=self._extract_source(ctx))

    #     match (ctx.name(), ctx.number_hint_natural(), ctx.string()):
    #         case (name, None, None):
    #             attrs = AST.PinDeclaration.Attrs(
    #                 kind=AST.PinDeclaration.Kind.NAME, name=self.visitName(name)
    #             )
    #         case (None, number_hint_natural, None):
    #             attrs = AST.PinDeclaration.Attrs(kind=AST.PinDeclaration.Kind.NUMBER)
    #             children["label"] = self.visitNumber_hint_natural(number_hint_natural)
    #         case (None, None, string):
    #             attrs = AST.PinDeclaration.Attrs(kind=AST.PinDeclaration.Kind.STRING)
    #             children["label"] = self.visitString(string)
    #         case _:
    #             raise ValueError(f"Unexpected pin statement: {ctx.getText()}")

    #     return AST.PinDeclaration.create_subgraph(
    #         g=self._graph, type_cache=self._type_cache, children=children, attrs=attrs
    #     )

    # def visitSignaldef_stmt(self, ctx: AtoParser.Signaldef_stmtContext) -> BoundNode:
    #     return AST.SignaldefStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.SignaldefStmt.Children(
    #             source=self._extract_source(ctx),
    #         ),
    #         attrs=AST.SignaldefStmt.Attrs(name=self.visitName(ctx.name())),
    #     )

    def visitString_stmt(self, ctx: AtoParser.String_stmtContext) -> AST.StringStmt:
        return AST.StringStmt.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            string_value=self.visitString(ctx.string()),
            string_source_info=self._extract_source_info(ctx.string()),
        )

    # def visitField_reference_or_declaration(
    #     self, ctx: AtoParser.Field_reference_or_declarationContext
    # ) -> BoundNode:
    #     match (ctx.field_reference(), ctx.declaration_stmt()):
    #         case (field_ref_ctx, None):
    #             return self.visitField_reference(field_ref_ctx)
    #         case (None, decl_stmt_ctx):
    #             return self.visitDeclaration_stmt(decl_stmt_ctx)
    #         case _:
    #             raise ValueError(
    #                 f"Unexpected field reference or declaration: {ctx.getText()}"
    #             )

    # def visitPass_stmt(self, ctx: AtoParser.Pass_stmtContext) -> BoundNode:
    #     return AST.PassStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.PassStmt.Children(
    #             source=self._extract_source(ctx),
    #         ),
    #         attrs=AST.PassStmt.Attrs(),
    #     )

    # def visitAssert_stmt(self, ctx: AtoParser.Assert_stmtContext) -> BoundNode:
    #     return AST.AssertStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.AssertStmt.Children(
    #             source=self._extract_source(ctx),
    #             comparison=self.visitComparison(ctx.comparison()),
    #         ),
    #         attrs=AST.AssertStmt.Attrs(),
    #     )

    # def visitTrait_stmt(self, ctx: AtoParser.Trait_stmtContext) -> BoundNode:
    #     attrs = AST.TraitStmt.Attrs()
    #     children = AST.TraitStmt.Children(
    #         source=self._extract_source(ctx),
    #         type_ref=self.visitType_reference(ctx.type_reference()),
    #     )

    #     if ctx.field_reference():
    #         children["target"] = self.visitField_reference(ctx.field_reference())

    #     if ctx.template():
    #         children["template"] = self.visitTemplate(ctx.template())

    #     if ctx.constructor():
    #         attrs["constructor"] = self.visitConstructor(ctx.constructor())

    #     return AST.TraitStmt.create_subgraph(
    #         g=self._graph, type_cache=self._type_cache, children=children, attrs=attrs
    #     )

    # def visitConstructor(self, ctx: AtoParser.ConstructorContext) -> str:
    #     return self.visitName(ctx.name())

    # def visitFor_stmt(self, ctx: AtoParser.For_stmtContext) -> BoundNode:
    #     return AST.ForStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ForStmt.Children(
    #             source=self._extract_source(ctx),
    #             iterable=self.visitIterable_references(ctx.iterable_references()),
    #             scope=AST.Scope.create_subgraph(
    #                 g=self._graph,
    #                 type_cache=self._type_cache,
    #                 children=AST.Scope.Children(
    #                     **{
    #                         f"scope_item_{i}": node
    #                         for i, node in enumerate(
    #                             child for child in self.visitBlock(ctx.block())
    #                         )
    #                     }
    #                 ),
    #             ),
    #         ),
    #         attrs=AST.ForStmt.Attrs(target=self.visitName(ctx.name())),
    #     )

    # def visitIterable_references(
    #     self, ctx: AtoParser.Iterable_referencesContext
    # ) -> BoundNode:
    #     match [ctx.field_reference(), ctx.list_literal_of_field_references()]:
    #         case [field_ref_ctx, None]:
    #             children = AST.IterableFieldRef.Children(
    #                 source=self._extract_source(ctx),
    #                 field=self.visitField_reference(field_ref_ctx),
    #             )

    #             if ctx.slice_():
    #                 children["slice"] = self.visitSlice(ctx.slice_())

    #             return AST.IterableFieldRef.create_subgraph(
    #                 g=self._graph,
    #                 type_cache=self._type_cache,
    #                 children=children,
    #                 attrs=AST.IterableFieldRef.Attrs(),
    #             )
    #         case [None, list_literal_ctx]:
    #             return self.visitList_literal_of_field_references(list_literal_ctx)
    #         case _:
    #             raise ValueError(f"Unexpected iterable references: {ctx.getText()}")

    # def visitList_literal_of_field_references(
    #     self, ctx: AtoParser.List_literal_of_field_referencesContext
    # ) -> BoundNode:
    #     return AST.FieldRefList.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.FieldRefList.Children(
    #             source=self._extract_source(ctx),
    #             **{
    #                 f"item_{i}": item
    #                 for i, item in enumerate(
    #                     [self.visitField_reference(fr) for fr in ctx.field_reference()]
    #                 )
    #             },
    #         ),
    #         attrs=AST.FieldRefList.Attrs(),
    #     )

    # def visitSlice(self, ctx: AtoParser.SliceContext) -> BoundNode:
    #     attrs = AST.Slice.Attrs()

    #     if ctx.slice_start():
    #         attrs["start"] = self.visitSlice_start(ctx.slice_start())

    #     if ctx.slice_stop():
    #         attrs["stop"] = self.visitSlice_stop(ctx.slice_stop())

    #     if ctx.slice_step():
    #         attrs["step"] = self.visitSlice_step(ctx.slice_step())

    #     return AST.Slice.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.Slice.Children(source=self._extract_source(ctx)),
    #         attrs=attrs,
    #     )

    # def visitSlice_start(self, ctx: AtoParser.Slice_startContext) -> int:
    #     return self.visitNumber_hint_integer(ctx.number_hint_integer())

    # def visitSlice_stop(self, ctx: AtoParser.Slice_stopContext) -> int:
    #     return self.visitNumber_hint_integer(ctx.number_hint_integer())

    # def visitSlice_step(self, ctx: AtoParser.Slice_stepContext) -> int:
    #     return self.visitNumber_hint_integer(ctx.number_hint_integer())

    @dataclass
    class _FieldRefPart:
        name: str
        key: int | None
        source_ctx: ParserRuleContext

    @dataclass
    class _FieldRef:
        parts: list[ANTLRVisitor._FieldRefPart]

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

    # def visitPin_reference_end(
    #     self, ctx: AtoParser.Pin_reference_endContext
    # ) -> BoundNode:
    #     return self.visitNumber_hint_natural(ctx.number_hint_natural())

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

    def visitAssignable(self, ctx: AtoParser.AssignableContext) -> AST.NewExpression:
        match (
            ctx.new_stmt(),
            ctx.literal_physical(),
            ctx.arithmetic_expression(),
            ctx.string(),
            ctx.boolean_(),
        ):
            case (new_stmt_ctx, None, None, None, None):
                return self.visitNew_stmt(new_stmt_ctx)
            case (None, literal_physical_ctx, None, None, None):
                return self.visitLiteral_physical(literal_physical_ctx)
            # case (None, None, arithmetic_expression_ctx, None, None):
            #     return self.visitArithmetic_expression(arithmetic_expression_ctx)
            # case (None, None, None, string_ctx, None):
            #     return self.visitString(string_ctx)
            # case (None, None, None, None, boolean_ctx):
            #     return self.visitBoolean_(boolean_ctx)
            case _:
                raise ValueError(f"Unexpected assignable: {ctx.getText()}")

    def visitNew_stmt(self, ctx: AtoParser.New_stmtContext) -> AST.NewExpression:
        return AST.NewExpression.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            type_ref_name=self.visitType_reference(ctx.type_reference()),
            type_ref_source_info=self._extract_source_info(ctx.type_reference()),
        )

        # TODO
        # if ctx.template() is not None:
        #     children["template"] = self.visitTemplate(ctx.template())

        # if ctx.new_count() is not None:
        #     children["new_count"] = self.visitNumber_hint_natural(ctx.new_count())

    def visitLiteral_physical(
        self, ctx: AtoParser.Literal_physicalContext
    ) -> AST.BilateralQuantity:
        match ctx.quantity(), ctx.bilateral_quantity(), ctx.bound_quantity():
            # case (quantity_ctx, None, None):
            #     return self.visitQuantity(quantity_ctx)
            case (None, bilateral_quantity_ctx, None):
                return self.visitBilateral_quantity(bilateral_quantity_ctx)
            # case (None, None, bound_quantity_ctx):
            #     return self.visitBound_quantity(bound_quantity_ctx)
            case _:
                raise ValueError(
                    f"Unexpected literal physical context: {ctx.getText()}"
                )

    # def visitArithmetic_expression(
    #     self, ctx: AtoParser.Arithmetic_expressionContext
    # ) -> BoundNode:
    #     right = self.visitSum(ctx.sum_())

    #     if ctx.arithmetic_expression():
    #         match [ctx.OR_OP(), ctx.AND_OP()]:
    #             case [or_op_ctx, None]:
    #                 operator = or_op_ctx.getText()
    #             case [None, and_op_ctx]:
    #                 operator = and_op_ctx.getText()
    #             case _:
    #                 raise ValueError(
    #                     f"Unexpected operator in arithmetic expression: {ctx.getText()}"
    #                 )

    #         return AST.BinaryExpression.create_subgraph(
    #             g=self._graph,
    #             type_cache=self._type_cache,
    #             children=AST.BinaryExpression.Children(
    #                 source=self._extract_source(ctx),
    #                 left=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #                 right=right,
    #             ),
    #             attrs=AST.BinaryExpression.Attrs(operator=operator),
    #         )

    #     return right

    # def visitSum(self, ctx: AtoParser.SumContext) -> BoundNode:
    #     right = self.visitTerm(ctx.term())

    #     if ctx.sum_():
    #         match [ctx.PLUS(), ctx.MINUS()]:
    #             case [plus_op_ctx, None]:
    #                 operator = plus_op_ctx.getText()
    #             case [None, minus_op_ctx]:
    #                 operator = minus_op_ctx.getText()
    #             case _:
    #                 raise ValueError(f"Unexpected sum operator: {ctx.getText()}")

    #         return AST.BinaryExpression.create_subgraph(
    #             g=self._graph,
    #             type_cache=self._type_cache,
    #             children=AST.BinaryExpression.Children(
    #                 source=self._extract_source(ctx),
    #                 left=self.visitSum(ctx.sum_()),
    #                 right=right,
    #             ),
    #             attrs=AST.BinaryExpression.Attrs(operator=operator),
    #         )

    #     return right

    # def visitTerm(self, ctx: AtoParser.TermContext) -> BoundNode:
    #     right = self.visitPower(ctx.power())

    #     if ctx.term():
    #         match [ctx.STAR(), ctx.DIV()]:
    #             case [star_op_ctx, None]:
    #                 operator = star_op_ctx.getText()
    #             case [None, div_op_ctx]:
    #                 operator = div_op_ctx.getText()
    #             case _:
    #                 raise ValueError(f"Unexpected term operator: {ctx.getText()}")

    #         return AST.BinaryExpression.create_subgraph(
    #             g=self._graph,
    #             type_cache=self._type_cache,
    #             children=AST.BinaryExpression.Children(
    #                 source=self._extract_source(ctx),
    #                 left=self.visitTerm(ctx.term()),
    #                 right=right,
    #             ),
    #             attrs=AST.BinaryExpression.Attrs(operator=operator),
    #         )

    #     return right

    # def visitPower(self, ctx: AtoParser.PowerContext) -> BoundNode:
    #     match ctx.atom():
    #         case [base, exponent]:
    #             return AST.BinaryExpression.create_subgraph(
    #                 g=self._graph,
    #                 type_cache=self._type_cache,
    #                 children=AST.BinaryExpression.Children(
    #                     source=self._extract_source(ctx), left=base, right=exponent
    #                 ),
    #                 attrs=AST.BinaryExpression.Attrs(operator=ctx.POWER().getText()),
    #             )
    #         case [base]:
    #             return base
    #         case _:
    #             raise ValueError(f"Unexpected power context: {ctx.getText()}")

    # def visitArithmetic_group(
    #     self, ctx: AtoParser.Arithmetic_groupContext
    # ) -> BoundNode:
    #     return AST.GroupExpression.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.GroupExpression.Children(
    #             source=self._extract_source(ctx),
    #             expression=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.GroupExpression.Attrs(),
    #     )

    # def visitAtom(self, ctx: AtoParser.AtomContext) -> BoundNode:
    #     match ctx.field_reference(), ctx.literal_physical(), ctx.arithmetic_group():
    #         case (field_ref_ctx, None, None):
    #             return self.visitField_reference(field_ref_ctx)
    #         case (None, literal_physical_ctx, None):
    #             return self.visitLiteral_physical(literal_physical_ctx)
    #         case (None, None, arithmetic_group_ctx):
    #             return self.visitArithmetic_group(arithmetic_group_ctx)
    #         case _:
    #             raise ValueError(f"Unexpected atom context: {ctx.getText()}")

    # def visitComparison(self, ctx: AtoParser.ComparisonContext) -> BoundNode:
    #     return AST.ComparisonExpression.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonExpression.Children(
    #             source=self._extract_source(ctx),
    #             left=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #             **{
    #                 f"clause_{i}": clause
    #                 for i, clause in enumerate(
    #                     [
    #                         self.visitCompare_op_pair(pair)
    #                         for pair in ctx.compare_op_pair()
    #                     ]
    #                 )
    #             },
    #         ),
    #         attrs=AST.ComparisonExpression.Attrs(),
    #     )

    # def visitCompare_op_pair(self, ctx: AtoParser.Compare_op_pairContext) -> BoundNode:
    #     match (
    #         ctx.lt_arithmetic_or(),
    #         ctx.gt_arithmetic_or(),
    #         ctx.lt_eq_arithmetic_or(),
    #         ctx.gt_eq_arithmetic_or(),
    #         ctx.in_arithmetic_or(),
    #         ctx.is_arithmetic_or(),
    #     ):
    #         case (lt_arithmetic_or_ctx, None, None, None, None, None):
    #             return self.visitLt_arithmetic_or(lt_arithmetic_or_ctx)
    #         case (None, gt_arithmetic_or_ctx, None, None, None, None):
    #             return self.visitGt_arithmetic_or(gt_arithmetic_or_ctx)
    #         case (None, None, lt_eq_arithmetic_or_ctx, None, None, None):
    #             return self.visitLt_eq_arithmetic_or(lt_eq_arithmetic_or_ctx)
    #         case (None, None, None, gt_eq_arithmetic_or_ctx, None, None):
    #             return self.visitGt_eq_arithmetic_or(gt_eq_arithmetic_or_ctx)
    #         case (None, None, None, None, in_arithmetic_or_ctx, None):
    #             return self.visitIn_arithmetic_or(in_arithmetic_or_ctx)
    #         case (None, None, None, None, None, is_arithmetic_or_ctx):
    #             return self.visitIs_arithmetic_or(is_arithmetic_or_ctx)
    #         case _:
    #             raise ValueError(f"Unexpected compare op pair context: {ctx.getText()}")

    # def visitLt_arithmetic_or(
    #     self, ctx: AtoParser.Lt_arithmetic_orContext
    # ) -> BoundNode:
    #     return AST.ComparisonClause.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonClause.Children(
    #             source=self._extract_source(ctx),
    #             right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.ComparisonClause.Attrs(operator=ctx.LESS_THAN().getText()),
    #     )

    # def visitGt_arithmetic_or(
    #     self, ctx: AtoParser.Gt_arithmetic_orContext
    # ) -> BoundNode:
    #     return AST.ComparisonClause.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonClause.Children(
    #             source=self._extract_source(ctx),
    #             right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.ComparisonClause.Attrs(operator=ctx.GREATER_THAN().getText()),
    #     )

    # def visitLt_eq_arithmetic_or(
    #     self, ctx: AtoParser.Lt_eq_arithmetic_orContext
    # ) -> BoundNode:
    #     return AST.ComparisonClause.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonClause.Children(
    #             source=self._extract_source(ctx),
    #             right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.ComparisonClause.Attrs(operator=ctx.LT_EQ().getText()),
    #     )

    # def visitGt_eq_arithmetic_or(
    #     self, ctx: AtoParser.Gt_eq_arithmetic_orContext
    # ) -> BoundNode:
    #     return AST.ComparisonClause.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonClause.Children(
    #             source=self._extract_source(ctx),
    #             right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.ComparisonClause.Attrs(operator=ctx.GT_EQ().getText()),
    #     )

    # def visitIn_arithmetic_or(
    #     self, ctx: AtoParser.In_arithmetic_orContext
    # ) -> BoundNode:
    #     return AST.ComparisonClause.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonClause.Children(
    #             source=self._extract_source(ctx),
    #             right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.ComparisonClause.Attrs(operator=ctx.WITHIN().getText()),
    #     )

    # def visitIs_arithmetic_or(
    #     self, ctx: AtoParser.Is_arithmetic_orContext
    # ) -> BoundNode:
    #     return AST.ComparisonClause.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ComparisonClause.Children(
    #             source=self._extract_source(ctx),
    #             right=self.visitArithmetic_expression(ctx.arithmetic_expression()),
    #         ),
    #         attrs=AST.ComparisonClause.Attrs(operator=ctx.IS().getText()),
    #     )

    def visitQuantity(
        self, ctx: AtoParser.QuantityContext
    ) -> tuple[int | float, str | None]:
        number = self.visitNumber(ctx.number())
        unit = self.visitUnit(ctx.unit()) if ctx.unit() else None
        return number, unit

    # def visitDeclaration_stmt(
    #     self, ctx: AtoParser.Declaration_stmtContext
    # ) -> BoundNode:
    #     return AST.DeclarationStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.DeclarationStmt.Children(
    #             source=self._extract_source(ctx),
    #             field_ref=self.visitField_reference(ctx.field_reference()),
    #             unit=self.visitUnit(ctx.unit()),
    #         ),
    #         attrs=AST.DeclarationStmt.Attrs(),
    #     )

    # def visitUnit(self, ctx: AtoParser.UnitContext) -> BoundNode:
    #     return AST.Unit.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.Unit.Children(source=self._extract_source(ctx)),
    #         attrs=AST.Unit.Attrs(symbol=self.visitName(ctx.name())),
    #     )

    def visitBilateral_quantity(
        self, ctx: AtoParser.Bilateral_quantityContext
    ) -> AST.BilateralQuantity:
        quantity_value, quantity_unit = self.visitQuantity(ctx.quantity())
        tolerance_value, tolerance_unit = self.visitBilateral_tolerance(
            ctx.bilateral_tolerance()
        )
        return AST.BilateralQuantity.create_instance(
            tg=self._type_graph,
            g=self._graph,
            source_info=self._extract_source_info(ctx),
            quantity_value=quantity_value,
            quantity_unit=quantity_unit,
            quantity_source_info=self._extract_source_info(ctx.quantity()),
            tolerance_value=tolerance_value,
            tolerance_unit=tolerance_unit,
            tolerance_source_info=self._extract_source_info(ctx.bilateral_tolerance()),
        )

    def visitBilateral_tolerance(
        self, ctx: AtoParser.Bilateral_toleranceContext
    ) -> tuple[int | float, str | None]:
        number = self.visitNumber_signless(ctx.number_signless())

        match [ctx.unit(), ctx.PERCENT()]:
            case [name_ctx, None]:
                unit = self.visitUnit(name_ctx)
            case [None, percent_ctx]:
                unit = self.visitTerminal(percent_ctx)
            case _:
                raise ValueError(
                    f"Unexpected bilateral tolerance context: {ctx.getText()}"
                )

        return number, unit

    # def visitBound_quantity(self, ctx: AtoParser.Bound_quantityContext) -> BoundNode:
    #     start, end = [self.visitQuantity(q) for q in ctx.quantity()]

    #     return AST.BoundedQuantity.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.BoundedQuantity.Children(
    #             source=self._extract_source(ctx), start=start, end=end
    #         ),
    #         attrs=AST.BoundedQuantity.Attrs(),
    #     )

    # def visitTemplate(self, ctx: AtoParser.TemplateContext) -> BoundNode:
    #     return AST.Template.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.Template.Children(
    #             source=self._extract_source(ctx),
    #             **{
    #                 f"arg_{i}": arg
    #                 for i, arg in enumerate(
    #                     [self.visitTemplate_arg(arg) for arg in ctx.template_arg()]
    #                 )
    #             },
    #         ),
    #         attrs=AST.Template.Attrs(),
    #     )

    # def visitTemplate_arg(self, ctx: AtoParser.Template_argContext) -> BoundNode:
    #     return AST.TemplateArg.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.TemplateArg.Children(
    #             source=self._extract_source(ctx), value=self.visitLiteral(ctx.literal())
    #         ),
    #         attrs=AST.TemplateArg.Attrs(name=self.visitName(ctx.name())),
    #     )

    # def visitLiteral(self, ctx: AtoParser.LiteralContext) -> BoundNode:
    #     match ctx.string(), ctx.boolean_(), ctx.number():
    #         case (string_ctx, None, None):
    #             return self.visitString(string_ctx)
    #         case (None, boolean_ctx, None):
    #             return self.visitBoolean_(boolean_ctx)
    #         case (None, None, number_ctx):
    #             return self.visitNumber(number_ctx)
    #         case _:
    #             raise ValueError(f"Unexpected literal context: {ctx.getText()}")

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

    # def visitNew_count(self, ctx: AtoParser.New_countContext) -> BoundNode:
    #     return self.visitNumber_hint_natural(ctx.number_hint_natural())

    # def visitBoolean_(self, ctx: AtoParser.Boolean_Context) -> BoundNode:
    #     match ctx.TRUE(), ctx.FALSE():
    #         case (_, None):
    #             attrs = AST.Boolean.Attrs(value=True)
    #         case (None, _):
    #             attrs = AST.Boolean.Attrs(value=False)
    #         case _:
    #             raise ValueError(f"Unexpected boolean context: {ctx.getText()}")

    #     return AST.Boolean.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.Boolean.Children(source=self._extract_source(ctx)),
    #         attrs=attrs,
    #     )

    # def visitNumber_signless(self, ctx: AtoParser.Number_signlessContext) -> BoundNode:
    #     return AST.Number.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.Number.Children(source=self._extract_source(ctx)),
    #         attrs=AST.Number.Attrs(value=self._parse_decimal(ctx.getText())),
    #     )

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

    # def visitMif(self, ctx: AtoParser.MifContext) -> BoundNode:
    #     return self.visitConnectable(ctx.connectable())

    # def visitBridgeable(self, ctx: AtoParser.BridgeableContext) -> BoundNode:
    #     return self.visitConnectable(ctx.connectable())

    # def visitConnectable(self, ctx: AtoParser.ConnectableContext) -> BoundNode:
    #     match ctx.field_reference(), ctx.signaldef_stmt(), ctx.pindef_stmt():
    #         case (field_ref_ctx, None, None):
    #             return self.visitField_reference(field_ref_ctx)
    #         case (None, signaldef_stmt_ctx, None):
    #             return self.visitSignaldef_stmt(signaldef_stmt_ctx)
    #         case (None, None, pindef_stmt_ctx):
    #             return self.visitPindef_stmt(pindef_stmt_ctx)
    #         case _:
    #             raise ValueError(f"Unexpected connectable: {ctx.getText()}")

    # def visitConnect_stmt(self, ctx: AtoParser.Connect_stmtContext) -> BoundNode:
    #     left, right = [self.visitMif(c) for c in ctx.mif()]
    #     return AST.ConnectStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.ConnectStmt.Children(
    #             source=self._extract_source(ctx), left=left, right=right
    #         ),
    #         attrs=AST.ConnectStmt.Attrs(),
    #     )

    # def visitDirected_connect_stmt(
    #     self, ctx: AtoParser.Directed_connect_stmtContext
    # ) -> BoundNode:
    #     match ctx.SPERM(), ctx.LSPERM():
    #         case (_, None):
    #             direction = AST.DirectedConnectStmt.Direction.RIGHT
    #         case (None, _):
    #             direction = AST.DirectedConnectStmt.Direction.LEFT
    #         case _:
    #             raise ValueError(
    #                 f"Unexpected directed connect statement: {ctx.getText()}"
    #             )

    #     match [self.visitBridgeable(c) for c in ctx.bridgeable()]:
    #         case [first]:
    #             left = first
    #             right = right = self.visitDirected_connect_stmt(
    #                 ctx.directed_connect_stmt()
    #             )
    #         case [first, second]:
    #             left = first
    #             right = second
    #         case _:
    #             raise ValueError(f"Unexpected bridgeables: {ctx.getText()}")

    #     return AST.DirectedConnectStmt.create_subgraph(
    #         g=self._graph,
    #         type_cache=self._type_cache,
    #         children=AST.DirectedConnectStmt.Children(
    #             source=self._extract_source(ctx), left=left, right=right
    #         ),
    #         attrs=AST.DirectedConnectStmt.Attrs(direction=direction.value),
    #     )


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
