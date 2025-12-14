import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from rich import print

import atopile.compiler.ast_types as AST
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.gentypegraph import (
    AddMakeChildAction,
    AddMakeLinkAction,
    AddTraitAction,
    FieldPath,
    ImportRef,
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
from faebryk.libs.util import cast_assert, not_none

_Unit = type[fabll.NodeT]
_Quantity = tuple[float, str]
_Range = tuple[float, float] | tuple[_Quantity, _Quantity]

logger = logging.getLogger(__name__)

# FIXME: needs expanding
STDLIB_ALLOWLIST: set[type[fabll.Node]] = (
    # Modules
    {
        F.Capacitor,
        F.Electrical,
        F.ElectricPower,
        F.Resistor,
        F.ResistorVoltageDivider,
        F.LED,
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
        F.has_net_name_suggestion,
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
    type_roots_fabll: dict[str, type[fabll.Node]]


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
        self._stack: list[graph.BoundNode] = []
        self._fabll_type_stack: list[type[fabll.Node]] = []
        self._g = g
        self._tg = tg
        self._state = state

    @contextmanager
    def enter(
        self, type_node: graph.BoundNode, fabll_type: type[fabll.Node]
    ) -> Generator[None, None, None]:
        self._stack.append(type_node)
        self._fabll_type_stack.append(fabll_type)
        try:
            yield
        finally:
            self._stack.pop()

    def current(self) -> graph.BoundNode:
        if not self._stack:
            raise DslException("Type context is not available")
        return self._stack[-1]

    def current_fabll(self) -> type[fabll.Node]:
        if not self._fabll_type_stack:
            raise DslException("fabll type context is not available")
        return self._fabll_type_stack[-1]

    def apply_action(self, action) -> None:
        match action:
            case AddMakeChildAction() as action:
                self._add_child(type_node=self.current(), action=action)
            case AddMakeLinkAction() as action:
                self._add_link(type_node=self.current(), action=action)
            case AddTraitAction() as action:
                self._add_trait(type_node=self.current(), action=action)
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
        return self._ensure_field_path(
            type_node=self.current(), field_path=path, validate=validate
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
        self, type_node: graph.BoundNode, action: AddMakeChildAction
    ) -> None:
        child_spec = action.child_spec
        symbol = child_spec.symbol

        # New fabll way of adding child fields
        if action.child_field is not None:
            # Add the child field to fabll type attributes
            self._add_child_field(
                type_node=type_node,
                action=action.child_field,
                identifier=str(action.target_path),
            )

            # Get the fabll node and bound node of current type
            assert self.current_fabll() is not None
            tnbtg = fabll.TypeNodeBoundTG(tg=self._tg, t=self.current_fabll())
            app_bnode = (
                self.current_fabll().bind_typegraph(tg=self._tg).get_or_create_type()
            )
            assert isinstance(action.child_field.identifier, str)
            # Execute the child field to create make child nodes on type node
            fabll.Node._exec_field(t=tnbtg, field=action.child_field)

            # Link make child.type reference to the child type node
            make_child = fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=app_bnode,
                child_identifier=action.child_field.identifier,
            )
            assert fabll.Node(not_none(make_child)).get_type_name() == "MakeChild"
            type_reference = self._tg.get_make_child_type_reference(
                make_child=not_none(make_child)
            )
            assert (
                fabll.Node(not_none(type_reference)).get_type_name() == "TypeReference"
            )

        else:  # Old way
            if (parent_reference := action.parent_reference) is None and (
                parent_path := action.parent_path
            ) is not None:
                parent_reference = self._ensure_field_path(
                    type_node=type_node, field_path=parent_path
                )

            if (
                child_type_identifier := child_spec.type_identifier
            ) is None and symbol is not None:
                child_type_identifier = symbol.name

            assert child_type_identifier is not None

            make_child = self._tg.add_make_child_deferred(
                type_node=type_node,
                child_type_identifier=child_type_identifier,
                identifier=action.target_path.leaf.identifier,
                node_attributes=None,
                mount_reference=parent_reference,
            )

            type_reference = not_none(
                self._tg.get_make_child_type_reference(make_child=make_child)
            )

        # Link now (local) or later (external)
        if symbol is not None and symbol.import_ref:
            # External imports: defer linking to build phase
            self._state.external_type_refs.append((type_reference, symbol.import_ref))
        else:
            # Local types: link immediately
            if (
                target := symbol.type_node
                if symbol is not None
                else child_spec.type_node
            ) is None:
                raise DslException(
                    f"Type `{child_type_identifier}` is not defined in scope"
                )

            fbrk.Linker.link_type_reference(
                g=self._g, type_reference=type_reference, target_type_node=target
            )

    # TODO FIXME: no type checking for is_interface trait on connected nodes.
    # We should use the fabll connect_to method for this.
    def _add_link(self, type_node: graph.BoundNode, action: AddMakeLinkAction) -> None:
        self._tg.add_make_link(
            type_node=type_node,
            lhs_reference=action.lhs_ref,
            rhs_reference=action.rhs_ref,
            edge_attributes=action.edge
            or fbrk.EdgeInterfaceConnection.build(shallow=False),
        )

    def _add_trait(self, type_node: graph.BoundNode, action: AddTraitAction) -> None:
        target_reference = action.target_reference or type_node
        trait_identifier = f"_trait_{action.trait_type_identifier}"

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
                f"Trait `{action.trait_type_identifier}` has no type node or import ref"
            )

        self._tg.add_make_link(
            type_node=type_node,
            lhs_reference=target_reference,
            rhs_reference=make_child,
            edge_attributes=fbrk.EdgeTrait.build(),
        )

        if action.template_args:
            for param_name, value in action.template_args.items():
                # TODO: Use fabll MakeChild_ConstrainToLiteral once available
                # param_ref = [trait_identifier, param_name]
                # constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(...)
                logger.info(
                    f"Template arg {param_name}={value} for trait "
                    f"{action.trait_type_identifier} (constraint pending)"
                )

    def _add_child_field(
        self, type_node: graph.BoundNode, action: fabll._ChildField, identifier: str
    ) -> None:
        # ALT self.AppNode.testing = fabll._ChildField(F.Electrical)
        if self.current_fabll() is not None:
            self.current_fabll()._handle_cls_attr(str(identifier), action)


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
            type_roots_fabll={},
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

        match node.get_block_type():
            case AST.BlockDefinition.BlockType.MODULE:

                class _Module(fabll.Node):
                    is_ato_block = fabll.Traits.MakeEdge(is_ato_block.MakeChild())
                    is_ato_module = fabll.Traits.MakeEdge(is_ato_module.MakeChild())
                    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

                _Block = _Module

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    is_ato_block = fabll.Traits.MakeEdge(is_ato_block.MakeChild())
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

        _Block.__name__ = module_name
        _Block.__qualname__ = module_name

        type_node = _Block.bind_typegraph(self._type_graph).get_or_create_type()
        self._state.type_roots[module_name] = type_node

        fbrk.EdgePointer.point_to(
            bound_node=type_node,
            target_node=node.instance.node(),
            identifier=AnyAtoBlock._definition_identifier,
            order=None,
        )

        # New fabll approach
        self._state.type_roots_fabll[module_name] = _Block

        with self._scope_stack.enter():
            with self._type_stack.enter(type_node, _Block):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))

        self._scope_stack.add_symbol(Symbol(name=module_name, type_node=type_node))

    def visit_PassStmt(self, node: AST.PassStmt):
        return NoOpAction()

    def visit_AstString(self, node: AST.AstString):
        return node.get_text()

    def visit_StringStmt(self, node: AST.StringStmt):
        # TODO: add docstring trait to preceding node
        return NoOpAction()

    def visit_SignaldefStmt(self, node: AST.SignaldefStmt):
        (signal_name,) = node.name.get().get_values()
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=signal_name),))

        if self._scope_stack.has_field(target_path):
            raise DslException(
                f"Signal `{signal_name}` is already defined in this scope"
            )

        self._scope_stack.add_field(target_path)

        return AddMakeChildAction(
            target_path=target_path,
            child_spec=NewChildSpec(
                type_identifier=F.Electrical.__name__,
                type_node=self._electrical_type,
            ),
            parent_reference=None,
            parent_path=None,
        )

    def _create_pin_type(self, pin_label: str) -> graph.BoundNode:
        import re

        regex = f"^{re.escape(str(pin_label))}$"

        class _Pin(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            _lead = is_lead.MakeChild()
            _lead_trait = fabll.Traits.MakeEdge(_lead)
            _pad_attach = can_attach_to_pad_by_name.MakeChild(regex)
            _lead.add_dependant(fabll.Traits.MakeEdge(_pad_attach, [_lead]))

        type_identifier = self._make_type_identifier(f"__pin_{pin_label}__")
        _Pin.__name__ = type_identifier
        _Pin.__qualname__ = type_identifier

        return _Pin.bind_typegraph(self._type_graph).get_or_create_type()

    def visit_PinDeclaration(self, node: AST.PinDeclaration):
        pin_label = node.get_label()
        if pin_label is None:
            raise DslException("Pin declaration has no label")

        if isinstance(pin_label, float) and pin_label.is_integer():
            pin_label_str = str(int(pin_label))
        else:
            pin_label_str = str(pin_label)

        # Pin labels can be numbers, so prefix with "pin_" for valid identifier
        identifier = f"pin_{pin_label_str}"
        target_path = FieldPath(segments=(FieldPath.Segment(identifier=identifier),))

        if self._scope_stack.has_field(target_path):
            raise DslException(
                f"Pin `{pin_label_str}` is already defined in this scope"
            )

        self._scope_stack.add_field(target_path)
        pin_type = self._create_pin_type(pin_label_str)

        return AddMakeChildAction(
            target_path=target_path,
            child_spec=NewChildSpec(
                type_identifier=f"__pin_{pin_label_str}__",
                type_node=pin_type,
            ),
            parent_reference=None,
            parent_path=None,
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
                    pointer_members = self._type_graph.collect_pointer_members(
                        type_node=self._type_stack.current(),
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
                target_path=target_path,
                child_spec=new_spec,
                parent_reference=parent_reference,
                parent_path=parent_path,
                child_field=fabll._ChildField(nodetype=new_spec.type_identifier),
            )

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

    def _ensure_ref(self, path: FieldPath) -> graph.BoundNode:
        (root, *_) = path.segments
        root_path = FieldPath(segments=(root,))

        if not self._scope_stack.has_field(root_path):
            raise DslException(f"Field `{root_path}` is not defined in scope")

        return self._type_stack.resolve_reference(path, validate=False)

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

            if not self._scope_stack.has_field(parent_path):
                raise DslException(f"Field `{parent_path}` is not defined in scope")

            parent_reference = self._type_stack.resolve_reference(parent_path)

        match assignable:
            case NewChildSpec() as new_spec:
                if self._scope_stack.has_field(target_path):
                    raise DslException(
                        f"Field `{target_path}` is already defined in this scope"
                    )
                return self._handle_new_child(
                    target_path, new_spec, parent_reference, parent_path
                )
            case (float() as value, str() as unit):
                ## fabll method
                is_expr = AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,
                            FieldPath.Segment("resistance_is_number"),
                        )
                    ),
                    child_spec=NewChildSpec(
                        symbol=Symbol(
                            name="Is",
                            import_ref=ImportRef(name="Is", path=None),
                            type_node=node.instance,
                        ),
                        type_node=node.instance,
                    ),
                    child_field=F.Literals.Numbers.MakeChild_ConstrainToSingleton(
                        param_ref=["r1", "resistance"],
                        value=value,
                        unit=unit,
                    ),
                    parent_reference=parent_reference,
                    parent_path=parent_path,
                )
            case str() as value:
                is_expr = AddMakeChildAction(
                    target_path=FieldPath(
                        segments=(
                            *target_path.segments,
                            FieldPath.Segment("string_is_string"),
                        )
                    ),
                    child_spec=NewChildSpec(
                        symbol=Symbol(
                            name="Is",
                            import_ref=ImportRef(name="Is", path=None),
                            type_node=node.instance,
                        ),
                    ),
                    child_field=F.Literals.Strings.MakeChild_ConstrainToLiteralSubset(
                        ["atomic_part", "footprint_"],
                        value,
                    ),
                    parent_reference=parent_reference,
                    parent_path=parent_path,
                )
                return is_expr
            case _:
                raise NotImplementedError(f"Unhandled assignable type: {assignable}")

    def visit_Quantity(self, node: AST.Quantity) -> _Quantity:
        return (node.get_value(), node.get_unit())

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
        if connectable_node.isinstance(AST.FieldRef):
            path = self.visit_FieldRef(connectable_node.cast(t=AST.FieldRef))
            (root, *_) = path.segments
            root_path = FieldPath(segments=(root,))

            if not self._scope_stack.has_field(root_path):
                raise DslException(f"Field `{root_path}` is not defined in scope")

            ref = self._type_stack.resolve_reference(path, validate=False)
            return ref, path

        elif connectable_node.isinstance(AST.SignaldefStmt):
            signal_node = connectable_node.cast(t=AST.SignaldefStmt)
            (signal_name,) = signal_node.name.get().get_values()
            target_path = FieldPath(
                segments=(FieldPath.Segment(identifier=signal_name),)
            )

            if not self._scope_stack.has_field(target_path):
                action = self.visit_SignaldefStmt(signal_node)
                self._type_stack.apply_action(action)

            ref = self._type_stack.resolve_reference(target_path, validate=False)
            return ref, target_path

        elif connectable_node.isinstance(AST.PinDeclaration):
            pin_node = connectable_node.cast(t=AST.PinDeclaration)
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

            if not self._scope_stack.has_field(target_path):
                action = self.visit_PinDeclaration(pin_node)
                self._type_stack.apply_action(action)

            ref = self._type_stack.resolve_reference(target_path, validate=False)
            return ref, target_path

        else:
            raise NotImplementedError(
                f"Unhandled connectable type: {connectable_node.get_type_name()}"
            )

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

        if isinstance(rhs, AST.DirectedConnectStmt):
            nested_lhs = rhs.get_lhs()
            nested_lhs_node = fabll.Traits(nested_lhs).get_obj_raw()
            _, middle_base_path = self._resolve_connectable_with_path(nested_lhs_node)

            action = self._add_directed_link(
                lhs_base_path, middle_base_path, node.get_direction()
            )
            self._type_stack.apply_action(action)

            return self.visit_DirectedConnectStmt(rhs)

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

        try:
            return self._type_graph.ensure_child_reference(
                type_node=self._type_stack.current(),
                path=path,
                validate=False,
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
        try:
            pointer_members = self._type_graph.collect_pointer_members(
                type_node=self._type_stack.current(),
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
            if not self._scope_stack.has_field(target_path):
                raise DslException(f"Field `{target_path}` is not defined in scope")
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

        return AddTraitAction(
            trait_type_identifier=trait_type_name,
            trait_type_node=symbol.type_node,
            trait_import_ref=symbol.import_ref,
            target_reference=target_reference,
            template_args=template_args,
        )
