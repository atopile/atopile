"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from faebryk.core.node import Node


@dataclass(order=True)
class FileLocation:
    start_line: int
    start_col: int
    end_line: int
    end_col: int


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
    _quantity: Quantity
    _tolerance: Quantity

    def __init__(self, quantity: Quantity, tolerance: Quantity) -> None:
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
    scope: Scope


class TextFragment(ASTNode):
    """A context-free fragment of ato code."""

    scope: Scope


class Whitespace(ASTNode): ...


class Comment(ASTNode): ...


class BlockDefinition(ASTNode):
    class BlockType(StrEnum):
        COMPONENT = "component"
        MODULE = "module"
        INTERFACE = "interface"

    block_type: BlockType
    scope: Scope
    _type_ref: TypeRef
    _super_type_ref: TypeRef | None

    def __init__(
        self,
        block_type: BlockType,
        type_ref: TypeRef,
        super_type_ref: TypeRef | None = None,
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

    _context: File | TextFragment

    def __init__(self, context: File | TextFragment) -> None:
        super().__init__()
        self._context = context

    def __postinit__(self):
        self.add(self._context, name="context")


class ForStmt(ASTNode):
    source: SourceChunk
    scope: Scope
    iterable: FieldRef


class PragmaStmt(ASTNode):
    pragma: str

    def __init__(self, pragma: str) -> None:
        super().__init__()
        self.pragma = pragma


class ImportStmt(ASTNode):
    _path: ImportPath | None
    _type_ref: TypeRef

    def __init__(self, path: ImportPath | None, type_ref: TypeRef) -> None:
        super().__init__()
        self._path = path
        self._type_ref = type_ref

    def __postinit__(self):
        if self._path is not None:
            self.add(self._path, name="path")
        self.add(self._type_ref, name="type_ref")


class AssignQuantityStmt(ASTNode):
    _field_ref: FieldRef
    _quantity: Quantity | BilateralQuantity | BoundedQuantity

    def __init__(
        self,
        field_ref: FieldRef,
        quantity: Quantity | BilateralQuantity | BoundedQuantity,
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
    args: list[TemplateArg]


class AssignNewStmt(ASTNode):
    _field_ref: FieldRef
    _type_ref: TypeRef
    _template: Template | None
    new_count: int | None

    def __init__(
        self,
        field_ref: FieldRef,
        type_ref: TypeRef,
        template: Template | None = None,
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
    _left_connectable: FieldRef
    _right_connectable: FieldRef

    def __init__(self, left_connectable: FieldRef, right_connectable: FieldRef) -> None:
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
    _left_bridgeable: FieldRef
    _right_bridgeable: "FieldRef | DirectedConnectStmt"

    def __init__(
        self,
        left_bridgeable: FieldRef,
        right_bridgeable: "FieldRef | DirectedConnectStmt",
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
    source: SourceChunk
    field_ref: FieldRef
    type_ref: TypeRef | None


class StringStmt(ASTNode):
    _string: String

    def __init__(self, string: String) -> None:
        super().__init__()
        self._string = string

    def __postinit__(self):
        self.add(self._string, name="string")


class PassStmt(ASTNode): ...


class TraitStmt(ASTNode): ...
