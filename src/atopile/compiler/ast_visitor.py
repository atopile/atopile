import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, ClassVar

import atopile.compiler.ast_types as AST
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler import CompilerException, DslException
from atopile.compiler.gentypegraph import (
    ActionGenerationError,
    ActionsFactory,
    AddMakeChildAction,
    AddMakeLinkAction,
    DeferredForLoop,
    FieldPath,
    ImportRef,
    LinkPath,
    NewChildSpec,
    NoOpAction,
    ParameterSpec,
    PendingInheritance,
    PendingRetype,
    ScopeState,
    Symbol,
)
from atopile.compiler.overrides import TraitOverrideRegistry
from faebryk.core.faebrykpy import EdgeTraversal
from faebryk.library.Units import UnitsNotCommensurableError
from faebryk.libs.util import cast_assert, groupby, import_from_path, not_none

_Quantity = tuple[float, fabll._ChildField]

logger = logging.getLogger(__name__)


# FIXME: needs expanding
# Allowlist for user-importable types — everything here should be documented and
# supported
AllowListT = set[type[fabll.Node]]
STDLIB_ALLOWLIST: AllowListT = (
    # Modules
    {
        F.Addressor,
        F.BJT,
        F.CAN_TTL,
        F.Capacitor,
        F.Crystal_Oscillator,
        F.Crystal,
        F.DifferentialPair,
        F.Diode,
        F.Electrical,
        F.ElectricLogic,
        F.ElectricPower,
        F.ElectricSignal,
        F.Ethernet,
        F.FilterElectricalRC,
        F.Fuse,
        F.HDMI,
        F.I2C,
        F.I2S,
        F.Inductor,
        F.JTAG,
        F.LED,
        F.MOSFET,
        F.MultiSPI,
        F.Net,
        F.PDM,
        F.Resistor,
        F.ResistorVoltageDivider,
        F.Regulator,
        F.AdjustableRegulator,
        F.RS232,
        F.SPI,
        F.SPIFlash,
        F.SWD,
        F.UART_Base,
        F.UART,
        F.USB2_0_IF,
        F.USB2_0,
        F.USB3,
        F.XtalIF,
    }
) | (
    # Traits
    {
        F.can_bridge_by_name,
        F.can_bridge,
        F.has_datasheet,
        F.has_designator_prefix,
        F.has_doc_string,
        F.has_net_name_affix,
        F.has_net_name_suggestion,
        F.has_package_requirements,
        F.Pickable.has_part_picked,
        F.has_part_removed,
        F.has_single_electric_reference,
        F.is_atomic_part,
        F.is_auto_generated,
        F.Pickable.is_pickable,
        F.requires_external_usage,
    }
)


# TODO: restore prefix, fix matching so packages still build
PIN_ID_PREFIX = ""


@dataclass
class BuildState:
    type_roots: dict[str, graph.BoundNode]
    external_type_refs: list[tuple[graph.BoundNode, ImportRef | None]]
    file_path: Path | None
    import_path: str | None
    pending_execution: list[DeferredForLoop] = field(default_factory=list)
    pending_inheritance: list[PendingInheritance] = field(default_factory=list)
    pending_retypes: list[PendingRetype] = field(default_factory=list)
    type_bound_tgs: dict[str, fabll.TypeNodeBoundTG] = field(default_factory=dict)
    constraining_expr_types: dict[str, type[fabll.Node]] = field(default_factory=dict)
    type_aliases: dict[str, dict[str, FieldPath]] = field(default_factory=dict)
    inheritance_imports: list[ImportRef] = field(default_factory=list)


class is_ato_block(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    source_dir = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, source_dir: str | None = None) -> fabll._ChildField:
        field = fabll._ChildField(cls)
        if source_dir is not None:
            field.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral(
                    [field, cls.source_dir], source_dir
                )
            )
        return field

    def get_source_dir(self) -> str:
        """Get the source directory path where the .ato file is located."""
        return self.source_dir.get().force_extract_literal().get_single()


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
    as_interface = fabll.Traits.ImpliedTrait(fabll.is_interface)


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

    def try_resolve_symbol(self, name: str) -> Symbol | None:
        for state in reversed(self.stack):
            if name in state.symbols:
                return state.symbols[name]

    def resolve_alias(self, name: str) -> FieldPath | None:
        return self.current.aliases.get(name)

    @property
    def depth(self) -> int:
        return len(self.stack)

    def symbol_exists(self, name: str) -> bool:
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
        self._stack: list[
            tuple[graph.BoundNode, fabll.TypeNodeBoundTG, str, type[fabll.Node]]
        ] = []
        self._g = g
        self._tg = tg
        self._state = state

    @contextmanager
    def enter(
        self,
        type_node: graph.BoundNode,
        bound_tg: fabll.TypeNodeBoundTG,
        type_identifier: str,
        constraint_expr: type[fabll.Node],
    ) -> Generator[None, None, None]:
        self._stack.append((type_node, bound_tg, type_identifier, constraint_expr))
        try:
            yield
        finally:
            self._stack.pop()

    def current(self) -> tuple[graph.BoundNode, fabll.TypeNodeBoundTG, str]:
        if not self._stack:
            raise CompilerException("Type context is not available")
        type_node, bound_tg, identifier, _ = self._stack[-1]
        return type_node, bound_tg, identifier

    def field_exists(self, identifier: str) -> bool:
        """Check if a direct child field exists on the current type."""
        type_node, _, _ = self.current()
        return (
            self._tg.get_make_child_type_reference_by_identifier(
                type_node=type_node, identifier=identifier
            )
            is not None
        )

    def get_alias(self, name: str) -> FieldPath | None:
        """Get a pin alias from the current type's persistent aliases."""
        _, _, type_identifier = self.current()
        type_aliases = self._state.type_aliases.get(type_identifier, {})
        return type_aliases.get(name)

    def add_alias(self, name: str, path: FieldPath) -> None:
        """Add a pin alias to the current type's persistent aliases."""
        _, _, type_identifier = self.current()
        if type_identifier not in self._state.type_aliases:
            self._state.type_aliases[type_identifier] = {}
        self._state.type_aliases[type_identifier][name] = path

    @property
    def constraint_expr(self) -> type[fabll.Node]:
        _, _, _, constraint_expr = self._stack[-1]
        return constraint_expr

    def apply_action(self, action) -> None:
        type_node, bound_tg, _ = self.current()

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

    def resolve_reference(self, path: FieldPath) -> graph.BoundNode:
        type_node, _, _ = self.current()
        identifiers: list[str | EdgeTraversal] = list(path.identifiers())
        try:
            return self._tg.ensure_child_reference(
                type_node=type_node, path=identifiers
            )
        except fbrk.TypeGraphPathError as exc:
            raise DslException(self._format_path_error(path, exc)) from exc

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

    def _add_child(
        self,
        type_node: graph.BoundNode,
        bound_tg: fabll.TypeNodeBoundTG,
        action: AddMakeChildAction,
    ) -> None:
        assert action.child_field is not None

        action.child_field._set_locator(action.get_identifier())
        action.child_field._soft_create = action.soft_create
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


class AnyAtoBlock(fabll.Node):
    _definition_identifier: ClassVar[str] = "definition"


class ASTVisitor:
    """
    Generates a TypeGraph from the AST.

    Error handling strategy:
    - Fail early (TODO: revisit — return list of errors and let caller decide impact)
    - Use DslException for errors arising from code contents (i.e. user errors)
    - Use CompilerException for errors arising from compiler internals (i.e.
      implementation errors)

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
        self._tg: fbrk.TypeGraph = type_graph
        self._state = BuildState(
            type_roots={},
            external_type_refs=[],
            file_path=file_path,
            import_path=import_path,
            pending_execution=[],
        )

        self._pointer_sequence_type = F.Collections.PointerSequence.bind_typegraph(
            self._tg
        ).get_or_create_type()
        self._electrical_type = F.Electrical.bind_typegraph(
            self._tg
        ).get_or_create_type()
        self._experiments: set[ASTVisitor._Experiment] = set()
        self._scope_stack = _ScopeStack()
        self._type_stack = _TypeContextStack(
            g=self._graph,
            tg=self._tg,
            state=self._state,
        )
        self._stdlib_allowlist = {
            type_._type_identifier(): type_
            for type_ in stdlib_allowlist or STDLIB_ALLOWLIST.copy()
        }
        self._expr_counter = 0

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

    def _execute_for_loops(self) -> None:
        """
        Execute deferred for-loops.

        Called by DeferredExecutor after inheritance and retype are applied.
        For-loops need visitor infrastructure (visit() method, scope/type stacks).
        """
        for type_id, loops in groupby(
            self._state.pending_execution, key=lambda lp: lp.type_identifier
        ).items():
            if (bound_tg := self._state.type_bound_tgs.get(type_id)) is None:
                raise CompilerException(f"Type `{type_id}` not found")
            type_node = bound_tg.get_or_create_type()

            for loop in sorted(loops, key=lambda lp: lp.source_order):
                self._execute_deferred_for_loop(type_node, type_id, loop)

    @contextmanager
    def _temporary_alias(self, name: str, path: FieldPath):
        """Install a temporary alias, checking for conflicts in both namespaces."""
        if self._scope_stack.symbol_exists(name):
            raise DslException(
                f"Loop variable `{name}` conflicts with an existing symbol in scope"
            )
        if self._type_stack.field_exists(name):
            raise DslException(
                f"Loop variable `{name}` conflicts with an existing field in scope"
            )

        state = self._scope_stack.current
        state.aliases[name] = path
        try:
            yield
        finally:
            state.aliases.pop(name, None)

    def _execute_loop_body(
        self, loop_var: str, element_paths: list[FieldPath], stmts: list[fabll.Node]
    ) -> None:
        """Execute loop body statements for each element path."""
        for element_path in element_paths:
            with self._temporary_alias(loop_var, element_path):
                for stmt in stmts:
                    self._type_stack.apply_action(self.visit(stmt))

    def _collect_sequence_element_paths(
        self, type_node: graph.BoundNode, loop: DeferredForLoop
    ) -> list[FieldPath]:
        """
        Collect element paths for a sequence container, sorted by index.
        Returns paths like (container, 0), (container, 1), etc.
        """
        (*parent_path, container_id) = loop.container_path

        owning_type = (
            self._tg.resolve_child_path(start_type=type_node, path=list(parent_path))
            if parent_path
            else type_node
        )

        resolved_node = fbrk.Linker.get_resolved_type(
            type_reference=not_none(
                self._tg.get_make_child_type_reference_by_identifier(
                    type_node=not_none(owning_type), identifier=container_id
                )
            )
        )

        if owning_type is None:
            raise CompilerException(f"Cannot resolve type for path {parent_path}")

        if resolved_node is None:
            # Incomplete linking
            raise CompilerException(
                f"Cannot resolve type for path {loop.container_path}"
            )

        if (
            not (type_name := fbrk.TypeGraph.get_type_name(type_node=resolved_node))
            == F.Collections.PointerSequence._type_identifier()
        ):
            raise DslException(
                f"Cannot iterate over `{'.'.join(loop.container_path)}`: "
                f"expected a sequence, got `{type_name}`"
            )

        return sorted(
            [
                FieldPath(
                    segments=(
                        *[
                            FieldPath.Segment(identifier=seg)
                            for seg in loop.container_path
                        ],
                        FieldPath.Segment(str(order), is_index=True),
                    )
                )
                for order, _ in self._tg.collect_pointer_members(
                    type_node=owning_type, container_path=[container_id]
                )
                if order is not None
            ],
            key=lambda p: int(p.leaf.identifier),
        )

    def _execute_deferred_for_loop(
        self, type_node: graph.BoundNode, type_identifier: str, loop: DeferredForLoop
    ) -> None:
        """Execute a single deferred for-loop."""
        element_paths = self._collect_sequence_element_paths(type_node, loop)

        start, stop, step = loop.slice_spec
        if start is not None or stop is not None or step is not None:
            element_paths = element_paths[slice(start, stop, step)]

        bound_tg = not_none(self._state.type_bound_tgs.get(type_identifier))
        if (
            constraint_expr := self._state.constraining_expr_types.get(type_identifier)
        ) is None:
            raise CompilerException(
                f"No constraint expression type registered for `{type_identifier}`"
            )
        with self._type_stack.enter(
            type_node, bound_tg, type_identifier, constraint_expr
        ):
            with self._scope_stack.enter():
                self._execute_loop_body(
                    loop.variable_name, element_paths, loop.body.stmts.get().as_list()
                )

    def visit(self, node: fabll.Node):
        # TODO: less magic dispatch
        node_type = cast_assert(str, node.get_type_name()).removeprefix("compiler_")
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

        is_stdlib = type_ref_name in self._stdlib_allowlist
        is_trait_shim = TraitOverrideRegistry.matches_trait_override(type_ref_name)
        if path is None and not is_stdlib and not is_trait_shim:
            raise DslException(f"Standard library import not found: {type_ref_name}")

        self._scope_stack.add_symbol(Symbol(name=type_ref_name, import_ref=import_ref))

    def visit_BlockDefinition(self, node: AST.BlockDefinition):
        if self._scope_stack.depth != 1:
            raise DslException("Nested block definitions are not permitted")

        module_name = node.get_type_ref_name()

        if self._scope_stack.symbol_exists(module_name):
            raise DslException(f"Symbol `{module_name}` already defined in scope")

        source_dir = (
            str(self._state.file_path.parent) if self._state.file_path else None
        )

        match node.get_block_type():
            case AST.BlockDefinition.BlockType.MODULE:

                class _Module(fabll.Node):
                    _is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_module = fabll.Traits.MakeEdge(is_ato_module.MakeChild())
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Module
                constraint_expr = F.Expressions.IsSubset

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    _is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_component = fabll.Traits.MakeEdge(
                        is_ato_component.MakeChild()
                    )
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Component
                constraint_expr = F.Expressions.Is

            case AST.BlockDefinition.BlockType.INTERFACE:

                class _Interface(fabll.Node):
                    is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_interface = fabll.Traits.MakeEdge(
                        is_ato_interface.MakeChild()
                    )
                    is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

                _Block = _Interface
                constraint_expr = F.Expressions.IsSubset

        type_identifier = self._make_type_identifier(module_name)
        _Block.__name__ = type_identifier
        _Block.__qualname__ = type_identifier

        type_node_bound_tg = fabll.TypeNodeBoundTG(tg=self._tg, t=_Block)
        type_node = type_node_bound_tg.get_or_create_type()
        self._state.type_bound_tgs[type_identifier] = type_node_bound_tg
        self._state.constraining_expr_types[type_identifier] = constraint_expr

        # Capture compiler-internal identifiers before we process statements
        auto_generated_ids = frozenset(
            id
            for id, _ in self._tg.collect_make_children(type_node=type_node)
            if id is not None
        )

        # Capture inheritance relationship for deferred resolution
        if (super_type_name := node.get_super_type_ref_name()) is not None:
            super_symbol = self._scope_stack.try_resolve_symbol(super_type_name)
            import_ref = (
                super_symbol.import_ref
                if super_symbol and super_symbol.import_ref
                else None
            )

            if import_ref is not None and import_ref.path is not None:
                self._state.inheritance_imports.append(import_ref)

            self._state.pending_inheritance.append(
                PendingInheritance(
                    derived_type=type_node,
                    derived_name=module_name,
                    parent_ref=(import_ref if import_ref else super_type_name),
                    source_order=len(self._state.pending_inheritance),
                    auto_generated_ids=auto_generated_ids,
                )
            )

        # Link type node back to AST definition
        fbrk.EdgePointer.point_to(
            bound_node=type_node,
            target_node=node.instance.node(),
            identifier=AnyAtoBlock._definition_identifier,
            index=None,
        )

        stmts = node.scope.get().stmts.get().as_list()
        with self._scope_stack.enter():
            with self._type_stack.enter(
                type_node, type_node_bound_tg, type_identifier, constraint_expr
            ):
                for stmt in stmts:
                    self._type_stack.apply_action(self.visit(stmt))

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
        """If first statement in block, attach as docstring trait to the type."""
        # TODO: handle File docstrings
        try:
            type_node, bound_tg, _ = self._type_stack.current()
        except CompilerException:
            return NoOpAction()

        block_node = fbrk.EdgePointer.get_pointed_node_by_identifier(
            bound_node=type_node, identifier=AnyAtoBlock._definition_identifier
        )
        if block_node is None:
            return NoOpAction()

        stmts = AST.BlockDefinition.bind_instance(block_node).scope.get().stmts.get()
        if stmts.as_list() and stmts.as_list()[0].instance.node().is_same(
            other=node.instance.node()
        ):
            field = fabll.Traits.MakeEdge(
                F.has_doc_string.MakeChild(node.string.get().get_text()).put_on_type()
            )
            field._set_locator("_has_doc_string")
            # FIXME return action
            fabll.Node._exec_field(t=bound_tg, field=field, type_field=True)
        return NoOpAction()

    def visit_SignaldefStmt(self, node: AST.SignaldefStmt):
        (signal_name,) = node.name.get().get_values()
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=signal_name),))

        return AddMakeChildAction(
            target_path=target_path,
            child_field=fabll._ChildField(
                nodetype=F.Electrical,
                identifier=signal_name,
            ),
        )

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
        self._type_stack.add_alias(pin_label_str, target_path)

        return AddMakeChildAction(
            target_path=target_path,
            child_field=ActionsFactory.pin_child_field(pin_label_str, identifier),
        )

    def visit_FieldRef(self, node: AST.FieldRef) -> FieldPath:
        segments: list[FieldPath.Segment] = []

        for part_node in node.parts.get().as_list():
            part = part_node.cast(t=AST.FieldRefPart)
            (name,) = part.name.get().get_values()
            segments.append(FieldPath.Segment(identifier=name))

            if (key := part.get_key()) is not None:
                segments.append(FieldPath.Segment(identifier=str(key), is_index=True))

        if (pin := node.get_pin()) is not None:
            segments.append(FieldPath.Segment(identifier=f"{PIN_ID_PREFIX}{pin}"))

        if not segments:
            raise DslException("Empty field reference encountered")

        (root, *other) = segments
        if (
            # First check loop aliases (transient), then persistent type aliases
            # (for pins)
            alias := self._scope_stack.resolve_alias(root.identifier)
            or self._type_stack.get_alias(root.identifier)
        ) is not None:
            segments = [*alias.segments, *other]

        return FieldPath(segments=tuple(segments))

    def _handle_new_child(
        self,
        target_path: FieldPath,
        new_spec: NewChildSpec,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | AddMakeChildAction:
        # FIXME: linker should handle this
        # Check if module type is in stdlib or an imported python module
        module_fabll_type = (
            self._stdlib_allowlist.get(new_spec.type_identifier)
            if new_spec.type_identifier is not None
            else None
        )
        if (
            module_fabll_type is None
            and new_spec.symbol is not None
            and new_spec.symbol.import_ref is not None
            and new_spec.symbol.import_ref.path is not None
        ):
            raw_path = Path(new_spec.symbol.import_ref.path)
            if not raw_path.is_absolute() and self._state.file_path is not None:
                raw_path = (self._state.file_path.parent / raw_path).resolve()
            if raw_path.suffix == ".py" and raw_path.exists():
                obj = import_from_path(raw_path, new_spec.symbol.import_ref.name)
                if not isinstance(obj, type) or not issubclass(obj, fabll.Node):
                    raise DslException(
                        f"Symbol `{new_spec.symbol.import_ref.name}` in `{raw_path}` "
                        "is not a fabll.Node"
                    )
                module_fabll_type = obj

        if new_spec.count is None:
            if target_path.leaf.is_index and target_path.parent_segments:
                container_path = FieldPath(segments=tuple(target_path.parent_segments))
                try:
                    type_node, _, _ = self._type_stack.current()
                    pointer_members = self._tg.collect_pointer_members(
                        type_node=type_node,
                        container_path=list(container_path.identifiers()),
                    )
                except fbrk.TypeGraphPathError as exc:
                    raise DslException(
                        self._type_stack._format_path_error(container_path, exc)
                    ) from exc

                member_identifiers = {
                    identifier
                    for identifier, _ in pointer_members
                    if identifier is not None
                }

                if target_path.leaf.identifier not in member_identifiers:
                    raise DslException(f"Field `{target_path}` is not defined in scope")

            # Check if field exists for non-indexed assignments with parent segments
            elif target_path.parent_segments:
                parent_path = FieldPath(segments=tuple(target_path.parent_segments))
                try:
                    type_node, _, _ = self._type_stack.current()
                    self._tg.collect_pointer_members(
                        type_node=type_node,
                        container_path=list(parent_path.identifiers()),
                    )
                except fbrk.TypeGraphPathError as exc:
                    raise DslException(
                        f"Field `{parent_path}` could not be resolved"
                    ) from exc

            assert new_spec.type_identifier is not None

            return ActionsFactory.new_child_action(
                target_path=target_path,
                type_identifier=new_spec.type_identifier,
                module_type=module_fabll_type,
                template_args=new_spec.template_args,
                import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
            )

        try:
            child_actions, link_actions, _ = ActionsFactory.new_child_array_actions(
                target_path=target_path,
                type_identifier=not_none(new_spec.type_identifier),
                module_type=module_fabll_type,
                template_args=new_spec.template_args,
                count=new_spec.count,
                import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
            )
        except ActionGenerationError as e:
            raise DslException(str(e)) from e

        return [*child_actions, *link_actions]

    def visit_Slice(self, node: AST.Slice) -> tuple[int | None, int | None, int | None]:
        start, stop, step = node.get_values()
        if step == 0:
            raise DslException("Slice step cannot be zero")
        return start, stop, step

    def visit_Assignment(self, node: AST.Assignment):
        # TODO: broaden assignable support and handle keyed/pin field references

        target_path = self.visit_FieldRef(node.get_target())
        assignable_node = node.assignable.get()

        if TraitOverrideRegistry.matches_assignment_override(
            target_path.leaf.identifier, assignable_node
        ):
            return TraitOverrideRegistry.handle_assignment(target_path, assignable_node)

        if TraitOverrideRegistry.matches_enum_parameter_override(
            target_path.leaf.identifier, assignable_node
        ):
            return TraitOverrideRegistry.handle_enum_parameter_assignment(
                target_path, assignable_node, self._type_stack.constraint_expr
            )

        if (assignable := self.visit_Assignable(assignable_node)) is None:
            return NoOpAction()

        match assignable:
            case NewChildSpec() as new_spec:
                if target_path.leaf.is_index:
                    raise DslException(
                        f"Field `{target_path}` with index can not be assigned with new"
                    )
                return self._handle_new_child(target_path, new_spec)
            case ParameterSpec() as param_spec:
                # If index, check if path is defined in scope
                if target_path.leaf.is_index and target_path.parent_segments:
                    container_path = FieldPath(
                        segments=tuple(target_path.parent_segments)
                    )
                    try:
                        type_node, _, _ = self._type_stack.current()
                        pointer_members = self._tg.collect_pointer_members(
                            type_node=type_node,
                            container_path=list(container_path.identifiers()),
                        )
                    except fbrk.TypeGraphPathError as exc:
                        raise DslException(
                            self._type_stack._format_path_error(container_path, exc)
                        ) from exc

                    member_identifiers = {
                        identifier
                        for identifier, _ in pointer_members
                        if identifier is not None
                    }

                    if target_path.leaf.identifier not in member_identifiers:
                        raise DslException(
                            f"Field `{target_path}` is not defined in scope"
                        )
                return ActionsFactory.parameter_actions(
                    target_path=target_path,
                    param_child=param_spec.param_child,
                    constraint_operand=param_spec.operand,
                    constraint_expr=self._type_stack.constraint_expr,
                    # parameter assignment implicitly creates the parameter, if it
                    # doesn't exist already
                    soft_create=True,
                )
            case _:
                raise NotImplementedError(f"Unhandled assignable type: {assignable}")

    def visit_Assignable(
        self, node: AST.Assignable
    ) -> ParameterSpec | NewChildSpec | None:
        match assignable := node.get_value().switch_cast():
            case AST.AstString() as string:
                return ParameterSpec(
                    param_child=F.Parameters.StringParameter.MakeChild(),
                    operand=self.visit_AstString(string),
                )
            case AST.Boolean() as boolean:
                return ParameterSpec(
                    param_child=F.Parameters.BooleanParameter.MakeChild(),
                    operand=self.visit_Boolean(boolean),
                )
            case AST.NewExpression() as new:
                return self.visit_NewExpression(new)
            case (
                AST.Quantity()
                | AST.BilateralQuantity()
                | AST.BoundedQuantity() as quantity
            ):
                lit, unit = self.visit(quantity)
                assert isinstance(lit, fabll._ChildField)
                return ParameterSpec(
                    param_child=F.Parameters.NumericParameter.MakeChild(unit=unit),
                    operand=lit,
                )
            case AST.BinaryExpression() | AST.GroupExpression() as arithmetic:
                expr = self.visit(arithmetic)
                assert isinstance(expr, fabll._ChildField)
                return ParameterSpec(
                    param_child=F.Parameters.NumericParameter.MakeChild_DeferredUnit(),
                    operand=expr,
                )

            case _:
                raise ValueError(f"Unhandled assignable type: {assignable}")

    def to_expression_tree(self, node: AST.is_arithmetic) -> fabll.RefPath:
        """Convert an arithmetic AST node to a RefPath for expression trees.

        Handles:
        - FieldRef -> list of string identifiers
        - Quantity/BilateralQuantity/BoundedQuantity -> [literal_child_field]
        - BinaryExpression/GroupExpression -> [expression_child_field]

        Note: The returned paths do NOT include "can_be_operand" suffix.
        This is because MakeChild_Constrain methods append it themselves.
        """
        visited = self.visit(fabll.Traits(node).get_obj_raw())

        match visited:
            case fabll._ChildField() as child_field:
                # Expression or standalone literal
                return [child_field]
            case FieldPath() as field_path:
                # Reference to existing field
                return list(field_path.identifiers())
            case (fabll._ChildField() as child_field, _):
                # Quantity with unit tuple (child_field, unit_type)
                return [child_field]

        raise DslException(
            f"Unknown arithmetic: {fabll.Traits(node).get_obj_raw().get_type_name()}"
        )

    def visit_AssertStmt(self, node: AST.AssertStmt) -> AddMakeChildAction:
        comparison_expression = node.get_comparison()
        comparison_clauses = comparison_expression.get_comparison_clauses()
        (root_comparison_clause, *_) = comparison_clauses

        lhs_refpath = self.to_expression_tree(comparison_expression.get_lhs())
        rhs_refpath = self.to_expression_tree(root_comparison_clause.get_rhs())

        if len(comparison_clauses) > 1:
            raise NotImplementedError(
                "Assert statement must have exactly one comparison clause (operator)"
            )
            # TODO: handle multiple clauses

        operator = root_comparison_clause.get_operator()

        match operator:
            case AST.ComparisonClause.ComparisonOperator.GREATER_THAN:
                expr_type = F.Expressions.GreaterThan
            case AST.ComparisonClause.ComparisonOperator.GT_EQ:
                expr_type = F.Expressions.GreaterOrEqual
            case AST.ComparisonClause.ComparisonOperator.LESS_THAN:
                expr_type = F.Expressions.LessThan
            case AST.ComparisonClause.ComparisonOperator.LT_EQ:
                expr_type = F.Expressions.LessOrEqual
            case AST.ComparisonClause.ComparisonOperator.WITHIN:
                expr_type = F.Expressions.IsSubset
            case AST.ComparisonClause.ComparisonOperator.IS:
                expr_type = F.Expressions.Is
            case _:
                raise DslException(f"Unknown comparison operator: {operator}")

        # Generate unique identifier for this assertion to avoid collisions
        # when multiple assertions target the same LHS
        expr_id = self._expr_counter
        self._expr_counter += 1

        expr = expr_type.MakeChild(lhs_refpath, rhs_refpath, assert_=True)
        expr.add_dependant(
            *[seg for seg in lhs_refpath if isinstance(seg, fabll._ChildField)],
            identifier=f"lhs_{expr_id}",
            before=True,
        )
        expr.add_dependant(
            *[seg for seg in rhs_refpath if isinstance(seg, fabll._ChildField)],
            identifier=f"rhs_{expr_id}",
            before=True,
        )

        # Create a unique target path for this assertion
        lhs_name = "_".join(
            str(seg)
            if isinstance(seg, str)
            else (seg.identifier if isinstance(seg.identifier, str) else "anon")
            for seg in lhs_refpath
            if isinstance(seg, (str, fabll._ChildField))
        )
        unique_id = f"_assert_{lhs_name}_{expr_id}"

        return AddMakeChildAction(
            target_path=FieldPath(segments=(FieldPath.Segment(unique_id),)),
            child_field=expr,
        )

    def visit_Quantity(
        self, node: AST.Quantity
    ) -> tuple["fabll._ChildField[F.Literals.Numbers]", type[fabll.Node]]:
        unit_t = (
            F.Units.Dimensionless
            if (symbol := node.try_get_unit_symbol()) is None
            else F.Units.decode_symbol(self._graph, self._tg, symbol)
        )
        operand = F.Literals.Numbers.MakeChild_SingleValue(
            value=node.get_value(), unit=unit_t
        )
        return operand, unit_t

    def visit_BinaryExpression(self, node: AST.BinaryExpression) -> "fabll._ChildField":
        operator = node.get_operator()
        lhs_refpath = self.to_expression_tree(node.get_lhs())
        rhs_refpath = self.to_expression_tree(node.get_rhs())

        match operator:
            case AST.BinaryExpression.BinaryOperator.ADD:
                expr_t = F.Expressions.Add
            case AST.BinaryExpression.BinaryOperator.SUBTRACT:
                expr_t = F.Expressions.Subtract
            case AST.BinaryExpression.BinaryOperator.MULTIPLY:
                expr_t = F.Expressions.Multiply
            case AST.BinaryExpression.BinaryOperator.DIVIDE:
                expr_t = F.Expressions.Divide
            case AST.BinaryExpression.BinaryOperator.POWER:
                expr_t = F.Expressions.Power
            case (
                AST.BinaryExpression.BinaryOperator.OR
                | AST.BinaryExpression.BinaryOperator.AND
            ):
                raise DslException(f"Unsupported binary operator: {operator}")

        expr = expr_t.MakeChild(lhs_refpath, rhs_refpath)
        expr.add_dependant(
            *[seg for seg in lhs_refpath if isinstance(seg, fabll._ChildField)],
            identifier="lhs",
            before=True,
        )
        expr.add_dependant(
            *[seg for seg in rhs_refpath if isinstance(seg, fabll._ChildField)],
            identifier="rhs",
            before=True,
        )
        return expr

    def visit_GroupExpression(
        self, node: AST.GroupExpression
    ) -> "fabll._ChildField | FieldPath | tuple[fabll._ChildField, type[fabll.Node]]":
        """Unwrap a parenthesized expression and delegate to inner expression."""
        inner_arithmetic = node.get_expression()
        return self.visit(fabll.Traits(inner_arithmetic).get_obj_raw())

    def visit_BoundedQuantity(
        self, node: AST.BoundedQuantity
    ) -> tuple["fabll._ChildField[F.Literals.Numbers]", type[fabll.Node]]:
        start_unit_symbol = node.start.get().try_get_unit_symbol()
        start_value = node.start.get().get_value()

        end_unit_symbol = node.end.get().try_get_unit_symbol()
        end_value = node.end.get().get_value()

        match [start_unit_symbol, end_unit_symbol]:
            case [None, None]:
                unit_t = F.Units.Dimensionless
            case [None, _]:
                unit_t = F.Units.decode_symbol(
                    self._graph, self._tg, not_none(end_unit_symbol)
                )
            case [_, None]:
                unit_t = F.Units.decode_symbol(
                    self._graph, self._tg, not_none(start_unit_symbol)
                )
            case [_, _] if start_unit_symbol != end_unit_symbol:
                unit_t = F.Units.decode_symbol(
                    self._graph, self._tg, not_none(start_unit_symbol)
                )
                end_unit_t = F.Units.decode_symbol(
                    self._graph, self._tg, not_none(end_unit_symbol)
                )

                unit_info = F.Units.extract_unit_info(unit_t)
                end_unit_info = F.Units.extract_unit_info(end_unit_t)
                if not unit_info.is_commensurable_with(end_unit_info):
                    raise DslException(
                        "Bounded quantity start and end units must be commensurable"
                    )
                end_value = unit_info.convert_value(end_value, end_unit_info)
            case [_, _]:
                unit_t = F.Units.decode_symbol(
                    self._graph, self._tg, not_none(start_unit_symbol)
                )
            case _:
                raise CompilerException(
                    "Unexpected bounded quantity start and end units"
                )

        operand = F.Literals.Numbers.MakeChild(
            min=start_value, max=end_value, unit=unit_t
        )
        return operand, unit_t

    def visit_BilateralQuantity(
        self, node: AST.BilateralQuantity
    ) -> tuple["fabll._ChildField[F.Literals.Numbers]", type[fabll.Node]]:
        quantity_value = node.quantity.get().get_value()
        quantity_unit_symbol = node.quantity.get().try_get_unit_symbol()

        tol_value = node.tolerance.get().get_value()
        tol_unit_symbol = node.tolerance.get().try_get_unit_symbol()

        def _decode_symbol(symbol: str) -> type[fabll.Node]:
            return F.Units.decode_symbol(self._graph, self._tg, symbol)

        match [quantity_unit_symbol, tol_unit_symbol]:
            case [None, None]:
                rel = False
                unit_t = F.Units.Dimensionless
            case [None, F.Units.PERCENT_SYMBOL]:
                rel = True
                unit_t = F.Units.Dimensionless
            case [_, F.Units.PERCENT_SYMBOL]:
                rel = True
                unit_t = _decode_symbol(not_none(quantity_unit_symbol))
            case [_, None]:
                rel = False
                unit_t = _decode_symbol(not_none(quantity_unit_symbol))
            case [None, _]:
                rel = False
                unit_t = _decode_symbol(not_none(tol_unit_symbol))
            case [_, _] if quantity_unit_symbol == tol_unit_symbol:
                rel = False
                unit_t = _decode_symbol(not_none(quantity_unit_symbol))
            case [_, _]:
                rel = False
                unit_t = _decode_symbol(not_none(quantity_unit_symbol))
                tol_unit_t = _decode_symbol(not_none(tol_unit_symbol))

                q_info = F.Units.extract_unit_info(unit_t)
                tol_info = F.Units.extract_unit_info(tol_unit_t)

                try:
                    tol_value = q_info.convert_value(tol_value, tol_info)
                except UnitsNotCommensurableError as e:
                    raise DslException(
                        f"Tolerance unit `{tol_unit_symbol}` is not commensurable "
                        f"with quantity unit `{quantity_unit_symbol}`"
                    ) from e
            case _:
                raise DslException("Unexpected quantity and tolerance units")

        operand = (
            F.Literals.Numbers.MakeChild_FromCenterRel(
                center=quantity_value, rel=tol_value / 100, unit=unit_t
            )
            if rel
            else F.Literals.Numbers.MakeChild(
                min=quantity_value - tol_value,
                max=quantity_value + tol_value,
                unit=unit_t,
            )
        )
        return operand, unit_t

    def visit_NewExpression(self, node: AST.NewExpression):
        type_name = node.get_type_ref_name()

        # Extract template arguments if present (e.g., new Addressor<address_bits=2>)
        if (
            template_args := self._extract_template_args(node.template.get())
        ) is not None:
            self.ensure_experiment(ASTVisitor._Experiment.MODULE_TEMPLATING)

        return NewChildSpec(
            symbol=self._scope_stack.try_resolve_symbol(type_name),
            type_identifier=type_name,
            count=node.get_new_count(),
            template_args=template_args,
        )

    # FIXME: refactor to match pattern
    def _resolve_connectable_with_path(
        self, connectable_node: fabll.Node
    ) -> tuple[FieldPath, list[AddMakeChildAction]]:
        """Resolve a connectable node to a path and any actions needed to create it.

        Handles two cases:
        - FieldRef: reference to existing field (must exist), no actions
        - Declarations (Signal, Pin): may create if not exists, returns creation actions
        """
        if connectable_node.isinstance(AST.FieldRef):
            return self._resolve_field_ref(connectable_node.cast(t=AST.FieldRef))
        return self._resolve_declaration(connectable_node)

    def _resolve_field_ref(
        self, field_ref: AST.FieldRef
    ) -> tuple[FieldPath, list[AddMakeChildAction]]:
        """Resolve a reference to an existing field. Returns empty action list."""
        path = self.visit_FieldRef(field_ref)
        # FIXME: refactor this, remove resolve_reference
        self._type_stack.resolve_reference(path)
        return path, []

    def _resolve_declaration(
        self, node: fabll.Node
    ) -> tuple[FieldPath, list[AddMakeChildAction]]:
        """
        Resolve a declaration node, returning creation actions if it doesn't exist.
        """
        target_path, visit_fn = self._get_declaration_info(node)

        # Special handling for (legacy) pin declarations in connection contexts
        # Check if already exists within the module's type context
        if node.isinstance(AST.PinDeclaration):
            if self._type_stack.field_exists(target_path.root.identifier):
                # Pin already exists, returning existing path (pin)
                return target_path, []

        # FIXME: invalid (pre-linking)
        # if not self._type_stack.field_exists(target_path.root.identifier):
        return target_path, [visit_fn()]

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

        lhs_path, lhs_actions = self._resolve_connectable_with_path(lhs_node)
        rhs_path, rhs_actions = self._resolve_connectable_with_path(rhs_node)

        # Convert FieldPath to LinkPath (list of string identifiers)
        # Apply legacy path translations (e.g., vcc -> hv, gnd -> lv)
        lhs_link_path = LinkPath(list(lhs_path.identifiers()))
        rhs_link_path = LinkPath(list(rhs_path.identifiers()))

        link_action = AddMakeLinkAction(lhs_path=lhs_link_path, rhs_path=rhs_link_path)
        return [*lhs_actions, *rhs_actions, link_action]

    def visit_RetypeStmt(self, node: AST.RetypeStmt):
        """
        Handle retype: `target.path -> NewType`

        Replaces an existing field's type reference with a new type.
        """
        type_node, _, _ = self._type_stack.current()
        target_path = self.visit_FieldRef(node.get_target())
        new_type_name = node.get_new_type_name()

        # Try to resolve symbol for import path, but allow forward references
        symbol = self._scope_stack.try_resolve_symbol(new_type_name)
        import_ref = symbol.import_ref if symbol else None

        # Linker will resolve this later
        new_type_ref = self._tg.add_type_reference(type_identifier=new_type_name)

        self._state.external_type_refs.append((new_type_ref, import_ref))
        self._state.pending_retypes.append(
            PendingRetype(
                containing_type=type_node,
                target_path=target_path,
                new_type_ref=new_type_ref,
                source_order=len(self._state.pending_retypes),
            )
        )

        return NoOpAction()

    def visit_DeclarationStmt(self, node: AST.DeclarationStmt):
        unit_symbol = node.unit_symbol.get().symbol.get().get_single()
        unit_t = F.Units.decode_symbol(self._graph, self._tg, not_none(unit_symbol))
        target_path = self.visit_FieldRef(node.get_field_ref())
        return ActionsFactory.parameter_actions(
            target_path=target_path,
            param_child=F.Parameters.NumericParameter.MakeChild(unit=unit_t),
            constraint_operand=None,
            constraint_expr=self._type_stack.constraint_expr,
        )

    def visit_DirectedConnectStmt(self, node: AST.DirectedConnectStmt):
        """
        `a ~> b` connects a.can_bridge.out_ to b.can_bridge.in_
        `a <~ b` connects a.can_bridge.in_ to b.can_bridge.out_
        """
        lhs = node.get_lhs()
        rhs = node.get_rhs()

        # Validate that all directions in a chain are the same (e.g. a ~> b ~> c)
        current_direction = node.get_direction()
        if nested_rhs := rhs.try_cast(t=AST.DirectedConnectStmt):
            nested_direction = nested_rhs.get_direction()
            if current_direction != nested_direction:
                raise DslException(
                    "Only one type of connection direction per statement allowed"
                )

        lhs_node = fabll.Traits(lhs).get_obj_raw()
        lhs_base_path, lhs_actions = self._resolve_connectable_with_path(lhs_node)

        if nested_rhs := rhs.try_cast(t=AST.DirectedConnectStmt):
            nested_lhs = nested_rhs.get_lhs()
            nested_lhs_node = fabll.Traits(nested_lhs).get_obj_raw()
            middle_base_path, middle_actions = self._resolve_connectable_with_path(
                nested_lhs_node
            )

            link_action = ActionsFactory.directed_link_action(
                lhs_base_path, middle_base_path, node.get_direction()
            )
            nested_actions = self.visit_DirectedConnectStmt(nested_rhs)

            return [*lhs_actions, *middle_actions, link_action, *nested_actions]

        rhs_node = fabll.Traits(rhs).get_obj_raw()
        rhs_base_path, rhs_actions = self._resolve_connectable_with_path(rhs_node)

        link_action = ActionsFactory.directed_link_action(
            lhs_base_path, rhs_base_path, node.get_direction()
        )
        return [*lhs_actions, *rhs_actions, link_action]

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

    def visit_ForStmt(self, node: AST.ForStmt):
        def validate_stmts(stmts: list[fabll.Node]) -> None:
            def error(node: fabll.Node) -> None:
                # FiXME: make this less fragile
                source_node = AST.SourceChunk.bind_instance(
                    not_none(
                        fbrk.EdgeComposition.get_child_by_identifier(
                            bound_node=node.instance, child_identifier="source"
                        )
                    )
                )
                source_text = source_node.get_text()
                stmt_str = source_text.split(" ")[0]
                raise DslException(f"Invalid statement in for loop: {stmt_str}")

            for stmt in stmts:
                for illegal_type in (
                    AST.ImportStmt,
                    AST.PinDeclaration,
                    AST.SignaldefStmt,
                    AST.TraitStmt,
                    AST.ForStmt,
                ):
                    if stmt.isinstance(illegal_type):
                        error(stmt)

                if stmt.isinstance(AST.Assignment):
                    assignment = stmt.cast(t=AST.Assignment)
                    assignable_value = (
                        assignment.assignable.get().get_value().switch_cast()
                    )
                    if assignable_value.isinstance(AST.NewExpression):
                        error(stmt)

        self.ensure_experiment(ASTVisitor._Experiment.FOR_LOOP)

        loop_var = node.target.get().get_single()
        iterable_node = node.iterable.get().deref()

        stmts = node.scope.get().stmts.get().as_list()
        validate_stmts(stmts)

        # List literals [a, b, c] — execute immediately, paths are known
        if iterable_node.isinstance(AST.FieldRefList):
            self._execute_loop_body(
                loop_var,
                element_paths=[
                    self.visit_FieldRef(item_ref.cast(t=AST.FieldRef))
                    for item_ref in iterable_node.cast(t=AST.FieldRefList)
                    .items.get()
                    .as_list()
                ],
                stmts=stmts,
            )

        # Sequence iteration (items or items[1:]) — defer to phase 2
        elif iterable_node.isinstance(AST.IterableFieldRef):
            iterable_field = iterable_node.cast(t=AST.IterableFieldRef)
            container_path = self.visit_FieldRef(iterable_field.get_field())
            slice_spec = self.visit_Slice(iterable_field.slice.get())
            _, _, type_identifier = self._type_stack.current()

            self._state.pending_execution.append(
                DeferredForLoop(
                    type_identifier=type_identifier,
                    container_path=container_path.identifiers(),
                    variable_name=loop_var,
                    slice_spec=slice_spec,
                    body=node.scope.get(),
                    source_order=len(self._state.pending_execution),
                )
            )

        else:
            raise CompilerException("Unexpected iterable type")

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

    def visit_TraitStmt(
        self, node: AST.TraitStmt
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | NoOpAction:
        """
        Visit a trait statement and return a list of actions to create the trait.

        Returns:
            A list containing:
            1. AddMakeChildAction to create the trait as a child
            2. AddMakeLinkAction to link the target to the trait with EdgeTrait
        """
        self.ensure_experiment(ASTVisitor._Experiment.TRAITS)

        (trait_type_name,) = node.type_ref.get().name.get().get_values()

        if not self._scope_stack.symbol_exists(trait_type_name):
            raise DslException(f"Trait `{trait_type_name}` must be imported before use")

        target_path_list: LinkPath = []
        if (target_field_ref := node.get_target()) is not None:
            target_path = self.visit_FieldRef(target_field_ref)
            target_path_list = list(target_path.identifiers())

        template_args = self._extract_template_args(node.template.get())

        if TraitOverrideRegistry.matches_trait_override(trait_type_name):
            return TraitOverrideRegistry.handle_trait(
                trait_type_name, target_path_list, template_args
            )
        else:
            try:
                trait_fabll_type = self._stdlib_allowlist[trait_type_name]
            except KeyError:
                raise DslException(f"External trait `{trait_type_name}` not supported")

            if not fabll.Traits.is_trait_type(trait_fabll_type):
                raise DslException(f"`{trait_type_name}` is not a valid trait")

            return ActionsFactory.trait_from_field(
                ActionsFactory.trait_field(trait_fabll_type, template_args),
                target_path_list,
            )
