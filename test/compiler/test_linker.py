import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
from atopile.compiler.build import (
    ImportPathNotFoundError,
    Linker,
    StdlibRegistry,
    build_file,
    build_source,
)


def _init_graph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)
    return g, tg, stdlib


def _build_snippet(source: str):
    g, tg, stdlib = _init_graph()
    result = build_source(g=g, tg=tg, source=textwrap.dedent(source))
    return g, tg, stdlib, result


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
    g, tg, stdlib, result = _build_snippet(
        """
        import Resistor

        module Root:
            part = new Resistor
        """
    )

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    assert not fbrk.Linker.collect_unresolved_type_references(type_graph=tg)


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

    g, tg, stdlib = _init_graph()
    result = build_file(g=g, tg=tg, import_path="entry.ato", path=entry_path)

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    assert not fbrk.Linker.collect_unresolved_type_references(type_graph=tg)


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

    g, tg, stdlib, result = _build_snippet(
        """
        from "generics/shim.ato" import ShimmedModule

        module Root:
            dep = new ShimmedModule
        """
    )

    linker = Linker(None, stdlib, tg, extra_search_paths=(modules_root,))
    linker.link_imports(g, result.state)

    assert not fbrk.Linker.collect_unresolved_type_references(type_graph=tg)


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

    g, tg, stdlib = _init_graph()
    result = build_file(g=g, tg=tg, import_path="entry.ato", path=entry_path)

    linker = Linker(config_obj, stdlib, tg)
    linker.link_imports(g, result.state)

    assert not fbrk.Linker.collect_unresolved_type_references(type_graph=tg)


def test_missing_import_raises_user_error():
    g, tg, stdlib, result = _build_snippet(
        """
        from "missing/module.ato" import DoesNotExist

        module Root:
            child = new DoesNotExist
        """
    )

    linker = Linker(None, stdlib, tg)
    with pytest.raises(ImportPathNotFoundError) as excinfo:
        linker.link_imports(g, result.state)

    assert "Unable to resolve import `missing/module.ato`" in str(excinfo.value)


def test_different_imports_resolve_to_different_nodes():
    """Different imported types should resolve to different nodes."""
    g, tg, stdlib, result = _build_snippet(
        """
        import Resistor
        import Capacitor

        module App:
            r = new Resistor
            c = new Capacitor
        """
    )

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)
    app_type = result.state.type_roots["App"]

    r_resolved = None
    c_resolved = None
    for identifier, make_child in tg.collect_make_children(type_node=app_type):
        type_ref = tg.get_make_child_type_reference(make_child=make_child)
        if identifier == "r":
            r_resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
        elif identifier == "c":
            c_resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)

    assert r_resolved is not None
    assert c_resolved is not None
    assert not r_resolved.node().is_same(other=c_resolved.node())


def test_multiple_references_same_import():
    """Multiple uses of the same imported type should resolve to the same node."""
    g, tg, stdlib, result = _build_snippet(
        """
        import Resistor

        module App:
            first = new Resistor
            second = new Resistor
            third = new Resistor
        """
    )

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    assert not fbrk.Linker.collect_unresolved_type_references(type_graph=tg)

    app_type = result.state.type_roots["App"]

    resolved_nodes = []
    for identifier, make_child in tg.collect_make_children(type_node=app_type):
        if identifier in ("first", "second", "third"):
            type_ref = tg.get_make_child_type_reference(make_child=make_child)
            resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
            assert resolved is not None
            resolved_nodes.append(resolved)

    assert len(resolved_nodes) == 3
    assert resolved_nodes[0].node().is_same(other=resolved_nodes[1].node())
    assert resolved_nodes[1].node().is_same(other=resolved_nodes[2].node())
