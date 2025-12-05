from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.gentypegraph import (
    AddMakeChildAction,
    AddMakeLinkAction,
    FieldPath,
    ImportRef,
    NewChildSpec,
    ScopeState,
    Symbol,
)
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.linker import Linker
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph, TypeGraphPathError
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView
from faebryk.libs.util import cast_assert, not_none

STDLIB_ALLOWLIST = {
    "Resistor": F.Resistor,
}


@dataclass
class BuildState:
    type_graph: TypeGraph
    type_roots: dict[str, BoundNode]
    external_type_refs: list[tuple[BoundNode, ImportRef]]
    file_path: Path | None


class DslException(Exception):
    """
    Exceptions arising from user's DSL code.
    """


class CompilerException(Exception):
    """
    Exceptions arising from internal compiler failures.
    """


class BlockType(StrEnum):
    MODULE = "module"
    COMPONENT = "component"
    INTERFACE = "interface"


class is_ato_block(fabll.Node):
    """
    Indicates type origin and originating block type (module, component, interface)
    """

    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()
    block_type = F.Literals.EnumsFactory(BlockType).MakeChild(
        *BlockType.__members__.values()
    )

    @classmethod
    def _MakeChild(cls, block_type: BlockType) -> fabll._ChildField[Any]:
        lit = F.Literals.EnumValue.MakeChild(
            name=block_type.name, value=block_type.value
        )
        out = fabll._ChildField(cls)
        out.add_dependant(lit, before=True)
        out.add_dependant(
            F.Expressions.Is.MakeChild_Constrain(
                operands=[[out, cls.block_type], [lit]]
            )
        )
        return out

    @classmethod
    def MakeChild_Module(cls) -> fabll._ChildField[Any]:
        return cls._MakeChild(BlockType.MODULE)

    @classmethod
    def MakeChild_Component(cls) -> fabll._ChildField[Any]:
        return cls._MakeChild(BlockType.COMPONENT)

    @classmethod
    def MakeChild_Interface(cls) -> fabll._ChildField[Any]:
        return cls._MakeChild(BlockType.INTERFACE)


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

        print(f"Added symbol {symbol} to scope")

    def add_field(self, path: FieldPath) -> None:
        current_state = self.current
        if (key := str(path)) in current_state.fields:
            raise DslException(f"Field `{key}` already defined in scope")

        current_state.fields.add(key)

        print(f"Added field {key} to scope")

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
        self, graph: GraphView, type_graph: TypeGraph, state: BuildState
    ) -> None:
        self._stack: list[BoundNode] = []
        self._graph = graph
        self._type_graph = type_graph
        self._state = state

    @contextmanager
    def enter(self, type_node: BoundNode) -> Generator[None, None, None]:
        self._stack.append(type_node)
        try:
            yield
        finally:
            self._stack.pop()

    def current(self) -> BoundNode:
        if not self._stack:
            raise DslException("Type context is not available")
        return self._stack[-1]

    def apply_action(self, action) -> None:
        match action:
            case AddMakeChildAction() as action:
                self._add_child(type_node=self.current(), action=action)
            case AddMakeLinkAction() as action:
                self._add_link(type_node=self.current(), action=action)
            case list() | tuple() as actions:
                for a in actions:
                    self.apply_action(a)
                return
            case None:  # TODO: why would this be None?
                return
            case _:
                raise NotImplementedError(f"Unhandled action: {action}")

    def resolve_reference(self, path: FieldPath, validate: bool = True) -> BoundNode:
        return self._ensure_field_path(
            type_node=self.current(), field_path=path, validate=validate
        )

    @staticmethod
    def _format_path_error(field_path: FieldPath, error: TypeGraphPathError) -> str:
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
        self, type_node: BoundNode, field_path: FieldPath, validate: bool = True
    ) -> BoundNode:
        identifiers = list(field_path.identifiers())
        try:
            return self._type_graph.ensure_child_reference(
                type_node=type_node, path=identifiers, validate=validate
            )
        except TypeGraphPathError as exc:
            raise DslException(self._format_path_error(field_path, exc)) from exc

    def _add_child(self, type_node: BoundNode, action: AddMakeChildAction) -> None:
        if (parent_reference := action.parent_reference) is None and (
            parent_path := action.parent_path
        ) is not None:
            parent_reference = self._ensure_field_path(
                type_node=type_node, field_path=parent_path
            )

        child_spec = action.child_spec
        symbol = child_spec.symbol

        if (
            child_type_identifier := child_spec.type_identifier
        ) is None and symbol is not None:
            child_type_identifier = symbol.name

        assert child_type_identifier is not None

        make_child = self._type_graph.add_make_child(
            type_node=type_node,
            child_type_identifier=child_type_identifier,
            identifier=action.target_path.leaf.identifier,
            node_attributes=None,
            mount_reference=parent_reference,
        )

        type_reference = not_none(
            self._type_graph.get_make_child_type_reference(make_child=make_child)
        )

        if symbol is not None and symbol.import_ref:
            self._state.external_type_refs.append((type_reference, symbol.import_ref))
            return

        if (
            target := symbol.type_node if symbol is not None else child_spec.type_node
        ) is None:
            raise DslException(
                f"Type `{child_type_identifier}` is not defined in scope"
            )

        Linker.link_type_reference(
            g=self._graph, type_reference=type_reference, target_type_node=target
        )

    def _add_link(self, type_node: BoundNode, action: AddMakeLinkAction) -> None:
        self._type_graph.add_make_link(
            type_node=type_node,
            lhs_reference=action.lhs_ref,
            rhs_reference=action.rhs_ref,
            edge_attributes=EdgeInterfaceConnection.build(shallow=False),
        )


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
        self, ast_root: AST.File, graph: GraphView, file_path: Path | None
    ) -> None:
        self._ast_root = ast_root
        self._graph = graph
        self._type_graph = TypeGraph.create(g=graph)
        self._state = BuildState(
            type_graph=self._type_graph,
            type_roots={},
            external_type_refs=[],
            file_path=file_path,
        )

        # TODO: from "system" type graph
        self._pointer_sequence_type = F.Collections.PointerSequence.bind_typegraph(
            self._type_graph
        ).get_or_create_type()
        self._experiments: set[ASTVisitor._Experiment] = set()
        self._scope_stack = _ScopeStack()
        self._type_stack = _TypeContextStack(
            graph=self._graph,
            type_graph=self._type_graph,
            state=self._state,
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

    def build(self) -> BuildState:
        # must start with a File (for now)
        assert self._ast_root.isinstance(AST.File)
        self.visit(self._ast_root)
        return self._state

    def visit(self, node: fabll.Node):
        # TODO: less magic dispatch

        node_type = cast_assert(str, node.get_type_name())
        print(f"Visiting node of type {node_type}")

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
                match pragma_args:
                    case [ASTVisitor._Experiment.BRIDGE_CONNECT]:
                        self.enable_experiment(ASTVisitor._Experiment.BRIDGE_CONNECT)
                    case [ASTVisitor._Experiment.FOR_LOOP]:
                        self.enable_experiment(ASTVisitor._Experiment.FOR_LOOP)
                    case [ASTVisitor._Experiment.TRAITS]:
                        self.enable_experiment(ASTVisitor._Experiment.TRAITS)
                    case [ASTVisitor._Experiment.MODULE_TEMPLATING]:
                        self.enable_experiment(ASTVisitor._Experiment.MODULE_TEMPLATING)
                    case [ASTVisitor._Experiment.INSTANCE_TRAITS]:
                        self.enable_experiment(ASTVisitor._Experiment.INSTANCE_TRAITS)
                    case _:
                        raise DslException(f"Experiment not recognized: `{pragma}`")
            case _:
                raise DslException(f"Pragma function not recognized: `{pragma}`")

    def visit_ImportStmt(self, node: AST.ImportStmt):
        type_ref_name = node.get_type_ref_name()
        path = node.get_path()
        import_ref = ImportRef(name=type_ref_name, path=path)

        if path is None and type_ref_name not in STDLIB_ALLOWLIST:
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
                    is_ato_block = (
                        # TODO: link from other typegraph
                        is_ato_block.MakeChild_Module()
                    )

                _Block = _Module

            case AST.BlockDefinition.BlockType.COMPONENT:

                class _Component(fabll.Node):
                    is_ato_block = is_ato_block.MakeChild_Component()

                _Block = _Component

            case AST.BlockDefinition.BlockType.INTERFACE:

                class _Interface(fabll.Node):
                    is_ato_block = is_ato_block.MakeChild_Interface()

                _Block = _Interface

        _Block.__name__ = module_name
        _Block.__qualname__ = module_name

        type_node = _Block.bind_typegraph(self._type_graph).get_or_create_type()
        self._state.type_roots[module_name] = type_node

        with self._scope_stack.enter():
            with self._type_stack.enter(type_node):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))

        self._scope_stack.add_symbol(Symbol(name=module_name, type_node=type_node))

    def visit_PassStmt(self, node: AST.PassStmt):
        pass

    def visit_StringStmt(self, node: AST.StringStmt):
        # TODO: add docstring trait to preceding node
        pass

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
        parent_reference: BoundNode | None,
        parent_path: FieldPath | None,
    ) -> list[AddMakeChildAction] | AddMakeChildAction:
        self._scope_stack.add_field(target_path)

        if new_spec.count is None:
            # TODO: review
            if target_path.leaf.is_index and parent_path is not None:
                try:
                    pointer_members = self._type_graph.iter_pointer_members(
                        type_node=self._type_stack.current(),
                        container_path=list(parent_path.identifiers()),
                    )
                except TypeGraphPathError as exc:
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

            return AddMakeChildAction(
                target_path=target_path,
                child_spec=new_spec,
                parent_reference=parent_reference,
                parent_path=parent_path,
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

    def visit_Assignment(self, node: AST.Assignment):
        # TODO: broaden assignable support and handle keyed/pin field references

        target_path = self.visit_FieldRef(node.target.get())
        assignable_t = node.assignable.get().get_value()
        assignable = self.visit(fabll.Traits(assignable_t).get_obj_raw())
        print(f"Assignable: {assignable}")

        parent_path: FieldPath | None = None
        parent_reference: BoundNode | None = None

        if target_path.parent_segments:
            parent_path = FieldPath(segments=tuple(target_path.parent_segments))

            if not self._scope_stack.has_field(parent_path):
                raise DslException(f"Field `{parent_path}` is not defined in scope")

            parent_reference = self._type_stack.resolve_reference(parent_path)

        if self._scope_stack.has_field(target_path):
            raise DslException(
                f"Field `{target_path}` is already defined in this scope"
            )

        match assignable:
            case NewChildSpec() as new_spec:
                return self._handle_new_child(
                    target_path, new_spec, parent_reference, parent_path
                )
            case _:
                raise NotImplementedError(f"Unhandled assignable type: {assignable}")

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

    def visit_ConnectStmt(self, node: AST.ConnectStmt):
        lhs, rhs = node.get_lhs(), node.get_rhs()
        lhs_node, rhs_node = (
            fabll.Traits(lhs).get_obj_raw(),
            fabll.Traits(rhs).get_obj_raw(),
        )

        # TODO: handle connectables other than field refs
        if not lhs_node.isinstance(AST.FieldRef):
            raise NotImplementedError("Unhandled connectable type for LHS")
        if not rhs_node.isinstance(AST.FieldRef):
            raise NotImplementedError("Unhandled connectable type for RHS")

        lhs_path = self.visit_FieldRef(lhs_node.cast(t=AST.FieldRef))
        rhs_path = self.visit_FieldRef(rhs_node.cast(t=AST.FieldRef))

        def _ensure_reference(path: FieldPath) -> BoundNode:
            (root, *_) = path.segments
            root_path = FieldPath(segments=(root,))

            if not self._scope_stack.has_field(root_path):
                raise DslException(f"Field `{root_path}` is not defined in scope")

            return self._type_stack.resolve_reference(path, validate=False)

        lhs_ref = _ensure_reference(lhs_path)
        rhs_ref = _ensure_reference(rhs_path)

        return AddMakeLinkAction(lhs_ref=lhs_ref, rhs_ref=rhs_ref)

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
            pointer_members = self._type_graph.iter_pointer_members(
                type_node=self._type_stack.current(),
                container_path=list(container_path.identifiers()),
            )
        except TypeGraphPathError as exc:
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
            container_path = self.visit_FieldRef(iterable_field.field.get())
            member_paths = self._pointer_member_paths(container_path)

            selected = self._select_elements(iterable_field, member_paths)
            item_paths = list(selected)
        else:
            raise DslException("Unexpected iterable type")

        (loop_var,) = node.target.get().get_values()
        # Execute body for each item by aliasing the loop var to the item's path
        for item_path in item_paths:
            with self._scope_stack.temporary_alias(loop_var, item_path):
                for stmt in node.scope.get().stmts.get().as_list():
                    self._type_stack.apply_action(self.visit(stmt))
