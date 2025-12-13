import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
from atopile.compiler.ast_visitor import DslException
from atopile.compiler.build import Linker, StdlibRegistry, build_file, build_source
from faebryk.core.faebrykpy import (
    EdgeComposition,
    EdgePointer,
    EdgeTrait,
)
from faebryk.libs.util import not_none

NULL_CONFIG = SimpleNamespace(project=None)


def _get_make_child(type_graph, type_node, name: str):
    for identifier, make_child in type_graph.collect_make_children(type_node=type_node):
        if identifier == name:
            return make_child
    raise AssertionError(f"expected make child `{name}`")


def _collect_make_links(tg: fbrk.TypeGraph, type_node: graph.BoundNode):
    return [
        (make_link, list(lhs_path), list(rhs_path))
        for make_link, lhs_path, rhs_path in tg.collect_make_links(type_node=type_node)
    ]


def _check_make_links(
    tg: fbrk.TypeGraph,
    type_node: graph.BoundNode,
    expected: list[tuple[list[str] | tuple[str, ...], list[str] | tuple[str, ...]]]
    | None = None,
    not_expected: list[tuple[list[str] | tuple[str, ...], list[str] | tuple[str, ...]]]
    | None = None,
) -> bool:
    paths = {
        (tuple(lhs_path), tuple(rhs_path))
        for _, lhs_path, rhs_path in _collect_make_links(tg, type_node)
    }

    if expected:
        for lhs_expected, rhs_expected in expected:
            if (tuple(lhs_expected), tuple(rhs_expected)) not in paths:
                return False

    if not_expected:
        for lhs_forbidden, rhs_forbidden in not_expected:
            if (tuple(lhs_forbidden), tuple(rhs_forbidden)) in paths:
                return False

    return True


def _build_snippet(source: str, import_path: str | None = None):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)
    result = build_source(
        g=g, tg=tg, source=textwrap.dedent(source), import_path=import_path
    )
    return g, tg, stdlib, result


def _collect_children_by_name(type_graph, type_node, name: str):
    return [
        child
        for identifier, child in type_graph.collect_make_children(type_node=type_node)
        if identifier == name
    ]


# TODO FIXME there's a lot of illegal use of for loops and connecting resistors together
# especially in the for loop tests


def test_block_definitions_recorded():
    _, _, _, result = _build_snippet(
        """
        module Root:
            pass

        component SomeComponent:
            pass

        interface SomeInterface:
            pass # FIXME: `signal line`
        """
    )

    assert set(result.state.type_roots.keys()) == {
        "Root",
        "SomeComponent",
        "SomeInterface",
    }


def test_make_child_and_linking():
    graph, tg, stdlib, result = _build_snippet(
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
    type_graph = tg

    child_node = _get_make_child(type_graph, app_type, "child")
    assert type_graph.debug_get_mount_chain(make_child=child_node) == []

    res_node = _get_make_child(type_graph, app_type, "res")
    assert type_graph.debug_get_mount_chain(make_child=res_node) == []

    unresolved = fbrk.Linker.collect_unresolved_type_references(type_graph=tg)
    assert not unresolved

    linker = Linker(NULL_CONFIG, stdlib, tg)
    linker.link_imports(graph, result.state)

    type_ref = type_graph.get_make_child_type_reference(make_child=res_node)
    assert type_ref is not None
    resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
    assert resolved is not None


def test_new_with_count_creates_pointer_sequence():
    g, tg, _, result = _build_snippet(
        """
        module Inner:
            pass

        module App:
            members = new Inner[3]
        """
    )

    app_type = result.state.type_roots["App"]
    members_node = _get_make_child(tg, app_type, "members")

    type_ref = tg.get_make_child_type_reference(make_child=members_node)
    assert type_ref is not None
    resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
    assert resolved is not None

    element_nodes = []
    for idx in ["0", "1", "2"]:
        element_nodes.append(_get_make_child(tg, app_type, idx))
        ref = tg.ensure_child_reference(
            type_node=app_type,
            path=["members", idx],
            validate=True,
        )
        assert ref is not None
    assert len(element_nodes) == 3


def test_new_with_count_children_have_mounts():
    g, tg, _, result = _build_snippet(
        """
        module Inner:
            pass

        module App:
            members = new Inner[2]
        """
    )

    app_type = result.state.type_roots["App"]
    members_node = _get_make_child(tg, app_type, "members")

    assert tg.debug_get_mount_chain(make_child=members_node) == []

    for idx in ["0", "1"]:
        elem_node = _get_make_child(tg, app_type, idx)
        assert tg.debug_get_mount_chain(make_child=elem_node) == ["members"]


def test_new_with_count_rejects_out_of_range_index():
    with pytest.raises(
        DslException,
        match=r"Field `members\[(2|2\.0)\]` is not defined in scope",
    ):
        _build_snippet(
            """
            module Inner:
                pass

            module App:
                members = new Inner[2]
                members[2] = new Inner
            """
        )


def test_typegraph_path_error_metadata():
    g, tg, _, result = _build_snippet(
        """
        module Inner:
            pass

        module App:
            members = new Inner[2]
        """
    )

    app_type = result.state.type_roots["App"]

    with pytest.raises(fbrk.TypeGraphPathError) as excinfo:
        tg.ensure_child_reference(
            type_node=app_type,
            path=["members", "5"],
            validate=True,
        )
    err = excinfo.value
    assert isinstance(err, fbrk.TypeGraphPathError)
    assert err.kind == "invalid_index"
    assert err.path == ["members", "5"]
    assert err.failing_segment == "5"
    assert err.failing_segment_index == 1
    assert err.index_value is None

    with pytest.raises(fbrk.TypeGraphPathError) as excinfo_missing:
        tg.ensure_child_reference(
            type_node=app_type,
            path=["missing", "child"],
            validate=True,
        )

    assert isinstance(excinfo_missing.value, fbrk.TypeGraphPathError)
    err_missing = excinfo_missing.value
    assert err_missing.kind in {"missing_parent", "missing_child"}
    assert err_missing.path == ["missing", "child"]
    assert err_missing.failing_segment_index == 0


def test_for_loop_connects_twice():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            left = new Resistor
            right = new Resistor
            sink = new Resistor

            for r in [left, right]:
                r ~ sink
        """
    )
    app_type = result.state.type_roots["App"]

    assert (
        _check_make_links(
            tg=tg,
            type_node=app_type,
            expected=[(["left"], ["sink"]), (["right"], ["sink"])],
        )
        is True
    )


def test_for_loop_requires_experiment():
    with pytest.raises(DslException, match="(?i)experiment.*enabled"):
        _build_snippet(
            """
            module Electrical:
                pass

            module Resistor:
                unnamed = new Electrical[2]

            module App:
                left = new Resistor
                right = new Resistor
                sink = new Resistor

                for r in [left, right]:
                    r ~ sink
            """
        )


def test_for_loop_over_sequence():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            connection = new Resistor

        module App:
            items = new Inner[2]
            sink = new Resistor

            for it in items:
                it.connection ~ sink
        """
    )
    # Path segments with indices are combined: items + [0] -> items[0]
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[
                (["items[0]", "connection"], ["sink"]),
                (["items[1]", "connection"], ["sink"]),
            ],
        )
        is True
    )


def test_for_loop_over_sequence_slice():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            connection = new Resistor

        module App:
            items = new Inner[3]
            sink = new Resistor

            for it in items[1:]:
                it.connection ~ sink
        """
    )

    # Path segments with indices are combined
    assert _check_make_links(
        tg=tg,
        type_node=result.state.type_roots["App"],
        expected=[
            (["items[1]", "connection"], ["sink"]),
            (["items[2]", "connection"], ["sink"]),
        ],
    )


def test_for_loop_over_sequence_slice_zero_step_errors():
    with pytest.raises(DslException, match="Slice step cannot be zero"):
        _build_snippet(
            """
            #pragma experiment("FOR_LOOP")

            module Inner:
                pass

            module App:
                items = new Inner[2]

                for it in items[::0]:
                    pass
            """
        )


def test_for_loop_over_sequence_stride():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            connection = new Resistor

        module App:
            items = new Inner[4]
            sink = new Resistor

            for it in items[0:4:2]:
                it.connection ~ sink
        """
    )

    # Path segments with indices are combined
    assert _check_make_links(
        tg=tg,
        type_node=result.state.type_roots["App"],
        expected=[
            (["items[0]", "connection"], ["sink"]),
            (["items[2]", "connection"], ["sink"]),
        ],
        not_expected=[
            (["items[1]", "connection"], ["sink"]),
            (["items[3]", "connection"], ["sink"]),
        ],
    )


def test_for_loop_alias_does_not_leak():
    with pytest.raises(DslException, match="not defined"):
        _build_snippet(
            """
            #pragma experiment("FOR_LOOP")

            module Electrical:
                pass

            module Resistor:
                unnamed = new Electrical[2]

            module App:
                left = new Resistor
                for r in [left]:
                    pass
                r ~ left
            """
        )


def test_for_loop_nested_field_paths():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            connection = new Resistor

        module App:
            left = new Inner
            sink = new Resistor
            for i in [left]:
                i.connection ~ sink
        """
    )
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["left", "connection"], ["sink"])],
            not_expected=[(["right", "connection"], ["sink"])],
        )
        is True
    )


def test_for_loop_assignment_creates_children():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module Inner:
            pass

        module App:
            left = new Inner
            right = new Inner
            for i in [left, right]:
                i.extra = new Resistor
        """
    )
    app_type = result.state.type_roots["App"]
    extras = _collect_children_by_name(tg, app_type, "extra")
    assert len(extras) == 2
    for extra in extras:
        chain = tg.debug_get_mount_chain(make_child=extra)
        assert chain, "expected extra to have mount chain"
        assert chain[-1] == "extra"
        assert chain[0] in {"left", "right"}


def test_two_for_loops_same_var_accumulates_links():
    _, tg, _, result = _build_snippet(
        """
        #pragma experiment("FOR_LOOP")

        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            a = new Resistor
            b = new Resistor
            c = new Resistor
            sink = new Resistor

            for r in [a, b]:
                r ~ sink
            for r in [c]:
                r ~ sink
        """
    )
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["a"], ["sink"]), (["b"], ["sink"]), (["c"], ["sink"])],
        )
        is True
    )


def test_for_loop_alias_shadow_symbol_raises():
    with pytest.raises(DslException, match="shadow"):
        _build_snippet(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module Electrical:
                pass

            module Resistor2:
                unnamed = new Electrical[2]

            module App:
                left = new Resistor2
                for Resistor in [left]:
                    pass
            """
        )


def test_nested_make_child_uses_mount_reference():
    _, tg, _, result = _build_snippet(
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

    base_node = _get_make_child(tg, app_type, "base")
    assert tg.debug_get_mount_chain(make_child=base_node) == []

    extra_node = _get_make_child(tg, app_type, "extra")
    assert tg.debug_get_mount_chain(make_child=extra_node) == ["base", "extra"]
    for _, lhs_path, rhs_path in _collect_make_links(tg, app_type):
        assert not lhs_path or lhs_path[0] not in ("base", "extra")
        assert not rhs_path or rhs_path[0] not in ("base", "extra")


def test_connects_between_top_level_fields():
    _, tg, _, result = _build_snippet(
        """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            left = new Resistor
            right = new Resistor
            left.unnamed[1] ~ right.unnamed[0]
        """
    )
    type_node = result.state.type_roots["App"]
    paths = {
        (tuple(lhs_path), tuple(rhs_path))
        for _, lhs_path, rhs_path in _collect_make_links(tg, type_node)
    }
    print(paths)
    # Path segments with indices are combined: unnamed + [1] -> unnamed[1]
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["left", "unnamed[1]"], ["right", "unnamed[0]"])],
        )
        is True
    )


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


def test_simple_connect():
    _, tg, _, result = _build_snippet(
        """
        module A:
            pass

        module App:
            left = new A
            right = new A
            left ~ right
        """
    )
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["left"], ["right"])],
        )
        is True
    )


def test_connect_resistor_simple():
    _, tg, _, result = _build_snippet(
        """
        import Resistor

        module App:
            left = new Resistor
            right = new Resistor
            left.unnamed[0] ~ right.unnamed[0]
        """
    )
    app_type = result.state.type_roots["App"]
    # Path segments with indices are combined: unnamed + [0] -> unnamed[0]
    # This matches how fabll names list children
    assert _check_make_links(
        tg=tg,
        type_node=app_type,
        expected=[(["left", "unnamed[0]"], ["right", "unnamed[0]"])],
        not_expected=[(["left"], ["right"])],
    )


def test_connect_unlinked_types():
    _, tg, _, result = _build_snippet(
        """
        from "A.ato" import A

        module App:
            left = new A
            right = new A
            left ~ right
        """
    )
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["left"], ["right"])],
        )
        is True
    )


def test_directed_connect():
    """Test directed connect creates links through can_bridge traits."""
    _, tg, _, result = _build_snippet(
        """
        import Resistor

        module App:
            left = new Resistor
            right = new Resistor
            left ~> right
        """
    )
    # Directed connect goes through can_bridge: left.out_ -> right.in_
    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["left", "can_bridge", "out_"], ["right", "can_bridge", "in_"])],
        )
        is True
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
    _, tg, _, result = _build_snippet(
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

    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[(["left", "connection"], ["right", "connection"])],
        )
        is True
    )


def test_deep_nested_connects_across_child_fields():
    _, tg, _, result = _build_snippet(
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

    assert (
        _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[
                (
                    ["left", "intermediate", "branch"],
                    ["right", "intermediate", "branch"],
                )
            ],
        )
        is True
    )


# TODO: should fail at instantiation?
# def test_nested_connect_missing_prefix_raises():
#     with pytest.raises(
#         DslException, match=r"Field `left\.missing\.branch` is not defined in scope"
#     ):
#         _, _, _, result = _build_snippet(
#             """
#         module Electrical:
#             pass

#         module Resistor:
#             unnamed = new Electrical[2]

#         module Level2:
#             branch = new Resistor

#         module Level1:
#             intermediate = new Level2

#         module App:
#             left = new Level1
#             left.missing.branch ~ left.intermediate.branch
#             """
#         )


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

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    app_type = result.state.type_roots["App"]
    child_node = _get_make_child(tg, app_type, "child")

    unresolved = fbrk.Linker.collect_unresolved_type_references(type_graph=tg)
    assert unresolved

    linker = Linker(NULL_CONFIG, stdlib, tg)
    linker.link_imports(g, result.state)

    type_ref = tg.get_make_child_type_reference(make_child=child_node)
    assert type_ref is not None
    resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
    assert resolved is not None


def test_local_type_cannot_shadow_import():
    """Local type definition cannot shadow imported type of same name."""
    with pytest.raises(DslException, match="already defined"):
        _build_snippet(
            """
            import Resistor

            module Resistor:
                pass
            """
        )


def test_multiple_local_references():
    """Multiple uses of the same local type should resolve to the same node."""
    _, tg, _, result = _build_snippet(
        """
        module Module:
            pass

        module App:
            first = new Module
            second = new Module
            third = new Module
        """
    )

    unresolved = fbrk.Linker.collect_unresolved_type_references(type_graph=tg)
    assert not unresolved

    for identifier, make_child in tg.collect_make_children(
        type_node=result.state.type_roots["App"]
    ):
        if identifier in ("first", "second", "third"):
            type_ref = tg.get_make_child_type_reference(make_child=make_child)
            resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
            assert resolved is not None
            assert resolved.node().is_same(
                other=result.state.type_roots["Module"].node()
            )


class TestTypeNamespacing:
    """Tests for .ato type namespacing."""

    def test_ato_types_namespaced(self):
        """Types from .ato files get namespaced identifiers."""
        _, tg, _, result = _build_snippet(
            """
            module MyModule:
                pass
            """
        )

        assert "MyModule" in result.state.type_roots

        type_node = result.state.type_roots["MyModule"]
        type_name = fbrk.TypeGraph.get_type_name(type_node=type_node)
        assert type_name == "test/file.ato::MyModule"

    def test_python_types_not_namespaced(self):
        """Python stdlib types use unprefixed names."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        registry = StdlibRegistry(tg)

        node = registry.get("Resistor")
        type_name = fbrk.TypeGraph.get_type_name(type_node=node)
        assert "::" not in type_name

    def test_single_typegraph_for_build(self):
        """All types from a build share the same TypeGraph."""

        _, _, stdlib, result = _build_snippet(
            """
            import Resistor

            module App:
                r = new Resistor
            """
        )

        stdlib_type = stdlib.get("Resistor")
        user_type = result.state.type_roots["App"]

        stdlib_tg = fbrk.TypeGraph.of_type(type_node=stdlib_type)
        user_tg = fbrk.TypeGraph.of_type(type_node=user_type)

        assert stdlib_tg is not None
        assert user_tg is not None
        assert (
            stdlib_tg.get_self_node()
            .node()
            .is_same(other=user_tg.get_self_node().node())
        )


class TestEdgeTraversalPathResolution:
    """
    Tests for resolving paths through different edge types (Composition, Trait, Pointer)
    """

    def test_edge_traversal_helpers(self):
        """Test that Edge type traverse() methods create correct EdgeTraversals."""
        comp = EdgeComposition.traverse(identifier="child")
        assert comp.identifier == "child"
        assert comp.edge_type == fbrk.EdgeComposition.get_tid()

        trait = EdgeTrait.traverse(trait_type_name="my_trait")
        assert trait.identifier == "my_trait"
        assert trait.edge_type == fbrk.EdgeTrait.get_tid()

        ptr = EdgePointer.traverse()
        assert ptr.identifier == ""  # Pointer traverse has no identifier
        assert ptr.edge_type == fbrk.EdgePointer.get_tid()

    def test_string_path_backwards_compatible(self):
        """Test that string paths still work (default to Composition edges)."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        Electrical = tg.add_type(identifier="Electrical")
        Resistor = tg.add_type(identifier="Resistor")
        tg.add_make_child(type_node=Resistor, child_type=Electrical, identifier="p1")
        tg.add_make_child(type_node=Resistor, child_type=Electrical, identifier="p2")

        # String path should work
        ref = tg.ensure_child_reference(type_node=Resistor, path=["p1"], validate=False)
        assert ref is not None

        # Resolve against an instance
        resistor_instance = tg.instantiate_node(type_node=Resistor, attributes={})
        resolved = tg.reference_resolve(reference_node=ref, base_node=resistor_instance)
        assert resolved is not None

        # Verify it resolved to p1
        p1_instance = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=resistor_instance, child_identifier="p1"
        )
        assert resolved.node().is_same(other=not_none(p1_instance).node())

    def test_mixed_path_creates_reference_chain(self):
        """Test that EdgeTraversal creates reference chains with correct edge types.

        This test verifies the reference chain structure is correct.
        Full integration testing with instantiation can be done once
        the linker properly resolves all type references.
        """
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)

        # Get the stdlib Resistor type (which has can_bridge trait)
        Resistor = stdlib.get("Resistor")

        # Create a reference path with mixed edge types
        # This just creates the reference chain, doesn't resolve it
        ref = tg.ensure_child_reference(
            type_node=Resistor,
            path=[
                EdgeTrait.traverse(trait_type_name="can_bridge"),
                EdgeComposition.traverse(identifier="in_"),
                EdgePointer.traverse(),
            ],
            validate=False,
        )
        assert ref is not None

        # Verify we can get the reference path back
        # Note: get_reference_path only returns non-empty identifiers
        path = tg.get_reference_path(reference=ref)
        assert len(path) == 2
        assert path[0] == "can_bridge"
        assert path[1] == "in_"

    def test_composition_and_traversal_path(self):
        """Test creating reference chains with composition followed by EdgeTraversal.

        Verifies the reference chain structure includes composition segments
        (strings) followed by trait and pointer segments (EdgeTraversal).
        """
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)

        # Create a simple module type
        App = tg.add_type(identifier="TestApp")
        Resistor = stdlib.get("Resistor")

        # Add resistor as child
        tg.add_make_child(type_node=App, child_type=Resistor, identifier="r")

        # Create a reference path:
        # r (Composition) -> can_bridge (Trait) -> in_ (Composition) -> deref (Pointer)
        ref = tg.ensure_child_reference(
            type_node=App,
            path=[
                "r",  # String = Composition edge (default)
                EdgeTrait.traverse(trait_type_name="can_bridge"),
                EdgeComposition.traverse(identifier="in_"),
                EdgePointer.traverse(),
            ],
            validate=False,
        )
        assert ref is not None

        # Verify the path was stored correctly
        # Note: get_reference_path only returns non-empty identifiers
        path = tg.get_reference_path(reference=ref)
        assert len(path) == 3
        assert path[0] == "r"
        assert path[1] == "can_bridge"
        assert path[2] == "in_"


def _filter_directed_connect_links(make_links):
    """Filter make_links to only include directed connect links (via can_bridge).

    Excludes trait-related links that are automatically added to modules
    (like is_ato_block, is_ato_module, is_module).
    """
    return [
        (node, lhs, rhs) for node, lhs, rhs in make_links if lhs and "can_bridge" in lhs
    ]


class TestDirectedConnectStmt:
    """Tests for visit_DirectedConnectStmt in the AST visitor.

    These tests verify that directed connect statements (a ~> b, a <~ b)
    create the correct MakeLink references through can_bridge traits.
    """

    def test_simple_directed_connect_right_arrow(self):
        """Test a ~> b (Direction.RIGHT) creates correct links.

        Direction RIGHT (~>) means arrow points right, signal flows LHS → RHS:
        - a.can_bridge.out_ connects to b.can_bridge.in_
        """
        _, tg, stdlib, result = _build_snippet(
            """
            from "generics/resistors.ato" import Resistor

            module App:
                r1 = new Resistor
                r2 = new Resistor
                r1 ~> r2
            """
        )

        App = result.state.type_roots["App"]

        # Filter to only get directed connect links (exclude trait links)
        make_links = _filter_directed_connect_links(_collect_make_links(tg, App))
        assert len(make_links) == 1

        _, lhs_path, rhs_path = make_links[0]
        # LHS should be: r1 -> can_bridge -> out_
        assert lhs_path == ["r1", "can_bridge", "out_"]
        # RHS should be: r2 -> can_bridge -> in_
        assert rhs_path == ["r2", "can_bridge", "in_"]

    def test_simple_directed_connect_left_arrow(self):
        """Test a <~ b (Direction.LEFT) creates correct links.

        Direction LEFT (<~) means arrow points left, signal flows RHS → LHS:
        - a.can_bridge.in_ connects to b.can_bridge.out_
        """
        _, tg, stdlib, result = _build_snippet(
            """
            from "generics/resistors.ato" import Resistor

            module App:
                r1 = new Resistor
                r2 = new Resistor
                r1 <~ r2
            """
        )

        App = result.state.type_roots["App"]

        make_links = _filter_directed_connect_links(_collect_make_links(tg, App))
        assert len(make_links) == 1

        _, lhs_path, rhs_path = make_links[0]
        # Direction LEFT: LHS gets in_, RHS gets out_
        assert lhs_path == ["r1", "can_bridge", "in_"]
        assert rhs_path == ["r2", "can_bridge", "out_"]

    def test_chained_directed_connect(self):
        """Test a ~> b ~> c creates two connections.

        Should create:
        - a.can_bridge.out_ -> b.can_bridge.in_
        - b.can_bridge.out_ -> c.can_bridge.in_
        """
        _, tg, stdlib, result = _build_snippet(
            """
            from "generics/resistors.ato" import Resistor

            module App:
                r1 = new Resistor
                r2 = new Resistor
                r3 = new Resistor
                r1 ~> r2 ~> r3
            """
        )

        App = result.state.type_roots["App"]

        make_links = _filter_directed_connect_links(_collect_make_links(tg, App))
        assert len(make_links) == 2

        # Extract paths for comparison (order may vary)
        link_paths = {(tuple(lhs), tuple(rhs)) for _, lhs, rhs in make_links}

        # First link: r1.out -> r2.in
        assert (
            ("r1", "can_bridge", "out_"),
            ("r2", "can_bridge", "in_"),
        ) in link_paths

        # Second link: r2.out -> r3.in
        assert (
            ("r2", "can_bridge", "out_"),
            ("r3", "can_bridge", "in_"),
        ) in link_paths

    def test_longer_chain(self):
        """Test a ~> b ~> c ~> d creates three connections."""
        _, tg, stdlib, result = _build_snippet(
            """
            from "generics/resistors.ato" import Resistor

            module App:
                r1 = new Resistor
                r2 = new Resistor
                r3 = new Resistor
                r4 = new Resistor
                r1 ~> r2 ~> r3 ~> r4
            """
        )

        App = result.state.type_roots["App"]

        make_links = _filter_directed_connect_links(_collect_make_links(tg, App))
        assert len(make_links) == 3

        link_paths = {(tuple(lhs), tuple(rhs)) for _, lhs, rhs in make_links}

        # Verify all expected connections exist
        expected = [
            (("r1", "can_bridge", "out_"), ("r2", "can_bridge", "in_")),
            (("r2", "can_bridge", "out_"), ("r3", "can_bridge", "in_")),
            (("r3", "can_bridge", "out_"), ("r4", "can_bridge", "in_")),
        ]
        for lhs_expected, rhs_expected in expected:
            assert (lhs_expected, rhs_expected) in link_paths
