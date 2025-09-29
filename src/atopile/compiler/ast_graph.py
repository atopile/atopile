"""
Generates an AST graph from the ANTLR4-generated AST.

Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter

import atopile.compiler.ast_types as AST
from atopile.compiler.parse import parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor


class Visitor(AtoParserVisitor):
    """
    Generates a native compiler graph from the ANTLR4-generated AST, with attached
    source context.
    """

    @staticmethod
    def _extract_source(ctx: ParserRuleContext) -> AST.SourceChunk:
        start_token = ctx.start
        stop_token = ctx.stop

        token_stream = ctx.parser.getInputStream()  # type: ignore

        rewriter = AtoRewriter(token_stream)

        text = rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start_token.tokenIndex,  # type: ignore
            stop_token.tokenIndex,  # type: ignore
        )

        return AST.SourceChunk(
            text,
            AST.FileLocation(
                start_token.line,  # type: ignore
                start_token.column,  # type: ignore
                stop_token.line,  # type: ignore
                stop_token.column,  # type: ignore
            ),
        )

    def _visitScopeChildren(self, ctx: ParserRuleContext, scope: AST.Scope) -> None:
        for child in ctx.getChildren():
            match node_or_nodes := self.visit(child):
                case AST._Node() | AST.SourceChunk():
                    scope.add(node_or_nodes)
                case Iterable():
                    for node in node_or_nodes:
                        # FIXME: assert is ASTNode
                        if isinstance(node, AST._Node):
                            scope.add(node)
                case None:
                    pass
                case _:
                    raise ValueError(f"Unexpected node type: {type(node_or_nodes)}")

    @staticmethod
    def _parse_int(text: str) -> int:
        normalized = text.replace("_", "")
        return int(normalized, 0)

    @staticmethod
    def _parse_decimal(text: str) -> Decimal:
        normalized = text.replace("_", "")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            # Fall back to Python's numeric parser for forms Decimal cannot parse directly
            return Decimal(str(int(normalized, 0)))

    def _make_binary(
        self,
        operator: str,
        left: AST._Node,
        right: AST._Node,
        ctx: ParserRuleContext,
    ) -> AST.BinaryExpression:
        node = AST.BinaryExpression(operator, left, right)
        node.add(self._extract_source(ctx))
        return node

    def _make_comparison_clause(
        self, operator: str, right: AST._Node, ctx: ParserRuleContext
    ) -> AST.ComparisonClause:
        clause = AST.ComparisonClause(operator, right)
        clause.add(self._extract_source(ctx))
        return clause

    def visitName(self, ctx: AtoParser.NameContext) -> str:
        return ctx.getText()

    def visitTypeReference(self, ctx: AtoParser.Type_referenceContext) -> AST.TypeRef:
        type_ref = AST.TypeRef(self.visitName(ctx.name()))
        type_ref.add(self._extract_source(ctx))
        return type_ref

    def visitArrayIndex(self, ctx: AtoParser.Array_indexContext) -> str | int | None:
        if key := ctx.key():
            text = key.getText()
            try:
                return self._parse_int(text)
            except ValueError:
                return text
        return None

    def visitBlocktype(
        self, ctx: AtoParser.BlocktypeContext
    ) -> AST.BlockDefinition.BlockType:
        return AST.BlockDefinition.BlockType(ctx.getText())

    def visitBlockdef(self, ctx: AtoParser.BlockdefContext) -> AST.BlockDefinition:
        block_type = self.visitBlocktype(ctx.blocktype())

        block_definition = AST.BlockDefinition(
            block_type, self.visitTypeReference(ctx.type_reference())
        )
        block_definition.add(self._extract_source(ctx))
        if super_type_ref := ctx.blockdef_super():
            block_definition.add(
                self.visitTypeReference(super_type_ref.type_reference())
            )

        self._visitScopeChildren(ctx.block(), block_definition.scope)

        return block_definition

    def visitFile_input(self, ctx: AtoParser.File_inputContext) -> AST.File:
        file = AST.File()
        # TODO: remove this and push all source chunks to leaf nodes
        # currently difficult due to comments going to a hidden channel
        file.source = self._extract_source(ctx)

        for child in ctx.getChildren():
            match node_or_nodes := self.visit(child):
                case AST._Node():
                    file.add(node_or_nodes)
                case Iterable():
                    # for node in node_or_nodes:
                    #     assert isinstance(node, AST.ASTNode), "missing a visitor method"
                    #     file.add(node)
                    pass
                case None:
                    pass
                case _:
                    raise ValueError(f"Unexpected node type: {type(node_or_nodes)}")

        return file

    def visitSimple_stmts(
        self, ctx: AtoParser.Simple_stmtsContext
    ) -> Iterable[AST._Node]:
        return itertools.chain.from_iterable(
            (
                child
                if (isinstance(child, Iterable) and not isinstance(child, str))
                else [child]
                for child in (self.visit(child) for child in ctx.simple_stmt())
            )
        )

    def visitPragma_stmt(self, ctx: AtoParser.Pragma_stmtContext) -> AST.PragmaStmt:
        pragma = AST.PragmaStmt(ctx.PRAGMA().getText().strip())
        pragma.add(self._extract_source(ctx))
        return pragma

    def visitImport_stmt(self, ctx: AtoParser.Import_stmtContext) -> AST.ImportStmt:
        if ctx.string():
            string_node = self.visitString(ctx.string())
            from_path = AST.ImportPath(string_node.value)
            from_path.add(self._extract_source(ctx.string()))
        else:
            from_path = None

        type_ref = self.visitTypeReference(ctx.type_reference())

        import_stmt = AST.ImportStmt(from_path, type_ref)
        import_stmt.add(self._extract_source(ctx))

        return import_stmt

    def visitRetype_stmt(self, ctx: AtoParser.Retype_stmtContext) -> AST.RetypeStmt:
        field_ref = self.visitField_reference(ctx.field_reference())
        type_ref = self.visitTypeReference(ctx.type_reference())
        retype = AST.RetypeStmt(field_ref, type_ref)
        retype.add(self._extract_source(ctx))
        return retype

    def visitPin_declaration(
        self, ctx: AtoParser.Pin_declarationContext
    ) -> AST.PinDeclaration:
        return self.visitPin_stmt(ctx.pin_stmt())

    def visitPindef_stmt(self, ctx: AtoParser.Pindef_stmtContext) -> AST.PinDeclaration:
        return self.visitPin_stmt(ctx.pin_stmt())

    def visitPin_stmt(self, ctx: AtoParser.Pin_stmtContext) -> AST.PinDeclaration:
        if ctx.name():
            value = self.visitName(ctx.name())
            pin = AST.PinDeclaration(AST.PinDeclaration.Kind.NAME, value)
        elif ctx.number_hint_natural():
            number_ctx = ctx.number_hint_natural().number_signless()
            number_node = self.visitNumber_signless(number_ctx)
            pin = AST.PinDeclaration(
                AST.PinDeclaration.Kind.NUMBER,
                int(number_node.value),
                number_node,
            )
        elif ctx.string():
            string_node = self.visitString(ctx.string())
            pin = AST.PinDeclaration(
                AST.PinDeclaration.Kind.STRING,
                string_node.value,
                string_node,
            )
        else:
            raise ValueError(f"Unexpected pin statement: {ctx.getText()}")

        pin.add(self._extract_source(ctx))
        return pin

    def visitSignaldef_stmt(
        self, ctx: AtoParser.Signaldef_stmtContext
    ) -> AST.SignaldefStmt:
        name = self.visitName(ctx.name())
        signal = AST.SignaldefStmt(name)
        signal.add(self._extract_source(ctx))
        return signal

    def visitString_stmt(self, ctx: AtoParser.String_stmtContext) -> AST.StringStmt:
        string = self.visitString(ctx.string())
        stmt = AST.StringStmt(string)
        stmt.add(self._extract_source(ctx))
        return stmt

    def visitPass_stmt(self, ctx: AtoParser.Pass_stmtContext) -> AST.PassStmt:
        stmt = AST.PassStmt()
        stmt.add(self._extract_source(ctx))
        return stmt

    def visitAssert_stmt(self, ctx: AtoParser.Assert_stmtContext) -> AST.AssertStmt:
        comparison = self.visitComparison(ctx.comparison())
        stmt = AST.AssertStmt(comparison)
        stmt.add(self._extract_source(ctx))
        return stmt

    def visitTrait_stmt(self, ctx: AtoParser.Trait_stmtContext) -> AST.TraitStmt:
        target = (
            self.visitField_reference(ctx.field_reference())
            if ctx.field_reference()
            else None
        )
        type_ref = self.visitTypeReference(ctx.type_reference())
        constructor = (
            self.visitConstructor(ctx.constructor()) if ctx.constructor() else None
        )
        template = self.visitTemplate(ctx.template()) if ctx.template() else None
        trait = AST.TraitStmt(type_ref, target, constructor, template)
        trait.add(self._extract_source(ctx))
        return trait

    def visitConstructor(self, ctx: AtoParser.ConstructorContext) -> str:
        return self.visitName(ctx.name())

    def visitFor_stmt(self, ctx: AtoParser.For_stmtContext) -> AST.ForStmt:
        target = self.visitName(ctx.name())
        iterable = self.visitIterable_references(ctx.iterable_references())
        for_stmt = AST.ForStmt(target, iterable)
        for_stmt.add(self._extract_source(ctx))
        self._visitScopeChildren(ctx.block(), for_stmt.scope)
        return for_stmt

    def visitIterable_references(
        self, ctx: AtoParser.Iterable_referencesContext
    ) -> AST._Node:
        if ctx.field_reference():
            field_ref = self.visitField_reference(ctx.field_reference())
            if ctx.slice():
                slice_node = self.visitSlice(ctx.slice())
                iterable_ref = AST.IterableFieldRef(field_ref, slice_node)
                iterable_ref.add(self._extract_source(ctx))
                return iterable_ref
            return field_ref
        if ctx.list_literal_of_field_references():
            return self.visitList_literal_of_field_references(
                ctx.list_literal_of_field_references()
            )
        raise ValueError(f"Unexpected iterable references: {ctx.getText()}")

    def visitList_literal_of_field_references(
        self, ctx: AtoParser.List_literal_of_field_referencesContext
    ) -> AST.FieldRefList:
        field_refs = [self.visitField_reference(fr) for fr in ctx.field_reference()]
        literal = AST.FieldRefList(field_refs)
        literal.add(self._extract_source(ctx))
        return literal

    def visitSlice(self, ctx: AtoParser.SliceContext) -> AST.Slice:
        if ctx.DOUBLE_COLON():
            start = None
            stop = None
            step = self.visitSlice_step(ctx.slice_step()) if ctx.slice_step() else None
        else:
            start = (
                self.visitSlice_start(ctx.slice_start()) if ctx.slice_start() else None
            )
            stop = self.visitSlice_stop(ctx.slice_stop()) if ctx.slice_stop() else None
            step = self.visitSlice_step(ctx.slice_step()) if ctx.slice_step() else None
        slice_node = AST.Slice(start, stop, step)
        slice_node.add(self._extract_source(ctx))
        return slice_node

    def visitSlice_start(self, ctx: AtoParser.Slice_startContext) -> int:
        return self.visitNumber_hint_integer(ctx.number_hint_integer())

    def visitSlice_stop(self, ctx: AtoParser.Slice_stopContext) -> int:
        return self.visitNumber_hint_integer(ctx.number_hint_integer())

    def visitSlice_step(self, ctx: AtoParser.Slice_stepContext) -> int:
        return self.visitNumber_hint_integer(ctx.number_hint_integer())

    def visitField_reference_part(
        self, ctx: AtoParser.Field_reference_partContext
    ) -> AST.FieldRefPart:
        key = None
        if ctx.array_index():
            key = self.visitArrayIndex(ctx.array_index())
        field_ref_part = AST.FieldRefPart(self.visitName(ctx.name()), key)
        field_ref_part.add(self._extract_source(ctx))
        return field_ref_part

    def visitField_reference(
        self, ctx: AtoParser.Field_referenceContext
    ) -> AST.FieldRef:
        field_ref = AST.FieldRef()
        field_ref.add(self._extract_source(ctx))
        for part in ctx.field_reference_part():
            field_ref_part = self.visitField_reference_part(part)
            field_ref.add(field_ref_part)
        if pin_ctx := ctx.pin_reference_end():
            number_ctx = pin_ctx.number_hint_natural()
            field_ref.pin = self.visitNumber_hint_natural(number_ctx)
        return field_ref

    def visitAssign_stmt(
        self, ctx: AtoParser.Assign_stmtContext
    ) -> AST.AssignNewStmt | AST.AssignQuantityStmt | AST.AssignValueStmt | None:
        field_ref_or_decl = ctx.field_reference_or_declaration()
        declaration_ctx = field_ref_or_decl.declaration_stmt()

        if declaration_ctx:
            target: AST.FieldRef | AST.DeclarationStmt = self.visitDeclaration_stmt(
                declaration_ctx
            )
        else:
            target = self.visitField_reference(field_ref_or_decl.field_reference())

        assignable = ctx.assignable()

        if new_stmt_ctx := assignable.new_stmt():
            type_ref = self.visitTypeReference(new_stmt_ctx.type_reference())
            template = (
                self.visitTemplate(new_stmt_ctx.template())
                if new_stmt_ctx.template()
                else None
            )
            count = (
                self.visitNew_count(new_stmt_ctx.new_count())
                if new_stmt_ctx.new_count()
                else None
            )
            new_stmt = AST.AssignNewStmt(target, type_ref, template, count)
            new_stmt.add(self._extract_source(ctx))
            return new_stmt
        if literal_physical_ctx := assignable.literal_physical():
            quantity = self.visitLiteral_physical(literal_physical_ctx)
            assign_quantity_stmt = AST.AssignQuantityStmt(target, quantity)
            assign_quantity_stmt.add(self._extract_source(ctx))
            return assign_quantity_stmt
        if string_ctx := assignable.string():
            string_value = self.visitString(string_ctx)
            assign_value_stmt = AST.AssignValueStmt(target, string_value)
            assign_value_stmt.add(self._extract_source(ctx))
            return assign_value_stmt
        if boolean_ctx := assignable.boolean_():
            boolean_value = self.visitBoolean_(boolean_ctx)
            assign_value_stmt = AST.AssignValueStmt(target, boolean_value)
            assign_value_stmt.add(self._extract_source(ctx))
            return assign_value_stmt
        if arithmetic_ctx := assignable.arithmetic_expression():
            expression_value = self.visitArithmetic_expression(arithmetic_ctx)
            assign_value_stmt = AST.AssignValueStmt(target, expression_value)
            assign_value_stmt.add(self._extract_source(ctx))
            return assign_value_stmt

        return None

    def visitLiteral_physical(
        self, ctx: AtoParser.Literal_physicalContext
    ) -> AST.Quantity | AST.BilateralQuantity | AST.BoundedQuantity:
        if ctx.quantity():
            return self.visitQuantity(ctx.quantity())
        elif ctx.bilateral_quantity():
            return self.visitBilateral_quantity(ctx.bilateral_quantity())
        elif ctx.bound_quantity():
            return self.visitBound_quantity(ctx.bound_quantity())
        else:
            raise ValueError(f"Unexpected literal physical context: {ctx.getText()}")

    def visitArithmetic_expression(
        self, ctx: AtoParser.Arithmetic_expressionContext
    ) -> AST._Node:
        right = self.visitSum(ctx.sum_())
        if ctx.arithmetic_expression():
            left = self.visitArithmetic_expression(ctx.arithmetic_expression())
            if token := ctx.OR_OP():
                operator = token.getText()
            elif token := ctx.AND_OP():
                operator = token.getText()
            else:
                raise ValueError(
                    f"Unexpected operator in arithmetic expression: {ctx.getText()}"
                )
            return self._make_binary(operator, left, right, ctx)
        return right

    def visitSum(self, ctx: AtoParser.SumContext) -> AST._Node:
        right = self.visitTerm(ctx.term())
        if ctx.sum_():
            left = self.visitSum(ctx.sum_())
            if ctx.PLUS():
                operator = ctx.PLUS().getText()
            elif ctx.MINUS():
                operator = ctx.MINUS().getText()
            else:
                raise ValueError(f"Unexpected sum operator: {ctx.getText()}")
            return self._make_binary(operator, left, right, ctx)
        return right

    def visitTerm(self, ctx: AtoParser.TermContext) -> AST._Node:
        right = self.visitPower(ctx.power())
        if ctx.term():
            left = self.visitTerm(ctx.term())
            if ctx.STAR():
                operator = ctx.STAR().getText()
            elif ctx.DIV():
                operator = ctx.DIV().getText()
            else:
                raise ValueError(f"Unexpected term operator: {ctx.getText()}")
            return self._make_binary(operator, left, right, ctx)
        return right

    def visitPower(self, ctx: AtoParser.PowerContext) -> AST._Node:
        base = self.visitFunctional(ctx.functional(0))
        functionals = list(ctx.functional())
        if len(functionals) == 2:
            exponent = self.visitFunctional(functionals[1])
            return self._make_binary("**", base, exponent, ctx)
        return base

    def visitFunctional(self, ctx: AtoParser.FunctionalContext) -> AST._Node:
        if ctx.name():
            name = self.visitName(ctx.name())
            args = [self.visitBound(bound_ctx) for bound_ctx in ctx.bound()]
            call = AST.FunctionCall(name, args)
            call.add(self._extract_source(ctx))
            return call
        return self.visitBound(ctx.bound(0))

    def visitBound(self, ctx: AtoParser.BoundContext) -> AST._Node:
        return self.visitAtom(ctx.atom())

    def visitArithmetic_group(
        self, ctx: AtoParser.Arithmetic_groupContext
    ) -> AST.GroupExpression:
        expression = self.visitArithmetic_expression(ctx.arithmetic_expression())
        group = AST.GroupExpression(expression)
        group.add(self._extract_source(ctx))
        return group

    def visitAtom(self, ctx: AtoParser.AtomContext) -> AST._Node:
        if ctx.field_reference():
            return self.visitField_reference(ctx.field_reference())
        if ctx.literal_physical():
            return self.visitLiteral_physical(ctx.literal_physical())
        if ctx.arithmetic_group():
            return self.visitArithmetic_group(ctx.arithmetic_group())
        raise ValueError(f"Unexpected atom context: {ctx.getText()}")

    def visitComparison(
        self, ctx: AtoParser.ComparisonContext
    ) -> AST.ComparisonExpression:
        left = self.visitArithmetic_expression(ctx.arithmetic_expression())
        clauses = [self.visitCompare_op_pair(pair) for pair in ctx.compare_op_pair()]
        comparison = AST.ComparisonExpression(left, clauses)
        comparison.add(self._extract_source(ctx))
        return comparison

    def visitCompare_op_pair(
        self, ctx: AtoParser.Compare_op_pairContext
    ) -> AST.ComparisonClause:
        for accessor in (
            ctx.lt_arithmetic_or,
            ctx.gt_arithmetic_or,
            ctx.lt_eq_arithmetic_or,
            ctx.gt_eq_arithmetic_or,
            ctx.in_arithmetic_or,
            ctx.is_arithmetic_or,
        ):
            if sub := accessor():
                return self.visit(sub)
        raise ValueError(f"Unexpected compare op pair context: {ctx.getText()}")

    def visitLt_arithmetic_or(
        self, ctx: AtoParser.Lt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        right = self.visitArithmetic_expression(ctx.arithmetic_expression())
        return self._make_comparison_clause("<", right, ctx)

    def visitGt_arithmetic_or(
        self, ctx: AtoParser.Gt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        right = self.visitArithmetic_expression(ctx.arithmetic_expression())
        return self._make_comparison_clause(">", right, ctx)

    def visitLt_eq_arithmetic_or(
        self, ctx: AtoParser.Lt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        right = self.visitArithmetic_expression(ctx.arithmetic_expression())
        return self._make_comparison_clause("<=", right, ctx)

    def visitGt_eq_arithmetic_or(
        self, ctx: AtoParser.Gt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        right = self.visitArithmetic_expression(ctx.arithmetic_expression())
        return self._make_comparison_clause(">=", right, ctx)

    def visitIn_arithmetic_or(
        self, ctx: AtoParser.In_arithmetic_orContext
    ) -> AST.ComparisonClause:
        right = self.visitArithmetic_expression(ctx.arithmetic_expression())
        return self._make_comparison_clause("within", right, ctx)

    def visitIs_arithmetic_or(
        self, ctx: AtoParser.Is_arithmetic_orContext
    ) -> AST.ComparisonClause:
        right = self.visitArithmetic_expression(ctx.arithmetic_expression())
        return self._make_comparison_clause("is", right, ctx)

    def visitQuantity(self, ctx: AtoParser.QuantityContext) -> AST.Quantity:
        number = self.visitNumber(ctx.number())
        unit = self.visitName(ctx.name()) if ctx.name() else None
        quantity = AST.Quantity(number, unit)
        quantity.add(self._extract_source(ctx))
        return quantity

    def visitDeclaration_stmt(
        self, ctx: AtoParser.Declaration_stmtContext
    ) -> AST.DeclarationStmt:
        field_ref = self.visitField_reference(ctx.field_reference())
        type_ref = self.visitType_info(ctx.type_info()) if ctx.type_info() else None
        declaration = AST.DeclarationStmt(field_ref, type_ref)
        declaration.add(self._extract_source(ctx))
        return declaration

    def visitType_info(self, ctx: AtoParser.Type_infoContext) -> AST.TypeRef:
        unit_name = self.visitName(ctx.unit().name())
        type_ref = AST.TypeRef(unit_name)
        type_ref.add(self._extract_source(ctx.unit()))
        return type_ref

    def visitBilateral_quantity(
        self, ctx: AtoParser.Bilateral_quantityContext
    ) -> AST.BilateralQuantity:
        bilateral_quantity = AST.BilateralQuantity(
            self.visitQuantity(ctx.quantity()),
            self.visitBilateral_tolerance(ctx.bilateral_tolerance()),
        )
        bilateral_quantity.add(self._extract_source(ctx))
        return bilateral_quantity

    def visitBilateral_tolerance(
        self, ctx: AtoParser.Bilateral_toleranceContext
    ) -> AST.Quantity:
        if ctx.name():
            unit = self.visitName(ctx.name())
        elif ctx.PERCENT():
            unit = "%"
        else:
            raise ValueError(f"Unexpected bilateral tolerance context: {ctx.getText()}")

        number = self.visitNumber_signless(ctx.number_signless())
        quantity = AST.Quantity(number, unit)
        quantity.add(self._extract_source(ctx))
        return quantity

    def visitBound_quantity(
        self, ctx: AtoParser.Bound_quantityContext
    ) -> AST.BoundedQuantity:
        quantities = list(ctx.quantity())
        start = self.visitQuantity(quantities[0])
        end = self.visitQuantity(quantities[1])
        bounded = AST.BoundedQuantity(start, end)
        bounded.add(self._extract_source(ctx))
        return bounded

    def visitTemplate(self, ctx: AtoParser.TemplateContext) -> AST.Template:
        args = [self.visitTemplate_arg(arg) for arg in ctx.template_arg()]
        template = AST.Template(args)
        template.add(self._extract_source(ctx))
        return template

    def visitTemplate_arg(self, ctx: AtoParser.Template_argContext) -> AST.TemplateArg:
        name = self.visitName(ctx.name())
        value_node = self.visitLiteral(ctx.literal())
        arg = AST.TemplateArg(name, value_node)
        arg.add(self._extract_source(ctx))
        return arg

    def visitLiteral(self, ctx: AtoParser.LiteralContext) -> AST.ASTNode:
        if ctx.string():
            return self.visitString(ctx.string())
        if ctx.boolean_():
            return self.visitBoolean_(ctx.boolean_())
        if ctx.number():
            return self.visitNumber(ctx.number())
        raise ValueError(f"Unexpected literal context: {ctx.getText()}")

    def visitString(self, ctx: AtoParser.StringContext) -> AST.String:
        node = AST.String(ctx.getText())
        node.add(self._extract_source(ctx))
        return node

    def visitNew_count(self, ctx: AtoParser.New_countContext) -> int:
        return self.visitNumber_hint_natural(ctx.number_hint_natural())

    def visitBoolean_(self, ctx: AtoParser.Boolean_Context) -> AST.Boolean:
        value = ctx.TRUE() is not None
        node = AST.Boolean(value)
        node.add(self._extract_source(ctx))
        return node

    def visitNumber_signless(self, ctx: AtoParser.Number_signlessContext) -> AST.Number:
        number = AST.Number(self._parse_decimal(ctx.getText()))
        number.add(self._extract_source(ctx))
        return number

    def visitNumber(self, ctx: AtoParser.NumberContext) -> AST.Number:
        number = AST.Number(self._parse_decimal(ctx.getText()))
        number.add(self._extract_source(ctx))
        return number

    def visitNumber_hint_natural(
        self, ctx: AtoParser.Number_hint_naturalContext
    ) -> int:
        text = ctx.getText()
        return self._parse_int(text)

    def visitNumber_hint_integer(
        self, ctx: AtoParser.Number_hint_integerContext
    ) -> int:
        text = ctx.getText()
        return self._parse_int(text)

    def visitMif(self, ctx: AtoParser.MifContext) -> AST.ASTNode:
        return self.visitConnectable(ctx.connectable())

    def visitBridgeable(self, ctx: AtoParser.BridgeableContext) -> AST.ASTNode:
        return self.visitConnectable(ctx.connectable())

    def visitConnectable(self, ctx: AtoParser.ConnectableContext) -> AST.ASTNode:
        if ctx.field_reference():
            return self.visitField_reference(ctx.field_reference())
        if ctx.signaldef_stmt():
            return self.visitSignaldef_stmt(ctx.signaldef_stmt())
        if ctx.pindef_stmt():
            return self.visitPindef_stmt(ctx.pindef_stmt())
        raise ValueError(f"Unexpected connectable: {ctx.getText()}")

    def visitConnect_stmt(self, ctx: AtoParser.Connect_stmtContext) -> AST.ConnectStmt:
        left, right = [self.visitMif(c) for c in ctx.mif()]
        connect_stmt = AST.ConnectStmt(left, right)
        connect_stmt.add(self._extract_source(ctx))
        return connect_stmt

    def visitDirected_connect_stmt(self, ctx: AtoParser.Directed_connect_stmtContext):
        if ctx.SPERM():
            direction = AST.DirectedConnectStmt.Direction.RIGHT
        elif ctx.LSPERM():
            direction = AST.DirectedConnectStmt.Direction.LEFT
        else:
            raise ValueError(f"Unexpected directed connect statement: {ctx.getText()}")

        match bridgeables := [self.visitBridgeable(c) for c in ctx.bridgeable()]:
            case [left]:
                right = self.visitDirected_connect_stmt(ctx.directed_connect_stmt())
            case [left, right]:
                pass
            case _:
                raise ValueError(f"Unexpected bridgeables: {bridgeables}")

        directed_connect_stmt = AST.DirectedConnectStmt(left, right, direction)
        directed_connect_stmt.add(self._extract_source(ctx))
        return directed_connect_stmt


def build_file(source_file: Path) -> AST.File:
    tree = parse_text_as_file(source_file.read_text(), source_file)
    visitor = Visitor()
    file = visitor.visit(tree)
    file.path = source_file
    return file
