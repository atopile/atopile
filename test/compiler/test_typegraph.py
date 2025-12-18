import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
from atopile.compiler.ast_visitor import DslException
from atopile.compiler.build import (
    Linker,
    StdlibRegistry,
    UndefinedSymbolError,
    build_file,
)
from atopile.errors import UserSyntaxError
from faebryk.libs.util import not_none
from test.compiler.conftest import build_type

NULL_CONFIG = SimpleNamespace(project=None)


def _get_make_child(type_graph: fbrk.TypeGraph, type_node: graph.BoundNode, name: str):
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


def _collect_children_by_name(
    type_graph: fbrk.TypeGraph, type_node: graph.BoundNode, name: str
):
    return [
        child
        for identifier, child in type_graph.collect_make_children(type_node=type_node)
        if identifier is not None and name in identifier
    ]


# TODO FIXME there's a lot of illegal use of for loops and connecting resistors together
# especially in the for loop tests


def test_block_definitions_recorded():
    _, _, _, result = build_type(
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
    graph, tg, stdlib, result = build_type(
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

    linker = Linker(NULL_CONFIG, stdlib, tg)
    linker.link_imports(graph, result.state)

    unresolved = fbrk.Linker.collect_unresolved_type_references(type_graph=tg)
    assert not unresolved

    type_ref = type_graph.get_make_child_type_reference(make_child=res_node)
    assert type_ref is not None
    resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
    assert resolved is not None


def test_new_with_count_creates_pointer_sequence():
    g, tg, _, result = build_type(
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
    for idx in ["members[0]", "members[1]", "members[2]"]:
        element_nodes.append(_get_make_child(tg, app_type, idx))
        ref = tg.ensure_child_reference(
            type_node=app_type,
            path=[idx],
            validate=True,
        )
        assert ref is not None
    assert len(element_nodes) == 3


def test_new_with_count_children_have_mounts():
    g, tg, _, result = build_type(
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

    for idx in ["members[0]", "members[1]"]:
        elem_node = _get_make_child(tg, app_type, idx)
        assert tg.debug_get_mount_chain(make_child=elem_node) == []


def test_new_with_count_rejects_out_of_range_index():
    with pytest.raises(
        DslException,
        match=r"Field `members\[(2|2\.0)\]` is not defined in scope",
    ):
        build_type(
            """
            module Inner:
                pass

            module App:
                members = new Inner[2]
                members[2] = new Inner
            """
        )


def test_typegraph_path_error_metadata():
    g, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
        build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
        build_type(
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
    _, tg, _, result = build_type(
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
        build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
        build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
        build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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
        build_type(
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
    _, tg, _, result = build_type(
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
    _, tg, _, result = build_type(
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


def test_nested_connect_missing_prefix_raises():
    with pytest.raises(
        DslException, match=r"Field `left\.missing\.branch` is not defined in scope"
    ):
        build_type(
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
        build_type(
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
        build_type(
            """
            import Resistor

            module Resistor:
                pass
            """
        )


def test_multiple_local_references():
    """Multiple uses of the same local type should resolve to the same node."""
    _, tg, _, result = build_type(
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


def test_forward_reference():
    # confirm in-order
    build_type(
        """
        module Child:
            pass

        module App:
            child = new Child
        """,
        link=True,
    )

    # no defintion later -> error
    with pytest.raises(UndefinedSymbolError):
        build_type(
            """
            module App:
                child = new Child
            """,
            link=True,
        )

    # out-of-order (forward reference)
    _, tg, _, result = build_type(
        """
        module App:
            child = new Child

        module Child:
            pass
        """,
        link=True,
    )

    app_type = result.state.type_roots["App"]
    child_node = _get_make_child(tg, app_type, "child")
    type_ref = tg.get_make_child_type_reference(make_child=child_node)
    assert type_ref is not None
    resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
    assert resolved is not None


class TestTypeNamespacing:
    """Tests for .ato type namespacing."""

    def test_ato_types_namespaced(self):
        """Types from .ato files get namespaced identifiers."""
        _, tg, _, result = build_type(
            """
            module MyModule:
                pass
            """,
            import_path="test/file.ato",
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

        _, _, stdlib, result = build_type(
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
        comp = fbrk.EdgeComposition.traverse(identifier="child")
        assert comp.identifier == "child"
        assert comp.edge_type == fbrk.EdgeComposition.get_tid()

        trait = fbrk.EdgeTrait.traverse(trait_type_name="my_trait")
        assert trait.identifier == "my_trait"
        assert trait.edge_type == fbrk.EdgeTrait.get_tid()

        ptr = fbrk.EdgePointer.traverse()
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
                fbrk.EdgeTrait.traverse(trait_type_name="can_bridge"),
                fbrk.EdgeComposition.traverse(identifier="in_"),
                fbrk.EdgePointer.traverse(),
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
                fbrk.EdgeTrait.traverse(trait_type_name="can_bridge"),
                fbrk.EdgeComposition.traverse(identifier="in_"),
                fbrk.EdgePointer.traverse(),
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


class TestCanBridgeByNameShim:
    """Tests for can_bridge_by_name trait shim.

    The can_bridge_by_name trait is a backwards-compatibility shim that translates
    to a can_bridge trait with the correct pointer paths. This allows ato code like:
        trait can_bridge_by_name<input_name="data_in", output_name="data_out">
    to create a can_bridge trait pointing to the named children.
    """

    def test_can_bridge_by_name_creates_can_bridge_trait(self):
        """Test that can_bridge_by_name creates a can_bridge trait."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("BRIDGE_CONNECT")

            import ElectricLogic
            import can_bridge_by_name

            module TestBridge:
                data_in = new ElectricLogic
                data_out = new ElectricLogic

                trait can_bridge_by_name<input_name="data_in", output_name="data_out">
            """,
            link=True,
        )

        test_bridge = result.state.type_roots["TestBridge"]

        # The can_bridge trait should have been created (named "can_bridge", not
        # "can_bridge_by_name")
        make_children = list(tg.collect_make_children(type_node=test_bridge))
        trait_names = [name for name, _ in make_children if name is not None]

        # Should have _trait_self_can_bridge (the shimmed trait)
        assert any("can_bridge" in name for name in trait_names), (
            f"Expected can_bridge trait, got: {trait_names}"
        )

    def test_can_bridge_by_name_with_default_names(self):
        """Test can_bridge_by_name with default input/output names."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("BRIDGE_CONNECT")

            import ElectricLogic
            import can_bridge_by_name

            module TestBridge:
                input = new ElectricLogic
                output = new ElectricLogic

                trait can_bridge_by_name
            """,
            link=True,
        )

        test_bridge = result.state.type_roots["TestBridge"]
        make_children = list(tg.collect_make_children(type_node=test_bridge))
        trait_names = [name for name, _ in make_children if name is not None]

        # Should have can_bridge trait with default paths to "input" and "output"
        assert any("can_bridge" in name for name in trait_names), (
            f"Expected can_bridge trait, got: {trait_names}"
        )

    def test_can_bridge_by_name_enables_directed_connect(self):
        """Test that can_bridge_by_name enables ~> syntax for custom modules."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("BRIDGE_CONNECT")

            import ElectricLogic
            import can_bridge_by_name

            module BridgeableModule:
                data_in = new ElectricLogic
                data_out = new ElectricLogic
                trait can_bridge_by_name<input_name="data_in", output_name="data_out">

            module App:
                a = new ElectricLogic
                b = new BridgeableModule
                c = new ElectricLogic

                a ~> b ~> c
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]

        # Verify directed connections were made through can_bridge
        make_links = _filter_directed_connect_links(_collect_make_links(tg, app_type))
        assert len(make_links) == 2, f"Expected 2 directed links, got {len(make_links)}"

        link_paths = {(tuple(lhs), tuple(rhs)) for _, lhs, rhs in make_links}

        # a.can_bridge.out_ -> b.can_bridge.in_ (which points to b.data_in)
        # b.can_bridge.out_ (which points to b.data_out) -> c.can_bridge.in_
        expected = {
            (("a", "can_bridge", "out_"), ("b", "can_bridge", "in_")),
            (("b", "can_bridge", "out_"), ("c", "can_bridge", "in_")),
        }
        assert link_paths == expected, f"Expected {expected}, got {link_paths}"


class TestHasDatasheetDefinedShim:
    """Tests for has_datasheet_defined trait shim.

    The has_datasheet_defined trait is a backwards-compatibility shim that translates
    to a has_datasheet trait. This allows ato code like:
        trait has_datasheet_defined<datasheet="https://example.com/ds.pdf">
    to create a has_datasheet trait with the specified datasheet URL.
    """

    def test_has_datasheet_defined_creates_has_datasheet_trait(self):
        """Test that has_datasheet_defined creates a has_datasheet trait."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")

            import has_datasheet_defined

            module TestPart:
                trait has_datasheet_defined<datasheet="https://example.com/ds.pdf">
            """,
            link=True,
        )

        test_part = result.state.type_roots["TestPart"]

        # The has_datasheet trait should have been created (named "has_datasheet",
        # not "has_datasheet_defined")
        make_children = list(tg.collect_make_children(type_node=test_part))
        trait_names = [name for name, _ in make_children if name is not None]

        # Should have _trait_self_has_datasheet (the shimmed trait)
        assert any("has_datasheet" in name for name in trait_names), (
            f"Expected has_datasheet trait, got: {trait_names}"
        )

    def test_has_datasheet_defined_requires_datasheet_arg(self):
        """Test that has_datasheet_defined requires a datasheet argument."""
        from atopile.compiler.ast_visitor import DslException

        with pytest.raises(DslException, match="requires a 'datasheet'"):
            build_type(
                """
                #pragma experiment("TRAITS")

                import has_datasheet_defined

                module TestPart:
                    trait has_datasheet_defined
                """,
                link=True,
            )


class TestHasSingleElectricReferenceSharedShim:
    """Tests for has_single_electric_reference_shared trait shim.

    The has_single_electric_reference_shared trait is a backwards-compatibility shim
    that translates to has_single_electric_reference. It also translates the
    `gnd_only` parameter to `ground_only`.
    """

    def test_has_single_electric_reference_shared_creates_trait(self):
        """Test that has_single_electric_reference_shared creates the correct trait."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")

            import has_single_electric_reference_shared

            module TestModule:
                trait has_single_electric_reference_shared<gnd_only=True>
            """,
            link=True,
        )

        test_module = result.state.type_roots["TestModule"]

        # The has_single_electric_reference trait should have been created
        make_children = list(tg.collect_make_children(type_node=test_module))
        trait_names = [name for name, _ in make_children if name is not None]

        # Should have has_single_electric_reference (the shimmed trait)
        assert any("has_single_electric_reference" in name for name in trait_names), (
            f"Expected has_single_electric_reference trait, got: {trait_names}"
        )

    def test_has_single_electric_reference_shared_default_gnd_only(self):
        """Test has_single_electric_reference_shared without gnd_only argument."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")

            import has_single_electric_reference_shared

            module TestModule:
                trait has_single_electric_reference_shared
            """,
            link=True,
        )

        test_module = result.state.type_roots["TestModule"]
        make_children = list(tg.collect_make_children(type_node=test_module))
        trait_names = [name for name, _ in make_children if name is not None]

        # Should have has_single_electric_reference
        assert any("has_single_electric_reference" in name for name in trait_names), (
            f"Expected has_single_electric_reference trait, got: {trait_names}"
        )


class TestConnectOverrides:
    """Tests for ConnectOverrides path translation shim.

    The ConnectOverrides class translates legacy path names in connect statements:
    - `vcc` -> `hv` (high voltage rail on ElectricPower)
    - `gnd` -> `lv` (low voltage rail on ElectricPower)
    """

    def test_vcc_translated_to_hv(self):
        """Test that .vcc is translated to .hv in connect statements."""
        _, tg, _, result = build_type(
            """
            import ElectricPower
            import Electrical

            module App:
                power = new ElectricPower
                e = new Electrical

                # Using legacy vcc naming - should be translated to hv
                e ~ power.vcc
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        make_links = _collect_make_links(tg, app_type)

        # Filter to the actual connect: e ~ power.hv (look for "power" in rhs)
        connect_links = [
            (lhs, rhs) for _, lhs, rhs in make_links if rhs and "power" in rhs
        ]
        assert len(connect_links) == 1

        lhs_path, rhs_path = connect_links[0]
        # The path should have "hv" not "vcc"
        assert "hv" in rhs_path, f"Expected 'hv' in {rhs_path}"
        assert "vcc" not in rhs_path, "vcc should have been translated to hv"

    def test_gnd_translated_to_lv(self):
        """Test that .gnd is translated to .lv in connect statements."""
        _, tg, _, result = build_type(
            """
            import ElectricPower
            import Electrical

            module App:
                power = new ElectricPower
                e = new Electrical

                # Using legacy gnd naming - should be translated to lv
                e ~ power.gnd
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        make_links = _collect_make_links(tg, app_type)

        # Filter to the actual connect: e ~ power.lv (look for "power" in rhs)
        connect_links = [
            (lhs, rhs) for _, lhs, rhs in make_links if rhs and "power" in rhs
        ]
        assert len(connect_links) == 1

        lhs_path, rhs_path = connect_links[0]
        # The path should have "lv" not "gnd"
        assert "lv" in rhs_path, f"Expected 'lv' in {rhs_path}"
        assert "gnd" not in rhs_path, "gnd should have been translated to lv"

    def test_non_legacy_paths_unchanged(self):
        """Test that paths without legacy names are not modified."""
        _, tg, _, result = build_type(
            """
            import ElectricPower
            import Electrical

            module App:
                power = new ElectricPower
                e = new Electrical

                # Using current naming - should be unchanged
                e ~ power.hv
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        make_links = _collect_make_links(tg, app_type)

        # Filter to the actual connect: e ~ power.hv (look for "power" in rhs)
        connect_links = [
            (lhs, rhs) for _, lhs, rhs in make_links if rhs and "power" in rhs
        ]
        assert len(connect_links) == 1

        lhs_path, rhs_path = connect_links[0]
        assert "hv" in rhs_path, f"Expected 'hv' in {rhs_path}"


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
        _, tg, stdlib, result = build_type(
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
        _, tg, stdlib, result = build_type(
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
        _, tg, stdlib, result = build_type(
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
        _, tg, stdlib, result = build_type(
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


class TestSignalsAndPins:
    """Tests for signal and pin declarations in the compiler."""

    def test_signal_declaration_creates_electrical_child(self):
        """Signal declaration creates an Electrical child with the signal name."""
        _, tg, _, result = build_type(
            """
            module App:
                signal my_sig
            """
        )

        app_type = result.state.type_roots["App"]
        my_sig_node = _get_make_child(tg, app_type, "my_sig")
        assert my_sig_node is not None

    def test_signal_declaration_as_statement(self):
        """Signal declaration works as a standalone statement."""
        _, tg, _, result = build_type(
            """
            module App:
                signal first
                signal second
            """
        )

        app_type = result.state.type_roots["App"]
        first_node = _get_make_child(tg, app_type, "first")
        second_node = _get_make_child(tg, app_type, "second")
        assert first_node is not None
        assert second_node is not None

    def test_signal_duplicate_raises(self):
        """Duplicate signal declaration raises an error."""
        with pytest.raises(DslException, match="already defined"):
            build_type(
                """
                module App:
                    signal my_sig
                    signal my_sig
                """
            )

    def test_pin_declaration_creates_child(self):
        """Pin declaration creates a child with is_lead trait."""
        _, tg, _, result = build_type(
            """
            component MyComp:
                pin 1
            """
        )

        comp_type = result.state.type_roots["MyComp"]
        pin_node = _get_make_child(tg, comp_type, "1")
        assert pin_node is not None

    def test_pin_declaration_with_name(self):
        """Pin declaration with name works."""
        _, tg, _, result = build_type(
            """
            component MyComp:
                pin vcc
            """
        )

        comp_type = result.state.type_roots["MyComp"]
        pin_node = _get_make_child(tg, comp_type, "vcc")
        assert pin_node is not None

    def test_pin_declaration_with_string(self):
        """Pin declaration with string label works."""
        _, tg, _, result = build_type(
            """
            component MyComp:
                pin "GND"
            """
        )

        comp_type = result.state.type_roots["MyComp"]
        pin_node = _get_make_child(tg, comp_type, "GND")
        assert pin_node is not None

    def test_signal_connect_to_field(self):
        """Signal can be connected to an existing field."""
        _, tg, _, result = build_type(
            """
            import Electrical

            module App:
                e = new Electrical
                signal my_sig
                my_sig ~ e
            """
        )

        app_type = result.state.type_roots["App"]

        assert _check_make_links(
            tg=tg,
            type_node=app_type,
            expected=[(["my_sig"], ["e"])],
        )

    def test_inline_signal_in_connect(self):
        """Signal can be declared inline in a connect statement."""
        _, tg, _, result = build_type(
            """
            import Electrical

            module App:
                e = new Electrical
                signal s ~ e
            """
        )

        app_type = result.state.type_roots["App"]

        # Verify signal was created
        sig_node = _get_make_child(tg, app_type, "s")
        assert sig_node is not None

        # Verify connection was made
        assert _check_make_links(
            tg=tg,
            type_node=app_type,
            expected=[(["s"], ["e"])],
        )

    def test_inline_pin_in_connect(self):
        """Pin can be declared inline in a connect statement."""
        _, tg, _, result = build_type(
            """
            import Electrical

            component MyComp:
                e = new Electrical
                e ~ pin 1
            """
        )

        comp_type = result.state.type_roots["MyComp"]

        # Verify pin was created
        pin_node = _get_make_child(tg, comp_type, "1")
        assert pin_node is not None

        # Verify connection was made
        assert _check_make_links(
            tg=tg,
            type_node=comp_type,
            expected=[(["e"], ["1"])],
        )

    def test_signal_to_pin_connect(self):
        """Signal can connect to pin using ~ operator."""
        _, tg, _, result = build_type(
            """
            component MyComp:
                signal my_sig ~ pin 1
            """
        )

        comp_type = result.state.type_roots["MyComp"]

        # Verify both signal and pin were created
        sig_node = _get_make_child(tg, comp_type, "my_sig")
        pin_node = _get_make_child(tg, comp_type, "1")
        assert sig_node is not None
        assert pin_node is not None

        # Verify connection was made
        assert _check_make_links(
            tg=tg,
            type_node=comp_type,
            expected=[(["my_sig"], ["1"])],
        )

    def test_multiple_pins_different_types(self):
        """Multiple pins with different label types work."""
        _, tg, _, result = build_type(
            """
            component MyComp:
                pin 1
                pin vcc
                pin "GND"
            """
        )

        comp_type = result.state.type_roots["MyComp"]

        # Verify all pins were created
        pin_1 = _get_make_child(tg, comp_type, "1")
        pin_vcc = _get_make_child(tg, comp_type, "vcc")
        pin_gnd = _get_make_child(tg, comp_type, "GND")

        assert pin_1 is not None
        assert pin_vcc is not None
        assert pin_gnd is not None

    def test_inline_signal_in_directed_connect(self):
        """Inline signals work in directed connect statements."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("BRIDGE_CONNECT")

            module App:
                signal a ~> signal b
            """
        )

        app_type = result.state.type_roots["App"]

        # Verify both signals were created
        sig_a = _get_make_child(tg, app_type, "a")
        sig_b = _get_make_child(tg, app_type, "b")
        assert sig_a is not None
        assert sig_b is not None

        # Verify directed connection was made through can_bridge
        make_links = _filter_directed_connect_links(_collect_make_links(tg, app_type))
        assert len(make_links) == 1

        _, lhs_path, rhs_path = make_links[0]
        assert lhs_path == ["a", "can_bridge", "out_"]
        assert rhs_path == ["b", "can_bridge", "in_"]

    def test_inline_pin_in_directed_connect(self):
        """Inline pins work in directed connect statements."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("BRIDGE_CONNECT")

            component MyComp:
                pin 1 ~> pin 2
            """
        )

        comp_type = result.state.type_roots["MyComp"]

        # Verify both pins were created
        pin_1 = _get_make_child(tg, comp_type, "1")
        pin_2 = _get_make_child(tg, comp_type, "2")
        assert pin_1 is not None
        assert pin_2 is not None

        # Verify directed connection was made through can_bridge
        make_links = _filter_directed_connect_links(_collect_make_links(tg, comp_type))
        assert len(make_links) == 1

        _, lhs_path, rhs_path = make_links[0]
        assert lhs_path == ["1", "can_bridge", "out_"]
        assert rhs_path == ["2", "can_bridge", "in_"]

    def test_chained_directed_connect_with_inline_signal(self):
        """Chained directed connect with inline signal in the middle works.

        Tests that `a ~> signal b ~> c` correctly creates signal b once
        and connects a->b and b->c.
        """
        _, tg, _, result = build_type(
            """
            #pragma experiment("BRIDGE_CONNECT")
            import Resistor

            module App:
                r1 = new Resistor
                r2 = new Resistor
                r1 ~> signal mid ~> r2
            """
        )

        app_type = result.state.type_roots["App"]

        # Verify signal was created (only once!)
        mid_sig = _get_make_child(tg, app_type, "mid")
        assert mid_sig is not None

        # Verify both connections were made
        make_links = _filter_directed_connect_links(_collect_make_links(tg, app_type))
        assert len(make_links) == 2

        link_paths = {(tuple(lhs), tuple(rhs)) for _, lhs, rhs in make_links}
        expected = {
            (("r1", "can_bridge", "out_"), ("mid", "can_bridge", "in_")),
            (("mid", "can_bridge", "out_"), ("r2", "can_bridge", "in_")),
        }
        assert link_paths == expected


# see src/atopile/compiler/parser/AtoLexer.g4
@pytest.mark.parametrize(
    "name,template",
    [
        (name, textwrap.dedent(template))
        for name in [
            "component",
            "module",
            "interface",
            "pin",
            "signal",
            "new",
            "from",
            "import",
            "for",
            "in",
            "assert",
            "to",
            "True",
            "False",
            "within",
            "is",
            "pass",
            "trait",
            "int",
            "float",
            "string",
            "str",
            "bytes",
            "if",
            "parameter",
            "param",
            "test",
            "require",
            "requires",
            "check",
            "report",
            "ensure",
        ]
        for template in [
            """
            module App:
                {name} = 10
            """,
            """
            import {name}
            """,
            """
            component {name}:
                pass
            """,
            """
            module {name}:
                pass
            """,
            """
            interface {name}:
                pass
            """,
        ]
    ],
)
def test_reserved_keywords_as_identifiers(name: str, template: str):
    template = textwrap.dedent(template)

    # ensure template is otherwise valid
    # note requires a valid import symbol
    build_type(template.format(name="Resistor"))

    with pytest.raises(UserSyntaxError):
        build_type(template.format(name=name))


class TestTraitStatements:
    def test_simple_trait_on_self(self):
        """Trait statement with no target attaches trait to enclosing block."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            import is_pickable

            module MyModule:
                pass
                trait is_pickable
            """
        )

        my_module_type = result.state.type_roots["MyModule"]

        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=my_module_type)
        ]
        trait_children = [
            (identifier, child)
            for identifier, child in make_children
            if identifier and "is_pickable" in identifier
        ]
        assert len(trait_children) == 1

    def test_trait_on_child_field(self):
        """Trait statement with target attaches trait to specified child."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            import is_pickable
            import Resistor

            module MyModule:
                r1 = new Resistor
                trait r1 is_pickable
            """
        )

        my_module_type = result.state.type_roots["MyModule"]

        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=my_module_type)
        ]
        assert any(identifier == "r1" for identifier, _ in make_children)
        trait_children = [
            (identifier, child)
            for identifier, child in make_children
            if identifier and "is_pickable" in identifier
        ]
        assert len(trait_children) == 1

    def test_trait_requires_experiment_flag(self):
        """Trait statement without experiment pragma raises error."""
        with pytest.raises(DslException, match="TRAITS.*not enabled"):
            build_type(
                """
                import is_pickable

                module MyModule:
                    trait is_pickable
                """
            )

    def test_trait_requires_import(self):
        """Trait statement without importing the trait raises error."""
        with pytest.raises(DslException, match="must be imported"):
            build_type(
                """
                #pragma experiment("TRAITS")

                module MyModule:
                    trait is_pickable
                """,
                link=True,
            )

    def test_trait_on_undefined_field_raises(self):
        """Trait applied to undefined field raises error."""
        with pytest.raises(DslException, match="not defined in scope"):
            build_type(
                """
                #pragma experiment("TRAITS")
                import is_pickable

                module MyModule:
                    trait undefined_field is_pickable
                """
            )

    def test_trait_with_template_args(self):
        """Trait with template arguments creates trait and constraint children."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            import is_atomic_part

            component MyComponent:
                trait is_atomic_part<manufacturer="Murata", partnumber="GRM123", footprint="C0805.kicad_mod", symbol="cap.kicad_sym">
            """  # noqa: E501
        )

        comp_type = result.state.type_roots["MyComponent"]

        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=comp_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_is_atomic_part" in identifiers
        constraint_ids = [id for id in identifiers if id.startswith("constrain_")]
        assert len(constraint_ids) == 4

    def test_trait_with_multiple_template_args(self):
        """Trait with all template arguments including optional model."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            import is_atomic_part

            component FullPart:
                trait is_atomic_part<manufacturer="Test Inc", partnumber="PN-001", footprint="fp.kicad_mod", symbol="sym.kicad_sym", model="part.step">
            """  # noqa: E501
        )

        comp_type = result.state.type_roots["FullPart"]
        make_children = list(tg.collect_make_children(type_node=comp_type))
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_is_atomic_part" in identifiers
        constraint_ids = [id for id in identifiers if id.startswith("constrain_")]
        assert len(constraint_ids) == 5

    def test_trait_template_args_create_constraints(self):
        """Template args create constraint child fields on the type."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("TRAITS")
            import is_atomic_part

            component ConstrainedPart:
                trait is_atomic_part<manufacturer="ACME", partnumber="12345", footprint="fp.mod", symbol="sym.sym">
            """  # noqa: E501
        )

        comp_type = result.state.type_roots["ConstrainedPart"]
        make_children = list(tg.collect_make_children(type_node=comp_type))
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_is_atomic_part" in identifiers
        constraint_ids = [id for id in identifiers if id.startswith("constrain_")]
        assert len(constraint_ids) == 4

    def test_trait_template_args_literal_values(self):
        """Template args constrain trait parameters to expected literal values."""
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from atopile.compiler.build import Linker

        g, tg, stdlib, result = build_type(
            """
            #pragma experiment("TRAITS")
            import is_atomic_part

            component ConstrainedPart:
                trait is_atomic_part<manufacturer="ACME Corp", partnumber="PN-99", footprint="fp.kicad_mod", symbol="sym.kicad_sym">
            """  # noqa: E501
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        comp_type = result.state.type_roots["ConstrainedPart"]
        comp_instance = tg.instantiate_node(type_node=comp_type, attributes={})

        part = fabll.Node.bind_instance(comp_instance)
        trait = part.get_trait(F.is_atomic_part)

        assert trait.get_manufacturer() == "ACME Corp"
        assert trait.get_partnumber() == "PN-99"
        assert trait.get_footprint() == "fp.kicad_mod"
        assert trait.get_symbol() == "sym.kicad_sym"


# FIXME: break up
def test_literal_assignment():
    import logging

    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.node as fabll
    import faebryk.library._F as F
    from faebryk.libs.util import not_none

    logging.basicConfig(level=logging.DEBUG)
    g, tg, stdlib, result = build_type(
        """
        import Resistor
        import is_atomic_part

        module App:
            r1 = new Resistor
            r1.max_power = 3 mW
            r1.resistance = 10ohm to 20ohm
            assert r1.max_voltage within 25 volt to 100 volt

            r2 = new Resistor
            r2.resistance = 100 ohm +/- 5%
            r2.max_power = 3 watt to 5 watt
            assert r2.max_voltage within 100kV +/- 1%

            atomic_part = new is_atomic_part
            atomic_part.footprint = "R_0402"
        """
    )

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    app_type_node = result.state.type_roots["App"]

    app_instance = fabll.Node(
        tg.instantiate_node(type_node=app_type_node, attributes={})
    )
    r1_bnode = fbrk.EdgeComposition.get_child_by_identifier(
        bound_node=app_instance.instance, child_identifier="r1"
    )
    r2_bnode = fbrk.EdgeComposition.get_child_by_identifier(
        bound_node=app_instance.instance, child_identifier="r2"
    )
    r1 = F.Resistor.bind_instance(not_none(r1_bnode))

    assert r1.max_power.get().force_extract_literal_subset().get_single() == 3
    assert (
        r1.max_power.get()
        .force_extract_literal_subset()
        .get_is_unit()
        ._extract_multiplier()
        == 0.001
    )
    assert fabll.Traits(r1.max_power.get().get_units()).get_obj(F.Units.Watt)
    assert r1.resistance.get().force_extract_literal_subset().get_values() == [
        10.0,
        20.0,
    ]
    assert r1.max_voltage.get().force_extract_literal_subset().get_values() == [
        25.0,
        100.0,
    ]

    r2 = F.Resistor.bind_instance(not_none(r2_bnode))
    assert r2.resistance.get().force_extract_literal_subset().get_values() == [
        95.0,
        105.0,
    ]
    assert r2.max_power.get().force_extract_literal_subset().get_values() == [3, 5]
    assert r2.max_voltage.get().force_extract_literal_subset().get_values() == [99, 101]
    assert (
        r2.max_voltage.get()
        .force_extract_literal_subset()
        .get_is_unit()
        ._extract_multiplier()
        == 1000
    )

    # atomic_party_bnode = fbrk.EdgeComposition.get_child_by_identifier(
    #     bound_node=app_instance.instance, child_identifier="atomic_part"
    # )
    # atomic_party = F.is_atomic_part.bind_instance(not_none(atomic_party_bnode))

    # assert (
    #     # TODO: This accessor pattern is crazy
    #     fabll.Traits(
    #         atomic_party.footprint.get()
    #         .is_parameter_operatable.get()
    #         .try_extract_literal(allow_subset=True)
    #     )
    #     .get_obj(F.Literals.Strings)
    #     .get_single()
    #     == "R_0402"
    # )


class TestModuleTemplating:
    """Test module templating with parameterized modules like Addressor."""

    def test_module_templating_requires_experiment_flag(self):
        """Module templating without experiment flag should fail."""
        with pytest.raises(DslException, match="(?i)experiment"):
            build_type(
                """
                import Addressor

                module App:
                    addressor = new Addressor<address_bits=2>
                """
            )

    def test_module_templating_basic(self):
        """Basic module templating creates the templated child."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("MODULE_TEMPLATING")
            import Addressor

            module App:
                addressor = new Addressor<address_bits=3>
            """
        )

        app_type = result.state.type_roots["App"]
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "addressor" in identifiers

    def test_module_templating_with_integer_arg(self):
        """Module templating with integer argument works correctly."""
        import faebryk.core.node as fabll
        from atopile.compiler.build import Linker

        g, tg, stdlib, result = build_type(
            """
            #pragma experiment("MODULE_TEMPLATING")
            import Addressor

            module App:
                addressor = new Addressor<address_bits=4>
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type = result.state.type_roots["App"]

        # Get the addressor MakeChild node
        addressor_make_child = _get_make_child(tg, app_type, "addressor")
        assert addressor_make_child is not None

        # Get the actual type from the MakeChild
        mc = fabll.MakeChild.bind_instance(addressor_make_child)
        addressor_type = mc.get_child_type()

        # Check addressor type has address_lines children (4 lines for address_bits=4)
        address_lines = [
            identifier
            for identifier, child in tg.collect_make_children(type_node=addressor_type)
            if identifier is not None and identifier.startswith("address_lines")
        ]
        assert len(address_lines) == 4

    def test_module_templating_array_with_template(self):
        """Module templating works with array instantiation."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("MODULE_TEMPLATING")
            import Addressor

            module App:
                addressors = new Addressor[3]<address_bits=2>
            """
        )

        app_type = result.state.type_roots["App"]
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        # Should have the pointer sequence and individual elements
        assert "addressors" in identifiers
        assert "addressors[0]" in identifiers
        assert "addressors[1]" in identifiers
        assert "addressors[2]" in identifiers

    def test_module_templating_multiple_templated_instances(self):
        """Multiple templated instances with different parameters."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("MODULE_TEMPLATING")
            import Addressor

            module App:
                addressor2 = new Addressor<address_bits=2>
                addressor4 = new Addressor<address_bits=4>
            """
        )

        app_type = result.state.type_roots["App"]
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "addressor2" in identifiers
        assert "addressor4" in identifiers

    def test_module_templating_float_to_int_conversion(self):
        """Template args that are whole-number floats are converted to int."""
        import faebryk.core.node as fabll
        from atopile.compiler.build import Linker

        g, tg, stdlib, result = build_type(
            """
            #pragma experiment("MODULE_TEMPLATING")
            import Addressor

            module App:
                addressor = new Addressor<address_bits=3>
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type = result.state.type_roots["App"]

        # Get the addressor MakeChild node
        addressor_make_child = _get_make_child(tg, app_type, "addressor")
        assert addressor_make_child is not None

        # Get the actual type from the MakeChild
        mc = fabll.MakeChild.bind_instance(addressor_make_child)
        addressor_type = mc.get_child_type()

        # Should have 3 address lines (float 3.0 converted to int 3)
        address_lines = [
            identifier
            for identifier, child in tg.collect_make_children(type_node=addressor_type)
            if identifier is not None and identifier.startswith("address_lines")
        ]
        assert len(address_lines) == 3


class TestAssignmentOverride:
    """Test assignment override functionality for legacy sugar syntax."""

    def test_required_true_attaches_trait(self):
        """Verify `power.required = True` attaches requires_external_usage trait."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            """
            import ElectricPower

            module App:
                power = new ElectricPower
                power.required = True
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_power_requires_external_usage" in identifiers

        # Check that the trait was linked to the power interface
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["power"], ["_trait_power_requires_external_usage"])],
        )

        # Instantiate and verify get_owner_node_of works
        from faebryk.core.faebrykpy import EdgeComposition
        from faebryk.libs.util import not_none

        app_instance = tg.instantiate_node(type_node=app_type, attributes={})

        # Get the power child
        power_node = not_none(
            EdgeComposition.get_child_by_identifier(
                bound_node=app_instance, child_identifier="power"
            )
        )

        # Get the trait instance on power
        trait_instance = fabll.Node.bind_instance(instance=power_node).get_trait(
            F.requires_external_usage
        )

        # Check that get_owner_node_of can find the owner
        owner = fbrk.EdgeTrait.get_owner_node_of(bound_node=trait_instance.instance)
        assert owner is not None, "EdgeTrait.get_owner_node_of returned None!"

    def test_required_false_is_noop(self):
        """Verify `power.required = False` does not attach any trait."""
        _, tg, _, result = build_type(
            """
            import ElectricPower

            module App:
                power = new ElectricPower
                power.required = False
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that no requires_external_usage trait was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_requires_external_usage" not in identifiers

    def test_package_imperial_format(self):
        """Test `package = "0402"` creates has_package_requirements trait."""
        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                resistor = new Resistor
                resistor.package = "0402"
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_resistor_has_package_requirements" in identifiers

        # Check that the trait was linked to the resistor
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["resistor"], ["_trait_resistor_has_package_requirements"])],
        )

    def test_package_with_prefix(self):
        """Test `package = "R0402"` strips R prefix and works correctly."""
        _, tg, _, result = build_type(
            """
            import Resistor

            module App:
                resistor = new Resistor
                resistor.package = "R0402"
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_resistor_has_package_requirements" in identifiers

    def test_package_invalid_raises(self):
        """Test invalid package string raises DslException."""
        with pytest.raises(DslException, match="Invalid package"):
            build_type(
                """
                import Resistor

                module App:
                    resistor = new Resistor
                    resistor.package = "INVALID_SIZE"
                """
            )

    def test_lcsc_id_attaches_trait(self):
        """Verify `node.lcsc_id = "C12345"` attaches has_explicit_part trait."""
        _, tg, _, result = build_type(
            """
            import Resistor

            module App:
                resistor = new Resistor
                resistor.lcsc_id = "C12345"
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_resistor_has_explicit_part" in identifiers

        # Check that the trait was linked to the resistor
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["resistor"], ["_trait_resistor_has_explicit_part"])],
        )

    def test_datasheet_url_attaches_trait(self):
        """Verify `node.datasheet_url = "..."` attaches has_datasheet trait."""
        _, tg, _, result = build_type(
            """
            import Resistor

            module App:
                resistor = new Resistor
                resistor.datasheet_url = "https://example.com/datasheet.pdf"
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_resistor_has_datasheet" in identifiers

        # Check that the trait was linked to the resistor
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["resistor"], ["_trait_resistor_has_datasheet"])],
        )

    def test_designator_prefix_attaches_trait(self):
        """Verify `node.designator_prefix = "U"` attaches trait."""
        _, tg, _, result = build_type(
            """
            import Resistor

            module App:
                resistor = new Resistor
                resistor.designator_prefix = "R"
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_resistor_has_designator_prefix" in identifiers

        # Check that the trait was linked to the resistor
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["resistor"], ["_trait_resistor_has_designator_prefix"])],
        )

    def test_override_net_name_attaches_trait(self):
        """Verify `node.override_net_name = "VCC"` attaches trait."""
        _, tg, _, result = build_type(
            """
            import Electrical

            module App:
                net = new Electrical
                net.override_net_name = "VCC"
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_net_has_net_name_suggestion" in identifiers

        # Check that the trait was linked to the net
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["net"], ["_trait_net_has_net_name_suggestion"])],
        )

    def test_suggest_net_name_attaches_trait(self):
        """Verify `node.suggest_net_name = "GND"` attaches trait."""
        _, tg, _, result = build_type(
            """
            import Electrical

            module App:
                net = new Electrical
                net.suggest_net_name = "GND"
            """
        )

        app_type = result.state.type_roots["App"]

        # Check that the trait child was created
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        assert "_trait_net_has_net_name_suggestion" in identifiers

        # Check that the trait was linked to the net
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["net"], ["_trait_net_has_net_name_suggestion"])],
        )


class TestMultiImportShim:
    """Tests for multi-import deprecation shim.

    The multi-import syntax (e.g., `import A, B`) is deprecated.
    These tests verify that:
    - Multiple imports on one line are correctly parsed
    - Each import is properly registered as a symbol
    - A deprecation warning is emitted
    """

    def test_multi_import_stdlib(self):
        """Test parsing multiple stdlib imports on one line."""
        _, tg, _, result = build_type(
            """
            import Resistor, Capacitor

            module App:
                r = new Resistor
                c = new Capacitor
            """
        )

        app_type = result.state.type_roots["App"]
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        # Both symbols should be available
        assert "r" in identifiers
        assert "c" in identifiers

    def test_multi_import_from_file(self):
        """Test parsing multiple imports from a file path."""
        _, tg, _, result = build_type(
            """
            from "somepackage.ato" import ModuleA, ModuleB

            module App:
                pass
            """
        )

        # The imports should have been registered (even if the file doesn't exist,
        # the symbols are still registered for later linking)
        assert result.state is not None

    def test_multi_import_emits_deprecation_warning(self, caplog):
        """Test that multi-import emits a deprecation warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            build_type(
                """
                import Resistor, Capacitor

                module App:
                    pass
                """
            )

        # Check that deprecation warning was logged
        warning_messages = [
            record.message
            for record in caplog.records
            if record.levelno == logging.WARNING
        ]
        assert any(
            "DEPRECATION" in msg and "Multiple imports" in msg
            for msg in warning_messages
        ), (
            f"Expected deprecation warning about multiple imports. Got: {warning_messages}"  # noqa E501
        )

    def test_single_import_no_warning(self, caplog):
        """Test that single import does not emit deprecation warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            build_type(
                """
                import Resistor

                module App:
                    r = new Resistor
                """
            )

        # Check that no multi-import deprecation warning was logged
        warning_messages = [
            record.message
            for record in caplog.records
            if record.levelno == logging.WARNING
        ]
        assert not any(
            "Multiple imports on one line" in msg for msg in warning_messages
        ), f"Unexpected deprecation warning for single import. Got: {warning_messages}"

    def test_multi_import_three_items(self):
        """Test parsing three stdlib imports on one line."""
        _, tg, _, result = build_type(
            """
            import Resistor, Capacitor, Inductor

            module App:
                r = new Resistor
                c = new Capacitor
                l = new Inductor
            """
        )

        app_type = result.state.type_roots["App"]
        make_children = [
            (identifier, child)
            for identifier, child in tg.collect_make_children(type_node=app_type)
        ]
        identifiers = [id for id, _ in make_children if id]

        # All three symbols should be available
        assert "r" in identifiers
        assert "c" in identifiers
        assert "l" in identifiers


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_literal_assignment)
