"""
Shared data structures and helpers for the TypeGraph-generation IR.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.faebrykpy import EdgeTraversal

LinkPath = list[str | EdgeTraversal]


@dataclass(frozen=True)
class ImportRef:
    name: str
    path: str | None = None

    def __repr__(self) -> str:
        path_part = f', path="{self.path}"' if self.path else ""
        return f"ImportRef(name={self.name}{path_part})"


@dataclass(frozen=True)
class Symbol:
    """
    Referring to type within file scope
    name:
    import_ref:
    type_node:
    """

    name: str
    import_ref: ImportRef | None = None
    type_node: graph.BoundNode | None = None

    def __repr__(self) -> str:
        return (
            f"Symbol(name={self.name}, import_ref={self.import_ref}, "
            f"type_node={self.type_node})"
        )


@dataclass(frozen=True)
class FieldPath:
    @dataclass(frozen=True)
    class Segment:
        identifier: str
        is_index: bool = False

    segments: tuple["FieldPath.Segment", ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("FieldPath cannot be empty")

    @property
    def parent_segments(self) -> Sequence["FieldPath.Segment"]:
        *head, _ = self.segments
        return head

    @property
    def leaf(self) -> "FieldPath.Segment":
        *_, tail = self.segments
        return tail

    def is_singleton(self) -> bool:
        return len(self.segments) == 1

    def __str__(self) -> str:
        parts: list[str] = []

        for segment in self.segments:
            if segment.is_index:
                parts[-1] = f"{parts[-1]}[{segment.identifier}]"
            else:
                parts.append(segment.identifier)

        return ".".join(parts)

    def identifiers(self) -> tuple[str, ...]:
        """
        Return the path as a tuple of identifiers suitable for TypeGraph lookups.

        Index segments (e.g., the '0' in 'unnamed[0]') are combined with their
        preceding name segment to form a single identifier like 'unnamed[0]',
        matching how fabll names list children.
        """
        parts: list[str] = []
        for segment in self.segments:
            if segment.is_index:
                parts[-1] = f"{parts[-1]}[{segment.identifier}]"
            else:
                parts.append(segment.identifier)
        return tuple(parts)

    def to_ref_path(self) -> fabll.RefPath:
        return [*self.identifiers()]


@dataclass(frozen=True)
class NewChildSpec:
    """
    Only for NewExpression

    symbol: The symbol to use for the child type.
    type_identifier: full path including file name. str for pre linker
    type_node:
    count: How many child instances to create
    template_args: Template arguments for parameterized modules
    (e.g., Addressor<address_bits=2>)
    """

    symbol: Symbol | None = None
    type_identifier: str | None = None
    type_node: graph.BoundNode | None = None
    count: int | None = None
    template_args: dict[str, str | bool | float] | None = None


@dataclass(frozen=True)
class ConstraintSpec:
    operand: (
        fabll._ChildField[F.Literals.Strings]
        | fabll._ChildField[F.Literals.Booleans]
        | fabll._ChildField[F.Literals.Numbers]
    )


@dataclass(frozen=True)
class AddMakeChildAction:
    """
    target_path: String path to target eg. resistor.resistance
    relative to parent reference node. eg. app
    parent_reference: Parent of the makechild node.
    parent_path: The path to the parent type.
    """

    target_path: FieldPath | fabll.RefPath
    parent_reference: graph.BoundNode | None
    parent_path: FieldPath | None
    child_field: fabll._ChildField | None = None
    import_ref: ImportRef | None = None

    def get_identifier(self) -> str:
        if isinstance(self.target_path, FieldPath):
            return self.target_path.leaf.identifier
        else:
            (*_, tail) = self.target_path
            match tail:
                case fabll._ChildField():
                    return tail.get_identifier()
                case type():
                    return tail._type_identifier()
                case str():
                    return tail
                case _:
                    raise ValueError(f"Invalid target path: {tail}")


@dataclass(frozen=True)
class AddMakeLinkAction:
    lhs_path: LinkPath
    rhs_path: LinkPath
    edge: fbrk.EdgeCreationAttributes | None = None


@dataclass(frozen=True)
class NoOpAction:
    pass


@dataclass
class ScopeState:
    symbols: dict[str, Symbol] = field(default_factory=dict)
    fields: set[str] = field(default_factory=set)
    # Aliases allow temporarily binding a loop variable name to a concrete
    # field path during `for` iteration. Only used within the current
    # lexical scope and intended to be short-lived.
    aliases: dict[str, FieldPath] = field(default_factory=dict)
