"""
Defines and generates an AST graph from the ANTLR4-generated AST.

Exists as a stop-gap until we move away from the ANTLR4 compiler front-end.
"""

import itertools
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.TokenStreamRewriter import TokenStreamRewriter

from atopile.compiler.parse import parse_text_as_file
from atopile.compiler.parse_utils import AtoRewriter
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.compiler.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.core.node import Node
from faebryk.libs.sets.numeric_sets import is_int


@dataclass(order=True)
class FileLocation:
    start_line: int
    start_col: int
    end_line: int
    end_col: int


class AST:
    """
    Graph-based representation of an ato file, constructed by the parser.

    Rules:
    - Must contain all information to reconstruct the original file exactly, regardless
      of syntactic validity.
    - Invalid *structure* should be impossible to represent.
    """

    class SourceChunk(Node):
        """
        A context-free chunk of source code. May not be syntactically valid.
        TODO: Only available in leaf types
        """

        text: str
        file_location: FileLocation

        def __init__(self, text: str, file_location: FileLocation) -> None:
            super().__init__()
            self.text = text
            self.file_location = file_location

    class ASTNode(Node): ...

    class TypeRef(ASTNode):
        name: str

        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

    class ImportPath(ASTNode):
        path: str

        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    class FieldRefPart(ASTNode):
        name: str
        key: int | None

        def __init__(self, name: str, key: int | None = None) -> None:
            super().__init__()
            self.name = name
            self.key = key

    class FieldRef(ASTNode):
        """Dotted field reference composed of parts, each with optional key."""

        def __init__(self) -> None:
            super().__init__()

    class Quantity(ASTNode):
        value: float
        unit: str | None

        def __init__(self, value: float, unit: str | None) -> None:
            super().__init__()
            self.unit = unit
            self.value = value

    class String(ASTNode):
        value: str

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    class Number(ASTNode):
        value: Decimal

        def __init__(self, value: Decimal) -> None:
            super().__init__()
            self.value = value

    class Boolean(ASTNode):
        value: bool

        def __init__(self, value: bool) -> None:
            super().__init__()
            self.value = value

    class BilateralQuantity(ASTNode):
        _quantity: "AST.Quantity"
        _tolerance: "AST.Quantity"

        def __init__(self, quantity: "AST.Quantity", tolerance: "AST.Quantity") -> None:
            super().__init__()
            self._quantity = quantity
            self._tolerance = tolerance

        def __postinit__(self):
            self.add(self._quantity, name="quantity")
            self.add(self._tolerance, name="tolerance")

    class BoundedQuantity(ASTNode):
        ...
        # def __init__(self, start: Quantity | None, end: Quantity | None) -> None:
        #     super().__init__()
        #     self.start = start
        #     self.end = end

    class Scope(ASTNode): ...

    class File(ASTNode):
        """A single .ato file."""

        path: Path | None = None
        scope: "AST.Scope"

    class TextFragment(ASTNode):
        """A context-free fragment of ato code."""

        scope: "AST.Scope"

    class Whitespace(ASTNode): ...

    class Comment(ASTNode): ...

    class BlockDefinition(ASTNode):
        class BlockType(StrEnum):
            COMPONENT = "component"
            MODULE = "module"
            INTERFACE = "interface"

        block_type: BlockType
        scope: "AST.Scope"
        _type_ref: "AST.TypeRef"
        _super_type_ref: "AST.TypeRef | None"

        def __init__(
            self,
            block_type: BlockType,
            type_ref: "AST.TypeRef",
            super_type_ref: "AST.TypeRef | None" = None,
        ) -> None:
            super().__init__()
            self.block_type = block_type
            self._type_ref = type_ref
            self._super_type_ref = super_type_ref

        def __postinit__(self):
            self.add(self._type_ref, name="type_ref")
            if self._super_type_ref is not None:
                self.add(self._super_type_ref, name="super_type_ref")

    class CompilationUnit(ASTNode):
        """A compilable unit of ato code."""

        _context: "AST.File | AST.TextFragment"

        def __init__(self, context: "AST.File | AST.TextFragment") -> None:
            super().__init__()
            self._context = context

        def __postinit__(self):
            self.add(self._context, name="context")

    class ForStmt(ASTNode):
        source: "AST.SourceChunk"
        scope: "AST.Scope"
        iterable: "AST.FieldRef"

    class PragmaStmt(ASTNode):
        pragma: str

        def __init__(self, pragma: str) -> None:
            super().__init__()
            self.pragma = pragma

    class ImportStmt(ASTNode):
        _path: "AST.ImportPath | None"
        _type_ref: "AST.TypeRef"

        def __init__(
            self, path: "AST.ImportPath | None", type_ref: "AST.TypeRef"
        ) -> None:
            super().__init__()
            self._path = path
            self._type_ref = type_ref

        def __postinit__(self):
            if self._path is not None:
                self.add(self._path, name="path")
            self.add(self._type_ref, name="type_ref")

    class AssignQuantityStmt(ASTNode):
        _field_ref: "AST.FieldRef"
        _quantity: "AST.Quantity | AST.BilateralQuantity | AST.BoundedQuantity"

        def __init__(
            self,
            field_ref: "AST.FieldRef",
            quantity: "AST.Quantity | AST.BilateralQuantity | AST.BoundedQuantity",
        ) -> None:
            super().__init__()
            self._field_ref = field_ref
            self._quantity = quantity

        def __postinit__(self):
            self.add(self._field_ref, name="field_ref")
            self.add(self._quantity, name="quantity")

    class TemplateArg(ASTNode):
        name: str

    class Template(ASTNode):
        args: list["AST.TemplateArg"]

    class AssignNewStmt(ASTNode):
        _field_ref: "AST.FieldRef"
        _type_ref: "AST.TypeRef"
        _template: "AST.Template | None"
        new_count: int | None

        def __init__(
            self,
            field_ref: "AST.FieldRef",
            type_ref: "AST.TypeRef",
            template: "AST.Template | None" = None,
            count: int | None = None,
        ) -> None:
            super().__init__()
            self._field_ref = field_ref
            self._type_ref = type_ref
            self._template = template
            self.new_count = count

        def __postinit__(self):
            self.add(self._field_ref, name="field_ref")
            self.add(self._type_ref, name="type_ref")
            if self._template is not None:
                self.add(self._template, name="template")

    class CumAssignStmt(ASTNode): ...

    class SetAssignStmt(ASTNode): ...

    class ConnectStmt(ASTNode):
        _left_connectable: "AST.FieldRef"
        _right_connectable: "AST.FieldRef"

        def __init__(
            self, left_connectable: "AST.FieldRef", right_connectable: "AST.FieldRef"
        ) -> None:
            super().__init__()
            self._left_connectable = left_connectable
            self._right_connectable = right_connectable

        def __postinit__(self):
            self.add(self._left_connectable, name="left")
            self.add(self._right_connectable, name="right")

    class DirectedConnectStmt(ASTNode):
        class Direction(StrEnum):
            RIGHT = "RIGHT"
            LEFT = "LEFT"

        direction: Direction
        _left_bridgeable: "AST.FieldRef"
        _right_bridgeable: "AST.FieldRef | AST.DirectedConnectStmt"

        def __init__(
            self,
            left_bridgeable: "AST.FieldRef",
            right_bridgeable: "AST.FieldRef | AST.DirectedConnectStmt",
            direction: Direction,
        ) -> None:
            super().__init__()
            self._left_bridgeable = left_bridgeable
            self._right_bridgeable = right_bridgeable
            self.direction = direction

        def __postinit__(self):
            self.add(self._left_bridgeable, name="left")
            self.add(self._right_bridgeable, name="right")

    class RetypeStmt(ASTNode): ...

    class PinDeclaration(ASTNode): ...

    class SignaldefStmt(ASTNode): ...

    class AssertStmt(ASTNode): ...

    class DeclarationStmt(ASTNode):
        source: "AST.SourceChunk"
        field_ref: "AST.FieldRef"
        type_ref: "AST.TypeRef | None"

    class StringStmt(ASTNode):
        _string: "AST.String"

        def __init__(self, string: "AST.String") -> None:
            super().__init__()
            self._string = string

        def __postinit__(self):
            self.add(self._string, name="string")

    class PassStmt(ASTNode): ...

    class TraitStmt(ASTNode): ...


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
            FileLocation(
                start_token.line,  # type: ignore
                start_token.column,  # type: ignore
                stop_token.line,  # type: ignore
                stop_token.column,  # type: ignore
            ),
        )

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

        scope = block_definition.scope

        for child in ctx.block().getChildren():
            match node_or_nodes := self.visit(child):
                case AST.ASTNode() | AST.SourceChunk():
                    scope.add(node_or_nodes)
                case Iterable():
                    for node in node_or_nodes:
                        # FIXME: assert is CompilerNode
                        if isinstance(node, AST.ASTNode):
                            scope.add(node)
                case None:
                    pass
                case _:
                    raise ValueError(f"Unexpected node type: {type(node_or_nodes)}")

        return block_definition

    def visitFile_input(self, ctx: AtoParser.File_inputContext) -> AST.File:
        file = AST.File()
        # TODO: remove this and push all source chunks to leaf nodes
        # currently difficult due to comments going to a hidden channel
        file.add(self._extract_source(ctx))

        scope = file.scope

        for child in ctx.getChildren():
            match node_or_nodes := self.visit(child):
                case AST.ASTNode() | AST.SourceChunk():
                    scope.add(node_or_nodes)
                case Iterable():
                    for node in node_or_nodes:
                        assert isinstance(node, AST.ASTNode), "missing a visitor method"
                        scope.add(node)
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
