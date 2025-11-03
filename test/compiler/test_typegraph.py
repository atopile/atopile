import textwrap
from pathlib import Path

import pytest

from atopile.compiler.ast_graph import (
    DslException,
    Linker,
    build_file,
    build_source,
    build_stdlib,
)
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.next import EdgeNext
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.graph.graph import GraphView


def _get_make_child(type_node, name: str):
    matches: list = []

    def _collector(ctx: list, bound_edge):
        child_node = EdgeComposition.get_child_node(edge=bound_edge.edge())
        child_bound = bound_edge.g().bind(node=child_node)
        identifier = child_bound.node().get_attr(key="child_identifier")
        if identifier == name:
            ctx.append(child_bound)

    EdgeComposition.visit_children_edges(
        bound_node=type_node,
        ctx=matches,
        f=_collector,
    )

    assert matches, f"expected make child `{name}`"
    return matches[0]


def _collect_make_links(type_node):
    results: list = []

    def _collector(ctx: list, bound_edge):
        child_node = bound_edge.g().bind(
            node=EdgeComposition.get_child_node(edge=bound_edge.edge())
        )
        lhs_ref = EdgeComposition.get_child_by_identifier(
            bound_node=child_node, child_identifier="lhs"
        )
        rhs_ref = EdgeComposition.get_child_by_identifier(
            bound_node=child_node, child_identifier="rhs"
        )
        if lhs_ref is None or rhs_ref is None:
            return

        def path(ref) -> list[str]:
            segments: list[str] = []
            current = ref
            while True:
                identifier = current.node().get_attr(key="child_identifier")
                if identifier is None:
                    return []
                segments.append(str(identifier))
                next_node = EdgeNext.get_next_node_from_node(node=current)
                if next_node is None:
                    break
                current = current.g().bind(node=next_node)
            return segments

        lhs_path = path(lhs_ref)
        rhs_path = path(rhs_ref)
        if not lhs_path or not rhs_path:
            return
        if lhs_path[0] == "is_ato_block" or rhs_path[0] == "is_ato_block":
            return
        ctx.append((child_node, lhs_path, rhs_path))

    EdgeComposition.visit_children_edges(
        bound_node=type_node,
        ctx=results,
        f=_collector,
    )
    return results


def _build_snippet(source: str):
    graph = GraphView.create()
    stdlib_tg, stdlib_registry = build_stdlib(graph)
    result = build_source(graph, textwrap.dedent(source))
    return graph, stdlib_tg, stdlib_registry, result


def test_block_definitions_recorded():
    _, _, _, result = _build_snippet(
        """
        module Root:
            pass

        component SomeComponent:
            pass

        interface SomeInterface:
            signal line
        """
    )

    assert set(result.state.type_roots.keys()) == {
        "Root",
        "SomeComponent",
        "SomeInterface",
    }


def test_make_child_and_linking():
    graph, stdlib_tg, stdlib_registry, result = _build_snippet(
        """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            pass

        module App:
            child = new Inner
            res = new Resistor
        """
    )
    app_type = result.state.type_roots["App"]

    child_node = _get_make_child(app_type, "child")
    assert (
        EdgeComposition.get_child_by_identifier(
            bound_node=child_node, child_identifier="mount"
        )
        is None
    )

    res_node = _get_make_child(app_type, "res")
    assert (
        EdgeComposition.get_child_by_identifier(
            bound_node=res_node, child_identifier="mount"
        )
        is None
    )

    unresolved = result.state.type_graph.collect_unresolved_type_references()
    assert not unresolved

    Linker.link_imports(graph, result.state, stdlib_registry, stdlib_tg)

    type_ref = EdgeComposition.get_child_by_identifier(
        bound_node=res_node, child_identifier="type_ref"
    )
    assert type_ref is not None
    resolved = EdgePointer.get_pointed_node_by_identifier(
        bound_node=type_ref, identifier="resolved"
    )
    assert resolved is not None


def test_nested_make_child_uses_mount_reference():
    _, _, _, result = _build_snippet(
        """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            pass

        module App:
            base = new Inner
            base.extra = new Resistor
        """
    )
    app_type = result.state.type_roots["App"]

    base_node = _get_make_child(app_type, "base")
    assert (
        EdgeComposition.get_child_by_identifier(
            bound_node=base_node, child_identifier="mount"
        )
        is None
    )

    extra_node = _get_make_child(app_type, "extra")
    mount_ref = EdgeComposition.get_child_by_identifier(
        bound_node=extra_node, child_identifier="mount"
    )
    assert mount_ref is not None
    assert _collect_make_links(app_type) == []


def test_connects_between_top_level_fields():
    _, _, _, result = _build_snippet(
        """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            left = new Resistor
            right = new Resistor
            left ~ right
        """
    )
    app_type = result.state.type_roots["App"]

    make_links = _collect_make_links(app_type)
    assert len(make_links) == 1

    (_, lhs_path, rhs_path) = make_links[0]
    assert lhs_path == ["left"]
    assert rhs_path == ["right"]


def test_assignment_requires_existing_field():
    with pytest.raises(DslException, match="not defined"):
        _build_snippet(
            """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            missing.child = new Resistor
            """
        )


def test_connect_requires_existing_fields():
    with pytest.raises(DslException, match="not defined"):
        _build_snippet(
            """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            left = new Resistor
            left ~ missing
            """
        )


def test_nested_connects_across_child_fields():
    _, _, _, result = _build_snippet(
        """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            connection = new Resistor

        module App:
            left = new Inner
            right = new Inner
            left.connection ~ right.connection
        """
    )
    app_type = result.state.type_roots["App"]

    make_links = _collect_make_links(app_type)
    assert len(make_links) == 1

    (_, lhs_path, rhs_path) = make_links[0]
    assert lhs_path == ["left", "connection"]
    assert rhs_path == ["right", "connection"]


def test_deep_nested_connects_across_child_fields():
    _, _, _, result = _build_snippet(
        """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Level2:
            branch = new Resistor

        module Level1:
            intermediate = new Level2

        module App:
            left = new Level1
            right = new Level1
            left.intermediate.branch ~ right.intermediate.branch
        """
    )
    app_type = result.state.type_roots["App"]

    make_links = _collect_make_links(app_type)
    assert len(make_links) == 1

    (_, lhs_path, rhs_path) = make_links[0]
    assert lhs_path == ["left", "intermediate", "branch"]
    assert rhs_path == ["right", "intermediate", "branch"]


def test_nested_connect_missing_prefix_raises():
    with pytest.raises(DslException, match="Failed to create reference"):
        _build_snippet(
            """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Level2:
            branch = new Resistor

        module Level1:
            intermediate = new Level2

        module App:
            left = new Level1
            left.missing.branch ~ left.intermediate.branch
            """
        )


def test_nested_block_definition_disallowed():
    with pytest.raises(DslException, match="not permitted"):
        _build_snippet(
            """
        import Resistor

        module Root:
            module Resistor:
                pass
        """
        )


def test_external_import_linking(tmp_path: Path):
    child_path = tmp_path / "child.ato"
    child_path.write_text(
        textwrap.dedent(
            """
            module Imported:
                pass
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            from "child.ato" import Imported

            module App:
                child = new Imported
            """
        ),
        encoding="utf-8",
    )

    graph = GraphView.create()
    stdlib_tg, stdlib_registry = build_stdlib(graph)

    result = build_file(graph, main_path)
    app_type = result.state.type_roots["App"]
    child_node = _get_make_child(app_type, "child")

    unresolved = result.state.type_graph.collect_unresolved_type_references()
    assert unresolved

    Linker.link_imports(graph, result.state, stdlib_registry, stdlib_tg)

    type_ref = EdgeComposition.get_child_by_identifier(
        bound_node=child_node, child_identifier="type_ref"
    )
    assert type_ref is not None
    resolved = EdgePointer.get_pointed_node_by_identifier(
        bound_node=type_ref, identifier="resolved"
    )
    assert resolved is not None
