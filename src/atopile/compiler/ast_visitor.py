import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, replace
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
    AddTraitAction,
    ConstraintSpec,
    FieldPath,
    ImportRef,
    NewChildSpec,
    NoOpAction,
    ScopeState,
    Symbol,
)
from atopile.errors import UserSyntaxError
from faebryk.core.faebrykpy import (
    EdgeComposition,
    EdgePointer,
    EdgeTrait,
    EdgeTraversal,
)
from faebryk.library.can_bridge import can_bridge
from faebryk.library.Lead import can_attach_to_pad_by_name, is_lead
from faebryk.libs.util import cast_assert, not_none

_Quantity = tuple[float, str]

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
        # FIXME: separate list for internal types
        F.Expressions.Is,
        F.Expressions.IsSubset,
        F.Literals.Numbers,
        F.Literals.NumericSet,
        F.Literals.NumericInterval,
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
    }
)


@dataclass
class BuildState:
    type_roots: dict[str, graph.BoundNode]
    external_type_refs: list[tuple[graph.BoundNode, ImportRef]]
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

    def add_field(self, path: FieldPath) -> None:
        current_state = self.current
        if (key := str(path)) in current_state.fields:
            raise DslException(f"Field `{key}` already defined in scope")

        current_state.fields.add(key)

        logger.info(f"Added field {key} to scope")

    def has_field(self, path: FieldPath) -> bool:
        return any(str(path) in state.fields for state in reversed(self.stack))

    def ensure_not_defined(self, path: FieldPath, label: str | None = None) -> None:
        """Raise if field is already defined in scope."""
        if self.has_field(path):
            name = label or str(path)
            raise DslException(f"`{name}` is already defined in this scope")

    def ensure_defined(self, path: FieldPath) -> None:
        """Raise if field is not defined in scope."""
        if not self.has_field(path):
            raise DslException(f"Field `{path}` is not defined in scope")

    def resolve_symbol(self, name: str) -> Symbol:
        for state in reversed(self.stack):
            if name in state.symbols:
                return state.symbols[name]

        raise DslException(f"Symbol `{name}` is not available in this scope")

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

    # FIXME: move to trait visitor
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

        is_unresolved_import = (
            action.import_ref is not None
            and action.child_field is not None
            and isinstance(action.child_field.nodetype, str)
        )

        if is_unresolved_import:
            assert isinstance(action.child_field.identifier, str)
            type_ref = self._tg.get_make_child_type_reference_by_identifier(
                type_node=type_node, identifier=action.child_field.identifier
            )
            self._state.external_type_refs.append(
                (not_none(type_ref), not_none(action.import_ref))
            )

    # TODO FIXME: no type checking for is_interface trait on connected nodes.
    # We should use the fabll connect_to method for this.
    def _add_link(
        self,
        type_node: graph.BoundNode,
        bound_tg: fabll.TypeNodeBoundTG,
        action: AddMakeLinkAction,
    ) -> None:
        self._tg.add_make_link(
            type_node=type_node,
            lhs_reference=action.lhs_ref,
            rhs_reference=action.rhs_ref,
            edge_attributes=action.edge
            or fbrk.EdgeInterfaceConnection.build(shallow=False),
        )

    def _add_trait(self, type_node: graph.BoundNode, action: AddTraitAction) -> None:
        # FIXME: switch to iterable of MakeChid / MakeLink actions
        target_reference = action.target_reference or type_node
        trait_identifier = f"_trait_{action.trait_type_identifier}"

        if action.trait_fabll_type is not None:
            trait_type = action.trait_fabll_type

            # Try calling trait's MakeChild with template args if available
            trait_field = self._create_trait_field(trait_type, action.template_args)

            trait_field_with_edge = fabll.Traits.MakeEdge(trait_field)
            _, bound_tg = self.current()
            fabll.Node._exec_field(t=bound_tg, field=trait_field_with_edge)
        else:
            make_child = self._tg.add_make_child_deferred(
                type_node=type_node,
                child_type_identifier=action.trait_type_identifier,
                identifier=trait_identifier,
                node_attributes=None,
                mount_reference=target_reference,
            )

            type_reference = not_none(
                self._tg.get_make_child_type_reference(make_child=make_child)
            )

            if action.trait_import_ref is not None:
                self._state.external_type_refs.append(
                    (type_reference, action.trait_import_ref)
                )
            elif action.trait_type_node is not None:
                fbrk.Linker.link_type_reference(
                    g=self._g,
                    type_reference=type_reference,
                    target_type_node=action.trait_type_node,
                )
            else:
                raise DslException(
                    f"Trait `{action.trait_type_identifier}` has no type node"
                )

            self._tg.add_make_link(
                type_node=type_node,
                lhs_reference=target_reference,
                rhs_reference=make_child,
                edge_attributes=fbrk.EdgeTrait.build(),
            )


class AnyAtoBlock(fabll.Node):
    _definition_identifier: ClassVar[str] = "definition"
    is_ato_block = fabll.Traits.MakeEdge(is_ato_block.MakeChild())


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

        self._scope_stack.add_symbol(Symbol(name=type_ref_name, import_ref=import_ref))

    def visit_BlockDefinition(self, node: AST.BlockDefinition):
        if self._scope_stack.depth != 1:
            raise DslException("Nested block definitions are not permitted")

        module_name = node.get_type_ref_name()

        if self._scope_stack.is_symbol_defined(module_name):
            raise DslException(f"Symbol `{module_name}` already defined in scope")

        # Get source directory for is_ato_block trait
        source_dir = str(self._state.file_path.parent) if self._state.file_path else ""

        # Create is_ato_block with source_dir constrained
        def _make_ato_block_field() -> fabll._ChildField:
            field = is_ato_block.MakeChild()
            field.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [field, is_ato_block.source_dir], source_dir
                )
            )
            return field

        match node.get_block_type():
            case AST.BlockDefinition.BlockType.MODULE:

                class _Module(fabll.Node):
                    _is_ato_block = fabll.Traits.MakeEdge(_make_ato_block_field())
                    is_ato_module = fabll.Traits.MakeEdge(is_ato_module.MakeChild())
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Module

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    _is_ato_block = fabll.Traits.MakeEdge(_make_ato_block_field())
                    is_ato_component = fabll.Traits.MakeEdge(
                        is_ato_component.MakeChild()
                    )

                _Block = _Component

            case AST.BlockDefinition.BlockType.INTERFACE:

                class _Interface(fabll.Node):
                    is_ato_block = fabll.Traits.MakeEdge(is_ato_block.MakeChild())
                    is_ato_interface = fabll.Traits.MakeEdge(
                        is_ato_interface.MakeChild()
                    )

                _Block = _Interface

        type_identifier = self._make_type_identifier(module_name)
        _Block.__name__ = type_identifier
        _Block.__qualname__ = type_identifier

        type_node = self._type_graph.add_type(
            identifier=self._make_type_identifier(module_name)
        )
        type_node_bound_tg = fabll.TypeNodeBoundTG(tg=self._type_graph, t=_Block)

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
    ) -> fabll._ChildField[F.Literals.Booleans]:
        return F.Literals.Booleans.MakeChild(node.get_value())

    def visit_Quantity(
        self, node: AST.Quantity
    ) -> fabll._ChildField[F.Literals.Numbers]:
        if (unit := node.get_unit()) is not None:
            unit_type, multiplier = F.Units.get_unit_type_from_symbol(unit)
            return F.Literals.Numbers.MakeChild_SingleValue(
                node.get_value() * multiplier, unit_type
            )

        return F.Literals.Numbers.MakeChild_SingleValue(
            node.get_value(), F.Units.Dimensionless
        )

    def visit_AstString(
        self, node: AST.AstString
    ) -> fabll._ChildField[F.Literals.Strings]:
        return F.Literals.Strings.MakeChild(node.get_text())

    def visit_StringStmt(self, node: AST.StringStmt):
        # TODO: add docstring trait to preceding node
        return NoOpAction()

    def visit_SignaldefStmt(self, node: AST.SignaldefStmt):
        (signal_name,) = node.name.get().get_values()
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=signal_name),))

        self._scope_stack.ensure_not_defined(target_path, f"Signal `{signal_name}`")
        self._scope_stack.add_field(target_path)

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
        identifier = f"pin_{pin_label_str}"
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=identifier),))

        self._scope_stack.ensure_not_defined(target_path, f"Pin `{pin_label_str}`")
        self._scope_stack.add_field(target_path)

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
            return AddMakeChildAction(
                target_path=target_path,  # FIXME: this seems wrong
                parent_reference=parent_reference,
                parent_path=parent_path,
                child_field=fabll._ChildField(
                    nodetype=new_spec.type_identifier,
                    identifier=target_path.leaf.identifier,
                ),
                import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
            )

        raise NotImplementedError()

        pointer_action = AddMakeChildAction(
            target_path=target_path,
            child_spec=NewChildSpec(
                type_identifier=F.Collections.PointerSequence.__name__,
                type_node=self._pointer_sequence_type,
            ),
            parent_reference=parent_reference,
            parent_path=parent_path,
        )

        element_spec = replace(new_spec, count=None)

        element_actions: list[AddMakeChildAction] = []

        for idx in range(new_spec.count):
            element_path = FieldPath(
                segments=(
                    *target_path.segments,
                    FieldPath.Segment(identifier=str(idx), is_index=True),
                )
            )

            self._scope_stack.add_field(element_path)
            element_actions.append(
                AddMakeChildAction(
                    target_path=element_path,
                    child_spec=element_spec,
                    parent_reference=None,
                    parent_path=FieldPath(segments=target_path.segments),
                )
            )

        return [pointer_action, *element_actions]

    def visit_Assignment(self, node: AST.Assignment):
        # TODO: broaden assignable support and handle keyed/pin field references

        target_path = self.visit_FieldRef(node.get_target())
        assignable_t = node.assignable.get().get_value()
        assignable = self.visit(fabll.Traits(assignable_t).get_obj_raw())
        logger.info(f"Assignable: {assignable}")

        parent_path: FieldPath | None = None
        parent_reference: graph.BoundNode | None = None

        if target_path.parent_segments:
            parent_path = FieldPath(segments=tuple(target_path.parent_segments))

            self._scope_stack.ensure_defined(parent_path)

            parent_reference = self._type_stack.resolve_reference(parent_path)

        match assignable:
            case NewChildSpec() as new_spec:
                self._scope_stack.ensure_not_defined(target_path)
                return self._handle_new_child(
                    target_path, new_spec, parent_reference, parent_path
                )
            case ConstraintSpec() as constraint_spec:
                # FIXME: add constraint type (is, ss) to spec?
                # FIXME: should be IsSubset unless top of stack is a component

                # operand as child of type
                operand_action = AddMakeChildAction(
                    target_path=target_path,  # TODO: is this actually the path of the param?
                    parent_reference=parent_reference,
                    parent_path=parent_path,
                    child_field=constraint_spec.operand,
                )

                # expr linking target param to operand
                expr_action = AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,  # FIXME: append _constraint suffix to target path tail segment?
                            FieldPath.Segment("constraint"),  # FIXME: must be unique
                        )
                    ),
                    parent_reference=parent_reference,
                    parent_path=parent_path,
                    child_field=F.Expressions.Is.MakeChild_Constrain(
                        [target_path.to_ref_path(), [constraint_spec.operand]]
                    ),
                )

                return [operand_action, expr_action]
            case _:
                raise NotImplementedError(f"Unhandled assignable type: {assignable}")

    def visit_Assignable(self, node: AST.Assignable) -> ConstraintSpec | NewChildSpec:
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
                lit = self.visit(quantity)
                assert isinstance(lit, fabll._ChildField)  # F.Literals.Numbers
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
        cbo_path: fabll.RefPath | None = None

        assignable = self.visit(fabll.Traits(node).get_obj_raw())

        match assignable:
            case FieldPath() as field_path:
                cbo_path = [*field_path.identifiers(), "can_be_operand"]
                return cbo_path
            case str() as value:
                child_field = F.Literals.Strings.MakeChild(value)
                return [child_field, "can_be_operand"]
            case (float() as value, str() as unit):
                unit_type, multiplier = F.Units.get_unit_type_from_symbol(unit)
                child_field = F.Literals.Numbers.MakeChild(
                    min=value * multiplier, max=value * multiplier, unit=unit_type
                )
                return [child_field, "can_be_operand"]
            case (
                (float() as start_value, str() as start_unit),
                (float() as end_value, str() as end_unit),
            ):
                assert start_unit == end_unit
                unit_type, multiplier = F.Units.get_unit_type_from_symbol(start_unit)
                child_field = F.Literals.Numbers.MakeChild(
                    min=start_value * multiplier,
                    max=end_value * multiplier,
                    unit=unit_type,
                )
                return [child_field, "can_be_operand"]

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
            raise UserSyntaxError(
                "Assert statement must have exactly one comparison clause (operator)"
            )
        # for clause in comparison_clauses:
        clause = list(comparison_clauses)[0]
        operator = clause.get_operator()

        if operator == ">":
            expr = F.Expressions.GreaterThan.MakeChild_Constrain(
                lhs_refpath, rhs_refpath
            )
        elif operator == ">=":
            expr = F.Expressions.GreaterOrEqual.MakeChild_Constrain(
                lhs_refpath, rhs_refpath
            )
        elif operator == "<":
            expr = F.Expressions.LessThan.MakeChild_Constrain(lhs_refpath, rhs_refpath)
        elif operator == "<=":
            expr = F.Expressions.LessOrEqual.MakeChild_Constrain(
                lhs_refpath, rhs_refpath
            )
        elif operator == "within":
            expr = F.Expressions.IsSubset.MakeChild_Constrain(lhs_refpath, rhs_refpath)
        elif operator == "is":
            expr = F.Expressions.Is.MakeChild_Constrain([lhs_refpath, rhs_refpath])
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
                    target_path=lhs_refpath,
                    parent_reference=None,
                    parent_path=None,
                    child_field=expr,
                )
            ]
        # TODO: is a plain assert legal?
        return NoOpAction()

    def visit_BoundedQuantity(
        self, node: AST.BoundedQuantity
    ) -> tuple[_Quantity, _Quantity]:
        return (
            (
                node.start.get().get_value(),
                node.start.get().get_unit() or F.Units.DIMENSIONLESS_SYMBOL,
            ),
            (
                node.end.get().get_value(),
                node.end.get().get_unit() or F.Units.DIMENSIONLESS_SYMBOL,
            ),
        )

    def visit_BilateralQuantity(
        self, node: AST.BilateralQuantity
    ) -> tuple[_Quantity, _Quantity]:
        assert node.tolerance.get().get_unit() == "%" or (
            node.quantity.get().get_unit() != node.tolerance.get().get_unit()
        )
        node_quantity_value = node.quantity.get().get_value()
        node_tolerance_value = node.tolerance.get().get_value()
        node_quantity_unit = node.quantity.get().get_unit()

        if (node.tolerance.get().get_unit()) == "%":
            tolerance_value = node_tolerance_value / 100
            start_value = node_quantity_value * (1 - tolerance_value)
            end_value = node_quantity_value * (1 + tolerance_value)
        else:
            start_value = node_quantity_value - node_tolerance_value
            end_value = node_quantity_value + node_tolerance_value

        return (
            (start_value, node_quantity_unit or F.Units.DIMENSIONLESS_SYMBOL),
            (end_value, node_quantity_unit or F.Units.DIMENSIONLESS_SYMBOL),
        )

    def visit_NewExpression(self, node: AST.NewExpression):
        type_name = node.get_type_ref_name()
        symbol = self._scope_stack.resolve_symbol(type_name)

        return NewChildSpec(
            symbol=symbol,
            type_identifier=symbol.name,
            type_node=symbol.type_node,
            count=node.get_new_count(),
        )

        # TODO: handle template args

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
            identifier = f"pin_{pin_label_str}"
            target_path = FieldPath(
                segments=(FieldPath.Segment(identifier=identifier),)
            )
            return target_path, lambda: self.visit_PinDeclaration(pin_node)

        raise NotImplementedError(f"Unhandled declaration type: {node.get_type_name()}")

    def visit_ConnectStmt(self, node: AST.ConnectStmt):
        lhs, rhs = node.get_lhs(), node.get_rhs()
        lhs_node = fabll.Traits(lhs).get_obj_raw()
        rhs_node = fabll.Traits(rhs).get_obj_raw()

        lhs_ref, _ = self._resolve_connectable_with_path(lhs_node)
        rhs_ref, _ = self._resolve_connectable_with_path(rhs_node)

        return AddMakeLinkAction(lhs_ref=lhs_ref, rhs_ref=rhs_ref)

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
            lhs_pointer = "out_"
            rhs_pointer = "in_"
        else:  # <~
            lhs_pointer = "in_"
            rhs_pointer = "out_"

        lhs_ref = self._resolve_bridge_path(lhs_path, lhs_pointer)
        rhs_ref = self._resolve_bridge_path(rhs_path, rhs_pointer)

        return AddMakeLinkAction(lhs_ref=lhs_ref, rhs_ref=rhs_ref)

    def _resolve_bridge_path(
        self, base_path: FieldPath, pointer: str
    ) -> graph.BoundNode:
        base_identifiers = list(base_path.identifiers())
        path: list[str | EdgeTraversal] = [
            *base_identifiers,
            EdgeTrait.traverse(trait_type=can_bridge),
            EdgeComposition.traverse(identifier=pointer),
            EdgePointer.traverse(),
        ]

        type_node, _ = self._type_stack.current()

        try:
            return self._type_graph.ensure_child_reference(
                type_node=type_node, path=path, validate=False
            )
        except fbrk.TypeGraphPathError as exc:
            raise DslException(
                f"Cannot resolve bridge path for {base_path}: {exc}"
            ) from exc

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
        for item_path in item_paths:
            with self._scope_stack.temporary_alias(loop_var, item_path):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))

        return NoOpAction()

    def visit_TraitStmt(self, node: AST.TraitStmt):
        self.ensure_experiment(ASTVisitor._Experiment.TRAITS)

        (trait_type_name,) = node.type_ref.get().name.get().get_values()
        symbol = self._scope_stack.resolve_symbol(trait_type_name)

        target_reference: graph.BoundNode | None = None
        if (target_field_ref := node.get_target()) is not None:
            target_path = self.visit_FieldRef(target_field_ref)
            self._scope_stack.ensure_defined(target_path)
            target_reference = self._type_stack.resolve_reference(
                target_path, validate=False
            )

        template_args: dict[str, str | bool | float] | None = None
        if node.template.get().args.get().as_list():
            template_args = {}
            for arg_node in node.template.get().args.get().as_list():
                arg = arg_node.cast(t=AST.TemplateArg)
                (name,) = arg.name.get().get_values()
                value = arg.get_value()
                if value is not None:
                    template_args[name] = value

        trait_fabll_type = self._stdlib_allowlist.get(trait_type_name)

        return AddTraitAction(
            trait_type_identifier=trait_type_name,
            trait_type_node=symbol.type_node,
            trait_import_ref=symbol.import_ref,
            target_reference=target_reference,
            template_args=template_args,
            trait_fabll_type=trait_fabll_type,
        )
