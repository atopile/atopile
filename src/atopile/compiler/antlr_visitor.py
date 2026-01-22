import itertools
from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from antlr4.tree.Tree import TerminalNodeImpl

import atopile.compiler.ast_types as AST
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from atopile.compiler import DslException
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor
from atopile.exceptions import DeprecatedException, downgrade
from atopile.logging import get_logger

logger = get_logger(__name__)


class ANTLRVisitor(AtoParserVisitor):
    """
    Generates a native AST graph from the ANTLR4-generated AST, with attached source
    context.

    Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
    """

    def __init__(
        self, graph: graph.GraphView, type_graph: fbrk.TypeGraph, file_path: Path | None
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
        token_stream = ctx.parser.getInputStream()  # type: ignore[reportOptionalMemberAccess]
        text = AtoRewriter(token_stream).getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start_token.tokenIndex,  # type: ignore[reportOptionalMemberAccess]
            stop_token.tokenIndex,  # type: ignore[reportOptionalMemberAccess]
        )
        return AST.SourceInfo(
            start_line=start_token.line,  # type: ignore[reportOptionalMemberAccess]
            start_col=start_token.column,  # type: ignore[reportOptionalMemberAccess]
            end_line=stop_token.line,  # type: ignore[reportOptionalMemberAccess]
            end_col=stop_token.column,  # type: ignore[reportOptionalMemberAccess]
            text=text,
            filepath=str(self._file_path) if self._file_path else None,
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

    def visitStmt(self, ctx: AtoParser.StmtContext) -> Iterable[AST.is_statement]:
        match (ctx.pragma_stmt(), ctx.simple_stmts(), ctx.compound_stmt()):
            case (pragma_stmt, None, None):
                return [self.visitPragma_stmt(pragma_stmt)]
            case (None, simple_stmts, None):
                return self.visitSimple_stmts(simple_stmts)
            case (None, None, compound_stmt):
                return [self.visitCompound_stmt(compound_stmt)]
            case _:
                assert False, f"Unexpected statement: {ctx.getText()}"

    def visitStmts(
        self, ctxs: Sequence[AtoParser.StmtContext]
    ) -> Iterable[AST.is_statement]:
        return itertools.chain.from_iterable(
            (child for child in self.visitStmt(child) if child is not None)
            for child in ctxs
        )

    def visitBlock(self, ctx: AtoParser.BlockContext) -> Iterable[AST.is_statement]:
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
            source_info=self._extract_source_info(ctx),
            path=str(self._file_path) if self._file_path is not None else "",
            stmts=self.visitStmts(ctx.stmt()),
        )

    def visitSimple_stmts(
        self, ctx: AtoParser.Simple_stmtsContext
    ) -> Iterable[AST.is_statement]:
        return itertools.chain.from_iterable(
            (
                child
                if (isinstance(child, Iterable) and not isinstance(child, str))
                else [child]
                for child in (self.visit(child) for child in ctx.simple_stmt())
            )
        )

    def visitSimple_stmt(
        self, ctx: AtoParser.Simple_stmtContext
    ) -> AST.is_statement | list[AST.is_statement]:
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

        stmt = self.visit(stmt_ctx)
        # Handle multi-import statements which return a list of ImportStmt
        if isinstance(stmt, list):
            return [s._is_statement.get() for s in stmt]
        return stmt._is_statement.get()

    def visitCompound_stmt(
        self, ctx: AtoParser.Compound_stmtContext
    ) -> AST.is_statement:
        match (ctx.blockdef(), ctx.for_stmt()):
            case (blockdef_ctx, None):
                block_def = self.visitBlockdef(blockdef_ctx)
                return block_def._is_statement.get()
            case (None, for_ctx):
                for_stmt = self.visitFor_stmt(for_ctx)
                return for_stmt._is_statement.get()
            case _:
                raise ValueError(f"Unexpected compound statement: {ctx.getText()}")

    def visitPragma_stmt(self, ctx: AtoParser.Pragma_stmtContext) -> AST.is_statement:
        pragma_stmt = self._new(AST.PragmaStmt).setup(
            source_info=self._extract_source_info(ctx),
            pragma=self.visit(ctx.PRAGMA()),
        )
        return pragma_stmt._is_statement.get()

    def visitImport_stmt(
        self, ctx: AtoParser.Import_stmtContext
    ) -> AST.ImportStmt | list[AST.ImportStmt]:
        type_refs = ctx.type_reference()
        path_info = self.visitString(ctx.string()) if ctx.string() else None
        source_info = self._extract_source_info(ctx)

        # Handle multiple imports on one line (deprecated syntax)
        if len(type_refs) > 1:
            with downgrade(DeprecatedException):
                raise DeprecatedException(
                    "Multiple imports on one line is deprecated. "
                    "Please use separate import statements for each module. "
                    f"Found: {ctx.getText()}"
                )
            return [
                self._new(AST.ImportStmt).setup(
                    source_info=source_info,
                    type_ref_name=name,
                    type_ref_source_info=ref_source_info,
                    path_info=path_info,
                )
                for name, ref_source_info in (
                    self.visitType_reference(ref) for ref in type_refs
                )
            ]

        # Single import (normal case)
        type_ref_name, type_ref_source_info = self.visitType_reference(type_refs[0])
        return self._new(AST.ImportStmt).setup(
            source_info=source_info,
            type_ref_name=type_ref_name,
            type_ref_source_info=type_ref_source_info,
            path_info=path_info,
        )

    def visitRetype_stmt(self, ctx: AtoParser.Retype_stmtContext) -> AST.RetypeStmt:
        type_ref_name, type_ref_source_info = self.visitType_reference(
            ctx.type_reference()
        )
        return self._new(AST.RetypeStmt).setup(
            source_info=self._extract_source_info(ctx),
            target_field_ref=self.visitField_reference(ctx.field_reference()),
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
            source_info=self._extract_source_info(ctx),
            kind=kind,
            label_value=label_value,
        )

    def visitSignaldef_stmt(
        self, ctx: AtoParser.Signaldef_stmtContext
    ) -> AST.SignaldefStmt:
        return self._new(AST.SignaldefStmt).setup(
            source_info=self._extract_source_info(ctx), name=self.visitName(ctx.name())
        )

    def visitString_stmt(self, ctx: AtoParser.String_stmtContext) -> AST.StringStmt:
        text, source_info = self.visitString(ctx.string())
        return self._new(AST.StringStmt).setup(
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
        return self._new(AST.PassStmt).setup(source_info=self._extract_source_info(ctx))

    def visitAssert_stmt(self, ctx: AtoParser.Assert_stmtContext) -> AST.AssertStmt:
        return self._new(AST.AssertStmt).setup(
            source_info=self._extract_source_info(ctx),
            comparison=self.visitComparison(ctx.comparison()),
        )

    def visitTrait_stmt(self, ctx: AtoParser.Trait_stmtContext) -> AST.TraitStmt:
        target_field_ref = (
            self.visitField_reference(ctx.field_reference())
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
            source_info=self._extract_source_info(ctx),
            type_ref_name=type_ref_name,
            type_ref_source_info=type_ref_source_info,
            target_field_ref=target_field_ref,
            template_info=template_info,
            constructor=constructor,
        )

    def visitConstructor(self, ctx: AtoParser.ConstructorContext) -> str:
        return self.visitName(ctx.name())

    def visitFor_stmt(self, ctx: AtoParser.For_stmtContext) -> AST.ForStmt:
        return self._new(AST.ForStmt).setup(
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
                return self._new(AST.IterableFieldRef).setup(
                    source_info=self._extract_source_info(ctx),
                    field_ref=self.visitField_reference(field_ref_ctx),
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

    def visitField_reference(
        self, ctx: AtoParser.Field_referenceContext
    ) -> AST.FieldRef:
        parts = [
            self.visitField_reference_part(part_ctx)
            for part_ctx in ctx.field_reference_part()
        ]
        field_ref = self._new(AST.FieldRef).setup(
            source_info=self._extract_source_info(ctx), parts=parts
        )
        if (pin_end := ctx.pin_reference_end()) is not None:
            pin_number = pin_end.number_hint_natural().getText()
            field_ref.pin.get().setup_from_values(pin_number)
        return field_ref

    def visitAssign_stmt(self, ctx: AtoParser.Assign_stmtContext) -> AST.Assignment:
        field_ref_ctx = ctx.field_reference_or_declaration().field_reference()
        decl_stmt_ctx = ctx.field_reference_or_declaration().declaration_stmt()

        match (field_ref_ctx, decl_stmt_ctx):
            case (field_ref_ctx, None):
                target_field_ref = self.visitField_reference(field_ref_ctx)
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
            source_info=self._extract_source_info(ctx),
            target_field_ref=target_field_ref,
            assignable_value=self.visitAssignable(ctx.assignable()),
            assignable_source_info=self._extract_source_info(ctx.assignable()),
        )

    def visitAssignable(self, ctx: AtoParser.AssignableContext) -> AST.is_assignable:
        match (
            ctx.new_stmt(),
            ctx.literal_physical(),
            ctx.arithmetic_expression(),
            ctx.string(),
            ctx.boolean_(),
        ):
            case (new_stmt_ctx, None, None, None, None):
                return self.visitNew_stmt(new_stmt_ctx)._is_assignable.get()
            case (None, literal_physical_ctx, None, None, None):
                return self.visitLiteral_physical(
                    literal_physical_ctx
                )._is_assignable.get()
            case (None, None, arithmetic_expression_ctx, None, None):
                return self.visitArithmetic_expression(
                    arithmetic_expression_ctx
                ).as_assignable.get()
            case (None, None, None, string_ctx, None):
                text, source_info = self.visitString(string_ctx)
                return (
                    self._new(AST.AstString)
                    .setup(source_info=source_info, text=text)
                    ._is_assignable.get()
                )
            case (None, None, None, None, boolean_ctx):
                return self.visitBoolean_(boolean_ctx)._is_assignable.get()
            case _:
                raise ValueError(f"Unexpected assignable: {ctx.getText()}")

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
    ) -> AST.is_arithmetic:
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
            return (
                self._new(AST.BinaryExpression)
                .setup(
                    source_info=self._extract_source_info(ctx),
                    operator=operator,
                    lhs=lhs,
                    rhs=rhs,
                )
                ._is_arithmetic.get()
            )

        return rhs

    def visitSum(self, ctx: AtoParser.SumContext) -> AST.is_arithmetic:
        rhs = self.visitTerm(ctx.term())

        if ctx.sum_() is not None:
            match [ctx.PLUS(), ctx.MINUS()]:
                case [plus_token, None]:
                    operator = self.visitTerminal(plus_token)
                case [None, minus_token]:
                    operator = self.visitTerminal(minus_token)
                case _:
                    raise ValueError(f"Unexpected sum operator: {ctx.getText()}")

            return (
                self._new(AST.BinaryExpression)
                .setup(
                    source_info=self._extract_source_info(ctx),
                    operator=operator,
                    lhs=self.visitSum(ctx.sum_()),
                    rhs=rhs,
                )
                ._is_arithmetic.get()
            )

        return rhs

    def visitTerm(self, ctx: AtoParser.TermContext) -> AST.is_arithmetic:
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
            return (
                self._new(AST.BinaryExpression)
                .setup(
                    source_info=self._extract_source_info(ctx),
                    operator=operator,
                    lhs=lhs,
                    rhs=rhs,
                )
                ._is_arithmetic.get()
            )

        return rhs

    def visitPower(self, ctx: AtoParser.PowerContext) -> AST.is_arithmetic:
        atoms = [self.visitAtom(atom_ctx) for atom_ctx in ctx.atom()]
        match atoms:
            case [base, exponent]:
                return (
                    self._new(AST.BinaryExpression)
                    .setup(
                        source_info=self._extract_source_info(ctx),
                        operator=ctx.POWER().getText(),
                        lhs=base.as_arithmetic.get(),
                        rhs=exponent.as_arithmetic.get(),
                    )
                    ._is_arithmetic.get()
                )
            case [single]:
                return single.as_arithmetic.get()
            case _:
                raise ValueError(f"Unexpected power context: {ctx.getText()}")

    def visitArithmetic_group(
        self, ctx: AtoParser.Arithmetic_groupContext
    ) -> AST.GroupExpression:
        return self._new(AST.GroupExpression).setup(
            source_info=self._extract_source_info(ctx),
            expression=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitAtom(self, ctx: AtoParser.AtomContext) -> AST.is_arithmetic_atom:
        match ctx.field_reference(), ctx.literal_physical(), ctx.arithmetic_group():
            case (field_ref_ctx, None, None):
                return self.visitField_reference(
                    field_ref_ctx
                )._is_arithmetic_atom.get()
            case (None, literal_ctx, None):
                return self.visitLiteral_physical(literal_ctx)._is_arithmetic_atom.get()
            case (None, None, group_ctx):
                return self.visitArithmetic_group(group_ctx)._is_arithmetic_atom.get()
            case _:
                raise ValueError(f"Unexpected atom context: {ctx.getText()}")

    def visitComparison(
        self, ctx: AtoParser.ComparisonContext
    ) -> AST.ComparisonExpression:
        return self._new(AST.ComparisonExpression).setup(
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
            source_info=self._extract_source_info(ctx),
            operator=ctx.LESS_THAN().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitGt_arithmetic_or(
        self, ctx: AtoParser.Gt_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            source_info=self._extract_source_info(ctx),
            operator=ctx.GREATER_THAN().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitLt_eq_arithmetic_or(
        self, ctx: AtoParser.Lt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            source_info=self._extract_source_info(ctx),
            operator=ctx.LT_EQ().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitGt_eq_arithmetic_or(
        self, ctx: AtoParser.Gt_eq_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            source_info=self._extract_source_info(ctx),
            operator=ctx.GT_EQ().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitIn_arithmetic_or(
        self, ctx: AtoParser.In_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
            source_info=self._extract_source_info(ctx),
            operator=ctx.WITHIN().getText(),
            rhs=self.visitArithmetic_expression(ctx.arithmetic_expression()),
        )

    def visitIs_arithmetic_or(
        self, ctx: AtoParser.Is_arithmetic_orContext
    ) -> AST.ComparisonClause:
        return self._new(AST.ComparisonClause).setup(
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

    def visitUnit(self, ctx: AtoParser.UnitContext | None) -> str | None:
        return None if ctx is None else self.visitName(ctx.name())

    def visitDeclaration_stmt(
        self, ctx: AtoParser.Declaration_stmtContext
    ) -> AST.DeclarationStmt:
        return self._new(AST.DeclarationStmt).setup(
            source_info=self._extract_source_info(ctx),
            field_ref=self.visitField_reference(ctx.field_reference()),
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
            case [None, None]:
                unit = None
                unit_source = None
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
            source_info=self._extract_source_info(ctx), value=value
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
        try:
            v = self._parse_int(ctx.getText())
            if v < 0:
                raise ValueError("Natural numbers must be non-negative")
            return v
        except ValueError:
            raise DslException(
                f"Expected a natural number (positive integer), got `{ctx.getText()}`"
            )

    def visitNumber_hint_integer(
        self, ctx: AtoParser.Number_hint_integerContext
    ) -> int:
        try:
            return self._parse_int(ctx.getText())
        except ValueError:
            raise DslException(f"Expected an integer, got `{ctx.getText()}`")

    def visitMif(self, ctx: AtoParser.MifContext) -> AST.is_connectable:
        return self.visitConnectable(ctx.connectable())

    def visitBridgeable(self, ctx: AtoParser.BridgeableContext) -> AST.is_connectable:
        return self.visitConnectable(ctx.connectable())

    def visitConnectable(self, ctx: AtoParser.ConnectableContext) -> AST.is_connectable:
        match ctx.field_reference(), ctx.signaldef_stmt(), ctx.pindef_stmt():
            case (field_ref_ctx, None, None):
                return self.visitField_reference(field_ref_ctx)._is_connectable.get()
            case (None, signaldef_stmt_ctx, None):
                return self.visitSignaldef_stmt(
                    signaldef_stmt_ctx
                )._is_connectable.get()
            case (None, None, pindef_stmt_ctx):
                return self.visitPindef_stmt(pindef_stmt_ctx)._is_connectable.get()
            case _:
                raise ValueError(f"Unexpected connectable: {ctx.getText()}")

    def visitConnect_stmt(self, ctx: AtoParser.Connect_stmtContext) -> AST.ConnectStmt:
        lhs, rhs = [self.visitMif(mif_ctx) for mif_ctx in ctx.mif()]

        return self._new(AST.ConnectStmt).setup(
            source_info=self._extract_source_info(ctx), lhs=lhs, rhs=rhs
        )

    def visitDirected_connect_stmt(
        self, ctx: AtoParser.Directed_connect_stmtContext
    ) -> AST.DirectedConnectStmt:
        match [ctx.SPERM(), ctx.LSPERM()]:
            case [_, None]:
                # ~> (SPERM) - arrow points right, signal flows left-to-right
                direction = AST.DirectedConnectStmt.Direction.RIGHT
            case [None, _]:
                # <~ (LSPERM) - arrow points left, signal flows right-to-left
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
            source_info=self._extract_source_info(ctx),
            direction=direction,
            lhs=lhs,
            rhs=rhs,
        )
