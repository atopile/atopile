import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from atopile.compiler.build import (
    ImportPathNotFoundError,
    Linker,
    build_file,
    build_source,
    build_stdlib,
)
from faebryk.core.zig.gen.faebryk.linker import Linker as _Linker
from faebryk.core.zig.gen.graph.graph import GraphView


def _init_graph():
    graph = GraphView.create()
    stdlib_tg, stdlib_registry = build_stdlib(graph)
    return graph, stdlib_tg, stdlib_registry


def _config_with_package(src: Path, package_identifier: str) -> SimpleNamespace:
    root = src.parents[1] if len(src.parents) > 1 else src.parent
    modules_dir = root / ".ato" / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    project = SimpleNamespace(
        paths=SimpleNamespace(src=src, modules=modules_dir, root=root),
        package=SimpleNamespace(identifier=package_identifier),
    )
    return SimpleNamespace(project=project)


def test_stdlib_import_resolved():
    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_source(
        graph,
        textwrap.dedent(
            """
            import Resistor

            module Root:
                part = new Resistor
            """
        ),
    )

    linker = Linker(None, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)

    assert not _Linker.collect_unresolved_type_references(
        type_graph=result.state.type_graph
    )


def test_resolves_relative_ato_import(tmp_path: Path):
    module_dir = tmp_path / "pkg"
    module_dir.mkdir(parents=True)

    imported_path = module_dir / "some_module.ato"
    imported_path.write_text(
        textwrap.dedent(
            """
            module SpecialResistor:
                pass
            """
        ),
        encoding="utf-8",
    )

    entry_path = tmp_path / "entry.ato"
    entry_path.write_text(
        textwrap.dedent(
            """
            from "pkg/some_module.ato" import SpecialResistor

            module Root:
                child = new SpecialResistor
            """
        ),
        encoding="utf-8",
    )

    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_file(graph, entry_path)

    linker = Linker(None, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)

    assert not _Linker.collect_unresolved_type_references(
        type_graph=result.state.type_graph
    )


def test_resolves_via_extra_search_path(tmp_path: Path):
    modules_root = tmp_path / "custom_modules"
    imported_path = modules_root / "generics" / "shim.ato"
    imported_path.parent.mkdir(parents=True)
    imported_path.write_text(
        textwrap.dedent(
            """
            module ShimmedModule:
                pass
            """
        ),
        encoding="utf-8",
    )

    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_source(
        graph,
        textwrap.dedent(
            """
            from "generics/shim.ato" import ShimmedModule

            module Root:
                dep = new ShimmedModule
            """
        ),
    )

    linker = Linker(
        None, stdlib_registry, stdlib_tg, extra_search_paths=(modules_root,)
    )
    linker.link_imports(graph, result.state)

    assert not _Linker.collect_unresolved_type_references(
        type_graph=result.state.type_graph
    )


def test_package_identifier_rewrite(tmp_path: Path):
    project_src = tmp_path / "proj" / "elec" / "src"
    project_src.mkdir(parents=True, exist_ok=True)
    config_obj = _config_with_package(project_src, "owner/pkg")

    module_path = project_src / "pkg_module.ato"
    module_path.write_text(
        textwrap.dedent(
            """
            module PackageModule:
                pass
            """
        ),
        encoding="utf-8",
    )

    entry_path = project_src / "entry.ato"
    entry_path.write_text(
        textwrap.dedent(
            """
            from "owner/pkg/pkg_module.ato" import PackageModule

            module Root:
                dep = new PackageModule
            """
        ),
        encoding="utf-8",
    )

    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_file(graph, entry_path)

    linker = Linker(config_obj, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)

    assert not _Linker.collect_unresolved_type_references(
        type_graph=result.state.type_graph
    )


def test_missing_import_raises_user_error():
    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_source(
        graph,
        textwrap.dedent(
            """
            from "missing/module.ato" import DoesNotExist

            module Root:
                child = new DoesNotExist
            """
        ),
    )

    linker = Linker(None, stdlib_registry, stdlib_tg)
    with pytest.raises(ImportPathNotFoundError) as excinfo:
        linker.link_imports(graph, result.state)

    assert "Unable to resolve import `missing/module.ato`" in str(excinfo.value)


def test_different_imports_resolve_to_different_nodes():
    """Different imported types should resolve to different nodes."""
    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_source(
        graph,
        textwrap.dedent(
            """
            import Resistor
            import Capacitor

            module App:
                r = new Resistor
                c = new Capacitor
            """
        ),
    )

    linker = Linker(None, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)
    type_graph = result.state.type_graph
    app_type = result.state.type_roots["App"]

    r_resolved = None
    c_resolved = None
    for identifier, make_child in type_graph.iter_make_children(type_node=app_type):
        type_ref = type_graph.get_make_child_type_reference(make_child=make_child)
        if identifier == "r":
            r_resolved = _Linker.get_resolved_type(type_reference=type_ref)
        elif identifier == "c":
            c_resolved = _Linker.get_resolved_type(type_reference=type_ref)

    assert r_resolved is not None
    assert c_resolved is not None
    assert not r_resolved.node().is_same(other=c_resolved.node())


def test_multiple_references_same_import():
    """Multiple uses of the same imported type should resolve to the same node."""
    graph, stdlib_tg, stdlib_registry = _init_graph()
    result = build_source(
        graph,
        textwrap.dedent(
            """
            import Resistor

            module App:
                first = new Resistor
                second = new Resistor
                third = new Resistor
            """
        ),
    )

    linker = Linker(None, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)

    assert not _Linker.collect_unresolved_type_references(
        type_graph=result.state.type_graph
    )

    type_graph = result.state.type_graph
    app_type = result.state.type_roots["App"]

    resolved_nodes = []
    for identifier, make_child in type_graph.iter_make_children(type_node=app_type):
        if identifier in ("first", "second", "third"):
            type_ref = type_graph.get_make_child_type_reference(make_child=make_child)
            resolved = _Linker.get_resolved_type(type_reference=type_ref)
            assert resolved is not None
            resolved_nodes.append(resolved)

    assert len(resolved_nodes) == 3
    assert resolved_nodes[0].node().is_same(other=resolved_nodes[1].node())
    assert resolved_nodes[1].node().is_same(other=resolved_nodes[2].node())
