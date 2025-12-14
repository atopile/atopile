"""
Entry points for building from ato sources.
"""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from atopile.compiler import ast_types as AST
from atopile.compiler.antlr_visitor import ANTLRVisitor
from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST, ASTVisitor, BuildState
from atopile.compiler.gentypegraph import ImportRef
from atopile.compiler.parse import parse_file, parse_text_as_file
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.config import find_project_dir
from faebryk.libs.util import once, unique


@dataclass
class BuildFileResult:
    ast_root: AST.File
    state: BuildState


class StdlibRegistry:
    """Lazy loader for stdlib types."""

    def __init__(
        self, tg: fbrk.TypeGraph, allowlist: dict[str, type[fabll.Node]] | None = None
    ) -> None:
        self._tg = tg
        self._cache: dict[str, graph.BoundNode] = {}
        self._allowlist = allowlist or STDLIB_ALLOWLIST.copy()

    def get(self, name: str) -> graph.BoundNode:
        if name not in self._cache:
            if name not in self._allowlist:
                raise KeyError(f"Unknown stdlib type: {name}")
            obj = self._allowlist[name]
            type_node = obj.bind_typegraph(self._tg).get_or_create_type()
            self._cache[name] = type_node
        return self._cache[name]

    def __contains__(self, name: str) -> bool:
        return name in self._allowlist


class TestStdlibRegistry:
    """Tests for lazy stdlib loading."""

    def test_lazy_loading(self):
        """Types are only created when first accessed."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        registry = StdlibRegistry(tg)

        assert tg.get_type_by_name(type_identifier="Resistor") is None

        node = registry.get("Resistor")
        assert node is not None
        assert tg.get_type_by_name(type_identifier="Resistor") is not None

    def test_caching(self):
        """Same type node returned on repeated access."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        registry = StdlibRegistry(tg)

        node1 = registry.get("Resistor")
        node2 = registry.get("Resistor")
        assert node1.node().is_same(other=node2.node())

    def test_unknown_type_raises(self):
        """KeyError raised for unknown stdlib types."""
        import pytest

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        registry = StdlibRegistry(tg)

        with pytest.raises(KeyError):
            registry.get("NotARealType")


class LinkerException(Exception):
    pass


class UnresolvedTypeReferencesError(LinkerException):
    def __init__(
        self,
        message: str,
        unresolved_type_references: list[tuple[graph.BoundNode, graph.BoundNode]],
    ) -> None:
        super().__init__(message)
        self.unresolved_type_references = unresolved_type_references


class ImportPathNotFoundError(LinkerException):
    pass


class CircularImportError(LinkerException):
    pass


class SearchPathResolver:
    """
    Implements search-path resolution for path-based imports.

    Resolution order:
    1. Directory containing the importing file (when available).
    2. Extra search paths supplied by the caller (insertion order, duplicates removed).
    3. Project `src` directory (from config, when known).
    4. Project `.ato/modules` directory (from config, when known).
    5. Project root directory (discovered via `find_project_dir`).

    Each candidate path is normalised (expanduser + resolve) and deduplicated. If the
    current project declares a package identifier and the import path starts with it,
    the resolver first rewrites the prefix to the project `src` directory and probes
    that absolute path immediately. If it does not exist, the raw import string is then
    checked relative to each search path in order. Any successful probe returns the
    normalised file location; otherwise an `ImportPathNotFoundError` is raised.
    """

    def __init__(self, config_obj, *, extra_search_paths: Iterable[Path]) -> None:
        project = getattr(config_obj, "project", None)
        package_cfg = getattr(project, "package", None)
        project_paths = getattr(project, "paths", None)
        self._extra_search_paths = extra_search_paths
        self._project_src = self._normalize_path_optional(
            getattr(project_paths, "src", None)
        )
        self._project_modules = self._normalize_path_optional(
            getattr(project_paths, "modules", None)
        )
        self._project_root = self._normalize_path_optional(
            getattr(project_paths, "root", None)
        )
        self._package_identifier = getattr(package_cfg, "identifier", None)

    @staticmethod
    def _normalize_path(path: Path) -> Path:
        return path.expanduser().resolve()

    @staticmethod
    def _normalize_path_optional(path: Path | None) -> Path | None:
        return None if path is None else SearchPathResolver._normalize_path(path)

    @property
    @once
    def static_paths(self) -> tuple[Path, ...]:
        return tuple(
            unique(
                [
                    SearchPathResolver._normalize_path(path)
                    for path in [
                        *self._extra_search_paths,
                        self._project_src,
                        self._project_modules,
                    ]
                    if path is not None
                ],
                key=str,
            )
        )

    def _rewrite_package_identifier(self, raw_path: str) -> Path | None:
        if (
            self._package_identifier is not None
            and self._project_src is not None
            and raw_path.startswith(self._package_identifier)
        ):
            return self._normalize_path(
                Path(
                    raw_path.replace(
                        self._package_identifier, str(self._project_src), 1
                    )
                )
            )

    def search_paths(self, base_file: Path | None) -> Generator[Path, None, None]:
        if base_file is not None:
            yield self._normalize_path(base_file).parent

        yield from self.static_paths

        if self._project_root is not None:
            yield self._project_root

        if (
            base_file is not None
            and (project_dir := find_project_dir(base_file)) is not None
        ):
            yield self._normalize_path(project_dir)

    @once
    def resolve(self, raw_path: str, base_file: Path | None) -> Path:
        # Package self-imports take precedence
        if (rewritten := self._rewrite_package_identifier(raw_path)) is not None:
            if rewritten.exists():
                return rewritten

        for search_dir in self.search_paths(base_file):
            if (candidate := search_dir / raw_path).exists():
                return self._normalize_path(candidate)

        raise ImportPathNotFoundError(f"Unable to resolve import `{raw_path}`")


class Linker:
    def __init__(
        self,
        config_obj,
        stdlib: StdlibRegistry,
        tg: fbrk.TypeGraph,
        extra_search_paths: Iterable[Path] | None = None,
    ) -> None:
        self._resolver = SearchPathResolver(
            config_obj, extra_search_paths=extra_search_paths or []
        )
        self._stdlib = stdlib
        self._tg = tg
        self._active_paths: set[Path] = set()
        self._linked_modules: dict[Path, dict[str, graph.BoundNode]] = {}

    def _build_imported_file(
        self, graph: graph.GraphView, import_ref: ImportRef, build_state: BuildState
    ) -> graph.BoundNode:
        assert import_ref.path is not None

        source_path = self._resolver.resolve(
            raw_path=import_ref.path, base_file=build_state.file_path
        )

        if source_path in self._linked_modules:
            return self._linked_modules[source_path][import_ref.name]

        assert source_path.exists()

        child_result = build_file(
            g=graph,
            tg=self._tg,
            import_path=import_ref.path,
            path=source_path,
        )
        self._link_recursive(graph, child_result.state)
        self._linked_modules[source_path] = child_result.state.type_roots
        return child_result.state.type_roots[import_ref.name]

    def link_imports(self, graph: graph.GraphView, build_state: BuildState) -> None:
        resolved_path = (
            self._resolver._normalize_path(build_state.file_path)
            if build_state.file_path is not None
            else None
        )

        match resolved_path:
            case None:
                self._link(graph, build_state)
            case _ if resolved_path in self._linked_modules:
                self._link_from_cache(
                    graph, build_state, self._linked_modules[resolved_path]
                )
            case _:
                with self._guard_path(resolved_path):
                    self._link(graph, build_state)
                    self._linked_modules[resolved_path] = build_state.type_roots

        # Only check for unresolved refs at the top level
        if unresolved := fbrk.Linker.collect_unresolved_type_references(
            type_graph=self._tg
        ):
            raise UnresolvedTypeReferencesError(
                "Unresolved type references remaining after linking", unresolved
            )

    def _link_recursive(self, graph: graph.GraphView, build_state: BuildState) -> None:
        """Link imports without checking unresolved refs (for recursive calls)."""
        resolved_path = (
            self._resolver._normalize_path(build_state.file_path)
            if build_state.file_path is not None
            else None
        )

        match resolved_path:
            case None:
                self._link(graph, build_state)
            case _ if resolved_path in self._linked_modules:
                self._link_from_cache(
                    graph, build_state, self._linked_modules[resolved_path]
                )
            case _:
                with self._guard_path(resolved_path):
                    self._link(graph, build_state)
                    self._linked_modules[resolved_path] = build_state.type_roots

    def _link(self, graph: graph.GraphView, build_state: BuildState) -> None:
        for type_reference, import_ref in build_state.external_type_refs:
            fbrk.Linker.link_type_reference(
                g=graph,
                type_reference=type_reference,
                target_type_node=(
                    self._stdlib.get(import_ref.name)
                    if import_ref.path is None
                    else self._build_imported_file(graph, import_ref, build_state)
                ),
            )

    def _link_from_cache(
        self,
        graph: graph.GraphView,
        build_state: BuildState,
        cached_type_roots: dict[str, graph.BoundNode],
    ) -> None:
        for type_reference, import_ref in build_state.external_type_refs:
            fbrk.Linker.link_type_reference(
                g=graph,
                type_reference=type_reference,
                target_type_node=(
                    self._stdlib.get(import_ref.name)
                    if import_ref.path is None
                    else cached_type_roots[import_ref.name]
                ),
            )

    @contextmanager
    def _guard_path(self, path: Path) -> Generator[None, None, None]:
        if path in self._active_paths:
            raise CircularImportError(f"Circular import detected at `{path}`")

        self._active_paths.add(path)

        try:
            yield
        finally:
            self._active_paths.remove(path)


def _build_from_ctx(
    *,
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    import_path: str | None,
    root_ctx: AtoParser.File_inputContext,
    file_path: Path | None,
    stdlib_allowlist: dict[str, type[fabll.Node]] | None = None,
) -> BuildFileResult:
    ast_root = ANTLRVisitor(g, tg, file_path).visit(root_ctx)
    assert isinstance(ast_root, AST.File)
    build_state = ASTVisitor(
        ast_root, g, tg, import_path, file_path, stdlib_allowlist
    ).build()
    return BuildFileResult(ast_root=ast_root, state=build_state)


def build_file(
    *,
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    import_path: str,
    path: Path,
    stdlib_allowlist: dict[str, type[fabll.Node]] | None = None,
) -> BuildFileResult:
    return _build_from_ctx(
        g=g,
        tg=tg,
        import_path=import_path,
        root_ctx=parse_file(path),
        file_path=path,
        stdlib_allowlist=stdlib_allowlist,
    )


def build_source(
    *,
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
    source: str,
    import_path: str | None = None,
    stdlib_allowlist: dict[str, type[fabll.Node]] | None = None,
) -> BuildFileResult:
    import uuid

    if import_path is None:
        import_path = f"__source_{uuid.uuid4().hex[:8]}__.ato"

    return _build_from_ctx(
        g=g,
        tg=tg,
        import_path=import_path,
        root_ctx=parse_text_as_file(source),
        file_path=None,
        stdlib_allowlist=stdlib_allowlist,
    )
