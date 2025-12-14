"""
Shared data structures and helpers for the TypeGraph-generation IR.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

import faebryk.core.graph as graph


@dataclass(frozen=True)
class ImportRef:
    name: str
    path: str | None = None

    def __repr__(self) -> str:
        path_part = f', path="{self.path}"' if self.path else ""
        return f"ImportRef(name={self.name}{path_part})"


@dataclass(frozen=True)
class Symbol:
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


@dataclass(frozen=True)
class NewChildSpec:
    symbol: Symbol | None = None
    type_identifier: str | None = None
    type_node: graph.BoundNode | None = None
    count: int | None = None


@dataclass(frozen=True)
class AddMakeChildAction:
    target_path: FieldPath
    child_spec: NewChildSpec
    parent_reference: graph.BoundNode | None
    parent_path: FieldPath | None


@dataclass(frozen=True)
class AddMakeLinkAction:
    lhs_ref: graph.BoundNode
    rhs_ref: graph.BoundNode


@dataclass(frozen=True)
class AddTraitAction:
    trait_type_identifier: str
    trait_type_node: graph.BoundNode | None
    trait_import_ref: "ImportRef | None"
    target_reference: graph.BoundNode | None
    template_args: dict[str, str | bool | float] | None = None


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
