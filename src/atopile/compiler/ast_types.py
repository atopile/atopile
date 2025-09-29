"""
Graph-based representation of an ato file, constructed by the parser.

Rules:
- Must contain all information to reconstruct the original file exactly, regardless
    of syntactic validity.
- Invalid *structure* should be impossible to represent.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

from ordered_set import OrderedSet

from faebryk.core.cpp import (
    GraphInterface,
    GraphInterfaceHierarchical,
    GraphInterfaceModuleConnection,
    LinkNamedParent,
    LinkParent,
    LinkSibling,
)
from faebryk.core.node import CNode
from faebryk.libs.util import Tree


def compose(parent: _Node, child: _Node) -> _Node:
    link = LinkParent()
    child.parent.connect(parent.children, link)
    return parent


class _Node(CNode):
    @runtime_checkable
    class Proto_Node(Protocol):
        is_type: GraphInterfaceHierarchical
        connections: GraphInterfaceHierarchical

    def __init__(self):
        super().__init__()
        # self.is_type = GraphInterfaceHierarchical(is_parent=False)
        self.connections = GraphInterfaceModuleConnection()
        CNode.transfer_ownership(self)

    def __setattr__(self, name: str, value, /) -> None:
        super().__setattr__(name, value)
        if isinstance(value, GraphInterface):
            value.node = self
            value.name = name
            self.self_gif.connect(value, link=LinkSibling())
        elif isinstance(value, _Node):
            # FIXME
            value.parent.connect(self.children, LinkNamedParent(name))

    def add(self, obj: _Node) -> _Node:
        compose(self, obj)
        return self

    def get_children[T: _Node](
        self,
        direct_only: bool,
        types: type[T] | tuple[type[T], ...],
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> OrderedSet[T]:
        return cast(
            OrderedSet[T],
            OrderedSet(
                super().get_children(
                    direct_only=direct_only,
                    types=types if isinstance(types, tuple) else (types,),
                    include_root=include_root,
                    f_filter=f_filter,  # type: ignore
                    sort=sort,
                )
            ),
        )

    def get_tree[T: _Node](
        self,
        types: type[T] | tuple[type[T], ...],
        include_root: bool = True,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> Tree[T]:
        out = self.get_children(
            direct_only=True,
            types=types,
            f_filter=f_filter,
            sort=sort,
        )
        tree = Tree[T](
            {
                n: n.get_tree(
                    types=types,
                    include_root=False,
                    f_filter=f_filter,
                    sort=sort,
                )
                for n in out
            }
        )
        if include_root:
            if isinstance(self, types):
                if not f_filter or f_filter(self):
                    tree = Tree[T]({self: tree})
        return tree


@dataclass(order=True)
class FileLocation:
    start_line: int
    start_col: int
    end_line: int
    end_col: int


class SourceChunk(_Node):
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


class TypeRef(_Node):
    name: str

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class ImportPath(_Node):
    path: str

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class FieldRefPart(_Node):
    name: str
    key: int | str | None

    def __init__(self, name: str, key: int | str | None = None) -> None:
        super().__init__()
        self.name = name
        self.key = key


class FieldRef(_Node):
    """Dotted field reference composed of parts, each with optional key."""

    pin: int | None

    def __init__(self, pin: int | None = None) -> None:
        super().__init__()
        self.pin = pin


class Quantity(_Node):
    def __init__(self, value: Number, unit: str | None) -> None:
        super().__init__()
        self.value = value
        self.unit = unit


class String(_Node):
    value: str

    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value


class Number(_Node):
    value: Decimal

    def __init__(self, value: Decimal) -> None:
        super().__init__()
        self.value = value


class Boolean(_Node):
    value: bool

    def __init__(self, value: bool) -> None:
        super().__init__()
        self.value = value


class BinaryExpression(_Node):
    operator: str
    left: _Node
    right: _Node

    def __init__(self, operator: str, left: _Node, right: _Node) -> None:
        super().__init__()
        self.operator = operator
        self.left = left
        self.right = right


class GroupExpression(_Node):
    expression: _Node

    def __init__(self, expression: _Node) -> None:
        super().__init__()
        self.expression = expression


class FunctionCall(_Node):
    name: str
    args: list[_Node]  # FIXME

    def __init__(self, name: str, args: list[_Node]) -> None:
        super().__init__()
        self.name = name
        self._args = args

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        for index, arg in enumerate(self._args):
            self.add(arg, name=f"arg[{index}]")


class ComparisonClause(_Node):
    operator: str
    _right: _Node

    def __init__(self, operator: str, right: _Node) -> None:
        super().__init__()
        self.operator = operator
        self._right = right

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._right, name="right")


class ComparisonExpression(_Node):
    _left: _Node
    _clauses: list[ComparisonClause]

    def __init__(self, left: _Node, clauses: list[ComparisonClause]) -> None:
        super().__init__()
        self._left = left
        self._clauses = clauses

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._left, name="left")
        for index, clause in enumerate(self._clauses):
            self.add(clause, name=f"clause[{index}]")


class BilateralQuantity(_Node):
    _quantity: Quantity
    _tolerance: Quantity

    def __init__(self, quantity: Quantity, tolerance: Quantity) -> None:
        super().__init__()
        self._quantity = quantity
        self._tolerance = tolerance

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._quantity, name="quantity")
        self.add(self._tolerance, name="tolerance")


class BoundedQuantity(_Node):
    _start: Quantity
    _end: Quantity

    def __init__(self, start: Quantity, end: Quantity) -> None:
        super().__init__()
        self._start = start
        self._end = end

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._start, name="start")
        self.add(self._end, name="end")


class Scope(_Node): ...


class File(_Node):
    """A single .ato file."""

    path: Path | None = None
    scope: Scope


class TextFragment(_Node):
    """A context-free fragment of ato code."""

    scope: Scope


class Whitespace(_Node): ...


class Comment(_Node): ...


class BlockDefinition(_Node):
    class BlockType(StrEnum):
        COMPONENT = "component"
        MODULE = "module"
        INTERFACE = "interface"

    block_type: BlockType

    def __init__(
        self,
        block_type: BlockType,
        type_ref: TypeRef,
        super_type_ref: TypeRef | None = None,
    ) -> None:
        super().__init__()
        self.block_type = block_type
        self.type_ref = type_ref
        if super_type_ref is not None:
            self.super_type_ref = super_type_ref

        self.scope = Scope()


class CompilationUnit(_Node):
    """A compilable unit of ato code."""

    _context: File | TextFragment

    def __init__(self, context: File | TextFragment) -> None:
        super().__init__()
        self._context = context

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.add(self._context, name="context")


class Slice(_Node):
    start: int | None
    stop: int | None
    step: int | None

    def __init__(self, start: int | None, stop: int | None, step: int | None) -> None:
        super().__init__()
        self.start = start
        self.stop = stop
        self.step = step


class IterableFieldRef(_Node):
    _field_ref: FieldRef
    _slice: Slice | None

    def __init__(self, field_ref: FieldRef, slice_: Slice | None = None) -> None:
        super().__init__()
        self._field_ref = field_ref
        self._slice = slice_

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._field_ref, name="field")
        if self._slice is not None:
            self.add(self._slice, name="slice")


class FieldRefList(_Node):
    _items: list[FieldRef]

    def __init__(self, items: list[FieldRef]) -> None:
        super().__init__()
        self._items = items

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        for index, item in enumerate(self._items):
            self.add(item, name=f"item[{index}]")


class ForStmt(_Node):
    scope: Scope
    target: str
    _iterable: _Node

    def __init__(self, target: str, iterable: _Node) -> None:
        super().__init__()
        self.target = target
        self._iterable = iterable

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._iterable, name="iterable")


class PragmaStmt(_Node):
    pragma: str

    def __init__(self, pragma: str) -> None:
        super().__init__()
        self.pragma = pragma


class ImportStmt(_Node):
    def __init__(self, path: ImportPath | None, type_ref: TypeRef) -> None:
        super().__init__()
        if path is not None:
            self.path = path
        self.type_ref = type_ref


class AssignQuantityStmt(_Node):
    _target: FieldRef | "DeclarationStmt"
    _quantity: Quantity | BilateralQuantity | BoundedQuantity

    def __init__(
        self,
        target: FieldRef | "DeclarationStmt",
        quantity: Quantity | BilateralQuantity | BoundedQuantity,
    ) -> None:
        super().__init__()
        self._target = target
        self._quantity = quantity

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._target, name="target")
        self.add(self._quantity, name="quantity")


class TemplateArg(_Node):
    name: str
    _value: _Node

    def __init__(self, name: str, value: _Node) -> None:
        super().__init__()
        self.name = name
        self._value = value

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._value, name="value")


class Template(_Node):
    _args: list[TemplateArg]

    def __init__(self, args: list[TemplateArg] | None = None) -> None:
        super().__init__()
        self._args = args or []

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        for index, arg in enumerate(self._args):
            self.add(arg, name=f"arg[{index}]")


class AssignValueStmt(_Node):
    _target: FieldRef | "DeclarationStmt"
    _value: _Node

    def __init__(self, target: FieldRef | "DeclarationStmt", value: _Node) -> None:
        super().__init__()
        self._target = target
        self._value = value

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._target, name="target")
        self.add(self._value, name="value")


class AssignNewStmt(_Node):
    _target: FieldRef | "DeclarationStmt"
    _type_ref: TypeRef
    _template: Template | None
    new_count: int | None

    def __init__(
        self,
        target: FieldRef | "DeclarationStmt",
        type_ref: TypeRef,
        template: Template | None = None,
        count: int | None = None,
    ) -> None:
        super().__init__()
        self._target = target
        self._type_ref = type_ref
        self._template = template
        self.new_count = count

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._target, name="target")
        self.add(self._type_ref, name="type_ref")
        if self._template is not None:
            self.add(self._template, name="template")


class CumAssignStmt(_Node): ...


class SetAssignStmt(_Node): ...


class ConnectStmt(_Node):
    _left_connectable: _Node
    _right_connectable: _Node

    def __init__(self, left_connectable: _Node, right_connectable: _Node) -> None:
        super().__init__()
        self._left_connectable = left_connectable
        self._right_connectable = right_connectable

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.add(self._left_connectable, name="left")
        self.add(self._right_connectable, name="right")


class DirectedConnectStmt(_Node):
    class Direction(StrEnum):
        RIGHT = "RIGHT"
        LEFT = "LEFT"

    direction: Direction
    _left_bridgeable: _Node
    _right_bridgeable: "_Node | DirectedConnectStmt"

    def __init__(
        self,
        left_bridgeable: _Node,
        right_bridgeable: "_Node | DirectedConnectStmt",
        direction: Direction,
    ) -> None:
        super().__init__()
        self._left_bridgeable = left_bridgeable
        self._right_bridgeable = right_bridgeable
        self.direction = direction

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.add(self._left_bridgeable, name="left")
        self.add(self._right_bridgeable, name="right")


class RetypeStmt(_Node):
    _field_ref: FieldRef
    _type_ref: TypeRef

    def __init__(self, field_ref: FieldRef, type_ref: TypeRef) -> None:
        super().__init__()
        self._field_ref = field_ref
        self._type_ref = type_ref

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._field_ref, name="field_ref")
        self.add(self._type_ref, name="type_ref")


class PinDeclaration(_Node):
    class Kind(StrEnum):
        NAME = "name"
        NUMBER = "number"
        STRING = "string"

    kind: Kind
    value: str | int
    _literal: _Node | None

    def __init__(
        self, kind: Kind, value: str | int, literal: _Node | None = None
    ) -> None:
        super().__init__()
        self.kind = kind
        self.value = value
        self._literal = literal

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        if self._literal is not None:
            self.add(self._literal, name="literal")


class SignaldefStmt(_Node):
    name: str

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class AssertStmt(_Node):
    _comparison: ComparisonExpression

    def __init__(self, comparison: ComparisonExpression) -> None:
        super().__init__()
        self._comparison = comparison

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._comparison, name="comparison")


class DeclarationStmt(_Node):
    _field_ref: FieldRef
    _type_ref: TypeRef | None

    def __init__(self, field_ref: FieldRef, type_ref: TypeRef | None = None) -> None:
        super().__init__()
        self._field_ref = field_ref
        self._type_ref = type_ref

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._field_ref, name="field_ref")
        if self._type_ref is not None:
            self.add(self._type_ref, name="type_ref")

    @property
    def field_ref(self) -> FieldRef:
        return self._field_ref

    @property
    def type_ref(self) -> TypeRef | None:
        return self._type_ref


class StringStmt(_Node):
    _string: String

    def __init__(self, string: String) -> None:
        super().__init__()
        self._string = string

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        self.add(self._string, name="string")


class PassStmt(_Node): ...


class TraitStmt(_Node):
    _target: FieldRef | None
    _type_ref: TypeRef
    constructor: str | None
    _template: Template | None

    def __init__(
        self,
        type_ref: TypeRef,
        target: FieldRef | None = None,
        constructor: str | None = None,
        template: Template | None = None,
    ) -> None:
        super().__init__()
        self._type_ref = type_ref
        self._target = target
        self.constructor = constructor
        self._template = template

    def __postinit__(self, *args, **kwargs) -> None:
        super().__postinit__(*args, **kwargs)
        if self._target is not None:
            self.add(self._target, name="target")
        self.add(self._type_ref, name="type_ref")
        if self._template is not None:
            self.add(self._template, name="template")


ASTNode = (
    AssertStmt,
    AssignNewStmt,
    AssignQuantityStmt,
    AssignValueStmt,
    BilateralQuantity,
    BinaryExpression,
    BlockDefinition,
    BlockDefinition.BlockType,
    Boolean,
    BoundedQuantity,
    Comment,
    ComparisonClause,
    ComparisonExpression,
    CompilationUnit,
    ConnectStmt,
    CumAssignStmt,
    DeclarationStmt,
    DirectedConnectStmt,
    FieldRef,
    FieldRefList,
    FieldRefPart,
    File,
    ForStmt,
    FunctionCall,
    GroupExpression,
    ImportPath,
    ImportStmt,
    IterableFieldRef,
    Number,
    PassStmt,
    PinDeclaration,
    PragmaStmt,
    Quantity,
    RetypeStmt,
    Scope,
    SetAssignStmt,
    SignaldefStmt,
    Slice,
    String,
    StringStmt,
    Template,
    TemplateArg,
    TextFragment,
    TraitStmt,
    TypeRef,
    Whitespace,
)
