import logging
import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, ClassVar

import atopile.compiler.ast_types as AST
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.gentypegraph import (
    AddMakeChildAction,
    AddMakeLinkAction,
    ConstraintSpec,
    FieldPath,
    ImportRef,
    LinkPath,
    NewChildSpec,
    NoOpAction,
    ScopeState,
    Symbol,
)
from faebryk.core.faebrykpy import (
    EdgeComposition,
    EdgePointer,
    EdgeTrait,
    EdgeTraversal,
)
from faebryk.library.can_bridge import can_bridge
from faebryk.library.Lead import can_attach_to_pad_by_name, is_lead
from faebryk.libs.smd import SMDSize
from faebryk.libs.util import cast_assert, not_none

_Quantity = tuple[float, fabll._ChildField]

logger = logging.getLogger(__name__)

# FIXME: needs expanding
STDLIB_ALLOWLIST: set[type[fabll.Node]] = (
    # Modules
    {
        F.Capacitor,
        F.Electrical,
        F.ElectricPower,
        F.ElectricLogic,
        F.ElectricSignal,
        F.DifferentialPair,
        F.Resistor,
        F.ResistorVoltageDivider,
        F.LED,
        F.Inductor,
        F.Diode,
        F.Addressor,
        F.I2C,
        F.SPI,
        F.I2S,
        F.JTAG,
        F.UART,
        F.MultiCapacitor,
        # FIXME: separate list for internal types
    }
) | (
    # Traits
    {
        F.has_explicit_part,
        F.has_designator_prefix,
        F.has_part_picked,
        F.has_datasheet,
        F.is_auto_generated,
        F.has_net_name_suggestion,
        F.has_net_name_affix,
        F.has_package_requirements,
        F.is_pickable,
        F.is_atomic_part,
        F.requires_external_usage,
        F.can_bridge,
        F.can_bridge_by_name,
        F.has_part_removed,
        F.has_single_electric_reference,
    }
)

TRAIT_ID_PREFIX = "_trait_"
PIN_ID_PREFIX = "pin_"

# Aliases for legacy trait names that map to the actual trait types
# This allows old ato code using deprecated names to still work
TRAIT_ALIASES: dict[str, type[fabll.Node]] = {
    "has_datasheet_defined": F.has_datasheet,
    "has_single_electric_reference_shared": F.has_single_electric_reference,
}


@dataclass
class BuildState:
    type_roots: dict[str, graph.BoundNode]
    external_type_refs: list[tuple[graph.BoundNode, ImportRef | None]]
    file_path: Path | None
    import_path: str | None


class DslException(Exception):
    """
    Exceptions arising from user's DSL code.
    """


class CompilerException(Exception):
    """
    Exceptions arising from internal compiler failures.
    """


class is_ato_block(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    source_dir = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, source_dir: str) -> fabll._ChildField:
        field = fabll._ChildField(cls)
        field.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [field, cls.source_dir], source_dir
            )
        )
        return field

    def get_source_dir(self) -> str:
        """Get the source directory path where the .ato file is located."""
        return self.source_dir.get().force_extract_literal().get_values()[0]


class is_ato_module(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_ato_block = fabll.Traits.ImpliedTrait(is_ato_block)
    as_module = fabll.Traits.ImpliedTrait(fabll.is_module)


class is_ato_component(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_ato_block = fabll.Traits.ImpliedTrait(is_ato_block)


class is_ato_interface(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_ato_block = fabll.Traits.ImpliedTrait(is_ato_block)


class _ScopeStack:
    stack: list[ScopeState]

    def __init__(self) -> None:
        self.stack = []

    @contextmanager
    def enter(self) -> Generator[ScopeState, None, None]:
        state = ScopeState()
        self.stack.append(state)
        try:
            yield state
        finally:
            self.stack.pop()

    @property
    def current(self) -> ScopeState:
        return self.stack[-1]

    def add_symbol(self, symbol: Symbol) -> None:
        current_state = self.current
        if symbol.name in current_state.symbols:
            raise DslException(f"Symbol `{symbol.name}` already defined in scope")

        current_state.symbols[symbol.name] = symbol

        logger.info(f"Added symbol {symbol} to scope")

    def add_field(self, path: FieldPath, label: str | None = None) -> None:
        current_state = self.current
        if (key := str(path)) in current_state.fields:
            name = label or str(path)
            raise DslException(f"Field `{name}` already defined in scope")

        current_state.fields.add(key)

        logger.info(f"Added field {key} to scope")

    def has_field(self, path: FieldPath) -> bool:
        return any(str(path) in state.fields for state in reversed(self.stack))

    def ensure_defined(self, path: FieldPath) -> None:
        """Raise if field is not defined in scope."""
        if not self.has_field(path):
            raise DslException(f"Field `{path}` is not defined in scope")

    def try_resolve_symbol(self, name: str) -> Symbol | None:
        for state in reversed(self.stack):
            if name in state.symbols:
                return state.symbols[name]

    @contextmanager
    def temporary_alias(self, name: str, path: FieldPath):
        assert self.stack, "Alias cannot be installed without an active scope"

        if self.is_symbol_defined(name):
            raise DslException(
                f"Alias `{name}` would shadow an existing symbol in scope"
            )

        state = self.current
        had_existing = name in state.aliases
        previous = state.aliases.get(name)
        state.aliases[name] = path
        try:
            yield
        finally:
            if had_existing:
                assert previous is not None
                state.aliases[name] = previous
            else:
                state.aliases.pop(name, None)

    def resolve_alias(self, name: str) -> FieldPath | None:
        return self.current.aliases.get(name)

    def add_alias(self, name: str, target: FieldPath) -> None:
        """
        Add a permanent alias in the current scope.
        Used for pin declarations only.
        """
        self.current.aliases[name] = target

    @property
    def depth(self) -> int:
        return len(self.stack)

    def is_symbol_defined(self, name: str) -> bool:
        return any(name in state.symbols for state in self.stack)


class _TypeContextStack:
    """
    Maintains the current TypeGraph context while emitting IR.

    All structural lookups are delegated back to the TypeGraph so mounts, pointer
    sequences, and other graph semantics are resolved in one place.

    Translates any `TypeGraphPathError` into a user-facing `DslException` that
    preserves the enriched error metadata.
    """

    def __init__(
        self, *, g: graph.GraphView, tg: fbrk.TypeGraph, state: BuildState
    ) -> None:
        self._stack: list[tuple[graph.BoundNode, fabll.TypeNodeBoundTG]] = []
        self._g = g
        self._tg = tg
        self._state = state

    @contextmanager
    def enter(
        self, type_node: graph.BoundNode, bound_tg: fabll.TypeNodeBoundTG
    ) -> Generator[None, None, None]:
        self._stack.append((type_node, bound_tg))
        try:
            yield
        finally:
            self._stack.pop()

    def current(self) -> tuple[graph.BoundNode, fabll.TypeNodeBoundTG]:
        if not self._stack:
            raise DslException("Type context is not available")
        return self._stack[-1]

    def apply_action(self, action) -> None:
        type_node, bound_tg = self.current()

        match action:
            case AddMakeChildAction() as action:
                self._add_child(type_node=type_node, bound_tg=bound_tg, action=action)
            case AddMakeLinkAction() as action:
                self._add_link(type_node=type_node, bound_tg=bound_tg, action=action)
            case list() | tuple() as actions:
                for a in actions:
                    self.apply_action(a)
                return
            case NoOpAction():
                return
            case _:
                raise NotImplementedError(f"Unhandled action: {action}")

    def resolve_reference(
        self, path: FieldPath, validate: bool = True
    ) -> graph.BoundNode:
        type_node, _ = self.current()
        return self._ensure_field_path(
            type_node=type_node, field_path=path, validate=validate
        )

    @staticmethod
    def _format_path_error(
        field_path: FieldPath, error: fbrk.TypeGraphPathError
    ) -> str:
        full_path = ".".join(error.path) if error.path else str(field_path)

        match error.kind:
            # FIXME: enum or different types or format on Zig side
            case "missing_parent":
                prefix = error.path[: error.failing_segment_index]
                joined = ".".join(prefix) if prefix else full_path
                return f"Field `{joined}` is not defined in scope"
            case "invalid_index":
                container_segments = error.path[: error.failing_segment_index]
                container = ".".join(container_segments)
                index_value = (
                    error.index_value
                    if error.index_value is not None
                    else error.failing_segment
                )
                if container:
                    return f"Field `{container}[{index_value}]` is not defined in scope"
                return f"Field `[ {index_value} ]` is not defined in scope"
            case _:
                return f"Field `{full_path}` is not defined in scope"

    def _ensure_field_path(
        self, type_node: graph.BoundNode, field_path: FieldPath, validate: bool = True
    ) -> graph.BoundNode:
        # Cast to list[str | EdgeTraversal] for type compatibility with the
        # ensure_child_reference API which accepts mixed string/EdgeTraversal paths
        identifiers: list[str | EdgeTraversal] = list(field_path.identifiers())
        try:
            return self._tg.ensure_child_reference(
                type_node=type_node, path=identifiers, validate=validate
            )
        except fbrk.TypeGraphPathError as exc:
            raise DslException(self._format_path_error(field_path, exc)) from exc

    def _add_child(
        self,
        type_node: graph.BoundNode,
        bound_tg: fabll.TypeNodeBoundTG,
        action: AddMakeChildAction,
    ) -> None:
        assert action.child_field is not None
        action.child_field._set_locator(action.get_identifier())
        fabll.Node._exec_field(t=bound_tg, field=action.child_field)

        # Track unresolved type references (both imports and local forward refs)
        if isinstance(action.child_field.nodetype, str):
            assert isinstance(action.child_field.identifier, str)
            type_ref = self._tg.get_make_child_type_reference_by_identifier(
                type_node=type_node, identifier=action.child_field.identifier
            )
            self._state.external_type_refs.append(
                (not_none(type_ref), action.import_ref)
            )

    # TODO FIXME: no type checking for is_interface trait on connected nodes.
    # We should use the fabll connect_to method for this.
    def _add_link(
        self,
        type_node: graph.BoundNode,
        bound_tg: fabll.TypeNodeBoundTG,
        action: AddMakeLinkAction,
    ) -> None:
        bound_tg.MakeEdge(
            lhs_reference_path=action.lhs_path,
            rhs_reference_path=action.rhs_path,
            edge=action.edge or fbrk.EdgeInterfaceConnection.build(shallow=False),
        )


def _create_trait_actions(
    trait_name: str,
    trait_field: fabll._ChildField,
    target_path: LinkPath,
) -> list[AddMakeChildAction | AddMakeLinkAction]:
    target_suffix = "_".join(str(p) for p in target_path) if target_path else "self"
    trait_identifier = f"{TRAIT_ID_PREFIX}{target_suffix}_{trait_name}"
    trait_field._set_locator(trait_identifier)

    actions: list[AddMakeChildAction | AddMakeLinkAction] = [
        AddMakeChildAction(
            target_path=[trait_identifier],
            parent_reference=None,
            parent_path=None,
            child_field=trait_field,
        ),
        AddMakeLinkAction(
            lhs_path=target_path,
            rhs_path=[trait_identifier],
            edge=fbrk.EdgeTrait.build(),
        ),
    ]
    return actions


def _parse_smd_size(value: str) -> SMDSize:
    """
    Parse package string to SMDSize enum.

    Handles:
    - Prefixes like R0402, C0603, L0805 (strips prefix)
    - Imperial format like 0402 (adds I prefix)
    - Direct enum names like I0402
    """
    # Strip R/C/L prefix for resistors/capacitors/inductors
    value = re.sub(r"^[RCL]", "I", value)

    # Assume imperial if just digits
    if re.match(r"^[0-9]+$", value):
        value = f"I{value}"

    # Validate against SMDSize enum
    valid_names = {s.name for s in SMDSize}
    if value not in valid_names:
        from faebryk.libs.util import md_list

        raise DslException(
            f"Invalid package: `{value}`. Valid packages are:\n"
            f"{md_list(s.name for s in SMDSize)}"
        )

    return SMDSize[value]


class AssignmentOverrides:
    """
    Registry of assignment overrides that convert assignments to trait operations.

    Handles legacy sugar syntax like:
    - `power.required = True` -> attaches requires_external_usage trait
    - `cap.package = "0402"` -> attaches has_package_requirements trait
    - `node.lcsc_id = "C12345"` -> attaches has_explicit_part trait
    - `node.datasheet_url = "https://..."` -> attaches has_datasheet trait
    - `node.designator_prefix = "U"` -> attaches has_designator_prefix trait
    - `net.override_net_name = "VCC"` -> attaches has_net_name_suggestion (EXPECTED)
    - `net.suggest_net_name = "VCC"` -> attaches has_net_name_suggestion (SUGGESTED)
    """

    @staticmethod
    def handle_required(
        target_path: FieldPath,
        value: bool,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.required = True/False`."""
        if not isinstance(value, bool):
            raise DslException(
                f"Invalid value for `required`: expected bool, "
                f"got {type(value).__name__}"
            )

        if not value:
            return [NoOpAction()]  # type: ignore[list-item]

        if not target_path.parent_segments:
            raise DslException("`required` must be set on a field, not at top level")

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        trait_field = F.requires_external_usage.MakeChild()
        return _create_trait_actions(
            "requires_external_usage", trait_field, parent_path
        )

    @staticmethod
    def handle_package(
        target_path: FieldPath,
        value: str,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.package = "0402"`."""
        if not isinstance(value, str):
            raise DslException(
                f"Invalid value for `package`: expected str, got {type(value).__name__}"
            )

        if not target_path.parent_segments:
            raise DslException("`package` must be set on a field, not at top level")

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        size = _parse_smd_size(value)
        trait_field = F.has_package_requirements.MakeChild(size=size)
        return _create_trait_actions(
            "has_package_requirements", trait_field, parent_path
        )

    @staticmethod
    def handle_lcsc_id(
        target_path: FieldPath,
        value: str,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.lcsc_id = "C12345"`."""
        if not isinstance(value, str):
            raise DslException(
                f"Invalid value for `lcsc_id`: expected str, got {type(value).__name__}"
            )

        if not target_path.parent_segments:
            raise DslException("`lcsc_id` must be set on a field, not at top level")

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        trait_field = F.has_explicit_part.MakeChild(
            mfr=None,
            partno=None,
            supplier_id="lcsc",
            supplier_partno=value,
            pinmap=None,
            override_footprint=None,
        )
        return _create_trait_actions("has_explicit_part", trait_field, parent_path)

    @staticmethod
    def handle_datasheet_url(
        target_path: FieldPath,
        value: str,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.datasheet_url = "https://..."`."""
        if not isinstance(value, str):
            raise DslException(
                f"Invalid value for `datasheet_url`: expected str, "
                f"got {type(value).__name__}"
            )

        if not target_path.parent_segments:
            raise DslException(
                "`datasheet_url` must be set on a field, not at top level"
            )

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        trait_field = F.has_datasheet.MakeChild(datasheet=value)
        return _create_trait_actions("has_datasheet", trait_field, parent_path)

    @staticmethod
    def handle_designator_prefix(
        target_path: FieldPath,
        value: str,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.designator_prefix = "U"`."""
        if not isinstance(value, str):
            raise DslException(
                f"Invalid value for `designator_prefix`: expected str, "
                f"got {type(value).__name__}"
            )

        if not target_path.parent_segments:
            raise DslException(
                "`designator_prefix` must be set on a field, not at top level"
            )

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        trait_field = F.has_designator_prefix.MakeChild(prefix=value)
        return _create_trait_actions("has_designator_prefix", trait_field, parent_path)

    @staticmethod
    def handle_override_net_name(
        target_path: FieldPath,
        value: str,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.override_net_name = "VCC"`."""
        if not isinstance(value, str):
            raise DslException(
                f"Invalid value for `override_net_name`: expected str, "
                f"got {type(value).__name__}"
            )

        if not target_path.parent_segments:
            raise DslException(
                "`override_net_name` must be set on a field, not at top level"
            )

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        trait_field = F.has_net_name_suggestion.MakeChild(
            name=value, level=F.has_net_name_suggestion.Level.EXPECTED
        )
        return _create_trait_actions(
            "has_net_name_suggestion", trait_field, parent_path
        )

    @staticmethod
    def handle_suggest_net_name(
        target_path: FieldPath,
        value: str,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """Handle `node.suggest_net_name = "VCC"`."""
        if not isinstance(value, str):
            raise DslException(
                f"Invalid value for `suggest_net_name`: expected str, "
                f"got {type(value).__name__}"
            )

        if not target_path.parent_segments:
            raise DslException(
                "`suggest_net_name` must be set on a field, not at top level"
            )

        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )
        trait_field = F.has_net_name_suggestion.MakeChild(
            name=value, level=F.has_net_name_suggestion.Level.SUGGESTED
        )
        return _create_trait_actions(
            "has_net_name_suggestion", trait_field, parent_path
        )

    # Mapping of field names to handler functions
    HANDLERS: ClassVar[dict[str, Callable[[FieldPath, Any], list | None]]] = {
        "required": handle_required.__func__,  # type: ignore[attr-defined]
        "package": handle_package.__func__,  # type: ignore[attr-defined]
        "lcsc_id": handle_lcsc_id.__func__,  # type: ignore[attr-defined]
        "datasheet_url": handle_datasheet_url.__func__,  # type: ignore[attr-defined]
        "designator_prefix": handle_designator_prefix.__func__,  # type: ignore[attr-defined]
        "override_net_name": handle_override_net_name.__func__,  # type: ignore[attr-defined]
        "suggest_net_name": handle_suggest_net_name.__func__,  # type: ignore[attr-defined]
    }

    @classmethod
    def try_handle(
        cls,
        target_path: FieldPath,
        assignable_node: AST.Assignable,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """
        Check if this assignment is an override and handle it.

        Returns:
            List of actions if this is an override, None otherwise.
        """
        leaf_name = target_path.leaf.identifier
        handler = cls.HANDLERS.get(leaf_name)

        if handler is None:
            return None

        value_node = assignable_node.get_value().switch_cast()

        value: str | bool
        if value_node.isinstance(AST.AstString):
            value = value_node.cast(t=AST.AstString).get_text()
        elif value_node.isinstance(AST.Boolean):
            value = value_node.cast(t=AST.Boolean).get_value()
        else:
            return None

        return handler(target_path, value)


class TraitOverrides:
    """
    Registry of trait overrides that translate legacy/aliased trait names to their
    actual implementations.

    Handles:
    - `trait can_bridge_by_name<input_name="x", output_name="y">` -> can_bridge
    - `trait has_datasheet_defined<datasheet="url">` -> has_datasheet
    """

    @staticmethod
    def handle_can_bridge_by_name(
        target_path_list: LinkPath,
        template_args: dict[str, Any] | None,
    ) -> list[AddMakeChildAction | AddMakeLinkAction]:
        """
        Translate can_bridge_by_name to can_bridge with RefPaths.

        This allows ato code like:
            trait can_bridge_by_name<input_name="data_in", output_name="data_out">
        to work by creating a can_bridge trait with the correct pointer paths.
        """
        input_name = (
            template_args.get("input_name", "input") if template_args else "input"
        )
        output_name = (
            template_args.get("output_name", "output") if template_args else "output"
        )
        if not isinstance(input_name, str) or not isinstance(output_name, str):
            raise DslException(
                "can_bridge_by_name requires string values for input_name and "
                "output_name"
            )
        # Create can_bridge.MakeEdge with paths to the named children
        trait_field = F.can_bridge.MakeEdge([input_name], [output_name])
        return _create_trait_actions("can_bridge", trait_field, target_path_list)

    @staticmethod
    def handle_has_datasheet_defined(
        target_path_list: LinkPath,
        template_args: dict[str, Any] | None,
    ) -> list[AddMakeChildAction | AddMakeLinkAction]:
        """
        Translate has_datasheet_defined to has_datasheet.

        This allows ato code like:
            trait has_datasheet_defined<datasheet="https://...">
        to work by creating a has_datasheet trait.
        """
        if not template_args or "datasheet" not in template_args:
            raise DslException(
                "has_datasheet_defined requires a 'datasheet' template argument"
            )
        datasheet = template_args["datasheet"]
        if not isinstance(datasheet, str):
            raise DslException(
                f"has_datasheet_defined requires a string value for 'datasheet', "
                f"got {type(datasheet).__name__}"
            )
        trait_field = F.has_datasheet.MakeChild(datasheet=datasheet)
        return _create_trait_actions("has_datasheet", trait_field, target_path_list)

    @staticmethod
    def handle_has_single_electric_reference_shared(
        target_path_list: LinkPath,
        template_args: dict[str, Any] | None,
    ) -> list[AddMakeChildAction | AddMakeLinkAction]:
        """
        Translate has_single_electric_reference_shared to has_single_electric_reference.

        This allows ato code like:
            trait has_single_electric_reference_shared<gnd_only=True>
        to work by creating a has_single_electric_reference trait with ground_only.
        """
        # Translate gnd_only -> ground_only
        ground_only = False
        if template_args and "gnd_only" in template_args:
            gnd_only_value = template_args["gnd_only"]
            if not isinstance(gnd_only_value, bool):
                raise DslException(
                    "has_single_electric_reference_shared requires a bool for "
                    "'gnd_only'"
                )
            ground_only = gnd_only_value

        trait_field = F.has_single_electric_reference.MakeChild(ground_only=ground_only)
        return _create_trait_actions(
            "has_single_electric_reference", trait_field, target_path_list
        )

    # Mapping of trait names to handler functions
    HANDLERS: ClassVar[dict[str, Callable[[LinkPath, dict[str, Any] | None], list]]] = {
        "can_bridge_by_name": handle_can_bridge_by_name.__func__,  # type: ignore
        "has_datasheet_defined": handle_has_datasheet_defined.__func__,  # type: ignore
        "has_single_electric_reference_shared": (
            handle_has_single_electric_reference_shared.__func__  # type: ignore
        ),
    }

    # Deprecation messages for legacy trait names
    DEPRECATION_MESSAGES: ClassVar[dict[str, str]] = {
        "can_bridge_by_name": (
            "DEPRECATION: 'can_bridge_by_name' is deprecated. "
            "Use 'can_bridge' with pointer paths instead."
        ),
        "has_datasheet_defined": (
            "DEPRECATION: 'has_datasheet_defined' is deprecated. "
            "Use 'has_datasheet' instead."
        ),
        "has_single_electric_reference_shared": (
            "DEPRECATION: 'has_single_electric_reference_shared' is deprecated. "
            "Use 'has_single_electric_reference' with 'ground_only' parameter instead."
        ),
    }

    @classmethod
    def try_handle(
        cls,
        trait_type_name: str,
        target_path_list: LinkPath,
        template_args: dict[str, Any] | None,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | None:
        """
        Check if this trait needs special handling and process it.

        Returns:
            List of actions if this is an override, None otherwise.
        """
        handler = cls.HANDLERS.get(trait_type_name)
        if handler is None:
            return None

        # Log deprecation warning
        if trait_type_name in cls.DEPRECATION_MESSAGES:
            logger.warning(cls.DEPRECATION_MESSAGES[trait_type_name])

        return handler(target_path_list, template_args)


class ConnectOverrides:
    """
    Registry of path translations for connect statements.

    Handles legacy path names that need to be translated to their current equivalents:
    - `vcc` -> `hv` (high voltage rail on ElectricPower)
    - `gnd` -> `lv` (low voltage rail on ElectricPower)

    This provides backwards compatibility for older ato code that used the legacy
    naming conventions for power interfaces.
    """

    # Mapping of legacy path segment names to their current equivalents
    PATH_TRANSLATIONS: ClassVar[dict[str, str]] = {
        "vcc": "hv",
        "gnd": "lv",
    }

    # Deprecation messages for legacy path names
    DEPRECATION_MESSAGES: ClassVar[dict[str, str]] = {
        "vcc": "DEPRECATION: '.vcc' is deprecated. Use '.hv' instead.",
        "gnd": "DEPRECATION: '.gnd' is deprecated. Use '.lv' instead.",
    }

    # Track which deprecation warnings have been emitted to avoid spam
    _warned_segments: ClassVar[set[str]] = set()

    @classmethod
    def translate_segment(cls, segment: str) -> str:
        """Translate a single path segment if it's a legacy name."""
        if segment in cls.PATH_TRANSLATIONS:
            # Emit deprecation warning (only once per segment type)
            if segment not in cls._warned_segments:
                logger.warning(cls.DEPRECATION_MESSAGES[segment])
                cls._warned_segments.add(segment)
            return cls.PATH_TRANSLATIONS[segment]
        return segment

    @classmethod
    def translate_identifiers(cls, identifiers: list[str]) -> list[str]:
        """Translate a list of string identifiers."""
        return [cls.translate_segment(s) for s in identifiers]

    @classmethod
    def translate_path(cls, path: LinkPath) -> LinkPath:
        """
        Translate any legacy path segments to their current equivalents.

        Only string segments are translated; EdgeTraversal objects are left unchanged.

        Args:
            path: A list of path segment identifiers (strings or EdgeTraversal)

        Returns:
            A new list with any legacy string names translated
        """
        result: LinkPath = []
        for segment in path:
            if isinstance(segment, str):
                result.append(cls.translate_segment(segment))
            else:
                result.append(segment)
        return result


class AnyAtoBlock(fabll.Node):
    _definition_identifier: ClassVar[str] = "definition"
    # FIXME: this should likely be removed or updated to use the new MakeChild
    # For now, we'll pass an empty string as source_dir since this seems to be a base type
    is_ato_block = fabll.Traits.MakeEdge(is_ato_block.MakeChild(source_dir=""))


class ASTVisitor:
    """
    Generates a TypeGraph from the AST.

    Error handling strategy:
    - Fail early (TODO: revisit — return list of errors and let caller decide impact)
    - Use DslException for errors arising from code contents

    Responsibilities & boundaries:
    - Translate parsed AST nodes into high-level TypeGraph actions (e.g.
      creating fields, wiring connections, recording imports) without peeking
      into fabll/node semantics or mutating the TypeGraph directly.
    - Maintain only minimal lexical bookkeeping (detecting redeclarations,
      ensuring names are declared before reuse); structural validation and path
      resolution are delegated to the TypeGraph.
    - Defer cross-file linkage, stdlib loading, and part selection to the
      surrounding build/linker code. This visitor produces a `BuildState` that
      higher layers consume to finish linking.

    TODO: store graph references instead of reifying as IR?
    """

    class _Pragma(StrEnum):
        EXPERIMENT = "experiment"

    class _Experiment(StrEnum):
        BRIDGE_CONNECT = "BRIDGE_CONNECT"
        FOR_LOOP = "FOR_LOOP"
        TRAITS = "TRAITS"
        MODULE_TEMPLATING = "MODULE_TEMPLATING"
        INSTANCE_TRAITS = "INSTANCE_TRAITS"

    def __init__(
        self,
        ast_root: AST.File,
        graph: graph.GraphView,
        type_graph: fbrk.TypeGraph,
        import_path: str | None,
        file_path: Path | None,
        stdlib_allowlist: set[type[fabll.Node]] | None = None,
    ) -> None:
        self._ast_root = ast_root
        self._graph = graph
        self._type_graph = type_graph
        self._state = BuildState(
            type_roots={},
            external_type_refs=[],
            file_path=file_path,
            import_path=import_path,
        )

        self._pointer_sequence_type = F.Collections.PointerSequence.bind_typegraph(
            self._type_graph
        ).get_or_create_type()
        self._electrical_type = F.Electrical.bind_typegraph(
            self._type_graph
        ).get_or_create_type()
        self._experiments: set[ASTVisitor._Experiment] = set()
        self._scope_stack = _ScopeStack()
        self._type_stack = _TypeContextStack(
            g=self._graph,
            tg=self._type_graph,
            state=self._state,
        )
        self._stdlib_allowlist = {
            type_._type_identifier(): type_
            for type_ in stdlib_allowlist or STDLIB_ALLOWLIST.copy()
        }
        # Add trait aliases (legacy names -> actual types)
        self._stdlib_allowlist.update(
            {alias: type_ for alias, type_ in TRAIT_ALIASES.items()}
        )

    @staticmethod
    def _parse_pragma(pragma_text: str) -> tuple[str, list[str | int | float | bool]]:
        """
        pragma_stmt: '#pragma' function_call
        function_call: NAME '(' argument (',' argument)* ')'
        argument: literal
        literal: STRING | NUMBER | BOOLEAN

        returns (name, [arg1, arg2, ...])
        """
        import re

        _pragma = "#pragma"
        _function_name = r"(?P<function_name>\w+)"
        _string = r'"([^"]*)"'
        _int = r"(\d+)"
        _args_str = r"(?P<args_str>.*?)"

        pragma_syntax = re.compile(
            rf"^{_pragma}\s+{_function_name}\(\s*{_args_str}\s*\)$"
        )
        _individual_arg_pattern = re.compile(rf"{_string}|{_int}")
        match = pragma_syntax.match(pragma_text)

        if match is None:
            raise DslException(f"Malformed pragma: '{pragma_text}'")

        data = match.groupdict()
        name = data["function_name"]
        args_str = data["args_str"]
        found_args = _individual_arg_pattern.findall(args_str)
        arguments = [
            string_arg if string_arg is not None else int(int_arg)
            for string_arg, int_arg in found_args
        ]
        return name, arguments

    def enable_experiment(self, experiment: _Experiment) -> None:
        print(f"Enabling experiment: {experiment}")
        self._experiments.add(experiment)

    def ensure_experiment(self, experiment: _Experiment) -> None:
        if experiment not in self._experiments:
            raise DslException(f"Experiment {experiment} is not enabled")

    def _make_type_identifier(self, name: str) -> str:
        """Create namespaced identifier for ato types."""
        if self._state.import_path is not None:
            return f"{self._state.import_path}::{name}"
        return name

    def build(self) -> BuildState:
        assert self._ast_root.isinstance(AST.File)
        self.visit(self._ast_root)
        return self._state

    def visit(self, node: fabll.Node):
        # TODO: less magic dispatch
        node_type = cast_assert(str, node.get_type_name())
        logger.info(f"Visiting node of type {node_type}")

        try:
            handler = getattr(self, f"visit_{node_type}")
        except AttributeError:
            raise NotImplementedError(f"No handler for node type: {node_type}")

        bound_node = getattr(AST, node_type).bind_instance(node.instance)
        return handler(bound_node)

    def visit_File(self, node: AST.File):
        self.visit(node.scope.get())

    def visit_Scope(self, node: AST.Scope):
        with self._scope_stack.enter():
            for scope_child in node.stmts.get().as_list():
                self.visit(scope_child)

    def visit_PragmaStmt(self, node: AST.PragmaStmt):
        if (pragma := node.get_pragma()) is None:
            raise DslException(f"Pragma statement has no pragma text: {node}")

        pragma_func_name, pragma_args = self._parse_pragma(pragma)

        match pragma_func_name:
            case ASTVisitor._Pragma.EXPERIMENT.value:
                if len(pragma_args) != 1:
                    raise DslException(
                        f"Experiment pragma takes exactly one argument: `{pragma}`"
                    )

                (experiment_name,) = pragma_args

                try:
                    experiment = ASTVisitor._Experiment(experiment_name)
                except ValueError:
                    raise DslException(
                        f"Experiment not recognized: `{experiment_name}`"
                    )

                self.enable_experiment(experiment)
            case _:
                raise DslException(f"Pragma function not recognized: `{pragma}`")

    def visit_ImportStmt(self, node: AST.ImportStmt):
        type_ref_name = node.get_type_ref_name()
        path = node.get_path()
        import_ref = ImportRef(name=type_ref_name, path=path)

        if path is None and type_ref_name not in self._stdlib_allowlist:
            raise DslException(f"Standard library import not found: {type_ref_name}")

        # Warn about deprecated trait aliases
        if type_ref_name in TRAIT_ALIASES:
            actual_type = TRAIT_ALIASES[type_ref_name]
            logger.warning(
                f"DEPRECATION: '{type_ref_name}' is deprecated. "
                f"Use '{actual_type.__name__}' instead."
            )

        self._scope_stack.add_symbol(Symbol(name=type_ref_name, import_ref=import_ref))

    def visit_BlockDefinition(self, node: AST.BlockDefinition):
        if self._scope_stack.depth != 1:
            raise DslException("Nested block definitions are not permitted")

        module_name = node.get_type_ref_name()

        if self._scope_stack.is_symbol_defined(module_name):
            raise DslException(f"Symbol `{module_name}` already defined in scope")

        # Get source directory for is_ato_block trait
        source_dir = str(self._state.file_path.parent) if self._state.file_path else ""

        match node.get_block_type():
            case AST.BlockDefinition.BlockType.MODULE:

                class _Module(fabll.Node):
                    _is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_module = fabll.Traits.MakeEdge(is_ato_module.MakeChild())
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Module

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    _is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_component = fabll.Traits.MakeEdge(
                        is_ato_component.MakeChild()
                    )

                _Block = _Component

            case AST.BlockDefinition.BlockType.INTERFACE:

                class _Interface(fabll.Node):
                    is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_interface = fabll.Traits.MakeEdge(
                        is_ato_interface.MakeChild()
                    )

                _Block = _Interface

        type_identifier = self._make_type_identifier(module_name)
        _Block.__name__ = type_identifier
        _Block.__qualname__ = type_identifier

        type_node = self._type_graph.add_type(identifier=type_identifier)
        type_node_bound_tg = fabll.TypeNodeBoundTG(tg=self._type_graph, t=_Block)

        # Process the class fields (traits) we just defined
        # Since we manually added the type node above, get_or_create_type inside TypeNodeBoundTG
        # will find it and skip _create_type, so we must call it manually.
        _Block._create_type(type_node_bound_tg)

        with self._scope_stack.enter():
            with self._type_stack.enter(type_node, type_node_bound_tg):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))

        # link back to AST node
        fbrk.EdgePointer.point_to(
            bound_node=type_node,
            target_node=node.instance.node(),
            identifier=AnyAtoBlock._definition_identifier,
            order=None,
        )

        self._state.type_roots[module_name] = type_node
        self._scope_stack.add_symbol(Symbol(name=module_name, type_node=type_node))

    def visit_PassStmt(self, node: AST.PassStmt):
        return NoOpAction()

    def visit_Boolean(
        self, node: AST.Boolean
    ) -> "fabll._ChildField[F.Literals.Booleans]":
        return F.Literals.Booleans.MakeChild(node.get_value())

    def visit_AstString(
        self, node: AST.AstString
    ) -> "fabll._ChildField[F.Literals.Strings]":
        return F.Literals.Strings.MakeChild(node.get_text())

    def visit_StringStmt(self, node: AST.StringStmt):
        # TODO: add docstring trait to preceding node
        return NoOpAction()

    def visit_SignaldefStmt(self, node: AST.SignaldefStmt):
        (signal_name,) = node.name.get().get_values()
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=signal_name),))

        self._scope_stack.add_field(target_path, label=f"Signal `{signal_name}`")

        return AddMakeChildAction(
            target_path=target_path,
            child_field=fabll._ChildField(
                nodetype=F.Electrical,
                identifier=signal_name,
            ),
            parent_reference=None,
            parent_path=None,
        )

    def _create_pin_child_field(
        self, pin_label: str, identifier: str
    ) -> fabll._ChildField:
        """
        Create a pin as an Electrical with is_lead trait attached.
        Pins are Electrical interfaces that also act as leads for footprint pads.
        """
        import re

        regex = f"^{re.escape(str(pin_label))}$"

        # Create Electrical with explicit identifier
        pin = fabll._ChildField(nodetype=F.Electrical, identifier=identifier)

        # Add is_lead trait to the pin (attached to pin itself via [pin])
        lead = is_lead.MakeChild()
        pin.add_dependant(fabll.Traits.MakeEdge(lead, [pin]))

        # Add can_attach_to_pad_by_name trait to the lead (to match pin label to pad)
        pad_attach = can_attach_to_pad_by_name.MakeChild(regex)
        lead.add_dependant(fabll.Traits.MakeEdge(pad_attach, [lead]))

        return pin

    def visit_PinDeclaration(self, node: AST.PinDeclaration):
        pin_label = node.get_label()
        if pin_label is None:
            raise DslException("Pin declaration has no label")

        if isinstance(pin_label, float) and pin_label.is_integer():
            pin_label_str = str(int(pin_label))
        else:
            pin_label_str = str(pin_label)

        # TODO: can identifiers include arbitrary strings, given a valid prefix?
        # Pin labels can be numbers, so prefix with "pin_" for valid identifier
        identifier = f"{PIN_ID_PREFIX}{pin_label_str}"
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=identifier),))

        self._scope_stack.add_field(target_path, label=f"Pin `{pin_label_str}`")
        self._scope_stack.add_alias(pin_label_str, target_path)

        return AddMakeChildAction(
            target_path=target_path,
            parent_reference=None,
            parent_path=None,
            child_field=self._create_pin_child_field(pin_label_str, identifier),
        )

    def visit_FieldRef(self, node: AST.FieldRef) -> FieldPath:
        segments: list[FieldPath.Segment] = []

        for part_node in node.parts.get().as_list():
            part = part_node.cast(t=AST.FieldRefPart)
            (name,) = part.name.get().get_values()
            segments.append(FieldPath.Segment(identifier=name))

            if (key := part.get_key()) is not None:
                segments.append(FieldPath.Segment(identifier=str(key), is_index=True))

        if node.get_pin() is not None:
            raise NotImplementedError(
                "Field references with pin suffixes are not supported yet"
            )

        if not segments:
            raise DslException("Empty field reference encountered")

        # Alias rewrite (for-loop variable): if the root segment is an alias,
        # expand it to the aliased field path.
        if (
            aliased := self._scope_stack.resolve_alias(segments[0].identifier)
        ) is not None:
            # Replace root with alias path
            segments = list(aliased.segments) + segments[1:]

        return FieldPath(segments=tuple(segments))

    def _handle_new_child(
        self,
        target_path: FieldPath,
        new_spec: NewChildSpec,
        parent_reference: graph.BoundNode | None,
        parent_path: FieldPath | None,
    ) -> list[AddMakeChildAction] | AddMakeChildAction:
        self._scope_stack.add_field(target_path)

        # Check if module type is in stdlib and supports templating
        module_fabll_type = (
            self._stdlib_allowlist.get(new_spec.type_identifier)
            if new_spec.type_identifier is not None
            else None
        )

        if new_spec.count is None:
            # TODO: review
            if target_path.leaf.is_index and parent_path is not None:
                try:
                    type_node, _ = self._type_stack.current()
                    pointer_members = self._type_graph.collect_pointer_members(
                        type_node=type_node,
                        container_path=list(parent_path.identifiers()),
                    )
                except fbrk.TypeGraphPathError as exc:
                    raise DslException(
                        self._type_stack._format_path_error(parent_path, exc)
                    ) from exc

                member_identifiers = {
                    identifier
                    for identifier, _ in pointer_members
                    if identifier is not None
                }

                if target_path.leaf.identifier not in member_identifiers:
                    raise DslException(f"Field `{target_path}` is not defined in scope")

            assert new_spec.type_identifier is not None

            # Use templated MakeChild if we have template args and a stdlib type
            if new_spec.template_args and module_fabll_type is not None:
                child_field = self._create_module_child_field(
                    module_type=module_fabll_type,
                    identifier=target_path.leaf.identifier,
                    template_args=new_spec.template_args,
                )
            else:
                child_field = fabll._ChildField(
                    nodetype=new_spec.type_identifier,
                    identifier=target_path.leaf.identifier,
                )

            return AddMakeChildAction(
                target_path=target_path,  # FIXME: this seems wrong
                parent_reference=parent_reference,
                parent_path=parent_path,
                child_field=child_field,
                import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
            )

        pointer_action = AddMakeChildAction(
            target_path=target_path,
            child_field=F.Collections.PointerSequence.MakeChild(),
            parent_reference=parent_reference,
            parent_path=parent_path,
        )

        element_actions: list[AddMakeChildAction] = []
        for idx in range(new_spec.count):
            element_path = FieldPath(
                segments=(
                    *target_path.segments,
                    FieldPath.Segment(identifier=str(idx), is_index=True),
                )
            )

            self._scope_stack.add_field(element_path)

            # Use templated MakeChild for array elements if applicable
            if new_spec.template_args and module_fabll_type is not None:
                element_child_field = self._create_module_child_field(
                    module_type=module_fabll_type,
                    identifier=element_path.identifiers()[0],
                    template_args=new_spec.template_args,
                )
            else:
                element_child_field = fabll._ChildField(
                    nodetype=not_none(new_spec.type_identifier),
                    identifier=element_path.identifiers()[0],
                )

            element_actions.append(
                AddMakeChildAction(
                    target_path=element_path,
                    child_field=element_child_field,
                    parent_reference=pointer_action.parent_reference,
                    parent_path=pointer_action.parent_path,
                    import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
                )
            )
        return [pointer_action, *element_actions]

    def visit_Assignment(self, node: AST.Assignment):
        # TODO: broaden assignable support and handle keyed/pin field references

        target_path = self.visit_FieldRef(node.get_target())

        # Check for assignment overrides (legacy sugar like .required, .package)
        assignable_node = node.assignable.get()
        override_actions = AssignmentOverrides.try_handle(target_path, assignable_node)
        if override_actions:
            return override_actions

        assignable = self.visit_Assignable(assignable_node)
        if assignable is None:
            return NoOpAction()

        parent_path: FieldPath | None = None
        parent_reference: graph.BoundNode | None = None

        if target_path.parent_segments:
            parent_path = FieldPath(segments=tuple(target_path.parent_segments))

            self._scope_stack.ensure_defined(parent_path)

            parent_reference = self._type_stack.resolve_reference(parent_path)

        match assignable:
            case NewChildSpec() as new_spec:
                return self._handle_new_child(
                    target_path, new_spec, parent_reference, parent_path
                )
            case ConstraintSpec() as constraint_spec:
                # FIXME: add constraint type (is, ss) to spec?
                # FIXME: should be IsSubset unless top of stack is a component

                unique_target_str = str(target_path).replace(".", "_")

                # operand as child of type
                operand_action = AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,
                            FieldPath.Segment(f"operand_{unique_target_str}"),
                        )
                    ),
                    parent_reference=parent_reference,
                    parent_path=parent_path,
                    child_field=constraint_spec.operand,
                )

                # expr linking target param to operand
                expr_action = AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,
                            FieldPath.Segment(f"constraint_{unique_target_str}"),
                        )
                    ),
                    parent_reference=parent_reference,
                    parent_path=parent_path,
                    child_field=F.Expressions.IsSubset.MakeChild(  # TODO: conditional
                        target_path.to_ref_path(),
                        [constraint_spec.operand],
                        assert_=True,
                    ),
                )
                return [operand_action, expr_action]
            case _:
                raise NotImplementedError(f"Unhandled assignable type: {assignable}")

    def visit_Assignable(
        self, node: AST.Assignable
    ) -> ConstraintSpec | NewChildSpec | None:
        match assignable := node.get_value().switch_cast():
            case AST.AstString() as string:
                return ConstraintSpec(operand=self.visit_AstString(string))
            case AST.Boolean() as boolean:
                return ConstraintSpec(operand=self.visit_Boolean(boolean))
            case AST.NewExpression() as new:
                return self.visit_NewExpression(new)
            case (
                AST.Quantity()
                | AST.BilateralQuantity()
                | AST.BoundedQuantity() as quantity
            ):
                return None  # TODO: handle quantities
                lit = self.visit(quantity)
                assert isinstance(lit, fabll._ChildField)
                return ConstraintSpec(operand=lit)
            case AST.BinaryExpression() | AST.GroupExpression() as arithmetic:
                expr = self.visit(arithmetic)
                assert isinstance(
                    expr, fabll._ChildField
                )  # F.Expressions.ExpressionNodes (some)
                return ConstraintSpec(operand=expr)
            case _:
                raise ValueError(f"Unhandled assignable type: {assignable}")

    # TODO: implement recursion until arrival at atomic
    def to_expression_tree(self, node: AST.is_arithmetic) -> fabll.RefPath:
        """Convert an arithmetic AST node to a RefPath for expression trees.

        Note: The returned paths do NOT include "can_be_operand" suffix.
        This is because MakeChild_Constrain methods append it themselves.
        """
        cbo_path: fabll.RefPath | None = None

        assignable = self.visit(fabll.Traits(node).get_obj_raw())

        # TODO: handle arithmetic expressions within assert
        match assignable:
            case fabll._ChildField() as child_field:
                return [child_field]
            case FieldPath() as field_path:
                cbo_path = list(field_path.identifiers())
                return cbo_path
            # case fabll.Node() if assignable.has_trait(AST.is_arithmetic_atom):
            #     return [assignable]

        raise DslException(
            f"Unknown arithmetic: {fabll.Traits(node).get_obj_raw().get_type_name()}"
        )

    def visit_AssertStmt(self, node: AST.AssertStmt):
        expr = None
        comparison_expression = node.get_comparison()
        comparison_clauses = comparison_expression.get_comparison_clauses()

        lhs_refpath = self.to_expression_tree(comparison_expression.get_lhs())
        rhs_refpath = self.to_expression_tree(list(comparison_clauses)[0].get_rhs())

        if len(list(comparison_clauses)) != 1:
            raise NotImplementedError(
                "Assert statement must have exactly one comparison clause (operator)"
            )
        # for clause in comparison_clauses:
        clause = list(comparison_clauses)[0]
        operator = clause.get_operator()

        if operator == ">":
            expr = F.Expressions.GreaterThan.MakeChild(
                lhs_refpath, rhs_refpath, assert_=True
            )
        elif operator == ">=":
            expr = F.Expressions.GreaterOrEqual.MakeChild(
                lhs_refpath, rhs_refpath, assert_=True
            )
        elif operator == "<":
            expr = F.Expressions.LessThan.MakeChild(
                lhs_refpath, rhs_refpath, assert_=True
            )
        elif operator == "<=":
            expr = F.Expressions.LessOrEqual.MakeChild(
                lhs_refpath, rhs_refpath, assert_=True
            )
        elif operator == "within":
            expr = F.Expressions.IsSubset.MakeChild(
                lhs_refpath, rhs_refpath, assert_=True
            )
        elif operator == "is":
            expr = F.Expressions.Is.MakeChild(lhs_refpath, rhs_refpath, assert_=True)
        else:
            raise DslException(f"Unknown comparison operator: {operator}")

        if expr is not None:
            # Add childfields from expression tree as dependant to expression
            for seg in lhs_refpath:
                if isinstance(seg, fabll._ChildField):
                    expr.add_dependant(seg, identifier="lhs", before=True)
            for seg in rhs_refpath:
                if isinstance(seg, fabll._ChildField):
                    expr.add_dependant(seg, identifier="rhs", before=True)
            return [
                AddMakeChildAction(
                    target_path=[*lhs_refpath, str(lhs_refpath).replace(".", "_")],
                    parent_reference=None,
                    parent_path=None,
                    child_field=expr,
                )
            ]
        # TODO: is a plain assert legal?
        return NoOpAction()

    def _get_unit_fabll_type(self, unit_symbol: str | None) -> type[fabll.Node]:
        if unit_symbol is None:
            # TODO: Dont allow to compile without unit symbol?
            # raise DslException("Unit symbol is required for quantity")
            return F.Units.Dimensionless
        else:
            return F.Units.decode_symbol(self._graph, self._type_graph, unit_symbol)

    def visit_Quantity(
        self, node: AST.Quantity
    ) -> "fabll._ChildField[F.Literals.Numbers]":
        # Make childfield and edge pointer to unit_ptr to unit node child field
        unit_type = self._get_unit_fabll_type(node.try_get_unit_symbol())

        return F.Literals.Numbers.MakeChild_SingleValue(node.get_value(), unit_type)

    def visit_BoundedQuantity(
        self, node: AST.BoundedQuantity
    ) -> "fabll._ChildField[F.Literals.Numbers]":
        start_unit_symbol = node.start.get().try_get_unit_symbol()
        end_unit_symbol = node.end.get().try_get_unit_symbol()
        # TODO: handle this more intelligentlly
        if start_unit_symbol is not None and end_unit_symbol is not None:
            assert start_unit_symbol == end_unit_symbol, (
                f"Unit mismatch: {start_unit_symbol} vs {end_unit_symbol}"
            )
        if start_unit_symbol is None or end_unit_symbol is None:
            raise DslException("Unit symbol is required for bounded quantity")

        unit_type = self._get_unit_fabll_type(start_unit_symbol)

        return F.Literals.Numbers.MakeChild(
            min=node.start.get().get_value(),
            max=node.end.get().get_value(),
            unit=unit_type,
        )

    def visit_BilateralQuantity(
        self, node: AST.BilateralQuantity
    ) -> "fabll._ChildField[F.Literals.Numbers]":
        quantity_unit_symbol = node.quantity.get().try_get_unit_symbol()
        tolerance_unit_symbol = node.tolerance.get().try_get_unit_symbol()
        # TODO: handle this more intelligentlly
        assert (
            tolerance_unit_symbol == "%"
            or quantity_unit_symbol == tolerance_unit_symbol
        )
        if quantity_unit_symbol is None or tolerance_unit_symbol is None:
            raise DslException("Unit symbol is required for bilateralquantity")
        unit_type = self._get_unit_fabll_type(quantity_unit_symbol)

        node_quantity_value = node.quantity.get().get_value()
        node_tolerance_value = node.tolerance.get().get_value()

        if tolerance_unit_symbol == "%":
            tolerance_value = node_tolerance_value / 100
            start_value = node_quantity_value * (1 - tolerance_value)
            end_value = node_quantity_value * (1 + tolerance_value)
        else:
            start_value = node_quantity_value - node_tolerance_value
            end_value = node_quantity_value + node_tolerance_value

        return F.Literals.Numbers.MakeChild(
            min=start_value,
            max=end_value,
            unit=unit_type,
        )

    def visit_NewExpression(self, node: AST.NewExpression):
        type_name = node.get_type_ref_name()
        symbol = self._scope_stack.try_resolve_symbol(type_name)

        # Extract template arguments if present (e.g., new Addressor<address_bits=2>)
        template_args = self._extract_template_args(node.template.get())
        if template_args is not None:
            self.ensure_experiment(ASTVisitor._Experiment.MODULE_TEMPLATING)

        return NewChildSpec(
            symbol=symbol,
            type_identifier=type_name,
            type_node=symbol.type_node if symbol else None,
            count=node.get_new_count(),
            template_args=template_args,
        )

    def _resolve_connectable_with_path(
        self, connectable_node: fabll.Node
    ) -> tuple[graph.BoundNode, FieldPath]:
        """Resolve a connectable node to a graph reference and path.

        Handles two cases:
        - FieldRef: reference to existing field (must exist)
        - Declarations (Signal, Pin): may create if not exists
        """
        if connectable_node.isinstance(AST.FieldRef):
            return self._resolve_field_ref(connectable_node.cast(t=AST.FieldRef))
        return self._resolve_declaration(connectable_node)

    def _resolve_field_ref(
        self, field_ref: AST.FieldRef
    ) -> tuple[graph.BoundNode, FieldPath]:
        """Resolve a reference to an existing field."""
        path = self.visit_FieldRef(field_ref)
        (root, *_) = path.segments
        root_path = FieldPath(segments=(root,))

        self._scope_stack.ensure_defined(root_path)

        ref = self._type_stack.resolve_reference(path, validate=False)
        return ref, path

    def _resolve_declaration(
        self, node: fabll.Node
    ) -> tuple[graph.BoundNode, FieldPath]:
        """Resolve a declaration node, creating it if it doesn't exist."""
        target_path, visit_fn = self._get_declaration_info(node)

        if not self._scope_stack.has_field(target_path):
            action = visit_fn()
            self._type_stack.apply_action(action)

        ref = self._type_stack.resolve_reference(target_path, validate=False)
        return ref, target_path

    def _get_declaration_info(
        self, node: fabll.Node
    ) -> tuple[FieldPath, Callable[[], Any]]:
        """Extract path and visit function for a declaration node.

        Returns:
            (target_path, visit_fn) where visit_fn creates the declaration action
        """
        if node.isinstance(AST.SignaldefStmt):
            signal_node = node.cast(t=AST.SignaldefStmt)
            (signal_name,) = signal_node.name.get().get_values()
            target_path = FieldPath(
                segments=(FieldPath.Segment(identifier=signal_name),)
            )
            return target_path, lambda: self.visit_SignaldefStmt(signal_node)

        elif node.isinstance(AST.PinDeclaration):
            pin_node = node.cast(t=AST.PinDeclaration)
            pin_label = pin_node.get_label()
            if pin_label is None:
                raise DslException("Pin declaration has no label")

            if isinstance(pin_label, float) and pin_label.is_integer():
                pin_label_str = str(int(pin_label))
            else:
                pin_label_str = str(pin_label)
            identifier = f"{PIN_ID_PREFIX}{pin_label_str}"
            target_path = FieldPath(
                segments=(FieldPath.Segment(identifier=identifier),)
            )
            return target_path, lambda: self.visit_PinDeclaration(pin_node)

        raise CompilerException(f"Unhandled declaration type: {node.get_type_name()}")

    def visit_ConnectStmt(self, node: AST.ConnectStmt):
        lhs, rhs = node.get_lhs(), node.get_rhs()
        lhs_node = fabll.Traits(lhs).get_obj_raw()
        rhs_node = fabll.Traits(rhs).get_obj_raw()

        _, lhs_path = self._resolve_connectable_with_path(lhs_node)
        _, rhs_path = self._resolve_connectable_with_path(rhs_node)

        # Convert FieldPath to LinkPath (list of string identifiers)
        # Apply legacy path translations (e.g., vcc -> hv, gnd -> lv)
        lhs_link_path: LinkPath = ConnectOverrides.translate_identifiers(
            list(lhs_path.identifiers())
        )
        rhs_link_path: LinkPath = ConnectOverrides.translate_identifiers(
            list(rhs_path.identifiers())
        )

        return AddMakeLinkAction(lhs_path=lhs_link_path, rhs_path=rhs_link_path)

    def visit_DeclarationStmt(self, node: AST.DeclarationStmt):
        unit_symbol = node.unit_symbol.get().symbol.get().get_single()
        unit_child_field = self._get_unit_fabll_type(unit_symbol)
        target_path = self.visit_FieldRef(node.get_field_ref())
        return AddMakeChildAction(
            target_path=target_path,
            parent_reference=None,
            parent_path=None,
            child_field=F.Parameters.NumericParameter.MakeChild(unit=unit_child_field),
        )

    def visit_DirectedConnectStmt(self, node: AST.DirectedConnectStmt):
        """
        `a ~> b` connects a.can_bridge.out_ to b.can_bridge.in_
        `a <~ b` connects a.can_bridge.in_ to b.can_bridge.out_
        """
        lhs = node.get_lhs()
        rhs = node.get_rhs()

        lhs_node = fabll.Traits(lhs).get_obj_raw()
        _, lhs_base_path = self._resolve_connectable_with_path(lhs_node)

        if nested_rhs := rhs.try_cast(t=AST.DirectedConnectStmt):
            nested_lhs = nested_rhs.get_lhs()
            nested_lhs_node = fabll.Traits(nested_lhs).get_obj_raw()
            _, middle_base_path = self._resolve_connectable_with_path(nested_lhs_node)

            action = self._add_directed_link(
                lhs_base_path, middle_base_path, node.get_direction()
            )
            self._type_stack.apply_action(action)

            return self.visit_DirectedConnectStmt(nested_rhs)

        rhs_node = fabll.Traits(rhs).get_obj_raw()
        _, rhs_base_path = self._resolve_connectable_with_path(rhs_node)

        return self._add_directed_link(
            lhs_base_path, rhs_base_path, node.get_direction()
        )

    def _add_directed_link(
        self,
        lhs_path: FieldPath,
        rhs_path: FieldPath,
        direction: AST.DirectedConnectStmt.Direction,
    ) -> AddMakeLinkAction:
        if direction == AST.DirectedConnectStmt.Direction.RIGHT:  # ~>
            lhs_pointer = F.can_bridge.out_.get_identifier()
            rhs_pointer = F.can_bridge.in_.get_identifier()
        else:  # <~
            lhs_pointer = F.can_bridge.in_.get_identifier()
            rhs_pointer = F.can_bridge.out_.get_identifier()

        lhs_link_path = self._build_bridge_path(lhs_path, lhs_pointer)
        rhs_link_path = self._build_bridge_path(rhs_path, rhs_pointer)

        return AddMakeLinkAction(lhs_path=lhs_link_path, rhs_path=rhs_link_path)

    def _build_bridge_path(self, base_path: FieldPath, pointer: str) -> LinkPath:
        """
        Build a LinkPath that traverses through the can_bridge trait.

        For a base_path like "a", this builds:
        ["a", EdgeTrait(can_bridge), EdgeComposition("out_"), EdgePointer()]
        """
        base_identifiers = list(base_path.identifiers())
        # Apply legacy path translations (e.g., vcc -> hv, gnd -> lv)
        base_identifiers = ConnectOverrides.translate_identifiers(base_identifiers)
        path: LinkPath = [
            *base_identifiers,
            EdgeTrait.traverse(trait_type=can_bridge),
            EdgeComposition.traverse(identifier=pointer),
            EdgePointer.traverse(),
        ]
        return path

    @staticmethod
    def _select_elements(
        iterable_field: AST.IterableFieldRef, sequence_elements: list[FieldPath]
    ) -> list[FieldPath]:
        start_idx, stop_idx, step_idx = iterable_field.slice.get().get_values()

        if step_idx == 0:
            raise DslException("Slice step cannot be zero")

        return (
            sequence_elements
            if (start_idx is None and stop_idx is None and step_idx is None)
            else sequence_elements[slice(start_idx, stop_idx, step_idx)]
        )

    def _pointer_member_paths(self, container_path: FieldPath) -> list[FieldPath]:
        type_node, _ = self._type_stack.current()
        try:
            pointer_members = self._type_graph.collect_pointer_members(
                type_node=type_node,
                container_path=list(container_path.identifiers()),
            )
        except fbrk.TypeGraphPathError as exc:
            raise DslException(
                self._type_stack._format_path_error(container_path, exc)
            ) from exc

        return [
            FieldPath(
                segments=(
                    *container_path.segments,
                    FieldPath.Segment(
                        identifier=identifier,
                        is_index=identifier.isdigit(),
                    ),
                )
            )
            for identifier in [
                identifier
                for identifier, _ in pointer_members
                if identifier is not None
            ]
        ]

    def visit_ForStmt(self, node: AST.ForStmt):
        def validate_stmt(stmt: fabll.Node) -> None:
            def error(node: fabll.Node) -> str:
                # TODO: make this less fragile
                source_text = stmt.source.get().get_text()  # type: ignore
                stmt_str = source_text.split(" ")[0]
                raise DslException(f"Invalid statement in for loop: {stmt_str}")

            for illegal_type in (
                AST.ImportStmt,
                AST.PinDeclaration,
                AST.SignaldefStmt,
                AST.TraitStmt,
            ):
                if stmt.isinstance(illegal_type):
                    assert isinstance(stmt, illegal_type)
                    error(stmt)

            if stmt.isinstance(AST.Assignment):
                assignment = stmt.cast(t=AST.Assignment)
                assignable_value = assignment.assignable.get().get_value().switch_cast()
                if assignable_value.isinstance(AST.NewExpression):
                    error(stmt)

        self.ensure_experiment(ASTVisitor._Experiment.FOR_LOOP)

        iterable_node = node.iterable.get().deref()
        item_paths: list[FieldPath]

        if iterable_node.isinstance(AST.FieldRefList):
            list_node = iterable_node.cast(t=AST.FieldRefList)
            items = list_node.items.get().as_list()
            item_paths = [
                self.visit_FieldRef(item_ref.cast(t=AST.FieldRef)) for item_ref in items
            ]

        elif iterable_node.isinstance(AST.IterableFieldRef):
            iterable_field = iterable_node.cast(t=AST.IterableFieldRef)
            container_path = self.visit_FieldRef(iterable_field.get_field())
            member_paths = self._pointer_member_paths(container_path)

            selected = self._select_elements(iterable_field, member_paths)
            item_paths = list(selected)
        else:
            raise DslException("Unexpected iterable type")

        (loop_var,) = node.target.get().get_values()
        stmts = node.scope.get().stmts.get().as_list()

        for stmt in stmts:
            validate_stmt(stmt)

        for item_path in item_paths:
            with self._scope_stack.temporary_alias(loop_var, item_path):
                for stmt in stmts:
                    self._type_stack.apply_action(self.visit(stmt))

        return NoOpAction()

    def _extract_template_args(
        self, template_node: AST.Template
    ) -> dict[str, str | bool | float] | None:
        args_list = template_node.args.get().as_list()
        if not args_list:
            return None

        template_args: dict[str, str | bool | float] = {}
        for arg_node in args_list:
            arg = arg_node.cast(t=AST.TemplateArg)
            (name,) = arg.name.get().get_values()
            value = arg.get_value()
            if value is not None:
                template_args[name] = value

        return template_args if template_args else None

    def _create_trait_field(
        self,
        trait_type: type[fabll.Node],
        template_args: dict[str, str | bool | float] | None,
    ) -> fabll._ChildField:
        """Create a trait field, using MakeChild with template args if available."""
        if template_args and hasattr(trait_type, "MakeChild"):
            try:
                return trait_type.MakeChild(**template_args)
            except TypeError as e:
                logger.warning(
                    f"MakeChild for {trait_type.__name__} failed with template "
                    f"args: {e}. Falling back to generic _ChildField."
                )

        # Fallback: create generic _ChildField and constrain string params
        trait_field = fabll._ChildField(trait_type)
        if template_args:
            for param_name, value in template_args.items():
                if isinstance(value, str):
                    attr = getattr(trait_type, param_name, None)
                    if attr is not None:
                        constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(
                            [trait_field, attr], value
                        )
                        trait_field.add_dependant(constraint)
                else:
                    logger.warning(
                        f"Template arg {param_name}={value} - non-string unsupported"
                    )
        return trait_field

    def _create_module_child_field(
        self,
        module_type: type[fabll.Node],
        identifier: str,
        template_args: dict[str, str | bool | float] | None,
    ) -> fabll._ChildField:
        if template_args and hasattr(module_type, "MakeChild"):
            converted_args: dict[str, str | bool | int | float] = {}
            for key, value in template_args.items():
                if isinstance(value, float) and value.is_integer():
                    converted_args[key] = int(value)
                else:
                    converted_args[key] = value

            try:
                child_field = module_type.MakeChild(**converted_args)
                child_field._set_locator(identifier)
                return child_field
            except TypeError as e:
                logger.warning(
                    f"MakeChild for {module_type.__name__} failed with template "
                    f"args {converted_args}: {e}. Falling back to generic _ChildField."
                )

        # Fallback: create generic _ChildField (no template support)
        return fabll._ChildField(
            nodetype=module_type,
            identifier=identifier,
        )

    def visit_TraitStmt(
        self, node: AST.TraitStmt
    ) -> list[AddMakeChildAction | AddMakeLinkAction]:
        """
        Visit a trait statement and return a list of actions to create the trait.

        Returns:
            A list containing:
            1. AddMakeChildAction to create the trait as a child
            2. AddMakeLinkAction to link the target to the trait with EdgeTrait
        """
        self.ensure_experiment(ASTVisitor._Experiment.TRAITS)

        (trait_type_name,) = node.type_ref.get().name.get().get_values()

        if not self._scope_stack.is_symbol_defined(trait_type_name):
            raise DslException(f"Trait `{trait_type_name}` must be imported before use")

        target_path_list: LinkPath = []
        if (target_field_ref := node.get_target()) is not None:
            target_path = self.visit_FieldRef(target_field_ref)
            self._scope_stack.ensure_defined(target_path)
            target_path_list = list(target_path.identifiers())

        template_args = self._extract_template_args(node.template.get())

        # Check if this trait needs special handling (legacy aliases/shims)
        override_result = TraitOverrides.try_handle(
            trait_type_name, target_path_list, template_args
        )
        if override_result is not None:
            return override_result

        trait_fabll_type = self._stdlib_allowlist.get(trait_type_name)
        if trait_fabll_type is None:
            raise DslException(f"External trait `{trait_type_name}` not supported")

        trait_field = self._create_trait_field(trait_fabll_type, template_args)
        return _create_trait_actions(trait_type_name, trait_field, target_path_list)
