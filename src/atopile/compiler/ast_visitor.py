import itertools
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, ClassVar, NoReturn

import atopile.compiler.ast_types as AST
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler import (
    CompilerException,
    DslException,
    DslFeatureNotEnabledError,
    DslImportError,
    DslKeyError,
    DslNotImplementedError,
    DslRichException,
    DslSyntaxError,
    DSLTracebackFrame,
    DSLTracebackStack,
    DslTypeError,
    DslUndefinedSymbolError,
    DslValueError,
)
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
from atopile.compiler.overrides import ReferenceOverrideRegistry, TraitOverrideRegistry
from atopile.errors import DeprecatedException, downgrade
from atopile.logging import get_logger
from faebryk.core.faebrykpy import EdgeTraversal
from faebryk.library.Units import UnitsNotCommensurableError
from faebryk.libs.util import cast_assert, groupby, import_from_path, not_none

_Quantity = tuple[float, fabll._ChildField]

logger = get_logger(__name__)


# FIXME: needs expanding
# Allowlist for user-importable types — everything here should be documented and
# supported
AllowListT = set[type[fabll.Node]]
STDLIB_ALLOWLIST: AllowListT = (
    # Modules
    {
        F.Addressor,
        F.SinglePinAddressor,
        F.BJT,
        F.CAN_TTL,
        F.Capacitor,
        F.CapacitorPolarized,
        F.MultiCapacitor,
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
        F.TestPoint,
        F.MountingHole,
        F.NetTie,
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
    external_type_refs: list[
        tuple[
            graph.BoundNode,
            ImportRef | None,
            fabll.Node | None,
            list[DSLTracebackFrame],
        ]
    ]  # [Type Reference Node, Import Reference, Source Chunk, Traceback Stack]
    file_path: Path | None
    import_path: str | None
    pending_execution: list[DeferredForLoop] = field(default_factory=list)
    pending_inheritance: list[PendingInheritance] = field(default_factory=list)
    pending_retypes: list[PendingRetype] = field(default_factory=list)
    type_bound_tgs: dict[str, fabll.TypeNodeBoundTG] = field(default_factory=dict)
    constraining_expr_types: dict[str, type[fabll.Node]] = field(default_factory=dict)
    type_aliases: dict[str, dict[str, FieldPath]] = field(default_factory=dict)
    inheritance_imports: list[ImportRef] = field(default_factory=list)

    def get_type_root(self, name: str) -> graph.BoundNode:
        return self.type_roots[name]


class is_ato_block(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    source_dir = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, source_dir: str | None = None) -> fabll._ChildField:
        field = fabll._ChildField(cls)
        if source_dir is not None:
            field.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [field, cls.source_dir], source_dir
                )
            )
        return field

    def get_source_dir(self) -> str:
        """Get the source directory path where the .ato file is located."""
        return self.source_dir.get().extract_singleton()


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
            raise DslKeyError(f"Symbol `{symbol.name}` already defined in scope")

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
        self,
        *,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        state: BuildState,
        traceback_stack: "DSLTracebackStack",
    ) -> None:
        self._stack: list[
            tuple[graph.BoundNode, fabll.TypeNodeBoundTG, str, type[fabll.Node]]
        ] = []
        self._g = g
        self._tg = tg
        self._state = state
        self._traceback_stack = traceback_stack

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
        # Apply reference overrides (e.g., reference_shim -> trait pointer deref)
        # This must happen before validation so virtual fields can be resolved
        identifiers: list[str | EdgeTraversal] = (
            ReferenceOverrideRegistry.transform_link_path(list(path.identifiers()))
        )
        try:
            return self._tg.ensure_child_reference(
                type_node=type_node, path=identifiers
            )
        except fbrk.TypeGraphPathError as exc:
            raise DslUndefinedSymbolError(self._format_path_error(path, exc)) from exc

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
        fabll.Node._exec_field(
            t=bound_tg,
            field=action.child_field,
            source_chunk_node=action.source_chunk_node,
        )

        # Track unresolved type references (both imports and local forward refs)
        if isinstance(action.child_field.nodetype, str):
            assert isinstance(action.child_field.identifier, str)
            type_ref = self._tg.get_make_child_type_reference_by_identifier(
                type_node=type_node, identifier=action.child_field.identifier
            )
            self._state.external_type_refs.append(
                (
                    not_none(type_ref),
                    action.import_ref,
                    action.source_chunk_node,
                    self._traceback_stack.get_frames(),
                )
            )

    # TODO FIXME: no type checking for is_interface trait on connected nodes.
    # We should use the fabll connect_to method for this.
    def _add_link(
        self,
        type_node: graph.BoundNode,
        bound_tg: fabll.TypeNodeBoundTG,
        action: AddMakeLinkAction,
    ) -> None:
        make_link_node = bound_tg.MakeEdge(
            lhs_reference_path=action.lhs_path,
            rhs_reference_path=action.rhs_path,
            edge=action.edge or fbrk.EdgeInterfaceConnection.build(shallow=False),
        )
        if action.source_chunk_node is not None:
            fabll.Node(make_link_node).set_source_pointer(action.source_chunk_node)


class AnyAtoBlock(fabll.Node):
    _definition_identifier: ClassVar[str] = "definition"
    _source_identifier: ClassVar[str] = "source"


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

        self._traceback_stack = DSLTracebackStack(file_path=file_path)
        self._experiments: set[ASTVisitor._Experiment] = set()
        self._scope_stack = _ScopeStack()
        self._type_stack = _TypeContextStack(
            g=self._graph,
            tg=self._tg,
            state=self._state,
            traceback_stack=self._traceback_stack,
        )
        self._stdlib_allowlist = {
            type_._type_identifier(): type_
            for type_ in stdlib_allowlist or STDLIB_ALLOWLIST.copy()
        }
        self._expr_counter = itertools.count()

    def _raise(
        self,
        exc_type: type[DslException],
        message: str,
        source_node: fabll.Node | None = None,
    ) -> NoReturn:
        """Raise a DslRichException with current context."""
        raise DslRichException(
            message,
            original=exc_type(message),
            source_node=source_node,
            traceback=self._traceback_stack.get_frames(),
        )

    def _decode_unit(self, node: AST.Quantity) -> type[fabll.Node]:
        if (symbol := node.try_get_unit_symbol()) is None:
            return F.Units.Dimensionless
        try:
            return F.Units.decode_symbol(self._graph, self._tg, symbol)
        except F.Units.UnitNotFoundError as e:
            self._raise(DslValueError, str(e), node)

    def _parse_pragma(
        self, pragma_text: str
    ) -> tuple[str, list[str | int | float | bool]]:
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
            self._raise(DslSyntaxError, f"Malformed pragma: '{pragma_text}'")

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
            self._raise(
                DslFeatureNotEnabledError, f"Experiment {experiment} is not enabled"
            )

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
            raise DslKeyError(
                f"Loop variable `{name}` conflicts with an existing symbol in scope"
            )
        if self._type_stack.field_exists(name):
            raise DslKeyError(
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
            raise DslTypeError(
                f"Cannot iterate over `{'.'.join(loop.container_path)}`: "
                f"expected a sequence, got `{type_name}`"
            )

        pointer_members = list(
            self._tg.collect_pointer_members(
                type_node=owning_type, container_path=[container_id]
            )
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
                for order, _ in pointer_members
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
        module = "atopile.compiler.ast_types"
        mod_suffix = "." + ".".join(reversed(module.split(".")))
        node_type = cast_assert(str, node.get_type_name()).removesuffix(mod_suffix)
        logger.info(f"Visiting node of type {node_type}")

        try:
            handler = getattr(self, f"visit_{node_type}")
        except AttributeError:
            raise NotImplementedError(f"No handler for node type: {node_type}")

        bound_node = getattr(AST, node_type).bind_instance(node.instance)

        # Automatically handle tracebacks for all visitor methods
        with self._traceback_stack.enter(bound_node):
            return handler(bound_node)

    def visit_File(self, node: AST.File):
        self.visit(node.scope.get())

    def visit_Scope(self, node: AST.Scope):
        with self._scope_stack.enter():
            for scope_child in node.stmts.get().as_list():
                self.visit(scope_child)

    def visit_PragmaStmt(self, node: AST.PragmaStmt):
        if (pragma := node.get_pragma()) is None:
            self._raise(
                DslSyntaxError, f"Pragma statement has no pragma text: {node}", node
            )

        pragma_func_name, pragma_args = self._parse_pragma(pragma)

        match pragma_func_name:
            case ASTVisitor._Pragma.EXPERIMENT.value:
                if len(pragma_args) != 1:
                    self._raise(
                        DslSyntaxError,
                        f"Experiment pragma takes exactly one argument: `{pragma}`",
                        node,
                    )

                (experiment_name,) = pragma_args

                try:
                    experiment = ASTVisitor._Experiment(experiment_name)
                except ValueError:
                    self._raise(
                        DslValueError,
                        f"Experiment not recognized: `{experiment_name}`",
                        node,
                    )

                self.enable_experiment(experiment)
            case _:
                self._raise(
                    DslSyntaxError, f"Pragma function not recognized: `{pragma}`", node
                )

    def visit_ImportStmt(self, node: AST.ImportStmt):
        type_ref_name = node.get_type_ref_name()
        path = node.get_path()
        import_ref = ImportRef(name=type_ref_name, path=path)

        is_stdlib = type_ref_name in self._stdlib_allowlist
        is_trait_shim = TraitOverrideRegistry.matches_trait_override(type_ref_name)
        if path is None and not is_stdlib and not is_trait_shim:
            self._raise(
                DslImportError,
                f"Standard library import not found: {type_ref_name}",
                node,
            )

        self._scope_stack.add_symbol(Symbol(name=type_ref_name, import_ref=import_ref))

    def visit_BlockDefinition(self, node: AST.BlockDefinition):
        if self._scope_stack.depth != 1:
            self._raise(
                DslSyntaxError, "Nested block definitions are not permitted", node
            )

        module_name = node.get_type_ref_name()

        if self._scope_stack.symbol_exists(module_name):
            self._raise(
                DslKeyError,
                f"Symbol `{module_name}` already defined in scope",
                node,
            )

        source_dir = (
            str(self._state.file_path.parent) if self._state.file_path else None
        )

        type_identifier = self._make_type_identifier(module_name)
        if existing_type := fabll.Node._seen_types.get(type_identifier):
            logger.debug(
                f"Type {type_identifier} already processed, skipping reprocessing"
            )
            type_node_bound_tg = fabll.TypeNodeBoundTG(tg=self._tg, t=existing_type)
            type_node = type_node_bound_tg.get_or_create_type()

            self._state.type_roots[module_name] = type_node
            self._scope_stack.add_symbol(Symbol(name=module_name, type_node=type_node))
            return

        match node.get_block_type():
            case AST.BlockDefinition.BlockType.MODULE:

                class _Module(fabll.Node):
                    _override_type_identifier = type_identifier
                    _is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_module = fabll.Traits.MakeEdge(is_ato_module.MakeChild())
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Module
                constraint_expr = F.Expressions.IsSubset

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    _override_type_identifier = type_identifier
                    _is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_component = fabll.Traits.MakeEdge(
                        is_ato_component.MakeChild()
                    )
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Component
                constraint_expr = F.Expressions.IsSuperset

            case AST.BlockDefinition.BlockType.INTERFACE:

                class _Interface(fabll.Node):
                    _override_type_identifier = type_identifier
                    is_ato_block = fabll.Traits.MakeEdge(
                        is_ato_block.MakeChild(source_dir=source_dir)
                    )
                    is_ato_interface = fabll.Traits.MakeEdge(
                        is_ato_interface.MakeChild()
                    )
                    is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

                _Block = _Interface
                constraint_expr = F.Expressions.IsSubset

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
                    source_node=node,
                )
            )

        # Link type node back to AST definition
        fbrk.EdgePointer.point_to(
            bound_node=type_node,
            target_node=node.instance.node(),
            identifier=AnyAtoBlock._definition_identifier,
            index=None,
        )
        if source_chunk := node.source.get():
            fabll.Node(type_node).add_source_chunk_trait(source_chunk)

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
            source_chunk_node=node.source.get(),
        )

    def visit_PinDeclaration(self, node: AST.PinDeclaration):
        pin_label = node.get_label()
        if pin_label is None:
            self._raise(DslSyntaxError, "Pin declaration has no label", node)

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
            source_chunk_node=node.source.get(),
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
            self._raise(DslSyntaxError, "Empty field reference encountered", node)

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
        source_chunk_node: AST.SourceChunk | None = None,
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
                    self._raise(
                        DslTypeError,
                        f"Symbol `{new_spec.symbol.import_ref.name}` in `{raw_path}` "
                        "is not a fabll.Node",
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
                    self._raise(
                        DslUndefinedSymbolError,
                        self._type_stack._format_path_error(container_path, exc),
                    )

                member_identifiers = {
                    identifier
                    for identifier, _ in pointer_members
                    if identifier is not None
                }

                if target_path.leaf.identifier not in member_identifiers:
                    self._raise(
                        DslUndefinedSymbolError,
                        f"Field `{target_path}` is not defined in scope",
                    )

            # Check if field exists for non-indexed assignments with parent segments
            elif target_path.parent_segments:
                parent_path = FieldPath(segments=tuple(target_path.parent_segments))
                try:
                    type_node, _, _ = self._type_stack.current()
                    self._tg.collect_pointer_members(
                        type_node=type_node,
                        container_path=list(parent_path.identifiers()),
                    )
                except fbrk.TypeGraphPathError:
                    self._raise(
                        DslUndefinedSymbolError,
                        f"Field `{parent_path}` could not be resolved",
                        source_chunk_node,
                    )

            assert new_spec.type_identifier is not None

            return ActionsFactory.new_child_action(
                target_path=target_path,
                type_identifier=new_spec.type_identifier,
                module_type=module_fabll_type,
                template_args=new_spec.template_args,
                import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
                source_chunk_node=source_chunk_node,
            )

        try:
            child_actions, link_actions, _ = ActionsFactory.new_child_array_actions(
                target_path=target_path,
                type_identifier=not_none(new_spec.type_identifier),
                module_type=module_fabll_type,
                template_args=new_spec.template_args,
                count=new_spec.count,
                import_ref=new_spec.symbol.import_ref if new_spec.symbol else None,
                source_chunk_node=source_chunk_node,
            )
        except ActionGenerationError as e:
            self._raise(DslValueError, str(e), source_chunk_node)

        return [*child_actions, *link_actions]

    def visit_Slice(self, node: AST.Slice) -> tuple[int | None, int | None, int | None]:
        start, stop, step = node.get_values()
        if step == 0:
            self._raise(DslValueError, "Slice step cannot be zero", node)
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

        if TraitOverrideRegistry.matches_default_override(
            target_path.leaf.identifier, assignable_node
        ):
            # Visit the assignable to get the literal field
            assignable = self.visit_Assignable(assignable_node)
            if not isinstance(assignable, ParameterSpec) or assignable.operand is None:
                self._raise(
                    DslSyntaxError,
                    "`.default` requires a physical quantity value "
                    "(e.g., `1A`, `10kohm +/- 5%`)",
                    node,
                )
            return TraitOverrideRegistry.handle_default_assignment(
                target_path, assignable.operand
            )

        if (assignable := self.visit_Assignable(assignable_node)) is None:
            return NoOpAction()

        match assignable:
            case NewChildSpec() as new_spec:
                if target_path.leaf.is_index:
                    self._raise(
                        DslSyntaxError,
                        f"Field `{target_path}` with index cannot be assigned with new",
                        node,
                    )
                return self._handle_new_child(
                    target_path, new_spec, source_chunk_node=node.source.get()
                )
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
                        self._raise(
                            DslUndefinedSymbolError,
                            self._type_stack._format_path_error(container_path, exc),
                            node,
                        )

                    member_identifiers = {
                        identifier
                        for identifier, _ in pointer_members
                        if identifier is not None
                    }

                    if target_path.leaf.identifier not in member_identifiers:
                        self._raise(
                            DslUndefinedSymbolError,
                            f"Field `{target_path}` is not defined in scope",
                            node,
                        )
                return ActionsFactory.parameter_actions(
                    target_path=target_path,
                    param_child=param_spec.param_child,
                    constraint_operand=param_spec.operand,
                    constraint_expr=self._type_stack.constraint_expr,
                    # parameter assignment implicitly creates the parameter, if it
                    # doesn't exist already
                    soft_create=True,
                    source_chunk_node=node.source.get(),
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

        self._raise(
            DslSyntaxError,
            f"Unknown arithmetic: {fabll.Traits(node).get_obj_raw().get_type_name()}",
            node,
        )

    def visit_AssertStmt(self, node: AST.AssertStmt) -> AddMakeChildAction:
        comparison_expression = node.get_comparison()
        comparison_clauses = comparison_expression.get_comparison_clauses()
        (root_comparison_clause, *_) = comparison_clauses

        lhs_refpath = self.to_expression_tree(comparison_expression.get_lhs())
        rhs_refpath = self.to_expression_tree(root_comparison_clause.get_rhs())

        if len(comparison_clauses) > 1:
            self._raise(
                DslNotImplementedError,
                "Assert statement must have exactly one comparison clause (operator)",
                node,
            )
            # TODO: handle multiple clauses

        operator = root_comparison_clause.get_operator()

        rhs_node = fabll.Traits(root_comparison_clause.get_rhs()).get_obj_raw()
        rhs_is_literal = (
            rhs_node.isinstance(AST.Quantity)
            or rhs_node.isinstance(AST.BilateralQuantity)
            or rhs_node.isinstance(AST.BoundedQuantity)
        )

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
                if rhs_is_literal:
                    with downgrade(DeprecatedException):
                        raise DeprecatedException(
                            "`assert x is <literal>` is deprecated. "
                            "Use `assert x within <literal>` instead."
                        )
                    expr_type = F.Expressions.IsSubset
                else:
                    expr_type = F.Expressions.Is
            case _:
                self._raise(
                    DslSyntaxError, f"Unknown comparison operator: {operator}", node
                )

        # Generate unique identifier for this assertion to avoid collisions
        # when multiple assertions target the same LHS
        expr_id = next(self._expr_counter)

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
            source_chunk_node=node.source.get(),
        )

    def visit_Quantity(
        self, node: AST.Quantity
    ) -> tuple["fabll._ChildField[F.Literals.Numbers]", type[fabll.Node]]:
        unit_t = self._decode_unit(node)
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
                self._raise(
                    DslSyntaxError, f"Unsupported binary operator: {operator}", node
                )

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
        return self.visit(node.get_expression().switch_cast())

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
                unit_t = self._decode_unit(node.end.get())
            case [_, None]:
                unit_t = self._decode_unit(node.start.get())
            case [_, _] if start_unit_symbol != end_unit_symbol:
                unit_t = self._decode_unit(node.start.get())
                end_unit_t = self._decode_unit(node.end.get())

                unit_info = F.Units.extract_unit_info(unit_t)
                end_unit_info = F.Units.extract_unit_info(end_unit_t)
                if not unit_info.is_commensurable_with(end_unit_info):
                    self._raise(
                        DslTypeError,
                        "Bounded quantity start and end units must be commensurable",
                        node,
                    )
                end_value = unit_info.convert_value(end_value, end_unit_info)
            case [_, _]:
                unit_t = self._decode_unit(node.start.get())
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

        match [quantity_unit_symbol, tol_unit_symbol]:
            case [None, None]:
                rel = False
                unit_t = F.Units.Dimensionless
            case [None, F.Units.PERCENT_SYMBOL]:
                rel = True
                unit_t = F.Units.Dimensionless
            case [_, F.Units.PERCENT_SYMBOL]:
                rel = True
                unit_t = self._decode_unit(node.quantity.get())
            case [_, None]:
                rel = False
                unit_t = self._decode_unit(node.quantity.get())
            case [None, _]:
                rel = False
                unit_t = self._decode_unit(node.tolerance.get())
            case [_, _] if quantity_unit_symbol == tol_unit_symbol:
                rel = False
                unit_t = self._decode_unit(node.quantity.get())
            case [_, _]:
                rel = False
                unit_t = self._decode_unit(node.quantity.get())
                tol_unit_t = self._decode_unit(node.tolerance.get())

                q_info = F.Units.extract_unit_info(unit_t)
                tol_info = F.Units.extract_unit_info(tol_unit_t)

                try:
                    tol_value = q_info.convert_value(tol_value, tol_info)
                except UnitsNotCommensurableError:
                    self._raise(
                        DslTypeError,
                        f"Tolerance unit `{tol_unit_symbol}` is not commensurable "
                        f"with quantity unit `{quantity_unit_symbol}`",
                        node,
                    )
            case _:
                self._raise(
                    DslSyntaxError, "Unexpected quantity and tolerance units", node
                )

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
                self._raise(DslSyntaxError, "Pin declaration has no label", node)

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
        # and reference overrides (e.g., reference_shim -> trait pointer deref)
        lhs_link_path = ReferenceOverrideRegistry.transform_link_path(
            LinkPath(list(lhs_path.identifiers()))
        )
        rhs_link_path = ReferenceOverrideRegistry.transform_link_path(
            LinkPath(list(rhs_path.identifiers()))
        )

        link_action = AddMakeLinkAction(
            lhs_path=lhs_link_path,
            rhs_path=rhs_link_path,
            source_chunk_node=node.source.get(),
        )
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

        self._state.external_type_refs.append(
            (new_type_ref, import_ref, node, self._traceback_stack.get_frames())
        )
        self._state.pending_retypes.append(
            PendingRetype(
                containing_type=type_node,
                target_path=target_path,
                new_type_ref=new_type_ref,
                source_order=len(self._state.pending_retypes),
                source_node=node,
            )
        )

        return NoOpAction()

    def visit_DeclarationStmt(self, node: AST.DeclarationStmt):
        unit_symbol = node.unit_symbol.get().symbol.get().get_single()
        try:
            unit_t = F.Units.decode_symbol(self._graph, self._tg, not_none(unit_symbol))
        except F.Units.UnitNotFoundError as e:
            self._raise(DslValueError, str(e), node)
        target_path = self.visit_FieldRef(node.get_field_ref())
        return ActionsFactory.parameter_actions(
            target_path=target_path,
            param_child=F.Parameters.NumericParameter.MakeChild(unit=unit_t),
            constraint_operand=None,
            constraint_expr=self._type_stack.constraint_expr,
            source_chunk_node=node.source.get(),
        )

    def _field_path_to_link_path(self, field_path: FieldPath) -> LinkPath:
        """
        Convert a FieldPath to LinkPath with reference override transformations applied.

        This applies transformations like `reference_shim` -> trait pointer dereference
        so that virtual fields can be used in connections.
        """
        return ReferenceOverrideRegistry.transform_link_path(
            LinkPath(list(field_path.identifiers()))
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
                raise DslRichException(
                    message="Only one connection direction per statement allowed",
                    original=DslException(
                        "Only one connection direction per statement allowed"
                    ),
                    source_node=node,
                )

        lhs_node = fabll.Traits(lhs).get_obj_raw()
        lhs_base_path, lhs_actions = self._resolve_connectable_with_path(lhs_node)
        lhs_link_path = self._field_path_to_link_path(lhs_base_path)

        if nested_rhs := rhs.try_cast(t=AST.DirectedConnectStmt):
            nested_lhs = nested_rhs.get_lhs()
            nested_lhs_node = fabll.Traits(nested_lhs).get_obj_raw()
            middle_base_path, middle_actions = self._resolve_connectable_with_path(
                nested_lhs_node
            )
            middle_link_path = self._field_path_to_link_path(middle_base_path)

            link_action = ActionsFactory.directed_link_action(
                lhs_link_path,
                middle_link_path,
                node.get_direction(),
                source_chunk_node=node.source.get(),
            )
            nested_actions = self.visit_DirectedConnectStmt(nested_rhs)

            return [*lhs_actions, *middle_actions, link_action, *nested_actions]

        rhs_node = fabll.Traits(rhs).get_obj_raw()
        rhs_base_path, rhs_actions = self._resolve_connectable_with_path(rhs_node)
        rhs_link_path = self._field_path_to_link_path(rhs_base_path)

        link_action = ActionsFactory.directed_link_action(
            lhs_link_path,
            rhs_link_path,
            node.get_direction(),
            source_chunk_node=node.source.get(),
        )
        return [*lhs_actions, *rhs_actions, link_action]

    def _select_elements(
        self, iterable_field: AST.IterableFieldRef, sequence_elements: list[FieldPath]
    ) -> list[FieldPath]:
        start_idx, stop_idx, step_idx = iterable_field.slice.get().get_values()

        if step_idx == 0:
            self._raise(DslValueError, "Slice step cannot be zero")

        return (
            sequence_elements
            if (start_idx is None and stop_idx is None and step_idx is None)
            else sequence_elements[slice(start_idx, stop_idx, step_idx)]
        )

    def visit_ForStmt(self, node: AST.ForStmt):
        def validate_stmts(stmts: list[fabll.Node]) -> None:
            def error(stmt_node: fabll.Node) -> None:
                source = self.get_source_chunk(stmt_node.instance)
                source_text = source.get_text().split(" ")[0] if source else ""
                self._raise(
                    DslSyntaxError,
                    (f"Invalid/Unsupported statement in for loop: {source_text}"),
                    node,
                )

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
            self._raise(
                DslImportError,
                f"Trait `{trait_type_name}` must be imported before use",
                node,
            )

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
                self._raise(
                    DslImportError,
                    f"External trait `{trait_type_name}` not supported",
                    node,
                )

            if not fabll.Traits.is_trait_type(trait_fabll_type):
                self._raise(
                    DslTypeError, f"`{trait_type_name}` is not a valid trait", node
                )

            return ActionsFactory.trait_from_field(
                ActionsFactory.trait_field(trait_fabll_type, template_args),
                target_path_list,
                source_chunk_node=node.source.get(),
            )

    @staticmethod
    def get_source_chunk(
        type_graph_node: graph.BoundNode,
    ) -> AST.SourceChunk | None:
        """
        Get corresponding SourceChunk for a given node in the typegraph.
        """
        import faebryk.library._F as F

        source_chunk_bnode = None
        if fabll.Node(type_graph_node).isinstance(AST.SourceChunk):
            source_chunk_bnode = type_graph_node
        if source_chunk_bnode is None:
            source_chunk_bnode = fbrk.EdgePointer.get_pointed_node_by_identifier(
                bound_node=type_graph_node,
                identifier=AnyAtoBlock._source_identifier,
            )
        if source_chunk_bnode is None:
            # Check for instance-level has_source_chunk trait
            node = fabll.Node.bind_instance(type_graph_node)
            if node.has_trait(F.has_source_chunk):
                trait = node.get_trait(F.has_source_chunk)
                source_chunk_bnode = trait.get_source_chunk_node()
        if source_chunk_bnode is None:
            source_chunk_bnode = fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=type_graph_node,
                child_identifier="source",
            )
        if source_chunk_bnode is None:
            return None
        return AST.SourceChunk.bind_instance(source_chunk_bnode)

    @staticmethod
    def get_source_chunk_for_connection(
        source_node: graph.BoundNode,
        target_node: graph.BoundNode,
        tg: fbrk.TypeGraph,
    ) -> AST.SourceChunk | None:
        """
        Find the source chunk for an EdgeInterfaceConnection between two nodes.

        Strategy:
        1. Find the common ancestor of both nodes
        2. Get the type node for the common ancestor
        3. Get all MakeLink nodes from that type
        4. Find the MakeLink whose lhs_path and rhs_path match the relative paths
           - First try exact match
           - Then try prefix match (for bridge connects where actual connection
             is between children of the declared endpoints)
        5. Return the source chunk from that MakeLink
        """
        from faebryk.library.can_bridge import strip_bridge_path_suffix

        source_py = fabll.Node.bind_instance(source_node)
        target_py = fabll.Node.bind_instance(target_node)

        source_hierarchy = source_py.get_hierarchy()
        target_hierarchy = target_py.get_hierarchy()
        common_len = 0
        for i in range(min(len(source_hierarchy), len(target_hierarchy))):
            if not source_hierarchy[i][0].is_same(target_hierarchy[i][0]):
                break
            common_len = i + 1
        if common_len == 0:
            return None
        common_ancestors = [node for node, _name in source_hierarchy[:common_len]]

        edge_tid = fbrk.EdgeInterfaceConnection.get_tid()

        def is_prefix_or_equal(prefix: list[str], full_path: list[str]) -> bool:
            if len(prefix) > len(full_path):
                return False
            return full_path[: len(prefix)] == prefix

        _logger = get_logger(__name__)

        # Track the global best prefix match across all ancestors
        # We only use prefix matches as a fallback if no exact match is found
        # Initialize score to 0 so only actual matches (score > 0) are recorded
        global_best_prefix_match: tuple["AST.SourceChunk | None", int] = (None, 0)

        for ancestor in reversed(common_ancestors):
            source_path = source_py.get_path_from_ancestor(ancestor)
            target_path = target_py.get_path_from_ancestor(ancestor)

            _logger.debug(
                "Searching ancestor %s: source_path=%s, target_path=%s",
                ancestor.get_full_name(),
                source_path,
                target_path,
            )

            if not source_path and not target_path:
                continue

            ancestor_type_edge = fbrk.EdgeType.get_type_edge(
                bound_node=ancestor.instance
            )
            if ancestor_type_edge is None:
                _logger.debug("  No type edge for ancestor")
                continue
            ancestor_type = ancestor.instance.g().bind(
                node=fbrk.EdgeType.get_type_node(edge=ancestor_type_edge.edge())
            )

            try:
                make_links = tg.collect_make_links(type_node=ancestor_type)
            except ValueError as e:
                _logger.debug("  Failed to collect make_links: %s", e)
                continue

            _logger.debug("  Found %d make_links", len(make_links))

            for make_link_node, lhs_tuple, rhs_tuple in make_links:
                edge_type_attr = make_link_node.node().get_attr(key="edge_type")
                if edge_type_attr is None or edge_type_attr != edge_tid:
                    continue

                lhs_path = strip_bridge_path_suffix(list(lhs_tuple))
                rhs_path = strip_bridge_path_suffix(list(rhs_tuple))

                _logger.debug(
                    "    MakeLink: lhs=%s, rhs=%s (looking for %s -> %s)",
                    lhs_path,
                    rhs_path,
                    source_path,
                    target_path,
                )

                if not lhs_path and not rhs_path:
                    continue

                if (lhs_path == source_path and rhs_path == target_path) or (
                    lhs_path == target_path and rhs_path == source_path
                ):
                    _logger.debug("    EXACT MATCH! make_link_node=%s", make_link_node)
                    chunk = ASTVisitor.get_source_chunk(make_link_node)
                    _logger.debug("    get_source_chunk returned: %s", chunk)
                    return chunk

                match_score = 0

                if is_prefix_or_equal(lhs_path, source_path) and is_prefix_or_equal(
                    rhs_path, target_path
                ):
                    match_score = len(lhs_path) + len(rhs_path)

                if is_prefix_or_equal(lhs_path, target_path) and is_prefix_or_equal(
                    rhs_path, source_path
                ):
                    score = len(lhs_path) + len(rhs_path)
                    match_score = max(match_score, score)

                # Only record if there's an actual prefix match (score > 0)
                if match_score > 0 and match_score > global_best_prefix_match[1]:
                    _logger.debug("    Prefix match score: %d", match_score)
                    global_best_prefix_match = (
                        ASTVisitor.get_source_chunk(make_link_node),
                        match_score,
                    )

        _logger.debug("No exact match found, returning best prefix match as fallback")
        return global_best_prefix_match[0]

    @staticmethod
    def _extract_filepath_from_source_node(
        source_node: fabll.Node | None,
    ) -> Path | None:
        if source_node is None:
            return None

        source_chunk_node = ASTVisitor.get_source_chunk(source_node.instance)
        if source_chunk_node is None:
            return None

        filepath_str = source_chunk_node.get_path()
        if filepath_str:
            return Path(filepath_str)
        return None


class TestSourceChunkForConnection:
    """
    Tests for get_source_chunk_for_connection to ensure correct source location
    tracking for ERC errors.
    """

    @staticmethod
    def test_exact_match_at_outer_ancestor_preferred_over_prefix_at_inner():
        """
        Test that an exact match at an outer ancestor takes precedence over
        a prefix match at an inner ancestor.

        Setup:
        - InnerModule has a connection: inner_pin ~ inner_power.lv
        - OuterModule wraps InnerModule and has: outer_pin ~ outer_power.lv
        - App has: outer.model.inner_pin ~ outer.outer_power.lv

        The connection in App should be found as an exact match at the App level,
        not confused with the prefix match at OuterModule level.
        """
        import textwrap

        from atopile.compiler.build import Linker, StdlibRegistry, build_source

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)

        # Build ato source with nested modules
        result = build_source(
            g=g,
            tg=tg,
            source=textwrap.dedent(
                """
                import Electrical
                import ElectricPower

                module InnerModule:
                    inner_power = new ElectricPower
                    inner_pin = new Electrical
                    # Connection at inner level (line 8)
                    inner_pin ~ inner_power.hv

                module OuterModule:
                    model = new InnerModule
                    outer_power = new ElectricPower
                    outer_pin = new Electrical
                    # Connection at outer level - similar pattern (line 15)
                    outer_pin ~ outer_power.lv

                module App:
                    outer = new OuterModule
                    # This connection should be found (line 20)
                    outer.model.inner_pin ~ outer.outer_power.lv
                """
            ),
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        # Instantiate the App
        app_type = result.state.type_roots["App"]
        app_instance = tg.instantiate_node(type_node=app_type, attributes={})

        # Get the connected nodes
        outer_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance, child_identifier="outer"
        )
        assert outer_node is not None

        model_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=outer_node, child_identifier="model"
        )
        assert model_node is not None

        inner_pin_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=model_node, child_identifier="inner_pin"
        )
        assert inner_pin_node is not None

        outer_power_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=outer_node, child_identifier="outer_power"
        )
        assert outer_power_node is not None

        lv_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=outer_power_node, child_identifier="lv"
        )
        assert lv_node is not None

        # Get source chunk for the connection
        source_chunk = ASTVisitor.get_source_chunk_for_connection(
            inner_pin_node, lv_node, tg
        )

        # The source should point to line 21 (the App connection),
        # not line 16 (the OuterModule connection which could be a prefix match)
        # Note: line numbers are 1-indexed and include the leading newline from dedent
        assert source_chunk is not None
        loc = source_chunk.loc.get()
        start_line = loc.get_start_line()
        # Line 21 is: outer.model.inner_pin ~ outer.outer_power.lv
        assert start_line == 21, (
            f"Expected source at line 21 (App connection), got line {start_line}"
        )

    @staticmethod
    def test_best_prefix_match_returned_when_no_exact_match():
        """
        Test that when there's no exact match, the best prefix match is returned.

        Setup:
        - InnerModule has interface connections that propagate
        - OuterModule has a connection that creates a prefix match
        - No exact match exists for the specific edge we're querying

        The best (highest scoring) prefix match should be returned.
        """
        import textwrap

        from atopile.compiler.build import Linker, StdlibRegistry, build_source

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)

        # Build ato source where connections propagate through interfaces
        result = build_source(
            g=g,
            tg=tg,
            source=textwrap.dedent(
                """
                import Electrical
                import ElectricPower

                module InnerModule:
                    power = new ElectricPower
                    pin_a = new Electrical
                    pin_b = new Electrical
                    # Connection at line 9
                    pin_a ~ power.hv

                module App:
                    inner = new InnerModule
                    external_power = new ElectricPower
                    # Connect powers - this creates transitive connections (line 14)
                    inner.power ~ external_power
                """
            ),
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        # Instantiate the App
        app_type = result.state.type_roots["App"]
        app_instance = tg.instantiate_node(type_node=app_type, attributes={})

        # Get nodes - the power interface connection creates transitive edges
        inner_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance, child_identifier="inner"
        )
        assert inner_node is not None

        inner_power_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=inner_node, child_identifier="power"
        )
        assert inner_power_node is not None

        inner_power_hv = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=inner_power_node, child_identifier="hv"
        )
        assert inner_power_hv is not None

        external_power_node = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance, child_identifier="external_power"
        )
        assert external_power_node is not None

        external_power_hv = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=external_power_node, child_identifier="hv"
        )
        assert external_power_hv is not None

        # Query for a connection that was created transitively
        # (inner.power.hv ~ external_power.hv via the power ~ power connection)
        source_chunk = ASTVisitor.get_source_chunk_for_connection(
            inner_power_hv, external_power_hv, tg
        )

        # Should find the best prefix match - the power ~ power connection at line 14
        # or the inner connection at line 9, depending on which scores higher
        # The key point is that SOME source chunk is returned (not None)
        # when prefix matching is needed
        assert source_chunk is not None, (
            "Expected a prefix match to be returned when no exact match exists"
        )

    @staticmethod
    def test_no_match_returns_none():
        """
        Test that when querying for a non-existent connection, None is returned
        even if there are other unrelated connections in the module.

        This ensures we don't incorrectly return the source chunk of an
        unrelated MakeLink just because it exists in the module.
        """
        import textwrap

        from atopile.compiler.build import Linker, StdlibRegistry, build_source

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)

        # Build ato source with connections, but query for unconnected nodes
        result = build_source(
            g=g,
            tg=tg,
            source=textwrap.dedent(
                """
                import Electrical

                module App:
                    # These pins ARE connected
                    connected_a = new Electrical
                    connected_b = new Electrical
                    connected_a ~ connected_b

                    # These pins are NOT connected
                    unconnected_a = new Electrical
                    unconnected_b = new Electrical
                """
            ),
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        # Instantiate the App
        app_type = result.state.type_roots["App"]
        app_instance = tg.instantiate_node(type_node=app_type, attributes={})

        # Get the unconnected nodes
        unconnected_a = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance, child_identifier="unconnected_a"
        )
        assert unconnected_a is not None

        unconnected_b = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance, child_identifier="unconnected_b"
        )
        assert unconnected_b is not None

        # Query for a connection between the unconnected nodes
        # There IS a MakeLink in App (connected_a ~ connected_b), but it
        # should NOT be returned since it doesn't match our query
        source_chunk = ASTVisitor.get_source_chunk_for_connection(
            unconnected_a, unconnected_b, tg
        )

        # Should return None - the connected_a ~ connected_b MakeLink
        # should not be returned just because it exists in the same module
        assert source_chunk is None, (
            "Expected None when querying for unconnected nodes, even if "
            "other connections exist in the module"
        )
