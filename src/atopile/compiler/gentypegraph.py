"""
Shared data structures and helpers for the TypeGraph-generation IR.
"""

import itertools
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import ClassVar

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler import CompilerException, DslException, DslRichException
from atopile.compiler import ast_types as AST
from atopile.logging import get_logger
from faebryk.core.faebrykpy import (
    EdgeComposition,
    EdgePointer,
    EdgeTrait,
    EdgeTraversal,
)
from faebryk.library.can_bridge import can_bridge
from faebryk.library.Lead import can_attach_to_pad_by_name, is_lead

logger = get_logger(__name__)

LinkPath = list[str | EdgeTraversal]


class ActionGenerationError(CompilerException):
    pass


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
    def root(self) -> "FieldPath.Segment":
        (head, *_) = self.segments
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

    @property
    def leaf_identifier(self) -> str:
        leaf_segment = self.leaf
        if leaf_segment.is_index:
            return f"{leaf_segment.identifier}[{leaf_segment.identifier}]"
        else:
            return leaf_segment.identifier

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
    count: int | None = None
    template_args: dict[str, str | bool | float] | None = None


@dataclass(frozen=True)
class ParameterSpec:
    """Specification for creating a parameter, optionally with a constraint."""

    param_child: fabll._ChildField | None
    operand: (
        fabll._ChildField[F.Literals.Numbers]
        | fabll._ChildField[F.Literals.Strings]
        | fabll._ChildField[F.Literals.Booleans]
        | None
    ) = None


class ActionsFactory:
    TRAIT_ID_PREFIX: ClassVar[str] = "_trait_"
    _unique_counter: ClassVar[Iterator[int]] = itertools.count()

    @staticmethod
    def _try_make_child(
        node_type: type[fabll.Node],
        template_args: dict[str, str | bool | float] | None,
        identifier: str | None = None,
    ) -> fabll._ChildField | None:
        """
        Attempt to create a child field using MakeChild with template args.

        Returns None if no template args or MakeChild unavailable.
        Raises if MakeChild exists but fails (user error in template args).
        """
        if not template_args or not hasattr(node_type, "MakeChild"):
            return None

        # Convert float-to-int where applicable (ato parses all numbers as float)
        converted: dict[str, str | bool | int | float] = {
            key: int(value)
            if isinstance(value, float) and value.is_integer()
            else value
            for key, value in template_args.items()
        }

        try:
            child_field = node_type.MakeChild(**converted)
        except TypeError as e:
            from atopile.compiler import DslException

            raise DslException(
                f"Invalid template arguments for {node_type.__name__}: {e}"
            ) from e

        if identifier is not None:
            child_field._set_locator(identifier)

        return child_field

    @staticmethod
    def trait_from_field(
        field: fabll._ChildField,
        target_path: LinkPath | None,
        source_chunk_node: AST.SourceChunk | None = None,
    ) -> "list[AddMakeChildAction | AddMakeLinkAction]":
        """Create actions to attach a trait to a target node."""
        trait_class = field.nodetype
        trait_class_name = (
            trait_class.__name__ if isinstance(trait_class, type) else trait_class
        )

        target_suffix = "_".join(str(p) for p in target_path) if target_path else "self"
        trait_identifier = (
            f"{ActionsFactory.TRAIT_ID_PREFIX}{target_suffix}_{trait_class_name}"
        )
        field._set_locator(trait_identifier)

        return [
            AddMakeChildAction(
                target_path=[trait_identifier],
                child_field=field,
                source_chunk_node=source_chunk_node,
            ),
            AddMakeLinkAction(
                lhs_path=target_path if target_path else [],
                rhs_path=[trait_identifier],
                edge=fbrk.EdgeTrait.build(),
                source_chunk_node=source_chunk_node,
            ),
        ]

    @staticmethod
    def pin_child_field(pin_label: str, identifier: str) -> fabll._ChildField:
        """
        Create a pin as an Electrical with is_lead trait attached.

        Pins are Electrical interfaces that also act as leads for footprint pads.
        The pin label is used to match against pad names in the footprint.
        """
        regex = f"^{re.escape(str(pin_label))}$"

        pin = fabll._ChildField(nodetype=F.Electrical, identifier=identifier)

        # Add is_lead trait to the pin
        lead = is_lead.MakeChild()
        pin.add_dependant(fabll.Traits.MakeEdge(lead, [pin]))

        # Add can_attach_to_pad_by_name trait to the lead (to match pin label to pad)
        pad_attach = can_attach_to_pad_by_name.MakeChild(regex)
        lead.add_dependant(fabll.Traits.MakeEdge(pad_attach, [lead]))

        return pin

    @staticmethod
    def trait_field(
        trait_type: type[fabll.Node],
        template_args: dict[str, str | bool | float] | None,
    ) -> fabll._ChildField:
        """Create a trait field, using MakeChild with template args if available."""
        if (
            field := ActionsFactory._try_make_child(trait_type, template_args)
        ) is not None:
            return field

        # Fallback: create generic _ChildField and constrain string params
        # FIXME: handle non-string template args
        field = fabll._ChildField(trait_type)
        if template_args is not None:
            for param_name, value in template_args.items():
                if isinstance(value, str):
                    if (attr := getattr(trait_type, param_name, None)) is not None:
                        constraint = F.Literals.Strings.MakeChild_SetSuperset(
                            [field, attr], value
                        )
                        field.add_dependant(constraint)
                else:
                    raise DslException(
                        f"Template arg {param_name}={value} - non-string unsupported"
                    )
        return field

    @staticmethod
    def _make_child_field(
        nodetype: str | type[fabll.Node],
        identifier: str,
        template_args: dict[str, str | bool | float] | None,
        source_chunk_node: "AST.SourceChunk | None" = None,
    ) -> fabll._ChildField:
        """Common implementation for child field creation."""
        if isinstance(nodetype, type):
            if (
                field := ActionsFactory._try_make_child(
                    nodetype, template_args, identifier
                )
            ) is not None:
                return field

            # If MakeChild exists with required params but no template_args,
            # the user forgot to use module templating
            if not template_args and hasattr(nodetype, "MakeChild"):
                import inspect

                sig = inspect.signature(nodetype.MakeChild)
                required = [
                    p.name
                    for p in sig.parameters.values()
                    if p.name not in ("cls", "self")
                    and p.default is inspect.Parameter.empty
                    and p.kind
                    not in (
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    )
                ]
                if required:
                    msg = (
                        f"`{nodetype.__name__}` requires module templating. "
                        f"Use: new {nodetype.__name__}"
                        f"<{', '.join(f'{p}=...' for p in required)}>"
                    )
                    raise DslRichException(
                        msg,
                        original=DslException(msg),
                        source_node=source_chunk_node,
                    )

        return fabll._ChildField(nodetype=nodetype, identifier=identifier)

    @staticmethod
    def module_child_field(
        module_type: type[fabll.Node],
        identifier: str,
        template_args: dict[str, str | bool | float] | None = None,
        source_chunk_node: "AST.SourceChunk | None" = None,
    ) -> fabll._ChildField:
        """Create a child field from a fabll.Node class with optional template args."""
        return ActionsFactory._make_child_field(
            module_type, identifier, template_args, source_chunk_node
        )

    @staticmethod
    def child_field(
        identifier: str,
        type_identifier: str,
        module_type: type[fabll.Node] | None = None,
        template_args: dict[str, str | bool | float] | None = None,
        source_chunk_node: "AST.SourceChunk | None" = None,
    ) -> fabll._ChildField:
        """
        Create a child field from a type identifier string.

        If module_type is provided, uses it for template arg support.
        """
        if module_type is not None:
            return ActionsFactory._make_child_field(
                module_type, identifier, template_args, source_chunk_node
            )
        return fabll._ChildField(nodetype=type_identifier, identifier=identifier)

    @staticmethod
    def directed_link_action(
        lhs_link_path: LinkPath,
        rhs_link_path: LinkPath,
        direction: AST.DirectedConnectStmt.Direction,
        source_chunk_node: AST.SourceChunk | None = None,
    ) -> "AddMakeLinkAction":
        """
        Create a link action for directed (~> or <~) connections via can_bridge.

        Args:
            lhs_link_path: Pre-transformed LinkPath for left-hand side
            rhs_link_path: Pre-transformed LinkPath for right-hand side
            direction: Connection direction (RIGHT for ~>, LEFT for <~)
        """
        if direction == AST.DirectedConnectStmt.Direction.RIGHT:  # ~>
            lhs_pointer = F.can_bridge.out_.get_identifier()
            rhs_pointer = F.can_bridge.in_.get_identifier()
        else:  # <~
            lhs_pointer = F.can_bridge.in_.get_identifier()
            rhs_pointer = F.can_bridge.out_.get_identifier()

        lhs_bridge_path = ActionsFactory._build_bridge_path(lhs_link_path, lhs_pointer)
        rhs_bridge_path = ActionsFactory._build_bridge_path(rhs_link_path, rhs_pointer)

        return AddMakeLinkAction(
            lhs_path=lhs_bridge_path,
            rhs_path=rhs_bridge_path,
            source_chunk_node=source_chunk_node,
        )

    @staticmethod
    def _build_bridge_path(base_link_path: LinkPath, pointer: str) -> LinkPath:
        """
        Build a LinkPath that traverses through the can_bridge trait.

        For a base_link_path like ["a"], this builds:
        ["a", EdgeTrait(can_bridge), EdgeComposition("out_"), EdgePointer()]

        Args:
            base_link_path: Pre-transformed LinkPath (may have EdgeTraversal)
            pointer: The pointer child in can_bridge (e.g., "out_" or "in_")
        """
        return [
            *base_link_path,
            EdgeTrait.traverse(trait_type=can_bridge),
            EdgeComposition.traverse(identifier=pointer),
            EdgePointer.traverse(),
        ]

    @staticmethod
    def new_child_action(
        target_path: "FieldPath",
        type_identifier: str,
        module_type: type[fabll.Node] | None,
        template_args: dict[str, str | bool | float] | None,
        import_ref: "ImportRef | None",
        source_chunk_node: AST.SourceChunk | None = None,
    ) -> "AddMakeChildAction":
        """Create a single AddMakeChildAction for a new child instantiation."""
        return AddMakeChildAction(
            target_path=target_path,
            child_field=ActionsFactory.child_field(
                identifier=target_path.leaf.identifier,
                type_identifier=type_identifier,
                module_type=module_type,
                template_args=template_args,
                source_chunk_node=source_chunk_node,
            ),
            import_ref=import_ref,
            source_chunk_node=source_chunk_node,
        )

    @staticmethod
    def new_child_array_actions(
        target_path: "FieldPath",
        type_identifier: str,
        module_type: type[fabll.Node] | None,
        template_args: dict[str, str | bool | float] | None,
        count: int,
        import_ref: "ImportRef | None",
        source_chunk_node: AST.SourceChunk | None = None,
    ) -> "tuple[list[AddMakeChildAction], list[AddMakeLinkAction], list[FieldPath]]":
        """
        Create actions for a new child array instantiation.

        Returns a tuple of:
        - Child actions (pointer + elements)
        - Link actions (pointer-to-element edges)
        - Element paths (for scope registration by caller)
        """
        pointer_action = AddMakeChildAction(
            target_path=target_path,
            child_field=F.Collections.PointerSequence.MakeChild(),
            source_chunk_node=source_chunk_node,
        )

        element_actions: list[AddMakeChildAction] = []
        link_actions: list[AddMakeLinkAction] = []
        element_paths: list[FieldPath] = []

        for idx in range(count):
            element_path = FieldPath(
                segments=(
                    *target_path.segments,
                    FieldPath.Segment(identifier=str(idx), is_index=True),
                )
            )
            element_paths.append(element_path)

            element_actions.append(
                AddMakeChildAction(
                    target_path=element_path,
                    child_field=ActionsFactory.child_field(
                        identifier=element_path.identifiers()[0],
                        type_identifier=type_identifier,
                        module_type=module_type,
                        template_args=template_args,
                        source_chunk_node=source_chunk_node,
                    ),
                    import_ref=import_ref,
                    source_chunk_node=source_chunk_node,
                )
            )

            try:
                edge_attrs = fbrk.EdgePointer.build(identifier="e", index=idx)
            except ValueError as e:
                if str(e).startswith("Index out of range"):
                    raise ActionGenerationError("List exceeds maximum size") from e
                else:
                    raise ActionGenerationError(str(e)) from e

            link_actions.append(
                AddMakeLinkAction(
                    lhs_path=list(target_path.identifiers()),
                    rhs_path=list(element_path.identifiers()),
                    edge=edge_attrs,
                )
            )

        return [pointer_action, *element_actions], link_actions, element_paths

    @staticmethod
    def parameter_actions(
        target_path: "FieldPath",
        param_child: fabll._ChildField | None,
        constraint_operand: fabll._ChildField | None,
        constraint_expr: type[fabll.Node] | None = None,
        source_chunk_node: AST.SourceChunk | None = None,
    ) -> "list[AddMakeChildAction]":
        actions: list[AddMakeChildAction] = []

        # For nested paths, we don't create the parameter MakeChild - it must exist
        # on the nested type. We only create constraints that reference the path.
        is_nested = not target_path.is_singleton()

        if param_child is not None and not is_nested:
            actions.append(
                AddMakeChildAction(
                    target_path=target_path,
                    child_field=param_child,
                    source_chunk_node=source_chunk_node,
                )
            )

        if constraint_operand is not None:
            if constraint_expr is None:
                raise CompilerException(
                    "constraint_expr is required when constraint_operand is provided"
                )

            unique_target_str = (
                str(target_path).replace(".", "_")
                + f"_{next(ActionsFactory._unique_counter)}"
            )

            # Operand as child of type
            actions.append(
                AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,
                            FieldPath.Segment(f"operand_{unique_target_str}"),
                        )
                    ),
                    child_field=constraint_operand,
                    source_chunk_node=source_chunk_node,
                ),
            )

            actions.append(
                AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,
                            FieldPath.Segment(f"constraint_{unique_target_str}"),
                        )
                    ),
                    child_field=constraint_expr.MakeChild(
                        target_path.to_ref_path(),
                        [constraint_operand],
                        assert_=True,
                    ),
                    source_chunk_node=source_chunk_node,
                )
            )

        return actions

    @staticmethod
    def deferred_expression_action(
        expression_path: "FieldPath",
        operand: fabll._ChildField,
    ) -> "AddMakeChildAction":
        """Create action for an expression whose parameter will be inferred later."""
        return AddMakeChildAction(
            target_path=expression_path,
            child_field=operand,
        )


@dataclass(frozen=True)
class AddMakeChildAction:
    """
    target_path: String path to target eg. resistor.resistance
    relative to parent reference node. eg. app
    """

    target_path: FieldPath | fabll.RefPath
    child_field: fabll._ChildField | None = None
    import_ref: ImportRef | None = None
    source_chunk_node: AST.SourceChunk | None = None

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
    source_chunk_node: AST.SourceChunk | None = None


@dataclass(frozen=True)
class NoOpAction:
    pass


@dataclass(frozen=True)
class PendingInheritance:
    """Records an inheritance relationship to be resolved after linking."""

    derived_type: graph.BoundNode
    derived_name: str
    parent_ref: "ImportRef | str"  # ImportRef for external, str for local
    source_order: int
    source_node: fabll.Node | None = None


@dataclass(frozen=True)
class PendingRetype:
    """Records a retype operation to be resolved after linking."""

    containing_type: graph.BoundNode  # Type where retype is declared
    target_path: FieldPath  # Path to resolve (e.g., button.button)
    new_type_ref: graph.BoundNode  # Type reference node (linker resolves this)
    source_order: int  # Preserve declaration order
    source_node: fabll.Node | None = None


@dataclass
class ScopeState:
    symbols: dict[str, Symbol] = field(default_factory=dict)
    # Aliases for temporary loop variable bindings during `for` iteration.
    # Only used within the current lexical scope and intended to be short-lived.
    aliases: dict[str, FieldPath] = field(default_factory=dict)


@dataclass
class DeferredForLoop:
    """A for-loop recorded for execution in a later compiler phase."""

    type_identifier: str
    container_path: tuple[str, ...]
    variable_name: str
    slice_spec: tuple[int | None, int | None, int | None]
    body: AST.Scope
    source_order: int
