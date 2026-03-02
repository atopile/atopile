"""
Deferred execution phase for the ato compiler.

After the AST visitor has built the type graph and the linker has resolved
all type references, this module executes deferred operations that require
fully linked types:

1. Inheritance resolution - copies parent structure into derived types
2. Retype operations - updates type references for `target -> NewType` statements
3. For-loop execution - expands deferred for-loops (delegated to visitor)
"""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
from atopile.compiler import DslException, DslRichException
from atopile.compiler.ast_visitor import BuildState
from atopile.compiler.gentypegraph import ImportRef
from faebryk.libs.util import DAG

if TYPE_CHECKING:
    from atopile.compiler.ast_visitor import ASTVisitor


class StdlibLookup(Protocol):
    """Protocol for stdlib type lookup (matches StdlibRegistry interface)."""

    def get(self, name: str) -> graph.BoundNode: ...
    def __contains__(self, name: str) -> bool: ...


class FileImportLookup(Protocol):
    """Protocol for looking up types from linked file imports."""

    def resolve(
        self, path: str, name: str, base_file: Path | None
    ) -> graph.BoundNode | None: ...


class DeferredExecutor:
    """
    Executes deferred operations after linking is complete.

    This is phase 2 of compilation, running after:
    - Phase 1a: AST visiting (builds type graph structure)
    - Phase 1b: Linking (resolves type references)

    And before:
    - Phase 3: Instantiation
    """

    def __init__(
        self,
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        state: BuildState,
        visitor: "ASTVisitor",
        stdlib: StdlibLookup | None = None,
        file_imports: FileImportLookup | None = None,
    ) -> None:
        self._g = g
        self._tg = tg
        self._pending_inheritance = state.pending_inheritance
        self._pending_retypes = state.pending_retypes
        self._type_roots = state.type_roots
        self._base_file = state.file_path
        self._visitor = visitor
        self._stdlib = stdlib
        self._file_imports = file_imports

    def execute(self) -> None:
        """Execute all deferred operations in order."""
        self._resolve_inheritance()
        self._execute_retypes()
        self._visitor._execute_for_loops()
        for type_node in self._type_roots.values():
            self._tg.mark_constructable(type_node=type_node)

    def _resolve_inheritance(self) -> None:
        """
        Resolve inheritance by copying parent structure into derived types.

        Processes base types before derived types using topological sort.
        """

        def _get_parent_name(parent_ref: ImportRef | str) -> str:
            return parent_ref.name if isinstance(parent_ref, ImportRef) else parent_ref

        def _resolve_parent_type(
            parent_ref: ImportRef | str,
        ) -> graph.BoundNode | None:
            """
            Resolve parent type from local type_roots, stdlib, or file imports.

            For stdlib imports (ImportRef with path=None), look up in stdlib registry.
            For file imports (ImportRef with path), use the file import resolver.
            For local types (str), look up in type_roots.
            """
            if isinstance(parent_ref, ImportRef):
                if parent_ref.path is None:
                    # stdlib import - look up in stdlib registry
                    if self._stdlib is not None and parent_ref.name in self._stdlib:
                        return self._stdlib.get(parent_ref.name)
                else:
                    # file import - use the file import resolver
                    if self._file_imports is not None:
                        return self._file_imports.resolve(
                            path=parent_ref.path,
                            name=parent_ref.name,
                            base_file=self._base_file,
                        )
            # Local type - look up in type_roots
            parent_name = _get_parent_name(parent_ref)
            return self._type_roots.get(parent_name)

        dag: DAG[str] = DAG()
        pending_by_name = {}

        for item in self._pending_inheritance:
            parent_name = _get_parent_name(item.parent_ref)
            dag.add_edge(parent=parent_name, child=item.derived_name)
            pending_by_name[item.derived_name] = item

        try:
            sorted_types = dag.topologically_sorted()
        except ValueError as e:
            raise DslRichException(
                "Circular inheritance detected",
                file_path=self._base_file,
            ) from e

        for type_name in sorted_types:
            if type_name not in pending_by_name:
                continue  # Base type without parent in this file

            item = pending_by_name[type_name]
            parent_name = _get_parent_name(item.parent_ref)

            if (parent_type := _resolve_parent_type(item.parent_ref)) is None:
                raise DslException(
                    f"Parent type `{parent_name}` not found for `{item.derived_name}`"
                )

            # Apply inheritance
            self._tg.merge_types(
                target=item.derived_type,
                source=parent_type,
            )

    def _execute_retypes(self) -> None:
        """
        Apply retype operations after all types are linked.

        For each retype `target -> NewType`:
        1. Resolve the target path to find owning type
        2. Get the MakeChild's type reference for the leaf field
        3. Update the type reference to point to the new type
        """
        for retype in sorted(self._pending_retypes, key=lambda r: r.source_order):
            try:
                target_path = retype.target_path
                path_ids = target_path.identifiers()

                if target_path.is_singleton():
                    parent_path = None
                    (leaf_id,) = path_ids
                else:
                    *parent_path, leaf_id = path_ids

                if parent_path is not None:
                    if (
                        owning_type := self._tg.resolve_child_path(
                            start_type=retype.containing_type, path=parent_path
                        )
                    ) is None:
                        raise DslException(
                            (
                                f"Cannot resolve path `{'.'.join(parent_path)}`",
                                " for retyping",
                            )
                        )
                else:
                    owning_type = retype.containing_type

                if (
                    type_ref := self._tg.get_make_child_type_reference_by_identifier(
                        type_node=owning_type, identifier=leaf_id
                    )
                ) is None:
                    raise DslException(
                        f"Cannot retype `{target_path}`: field does not exist"
                    )

                # linker should by now have resolved the type reference
                if (
                    new_type := fbrk.Linker.get_resolved_type(
                        type_reference=retype.new_type_ref
                    )
                ) is None:
                    type_id = fbrk.TypeGraph.get_type_reference_identifier(
                        type_reference=retype.new_type_ref
                    )
                    raise DslException(f"Cannot retype to `{type_id}`: type not linked")

                # Apply retyping
                fbrk.Linker.update_type_reference(
                    g=self._g, type_reference=type_ref, target_type_node=new_type
                )
            except DslException as ex:
                raise DslRichException(
                    str(ex),
                    original=ex,
                    source_node=retype.source_node,
                ) from ex
