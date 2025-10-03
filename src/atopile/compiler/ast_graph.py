"""
Generates an AST graph from the ANTLR4-generated AST.

Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from antlr4.tree.Tree import TerminalNodeImpl

import atopile.compiler.ast_types as AST
from atopile.compiler.graph_mock import BoundNode, GraphView
from atopile.compiler.parse import parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor


class Visitor(AtoParserVisitor):
    """
    Generates a native compiler graph from the ANTLR4-generated AST, with attached
    source context.
    """

    def __init__(self, graph: GraphView, file_path: Path) -> None:
        super().__init__()
        self._graph = graph
        self._file_path = file_path

    def _extract_source(self, ctx: ParserRuleContext) -> BoundNode:
        start_token = ctx.start
        stop_token = ctx.stop
        token_stream = ctx.parser.getInputStream()  # type: ignore
        text = AtoRewriter(token_stream).getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start_token.tokenIndex,  # type: ignore
            stop_token.tokenIndex,  # type: ignore
        )

        start_line, start_col = start_token.line, start_token.column  # type: ignore
        end_line, end_col = stop_token.line, stop_token.column  # type: ignore

        return AST.SourceChunk.create_subgraph(
            g=self._graph,
            children=AST.SourceChunk.Children(
                loc=AST.FileLocation.create(
                    g=self._graph,
                    attrs=AST.FileLocation.Attrs(
                        start_line=start_line,
                        start_col=start_col,
                        end_line=end_line,
                        end_col=end_col,
                    ),
                )
            ),
            attrs=AST.SourceChunk.Attrs(text=text),
        )

    # @staticmethod
    # def _parse_int(text: str) -> int:
    #     normalized = text.replace("_", "")
    #     return int(normalized, 0)

    # @staticmethod
    # def _parse_decimal(text: str) -> Decimal:
    #     normalized = text.replace("_", "")
    #     try:
    #         return Decimal(normalized)
    #     except InvalidOperation:
    #         # Fall back to Python's numeric parser for forms Decimal cannot parse directly
    #         return Decimal(str(int(normalized, 0)))

    # def _make_binary(
    #     self,
    #     operator: str,
    #     left: AST._Node,
    #     right: AST._Node,
    #     ctx: ParserRuleContext,
    # ) -> AST.BinaryExpression:
    #     node = AST.BinaryExpression.create(self._graph, operator, left, right)
    #     AST.add(self._graph, node, self._extract_source(ctx))
    #     return node

    # def _make_comparison_clause(
    #     self, operator: str, right: AST._Node, ctx: ParserRuleContext
    # ) -> AST.ComparisonClause:
    #     clause = AST.ComparisonClause.create(self._graph, operator, right)
    #     AST.add(self._graph, clause, self._extract_source(ctx))
    #     return clause

    # def visitName(self, ctx: AtoParser.NameContext) -> str:
    #     return ctx.getText()

    def visitTypeReference(self, ctx: AtoParser.Type_referenceContext) -> BoundNode:
        type_ref = AST.TypeRef.create_subgraph(
            g=self._graph,
            children=AST.TypeRef.Children(source=self._extract_source(ctx)),
            attrs=AST.TypeRef.Attrs(name=self.visitName(ctx.name())),
        )
        return type_ref

    # def visitArrayIndex(self, ctx: AtoParser.Array_indexContext) -> str | int | None:
    #     if key := ctx.key():
    #         text = key.getText()
    #         try:
    #             return self._parse_int(text)
    #         except ValueError:
    #             return text
    #     return None

    def visitStmt(self, ctx: AtoParser.StmtContext) -> Iterable[BoundNode]:
        match (ctx.pragma_stmt(), ctx.simple_stmts(), ctx.compound_stmt()):
            case (pragma_stmt, None, None):
                return [self.visitPragma_stmt(pragma_stmt)]
            case (None, simple_stmts, None):
                return self.visitSimple_stmts(simple_stmts)
            case (None, None, compound_stmt):
                return [self.visitCompound_stmt(compound_stmt)]
            case _:
                assert False, f"Unexpected statement: {ctx.getText()}"

    def visitStmts(self, ctx: AtoParser.StmtsContext) -> Iterable[BoundNode]:
        return itertools.chain.from_iterable(
            (child for child in self.visitStmt(child) if child is not None)
            for child in ctx
        )

    def visitBlocktype(
        self, ctx: AtoParser.BlocktypeContext
    ) -> AST.BlockDefinition.BlockTypeT:
        return cast(AST.BlockDefinition.BlockTypeT, ctx.getText())

    def visitBlock(self, ctx: AtoParser.BlockContext) -> Iterable[BoundNode]:
        return itertools.chain.from_iterable(
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

    def visitBlockdef(self, ctx: AtoParser.BlockdefContext) -> BoundNode:
        block_type = self.visitBlocktype(ctx.blocktype())
        type_ref = self.visitTypeReference(ctx.type_reference())

        scope_children = self.visitBlock(ctx.block())
        print(list(scope_children))

        children = AST.BlockDefinition.Children(
            source=self._extract_source(ctx),
            type_ref=type_ref,
            scope=AST.Scope.create_subgraph(
                g=self._graph,
                children=AST.Scope.Children(
                    **{
                        f"scope_item_{i}": node
                        for i, node in enumerate(
                            child for child in self.visitBlock(ctx.block())
                        )
                    }
                ),
            ),
        )

        if super_ctx := ctx.blockdef_super():
            children["super_type_ref"] = self.visitTypeReference(
                super_ctx.type_reference()
            )

        block_definition = AST.BlockDefinition.create_subgraph(
            g=self._graph,
            children=children,
            attrs=AST.BlockDefinition.Attrs(block_type=block_type),
        )

        return block_definition

    def visitFile_input(self, ctx: AtoParser.File_inputContext) -> BoundNode:
        scope_children = (
            child for child in self.visitStmts(ctx.stmt()) if child is not None
        )

        scope_children = list(scope_children)
        print(scope_children)

        return AST.File.create_subgraph(
            g=self._graph,
            attrs=AST.File.Attrs(path=str(self._file_path)),
            children=AST.File.Children(
                source=self._extract_source(ctx),
                scope=AST.Scope.create_subgraph(
                    g=self._graph,
                    children=AST.Scope.Children(
                        **{
                            f"scope_item_{i}": node
                            for i, node in enumerate(scope_children)
                        }
                    ),
                ),
            ),
        )

    def visitSimple_stmts(
        self, ctx: AtoParser.Simple_stmtsContext
    ) -> Iterable[BoundNode]:
        return itertools.chain.from_iterable(
            (
                child
                if (isinstance(child, Iterable) and not isinstance(child, str))
                else [child]
                for child in (self.visit(child) for child in ctx.simple_stmt())
            )
        )

    def visitPragma_stmt(self, ctx: AtoParser.Pragma_stmtContext) -> BoundNode:
        pragma_text = self.visit(ctx.PRAGMA())
        return AST.PragmaStmt.create_subgraph(
            g=self._graph,
            children=AST.PragmaStmt.Children(source=self._extract_source(ctx)),
            attrs=AST.PragmaStmt.Attrs(pragma=pragma_text),
        )

    def visitImport_stmt(self, ctx: AtoParser.Import_stmtContext) -> BoundNode:
        type_ref = self.visitTypeReference(ctx.type_reference())

        children = AST.ImportStmt.Children(
            source=self._extract_source(ctx), type_ref=type_ref
        )

        if ctx.string():
            children["path"] = AST.ImportPath.create_subgraph(
                g=self._graph,
                children=AST.ImportPath.Children(
                    source=self._extract_source(ctx.string()),
                    string=self.visitString(ctx.string()),
                ),
                attrs=AST.ImportPath.Attrs(),
            )

        import_stmt = AST.ImportStmt.create_subgraph(
            g=self._graph, children=children, attrs=AST.ImportStmt.Attrs()
        )

        return import_stmt

    # def visitRetype_stmt(self, ctx: AtoParser.Retype_stmtContext) -> AST.RetypeStmt:
    #     field_ref = self.visitField_reference(ctx.field_reference())
    #     type_ref = self.visitTypeReference(ctx.type_reference())
    #     retype = AST.RetypeStmt.create(self._graph, field_ref, type_ref)
    #     AST.add(self._graph, retype, self._extract_source(ctx))
    #     return retype

    # def visitPin_declaration(
    #     self, ctx: AtoParser.Pin_declarationContext
    # ) -> AST.PinDeclaration:
    #     return self.visitPin_stmt(ctx.pin_stmt())

    # def visitPindef_stmt(self, ctx: AtoParser.Pindef_stmtContext) -> AST.PinDeclaration:
    #     return self.visitPin_stmt(ctx.pin_stmt())

    # def visitPin_stmt(self, ctx: AtoParser.Pin_stmtContext) -> AST.PinDeclaration:
    #     if ctx.name():
    #         value = self.visitName(ctx.name())
    #         pin = AST.PinDeclaration.create(
    #             self._graph,
    #             AST.PinDeclaration.Kind.NAME,
    #             value,
    #         )
    #     elif ctx.number_hint_natural():
    #         number_ctx = ctx.number_hint_natural().number_signless()
    #         number_node = self.visitNumber_signless(number_ctx)
    #         pin = AST.PinDeclaration.create(
    #             self._graph,
    #             AST.PinDeclaration.Kind.NUMBER,
    #             int(number_node.value),
    #             number_node,
    #         )
    #     elif ctx.string():
    #         string_node = self.visitString(ctx.string())
    #         pin = AST.PinDeclaration.create(
    #             self._graph,
    #             AST.PinDeclaration.Kind.STRING,
    #             string_node.value,
    #             string_node,
    #         )
    #     else:
    #         raise ValueError(f"Unexpected pin statement: {ctx.getText()}")

    #     AST.add(self._graph, pin, self._extract_source(ctx))
    #     return pin

    # def visitSignaldef_stmt(
    #     self, ctx: AtoParser.Signaldef_stmtContext
    # ) -> AST.SignaldefStmt:
    #     name = self.visitName(ctx.name())
    #     signal = AST.SignaldefStmt.create(self._graph, name)
    #     AST.add(self._graph, signal, self._extract_source(ctx))
    #     return signal

    def visitString_stmt(self, ctx: AtoParser.String_stmtContext) -> BoundNode:
        return AST.StringStmt.create_subgraph(
            g=self._graph,
            children=AST.StringStmt.Children(
                source=self._extract_source(ctx), string=self.visitString(ctx.string())
            ),
            attrs=AST.StringStmt.Attrs(),
        )

    # def visitPass_stmt(self, ctx: AtoParser.Pass_stmtContext) -> AST.PassStmt:
    #     stmt = AST.PassStmt.create(self._graph)
    #     AST.add(self._graph, stmt, self._extract_source(ctx))
    #     return stmt

    # def visitAssert_stmt(self, ctx: AtoParser.Assert_stmtContext) -> AST.AssertStmt:
    #     comparison = self.visitComparison(ctx.comparison())
    #     stmt = AST.AssertStmt.create(self._graph, comparison)
    #     AST.add(self._graph, stmt, self._extract_source(ctx))
    #     return stmt

    # def visitTrait_stmt(self, ctx: AtoParser.Trait_stmtContext) -> AST.TraitStmt:
    #     target = (
    #         self.visitField_reference(ctx.field_reference())
    #         if ctx.field_reference()
    #         else None
    #     )
    #     type_ref = self.visitTypeReference(ctx.type_reference())
    #     constructor = (
    #         self.visitConstructor(ctx.constructor()) if ctx.constructor() else None
    #     )
    #     template = self.visitTemplate(ctx.template()) if ctx.template() else None
    #     trait = AST.TraitStmt.create(
    #         self._graph,
    #         type_ref,
    #         target,
    #         constructor,
    #         template,
    #     )
    #     AST.add(self._graph, trait, self._extract_source(ctx))
    #     return trait

    # def visitConstructor(self, ctx: AtoParser.ConstructorContext) -> str:
    #     return self.visitName(ctx.name())

    # def visitFor_stmt(self, ctx: AtoParser.For_stmtContext) -> AST.ForStmt:
    #     target = self.visitName(ctx.name())
    #     iterable = self.visitIterable_references(ctx.iterable_references())
    #     for_stmt = AST.ForStmt.create(self._graph, target, iterable)
    #     AST.add(self._graph, for_stmt, self._extract_source(ctx))
    #     self._visitScopeChildren(ctx.block(), for_stmt.scope)
    #     return for_stmt

    # def visitIterable_references(
    #     self, ctx: AtoParser.Iterable_referencesContext
    # ) -> AST._Node:
    #     if ctx.field_reference():
    #         field_ref = self.visitField_reference(ctx.field_reference())
    #         if ctx.slice():
    #             slice_node = self.visitSlice(ctx.slice())
    #             iterable_ref = AST.IterableFieldRef.create(
    #                 self._graph,
    #                 field_ref,
    #                 slice_node,
    #             )
    #             AST.add(self._graph, iterable_ref, self._extract_source(ctx))
    #             return iterable_ref
    #         return field_ref
    #     if ctx.list_literal_of_field_references():
    #         return self.visitList_literal_of_field_references(
    #             ctx.list_literal_of_field_references()
    #         )
    #     raise ValueError(f"Unexpected iterable references: {ctx.getText()}")

    # def visitList_literal_of_field_references(
    #     self, ctx: AtoParser.List_literal_of_field_referencesContext
    # ) -> AST.FieldRefList:
    #     field_refs = [self.visitField_reference(fr) for fr in ctx.field_reference()]
    #     literal = AST.FieldRefList.create(self._graph, field_refs)
    #     AST.add(self._graph, literal, self._extract_source(ctx))
    #     return literal

    # def visitSlice(self, ctx: AtoParser.SliceContext) -> AST.Slice:
    #     if ctx.DOUBLE_COLON():
    #         start = None
    #         stop = None
    #         step = self.visitSlice_step(ctx.slice_step()) if ctx.slice_step() else None
    #     else:
    #         start = (
    #             self.visitSlice_start(ctx.slice_start()) if ctx.slice_start() else None
    #         )
    #         stop = self.visitSlice_stop(ctx.slice_stop()) if ctx.slice_stop() else None
    #         step = self.visitSlice_step(ctx.slice_step()) if ctx.slice_step() else None
    #     slice_node = AST.Slice.create(self._graph, start, stop, step)
    #     AST.add(self._graph, slice_node, self._extract_source(ctx))
    #     return slice_node

    # def visitSlice_start(self, ctx: AtoParser.Slice_startContext) -> int:
    #     return self.visitNumber_hint_integer(ctx.number_hint_integer())

    # def visitSlice_stop(self, ctx: AtoParser.Slice_stopContext) -> int:
    #     return self.visitNumber_hint_integer(ctx.number_hint_integer())

    # def visitSlice_step(self, ctx: AtoParser.Slice_stepContext) -> int:
    #     return self.visitNumber_hint_integer(ctx.number_hint_integer())

    # def visitField_reference_part(
    #     self, ctx: AtoParser.Field_reference_partContext
    # ) -> AST.FieldRefPart:
    #     key = None
    #     if ctx.array_index():
    #         key = self.visitArrayIndex(ctx.array_index())
    #     field_ref_part = AST.FieldRefPart.create(
    #         self._graph,
    #         self.visitName(ctx.name()),
    #         key,
    #     )
    #     AST.add(self._graph, field_ref_part, self._extract_source(ctx))
    #     return field_ref_part

    # def visitField_reference(
    #     self, ctx: AtoParser.Field_referenceContext
    # ) -> AST.FieldRef:
    #     field_ref = AST.FieldRef.create(self._graph)
    #     AST.add(self._graph, field_ref, self._extract_source(ctx))
    #     for part in ctx.field_reference_part():
    #         field_ref_part = self.visitField_reference_part(part)
    #         AST.add(self._graph, field_ref, field_ref_part)
    #     if pin_ctx := ctx.pin_reference_end():
    #         number_ctx = pin_ctx.number_hint_natural()
    #         AST.set_attr(
    #             field_ref,
    #             pin=self.visitNumber_hint_natural(number_ctx),
    #         )
    #     return field_ref

    def visitAssign_stmt(self, ctx: AtoParser.Assign_stmtContext) -> BoundNode:
        field_ref_or_decl = ctx.field_reference_or_declaration()
        declaration_ctx = field_ref_or_decl.declaration_stmt()

        if declaration_ctx:
            target = self.visitDeclaration_stmt(declaration_ctx)
        else:
            target = self.visitField_reference(field_ref_or_decl.field_reference())

        assignable = ctx.assignable()

        match [
            assignable.new_stmt(),
            assignable.literal_physical(),
            assignable.arithmetic_expression(),
            assignable.string(),
            assignable.boolean_(),
        ]:
            case [new_stmt_ctx, None, None, None, None]:
                children = AST.AssignNewStmt.Children(
                    target=target,
                    type_ref=self.visitTypeReference(new_stmt_ctx.type_reference()),
                    source=self._extract_source(ctx),
                )

                attrs = AST.AssignNewStmt.Attrs()

                if template_ctx := new_stmt_ctx.template():
                    children["template"] = self.visitTemplate(template_ctx)

                if new_stmt_ctx.new_count():
                    attrs["new_count"] = self.visitNew_count(new_stmt_ctx.new_count())

                return AST.AssignNewStmt.create_subgraph(
                    g=self._graph, children=children, attrs=attrs
                )
            case [None, literal_physical_ctx, None, None, None]:
                return AST.AssignQuantityStmt.create_subgraph(
                    g=self._graph,
                    children=AST.AssignQuantityStmt.Children(
                        target=target,
                        quantity=self.visitLiteral_physical(literal_physical_ctx),
                        source=self._extract_source(ctx),
                    ),
                    attrs=AST.AssignQuantityStmt.Attrs(),
                )
            case [None, None, arithmetic_ctx, None, None]:
                return AST.AssignValueStmt.create_subgraph(
                    g=self._graph,
                    children=AST.AssignValueStmt.Children(
                        target=target,
                        value=self.visitArithmetic_expression(arithmetic_ctx),
                        source=self._extract_source(ctx),
                    ),
                    attrs=AST.AssignValueStmt.Attrs(),
                )
            case [None, None, None, string_ctx, None]:
                return AST.AssignValueStmt.create_subgraph(
                    g=self._graph,
                    children=AST.AssignValueStmt.Children(
                        target=target,
                        value=self.visitString(string_ctx),
                        source=self._extract_source(ctx),
                    ),
                    attrs=AST.AssignValueStmt.Attrs(),
                )
            case [None, None, None, None, boolean_ctx]:
                return AST.AssignValueStmt.create_subgraph(
                    g=self._graph,
                    children=AST.AssignValueStmt.Children(
                        target=target,
                        value=self.visitBoolean_(boolean_ctx),
                        source=self._extract_source(ctx),
                    ),
                    attrs=AST.AssignValueStmt.Attrs(),
                )
            case _:
                raise ValueError(f"Unexpected assignable context: {ctx.getText()}")

    # def visitLiteral_physical(
    #     self, ctx: AtoParser.Literal_physicalContext
    # ) -> AST.Quantity | AST.BilateralQuantity | AST.BoundedQuantity:
    #     if ctx.quantity():
    #         return self.visitQuantity(ctx.quantity())
    #     elif ctx.bilateral_quantity():
    #         return self.visitBilateral_quantity(ctx.bilateral_quantity())
    #     elif ctx.bound_quantity():
    #         return self.visitBound_quantity(ctx.bound_quantity())
    #     else:
    #         raise ValueError(f"Unexpected literal physical context: {ctx.getText()}")

    # def visitArithmetic_expression(
    #     self, ctx: AtoParser.Arithmetic_expressionContext
    # ) -> AST._Node:
    #     right = self.visitSum(ctx.sum_())
    #     if ctx.arithmetic_expression():
    #         left = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #         if token := ctx.OR_OP():
    #             operator = token.getText()
    #         elif token := ctx.AND_OP():
    #             operator = token.getText()
    #         else:
    #             raise ValueError(
    #                 f"Unexpected operator in arithmetic expression: {ctx.getText()}"
    #             )
    #         return self._make_binary(operator, left, right, ctx)
    #     return right

    # def visitSum(self, ctx: AtoParser.SumContext) -> AST._Node:
    #     right = self.visitTerm(ctx.term())
    #     if ctx.sum_():
    #         left = self.visitSum(ctx.sum_())
    #         if ctx.PLUS():
    #             operator = ctx.PLUS().getText()
    #         elif ctx.MINUS():
    #             operator = ctx.MINUS().getText()
    #         else:
    #             raise ValueError(f"Unexpected sum operator: {ctx.getText()}")
    #         return self._make_binary(operator, left, right, ctx)
    #     return right

    # def visitTerm(self, ctx: AtoParser.TermContext) -> AST._Node:
    #     right = self.visitPower(ctx.power())
    #     if ctx.term():
    #         left = self.visitTerm(ctx.term())
    #         if ctx.STAR():
    #             operator = ctx.STAR().getText()
    #         elif ctx.DIV():
    #             operator = ctx.DIV().getText()
    #         else:
    #             raise ValueError(f"Unexpected term operator: {ctx.getText()}")
    #         return self._make_binary(operator, left, right, ctx)
    #     return right

    # def visitPower(self, ctx: AtoParser.PowerContext) -> AST._Node:
    #     base = self.visitFunctional(ctx.functional(0))
    #     functionals = list(ctx.functional())
    #     if len(functionals) == 2:
    #         exponent = self.visitFunctional(functionals[1])
    #         return self._make_binary("**", base, exponent, ctx)
    #     return base

    # def visitFunctional(self, ctx: AtoParser.FunctionalContext) -> AST._Node:
    #     if ctx.name():
    #         name = self.visitName(ctx.name())
    #         args = [self.visitBound(bound_ctx) for bound_ctx in ctx.bound()]
    #         call = AST.FunctionCall.create(self._graph, name, args)
    #         AST.add(self._graph, call, self._extract_source(ctx))
    #         return call
    #     return self.visitBound(ctx.bound(0))

    # def visitBound(self, ctx: AtoParser.BoundContext) -> AST._Node:
    #     return self.visitAtom(ctx.atom())

    # def visitArithmetic_group(
    #     self, ctx: AtoParser.Arithmetic_groupContext
    # ) -> AST.GroupExpression:
    #     expression = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     group = AST.GroupExpression.create(self._graph, expression)
    #     AST.add(self._graph, group, self._extract_source(ctx))
    #     return group

    # def visitAtom(self, ctx: AtoParser.AtomContext) -> AST._Node:
    #     if ctx.field_reference():
    #         return self.visitField_reference(ctx.field_reference())
    #     if ctx.literal_physical():
    #         return self.visitLiteral_physical(ctx.literal_physical())
    #     if ctx.arithmetic_group():
    #         return self.visitArithmetic_group(ctx.arithmetic_group())
    #     raise ValueError(f"Unexpected atom context: {ctx.getText()}")

    # def visitComparison(
    #     self, ctx: AtoParser.ComparisonContext
    # ) -> AST.ComparisonExpression:
    #     left = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     clauses = [self.visitCompare_op_pair(pair) for pair in ctx.compare_op_pair()]
    #     comparison = AST.ComparisonExpression.create(self._graph, left, clauses)
    #     AST.add(self._graph, comparison, self._extract_source(ctx))
    #     return comparison

    # def visitCompare_op_pair(
    #     self, ctx: AtoParser.Compare_op_pairContext
    # ) -> AST.ComparisonClause:
    #     for accessor in (
    #         ctx.lt_arithmetic_or,
    #         ctx.gt_arithmetic_or,
    #         ctx.lt_eq_arithmetic_or,
    #         ctx.gt_eq_arithmetic_or,
    #         ctx.in_arithmetic_or,
    #         ctx.is_arithmetic_or,
    #     ):
    #         if sub := accessor():
    #             return self.visit(sub)
    #     raise ValueError(f"Unexpected compare op pair context: {ctx.getText()}")

    # def visitLt_arithmetic_or(
    #     self, ctx: AtoParser.Lt_arithmetic_orContext
    # ) -> AST.ComparisonClause:
    #     right = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     return self._make_comparison_clause("<", right, ctx)

    # def visitGt_arithmetic_or(
    #     self, ctx: AtoParser.Gt_arithmetic_orContext
    # ) -> AST.ComparisonClause:
    #     right = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     return self._make_comparison_clause(">", right, ctx)

    # def visitLt_eq_arithmetic_or(
    #     self, ctx: AtoParser.Lt_eq_arithmetic_orContext
    # ) -> AST.ComparisonClause:
    #     right = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     return self._make_comparison_clause("<=", right, ctx)

    # def visitGt_eq_arithmetic_or(
    #     self, ctx: AtoParser.Gt_eq_arithmetic_orContext
    # ) -> AST.ComparisonClause:
    #     right = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     return self._make_comparison_clause(">=", right, ctx)

    # def visitIn_arithmetic_or(
    #     self, ctx: AtoParser.In_arithmetic_orContext
    # ) -> AST.ComparisonClause:
    #     right = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     return self._make_comparison_clause("within", right, ctx)

    # def visitIs_arithmetic_or(
    #     self, ctx: AtoParser.Is_arithmetic_orContext
    # ) -> AST.ComparisonClause:
    #     right = self.visitArithmetic_expression(ctx.arithmetic_expression())
    #     return self._make_comparison_clause("is", right, ctx)

    # def visitQuantity(self, ctx: AtoParser.QuantityContext) -> AST.Quantity:
    #     number = self.visitNumber(ctx.number())
    #     unit = self.visitName(ctx.name()) if ctx.name() else None
    #     quantity = AST.Quantity.create(self._graph, number, unit)
    #     AST.add(self._graph, quantity, self._extract_source(ctx))
    #     return quantity

    # def visitDeclaration_stmt(
    #     self, ctx: AtoParser.Declaration_stmtContext
    # ) -> AST.DeclarationStmt:
    #     field_ref = self.visitField_reference(ctx.field_reference())
    #     type_ref = self.visitType_info(ctx.type_info()) if ctx.type_info() else None
    #     declaration = AST.DeclarationStmt.create(self._graph, field_ref, type_ref)
    #     AST.add(self._graph, declaration, self._extract_source(ctx))
    #     return declaration

    # def visitType_info(self, ctx: AtoParser.Type_infoContext) -> AST.TypeRef:
    #     unit_name = self.visitName(ctx.unit().name())
    #     type_ref = AST.TypeRef.create(self._graph, unit_name)
    #     AST.add(self._graph, type_ref, self._extract_source(ctx.unit()))
    #     return type_ref

    # def visitBilateral_quantity(
    #     self, ctx: AtoParser.Bilateral_quantityContext
    # ) -> AST.BilateralQuantity:
    #     bilateral_quantity = AST.BilateralQuantity.create(
    #         self._graph,
    #         self.visitQuantity(ctx.quantity()),
    #         self.visitBilateral_tolerance(ctx.bilateral_tolerance()),
    #     )
    #     AST.add(self._graph, bilateral_quantity, self._extract_source(ctx))
    #     return bilateral_quantity

    # def visitBilateral_tolerance(
    #     self, ctx: AtoParser.Bilateral_toleranceContext
    # ) -> AST.Quantity:
    #     if ctx.name():
    #         unit = self.visitName(ctx.name())
    #     elif ctx.PERCENT():
    #         unit = "%"
    #     else:
    #         raise ValueError(f"Unexpected bilateral tolerance context: {ctx.getText()}")

    #     number = self.visitNumber_signless(ctx.number_signless())
    #     quantity = AST.Quantity.create(self._graph, number, unit)
    #     AST.add(self._graph, quantity, self._extract_source(ctx))
    #     return quantity

    # def visitBound_quantity(
    #     self, ctx: AtoParser.Bound_quantityContext
    # ) -> AST.BoundedQuantity:
    #     quantities = list(ctx.quantity())
    #     start = self.visitQuantity(quantities[0])
    #     end = self.visitQuantity(quantities[1])
    #     bounded = AST.BoundedQuantity.create(self._graph, start, end)
    #     AST.add(self._graph, bounded, self._extract_source(ctx))
    #     return bounded

    # def visitTemplate(self, ctx: AtoParser.TemplateContext) -> AST.Template:
    #     args = [self.visitTemplate_arg(arg) for arg in ctx.template_arg()]
    #     template = AST.Template.create(self._graph, args)
    #     AST.add(self._graph, template, self._extract_source(ctx))
    #     return template

    # def visitTemplate_arg(self, ctx: AtoParser.Template_argContext) -> AST.TemplateArg:
    #     name = self.visitName(ctx.name())
    #     value_node = self.visitLiteral(ctx.literal())
    #     arg = AST.TemplateArg.create(self._graph, name, value_node)
    #     AST.add(self._graph, arg, self._extract_source(ctx))
    #     return arg

    # def visitLiteral(self, ctx: AtoParser.LiteralContext) -> AST.ASTNode:
    #     if ctx.string():
    #         return self.visitString(ctx.string())
    #     if ctx.boolean_():
    #         return self.visitBoolean_(ctx.boolean_())
    #     if ctx.number():
    #         return self.visitNumber(ctx.number())
    #     raise ValueError(f"Unexpected literal context: {ctx.getText()}")

    def visitTerminal(self, node: TerminalNodeImpl) -> str:
        return node.getText()

    def visitString(self, ctx: AtoParser.StringContext) -> BoundNode:
        return AST.String.create_subgraph(
            g=self._graph,
            children=AST.String.Children(source=self._extract_source(ctx)),
            attrs=AST.String.Attrs(
                string=self.visitTerminal(ctx.STRING())
            ),  # TODO: just the string contents, without quotes
        )

    # def visitNew_count(self, ctx: AtoParser.New_countContext) -> int:
    #     return self.visitNumber_hint_natural(ctx.number_hint_natural())

    # def visitBoolean_(self, ctx: AtoParser.Boolean_Context) -> AST.Boolean:
    #     value = ctx.TRUE() is not None
    #     node = AST.Boolean.create(self._graph, value)
    #     AST.add(self._graph, node, self._extract_source(ctx))
    #     return node

    # def visitNumber_signless(self, ctx: AtoParser.Number_signlessContext) -> AST.Number:
    #     number = AST.Number.create(self._graph, self._parse_decimal(ctx.getText()))
    #     AST.add(self._graph, number, self._extract_source(ctx))
    #     return number

    # def visitNumber(self, ctx: AtoParser.NumberContext) -> AST.Number:
    #     number = AST.Number.create(self._graph, self._parse_decimal(ctx.getText()))
    #     AST.add(self._graph, number, self._extract_source(ctx))
    #     return number

    # def visitNumber_hint_natural(
    #     self, ctx: AtoParser.Number_hint_naturalContext
    # ) -> int:
    #     text = ctx.getText()
    #     return self._parse_int(text)

    # def visitNumber_hint_integer(
    #     self, ctx: AtoParser.Number_hint_integerContext
    # ) -> int:
    #     text = ctx.getText()
    #     return self._parse_int(text)

    # def visitMif(self, ctx: AtoParser.MifContext) -> AST.ASTNode:
    #     return self.visitConnectable(ctx.connectable())

    # def visitBridgeable(self, ctx: AtoParser.BridgeableContext) -> AST.ASTNode:
    #     return self.visitConnectable(ctx.connectable())

    # def visitConnectable(self, ctx: AtoParser.ConnectableContext) -> AST.ASTNode:
    #     if ctx.field_reference():
    #         return self.visitField_reference(ctx.field_reference())
    #     if ctx.signaldef_stmt():
    #         return self.visitSignaldef_stmt(ctx.signaldef_stmt())
    #     if ctx.pindef_stmt():
    #         return self.visitPindef_stmt(ctx.pindef_stmt())
    #     raise ValueError(f"Unexpected connectable: {ctx.getText()}")

    # def visitConnect_stmt(self, ctx: AtoParser.Connect_stmtContext) -> AST.ConnectStmt:
    #     left, right = [self.visitMif(c) for c in ctx.mif()]
    #     connect_stmt = AST.ConnectStmt.create(self._graph, left, right)
    #     AST.add(self._graph, connect_stmt, self._extract_source(ctx))
    #     return connect_stmt

    # def visitDirected_connect_stmt(self, ctx: AtoParser.Directed_connect_stmtContext):
    #     if ctx.SPERM():
    #         direction = AST.DirectedConnectStmt.Direction.RIGHT
    #     elif ctx.LSPERM():
    #         direction = AST.DirectedConnectStmt.Direction.LEFT
    #     else:
    #         raise ValueError(f"Unexpected directed connect statement: {ctx.getText()}")

    #     match bridgeables := [self.visitBridgeable(c) for c in ctx.bridgeable()]:
    #         case [left]:
    #             right = self.visitDirected_connect_stmt(ctx.directed_connect_stmt())
    #         case [left, right]:
    #             pass
    #         case _:
    #             raise ValueError(f"Unexpected bridgeables: {bridgeables}")

    #     directed_connect_stmt = AST.DirectedConnectStmt.create(
    #         self._graph,
    #         left,
    #         right,
    #         direction,
    #     )
    #     AST.add(self._graph, directed_connect_stmt, self._extract_source(ctx))
    #     return directed_connect_stmt


def build_file(source_file: Path) -> BoundNode:
    graph = GraphView.create()
    tree = parse_text_as_file(source_file.read_text(), source_file)
    return Visitor(graph, source_file).visit(tree)
