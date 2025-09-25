"""
Generates an AST graph from the ANTLR4-generated AST.

Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
"""

import itertools
from collections.abc import Iterable
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter

import atopile.compiler.ast_types as AST
from atopile.compiler.parse import parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.libs.sets.numeric_sets import is_int


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
                case AST.ASTNode() | AST.SourceChunk():
                    scope.add(node_or_nodes)
                case Iterable():
                    for node in node_or_nodes:
                        # FIXME: assert is ASTNode
                        if isinstance(node, AST.ASTNode):
                            scope.add(node)
                case None:
                    pass
                case _:
                    raise ValueError(f"Unexpected node type: {type(node_or_nodes)}")

    def visitName(self, ctx: AtoParser.NameContext) -> str:
        return ctx.getText()

    def visitTypeReference(self, ctx: AtoParser.Type_referenceContext) -> AST.TypeRef:
        type_ref = AST.TypeRef(self.visitName(ctx.name()))
        type_ref.add(self._extract_source(ctx))
        return type_ref

    def visitArrayIndex(self, ctx: AtoParser.Array_indexContext) -> str | int | None:
        if key := ctx.key():
            if is_int(text := key.getText()):
                return int(text)
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
        file.add(self._extract_source(ctx))

        for child in ctx.getChildren():
            match node_or_nodes := self.visit(child):
                case AST.ASTNode() | AST.SourceChunk():
                    file.add(node_or_nodes)
                case Iterable():
                    for node in node_or_nodes:
                        assert isinstance(node, AST.ASTNode), "missing a visitor method"
                        file.add(node)
                case None:
                    pass
                case _:
                    raise ValueError(f"Unexpected node type: {type(node_or_nodes)}")

        return file

    def visitSimple_stmts(
        self, ctx: AtoParser.Simple_stmtsContext
    ) -> Iterable[AST.ASTNode]:
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
            from_path = AST.ImportPath(self.visitString(ctx.string()))
            from_path.add(self._extract_source(ctx.string()))
        else:
            from_path = None

        type_ref = self.visitTypeReference(ctx.type_reference())

        import_stmt = AST.ImportStmt(from_path, type_ref)
        import_stmt.add(self._extract_source(ctx))

        return import_stmt

    def visittString_stmt(self, ctx: AtoParser.String_stmtContext) -> AST.StringStmt:
        string = AST.String(self.visitString(ctx.string()))
        stmt = AST.StringStmt(string)
        stmt.add(self._extract_source(ctx))
        return stmt

    def visitField_reference_part(
        self, ctx: AtoParser.Field_reference_partContext
    ) -> AST.FieldRefPart:
        # TODO: handle keys
        field_ref_part = AST.FieldRefPart(self.visitName(ctx.name()))
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
        return field_ref

    def visitAssign_stmt(
        self, ctx: AtoParser.Assign_stmtContext
    ) -> AST.AssignNewStmt | AST.AssignQuantityStmt | None:
        field_ref_or_decl = ctx.field_reference_or_declaration()

        # new node assignments only
        # TODO: other assignments

        # TODO: change the grammar to make this easier
        if field_ref := field_ref_or_decl.field_reference():
            field_ref = self.visitField_reference(field_ref)

            if new_stmt_ctx := ctx.assignable().new_stmt():
                type_ref = self.visitTypeReference(new_stmt_ctx.type_reference())
                # template = self.visitTemplate(new_stmt_ctx.template())
                template = None  # TODO
                # count = self.visitNew_count(new_stmt_ctx.new_count())
                count = None  # TODO
                new_stmt = AST.AssignNewStmt(field_ref, type_ref, template, count)
                new_stmt.add(self._extract_source(ctx))
                return new_stmt
            elif literal_physical_ctx := ctx.assignable().literal_physical():
                quantity = self.visitLiteral_physical(literal_physical_ctx)
                assign_quantity_stmt = AST.AssignQuantityStmt(field_ref, quantity)
                assign_quantity_stmt.add(self._extract_source(ctx))
                return assign_quantity_stmt
            else:
                return None
        else:
            # TODO: handle declaration
            assert False

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

    def visitQuantity(self, ctx: AtoParser.QuantityContext) -> AST.Quantity:
        quantity = AST.Quantity(
            self.visitNumber(ctx.number()), self.visitName(ctx.name())
        )
        quantity.add(self._extract_source(ctx))
        return quantity

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

        quantity = AST.Quantity(self.visitNumber_signless(ctx.number_signless()), unit)
        quantity.add(self._extract_source(ctx))
        return quantity

    def visitMif(self, ctx: AtoParser.MifContext) -> AST.FieldRef:
        if ctx.connectable().field_reference():
            return self.visitField_reference(ctx.connectable().field_reference())
        else:
            assert False, "remove signal/pin keywords"

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
