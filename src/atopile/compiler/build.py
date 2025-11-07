"""
Entry points for building from ato sources.
"""

from dataclasses import dataclass
from pathlib import Path

from atopile.compiler import ast_types as AST
from atopile.compiler.antlr_visitor import ANTLRVisitor
from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST, ASTVisitor, BuildState
from atopile.compiler.parse import parse_file, parse_text_as_file
from atopile.compiler.parser.AtoParser import AtoParser
from faebryk.core.zig.gen.faebryk.linker import Linker as _Linker
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView


@dataclass
class BuildFileResult:
    ast_root: AST.File
    state: BuildState


class LinkerException(Exception):
    pass


class Linker:
    @staticmethod
    def _resolve_import_path(base_file: Path | None, raw_path: str) -> Path:
        # TODO: include all search paths
        # TODO: get base dirs from config
        search_paths = [
            *([base_file.parent] if base_file is not None else []),
            Path(".ato/modules"),
        ]

        for search_path in search_paths:
            if (candidate := search_path / raw_path).exists():
                return candidate

        raise LinkerException(f"Import path not found: `{raw_path}`")

    @staticmethod
    def link_imports(
        graph: GraphView,
        build_state: BuildState,
        stdlib_registry: dict[str, BoundNode],
        stdlib_tg: TypeGraph,
    ) -> None:
        # TODO: handle cycles

        for type_reference, import_ref in build_state.external_type_refs:
            if import_ref.path is None:
                target_type_node = stdlib_registry[import_ref.name]

            else:
                source_path = Linker._resolve_import_path(
                    base_file=build_state.file_path, raw_path=import_ref.path
                )
                assert source_path.exists()

                child_result = build_file(graph, source_path)
                Linker.link_imports(
                    graph, child_result.state, stdlib_registry, stdlib_tg
                )
                target_type_node = child_result.state.type_roots[import_ref.name]

            _Linker.link_type_reference(
                g=graph,
                type_reference=type_reference,
                target_type_node=target_type_node,
            )

        if build_state.type_graph.collect_unresolved_type_references():
            raise LinkerException("Unresolved type references remaining after linking")


def build_stdlib(graph: GraphView) -> tuple[TypeGraph, dict[str, BoundNode]]:
    tg = TypeGraph.create(g=graph)
    registry: dict[str, BoundNode] = {}

    for name, obj in STDLIB_ALLOWLIST.items():
        type_node = obj.bind_typegraph(tg).get_or_create_type()
        registry[name] = type_node

    return tg, registry


def _build_from_ctx(
    graph: GraphView, root_ctx: AtoParser.File_inputContext, file_path: Path | None
) -> BuildFileResult:
    ast_type_graph = TypeGraph.create(g=graph)
    ast_root = ANTLRVisitor(graph, ast_type_graph, file_path).visit(root_ctx)
    assert isinstance(ast_root, AST.File)
    build_state = ASTVisitor(ast_root, graph, file_path).build()
    return BuildFileResult(ast_root=ast_root, state=build_state)


def build_file(graph: GraphView, path: Path) -> BuildFileResult:
    # TODO: per-file caching
    return _build_from_ctx(graph, parse_file(path), path)


def build_source(graph: GraphView, source: str) -> BuildFileResult:
    return _build_from_ctx(graph, parse_text_as_file(source), file_path=None)
