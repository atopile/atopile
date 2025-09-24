from decimal import Decimal
from pathlib import Path

from faebryk.core.node import Node

"""
Graph-based representation of an ato file, constructed by the parser.

Must contain all information to reconstruct the original file exactly, regardless of
syntactic validity.
"""


class SourceChunk(Node):
    """
    A context-free chunk of source code. May not be syntactically valid.
    Only available in leaf types.
    """

    text: str

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class CompilerNode(Node): ...


class TypeRef(CompilerNode):
    name: str

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class FieldRefPart(CompilerNode):
    name: str
    key: int | None

    def __init__(self, name: str, key: int | None = None) -> None:
        super().__init__()
        self.name = name
        self.key = key


class FieldRef(CompilerNode):
    """Dotted field reference composed of parts, each with optional key."""

    parts: list[FieldRefPart]

    def __init__(self, *names: str) -> None:
        super().__init__()
        for n in names:
            self.add(FieldRefPart(n), container=self.parts)


class Quantity(CompilerNode):
    value: float
    unit: str

    def __init__(self, value: float, unit: str) -> None:
        super().__init__()
        self.unit = unit
        self.value = value


class String(CompilerNode):
    value: str


class Number(CompilerNode):
    value: Decimal


class Boolean(CompilerNode):
    value: bool


class BilateralQuantity(CompilerNode):
    quantity: Quantity | None
    tolerance: Quantity | None


class BoundedQuantity(CompilerNode):
    start: Quantity | None
    end: Quantity | None


class Scope(CompilerNode): ...


class File(CompilerNode):
    """A single .ato file."""

    path: Path
    scope: Scope


class TextFragment(CompilerNode):
    """A context-free fragment of ato code."""

    scope: Scope


class Whitespace(CompilerNode):
    source: SourceChunk


class Comment(CompilerNode):
    source: SourceChunk


class BlockDefinition(CompilerNode):
    source: SourceChunk  # note: only the first line (body is in children)
    scope: Scope


class CompilationUnit(CompilerNode):
    """A compilable unit of ato code."""

    context: File | TextFragment
    type_ref: TypeRef | None


class ForStmt(CompilerNode):
    source: SourceChunk
    scope: Scope
    iterable: FieldRef


class PragmaStmt(CompilerNode):
    pragma: str

    def __init__(self, pragma: str) -> None:
        super().__init__()
        self.pragma = pragma
        self.add


class ImportStmt(CompilerNode):
    source: SourceChunk
    path: Path
    type_ref: TypeRef | None


class AssignQuantityStmt(CompilerNode):
    source: SourceChunk
    field_ref: FieldRef
    quantity: Quantity | BilateralQuantity | BoundedQuantity


class TemplateArg(CompilerNode):
    name: str


class Template(CompilerNode):
    args: list[TemplateArg]


class AssignNewStmt(CompilerNode):
    source: SourceChunk
    field_ref: FieldRef
    type_ref: TypeRef | None
    new_count: int | None
    template: Template | None

    def __init__(
        self, count: int | None = None, template: Template | None = None
    ) -> None:
        super().__init__()
        self.new_count = count
        self.template = template


class CumAssignStmt(CompilerNode): ...


class SetAssignStmt(CompilerNode): ...


class ConnectStmt(CompilerNode): ...


class DirectedConnectStmt(CompilerNode): ...


class RetypeStmt(CompilerNode): ...


class PinDeclaration(CompilerNode): ...


class SignaldefStmt(CompilerNode): ...


class AssertStmt(CompilerNode): ...


class DeclarationStmt(CompilerNode):
    source: SourceChunk
    field_ref: FieldRef
    type_ref: TypeRef | None


class StringStmt(CompilerNode): ...


class PassStmt(CompilerNode): ...


class TraitStmt(CompilerNode): ...
