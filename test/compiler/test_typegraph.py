import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F
from atopile.compiler import DslRichException, DslUndefinedSymbolError
from atopile.compiler.ast_visitor import ASTVisitor, DslException
from atopile.compiler.build import Linker, StdlibRegistry, build_file
from atopile.errors import UserSyntaxError
from faebryk.core.solver.mutator import MutationMap, Mutator
from faebryk.core.solver.symbolic.structural import transitive_subset
from faebryk.core.solver.utils import ContradictionByLiteral
from faebryk.libs.util import not_none
from test.compiler.conftest import build_instance, build_type

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

    res_node = _get_make_child(type_graph, app_type, "res")

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
        """,
        link=True,
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
        ref = tg.ensure_child_reference(type_node=app_type, path=[idx])
        assert ref is not None
    assert len(element_nodes) == 3


def test_new_with_count_children_are_created():
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
    assert members_node is not None

    for idx in ["members[0]", "members[1]"]:
        elem_node = _get_make_child(tg, app_type, idx)
        assert elem_node is not None


def test_new_with_count_rejects_out_of_range_index():
    with pytest.raises(
        DslException,
        match=r"Field `members\[(2|2\.0)\]` with index cannot be assigned with new",
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
    with pytest.raises(
        DslException, match=r"Field `members\[5\]` is not defined in scope"
    ):
        g, tg, _, result = build_type(
            """
            module Inner:
                pass

            module App:
                members = new Inner[2]

                members[5] = "value"
            """,
            link=True,
        )

    with pytest.raises(DslException, match=r"Field `missing` could not be resolved"):
        g, tg, _, result = build_type(
            """
            module App:
                missing.child = new Resistor
            """,
            link=True,
        )


class TestForLoops:
    def test_for_loop_connects_twice(self):
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

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

    def test_for_loop_requires_experiment(self):
        with pytest.raises(DslException, match="(?i)experiment.*enabled"):
            build_type(
                """
                import Resistor

                module App:
                    left = new Resistor
                    right = new Resistor
                    sink = new Resistor

                    for r in [left, right]:
                        r ~ sink
                """
            )

    def test_for_loop_over_sequence(self):
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module Inner:
                connection = new Resistor

            module App:
                items = new Inner[2]
                sink = new Resistor

                for it in items:
                    it.connection ~ sink
            """,
            link=True,
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

    def test_for_loop_over_sequence_slice(self):
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module Inner:
                connection = new Resistor

            module App:
                items = new Inner[3]
                sink = new Resistor

                for it in items[1:]:
                    it.connection ~ sink
            """,
            link=True,
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

    def test_for_loop_over_sequence_slice_zero_step_errors(self):
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

    def test_for_loop_over_sequence_stride(self):
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module Inner:
                connection = new Resistor

            module App:
                items = new Inner[4]
                sink = new Resistor

                for it in items[0:4:2]:
                    it.connection ~ sink
            """,
            link=True,
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

    def test_for_loop_alias_does_not_leak(self):
        with pytest.raises(DslException, match="Field `r` could not be resolved"):
            build_type(
                """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module App:
                    left = new Resistor
                    for r in [left]:
                        pass
                    r ~ left
                """,
                link=True,
            )

    def test_for_loop_nested_field_paths(self):
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

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

    def test_two_for_loops_same_var_accumulates_links(self):
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

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

    def test_for_loop_over_nested_sequence(self):
        """Test iterating over a sequence that is a child of a child (nested path)."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module Inner:
                items = new Resistor[2]

            module App:
                inner = new Inner
                sink = new Resistor

                for item in inner.items:
                    item ~ sink
            """,
            link=True,
        )

        assert _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[
                (["inner", "items[0]"], ["sink"]),
                (["inner", "items[1]"], ["sink"]),
            ],
        )

    def test_for_loop_over_nested_sequence_with_slice(self):
        """Test slicing a sequence that is a child of a child."""
        _, tg, _, result = build_type(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module Inner:
                items = new Resistor[4]

            module App:
                inner = new Inner
                sink = new Resistor

                for item in inner.items[1:3]:
                    item ~ sink
            """,
            link=True,
        )

        assert _check_make_links(
            tg=tg,
            type_node=result.state.type_roots["App"],
            expected=[
                (["inner", "items[1]"], ["sink"]),
                (["inner", "items[2]"], ["sink"]),
            ],
            not_expected=[
                (["inner", "items[0]"], ["sink"]),
                (["inner", "items[3]"], ["sink"]),
            ],
        )

    def test_for_loop_alias_shadow_symbol_raises(self):
        with pytest.raises(
            DslException,
            match="Loop variable `Resistor` conflicts with an existing symbol in scope",
        ):
            build_type(
                """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module Resistor2:
                    pass

                module App:
                    left = new Resistor2
                    for Resistor in [left]:
                        pass
                """
            )


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
    with pytest.raises(DslException, match="Field `missing` could not be resolved"):
        build_type(
            """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            missing.child = new Resistor
            """,
            link=True,
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
            expected=[
                (["left", "can_bridge", "out_", ""], ["right", "can_bridge", "in_", ""])
            ],
        )
        is True
    )


def test_connect_requires_existing_fields():
    with pytest.raises(DslException, match="Field `missing` could not be resolved"):
        build_type(
            """
        module Electrical:
            pass

        module Resistor:
            unnamed = new Electrical[2]

        module App:
            left = new Resistor
            left ~ missing
            """,
            link=True,
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
        DslException, match="Field `left.missing.branch` could not be resolved"
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
            """,
            link=True,
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
        """,
        link=True,
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
    with pytest.raises(DslRichException) as e:
        build_type(
            """
            module App:
                child = new Child
            """,
            link=True,
        )

    assert isinstance(e.value.original, DslUndefinedSymbolError)

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
        tg.mark_constructable(type_node=Electrical)
        Resistor = tg.add_type(identifier="Resistor")
        tg.add_make_child(type_node=Resistor, child_type=Electrical, identifier="p1")
        tg.add_make_child(type_node=Resistor, child_type=Electrical, identifier="p2")
        tg.mark_constructable(type_node=Resistor)

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
        )
        assert ref is not None
        tg.validate_type(type_node=Resistor)

        # Verify we can get the reference path back
        # Includes empty string "" for pointer dereference
        path = tg.get_reference_path(reference=ref)
        assert len(path) == 3
        assert path[0] == "can_bridge"
        assert path[1] == "in_"
        assert path[2] == ""  # Pointer dereference

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
        )
        tg.validate_type(type_node=App)
        assert ref is not None

        # Verify the path was stored correctly
        # Includes empty string "" for pointer dereference
        path = tg.get_reference_path(reference=ref)
        assert len(path) == 4
        assert path[0] == "r"
        assert path[1] == "can_bridge"
        assert path[2] == "in_"
        assert path[3] == ""  # Pointer dereference


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

            import ElectricPower
            import ElectricLogic
            import can_bridge_by_name

            module BridgeableModule:
                data_in = new ElectricLogic
                data_out = new ElectricLogic
                trait can_bridge_by_name<input_name="data_in", output_name="data_out">

            module App:
                a = new ElectricPower
                b = new BridgeableModule
                c = new ElectricLogic

                a.hv ~> b ~> c
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
            (("a", "hv", "can_bridge", "out_", ""), ("b", "can_bridge", "in_", "")),
            (("b", "can_bridge", "out_", ""), ("c", "can_bridge", "in_", "")),
        }
        assert link_paths == expected, f"Expected {expected}, got {link_paths}"

    def test_can_bridge_by_name_instantiation_and_trait_access(self):
        """Test that can_bridge_by_name properly sets up the _can_bridge trait.

        This is a regression test for the bug where can_bridge_by_name defined
        `can_bridge` but accessed `self._can_bridge` in setup(), causing an
        AttributeError. The fix ensures the attribute is named `_can_bridge`.
        """
        import faebryk.core.node as fabll
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("BRIDGE_CONNECT")

            import ElectricLogic
            import can_bridge_by_name

            module BridgeableModule:
                data_in = new ElectricLogic
                data_out = new ElectricLogic
                trait can_bridge_by_name<input_name="data_in", output_name="data_out">
            """,
            link=True,
        )

        bridge_type = result.state.type_roots["BridgeableModule"]

        # Instantiate the module - this is where the bug would manifest
        # as an AttributeError when accessing self._can_bridge
        bridge_instance = tg.instantiate_node(type_node=bridge_type, attributes={})

        # Verify the module has the can_bridge trait
        bridge_node = fabll.Node.bind_instance(bridge_instance)
        assert bridge_node.has_trait(F.can_bridge), (
            "BridgeableModule should have can_bridge trait"
        )

        # Get the can_bridge trait and verify its pointers are set up
        can_bridge_trait = bridge_node.get_trait(F.can_bridge)

        # The in_ pointer should point to data_in
        in_node = can_bridge_trait.get_in()
        assert in_node is not None, "can_bridge.in_ should be set"
        assert in_node.get_name() == "data_in", (
            f"can_bridge.in_ should point to 'data_in', got '{in_node.get_name()}'"
        )

        # The out_ pointer should point to data_out
        out_node = can_bridge_trait.get_out()
        assert out_node is not None, "can_bridge.out_ should be set"
        assert out_node.get_name() == "data_out", (
            f"can_bridge.out_ should point to 'data_out', got '{out_node.get_name()}'"
        )


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

        with pytest.raises(
            DslException, match="Missing value for `has_datasheet_defined`: 'datasheet'"
        ):
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
        assert lhs_path == ["r1", "can_bridge", "out_", ""]
        # RHS should be: r2 -> can_bridge -> in_
        assert rhs_path == ["r2", "can_bridge", "in_", ""]

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
        assert lhs_path == ["r1", "can_bridge", "in_", ""]
        assert rhs_path == ["r2", "can_bridge", "out_", ""]

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
            ("r1", "can_bridge", "out_", ""),
            ("r2", "can_bridge", "in_", ""),
        ) in link_paths

        # Second link: r2.out -> r3.in
        assert (
            ("r2", "can_bridge", "out_", ""),
            ("r3", "can_bridge", "in_", ""),
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
            (("r1", "can_bridge", "out_", ""), ("r2", "can_bridge", "in_", "")),
            (("r2", "can_bridge", "out_", ""), ("r3", "can_bridge", "in_", "")),
            (("r3", "can_bridge", "out_", ""), ("r4", "can_bridge", "in_", "")),
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
                """,
                link=True,
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
        assert lhs_path == ["a", "can_bridge", "out_", ""]
        assert rhs_path == ["b", "can_bridge", "in_", ""]

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
        assert lhs_path == ["1", "can_bridge", "out_", ""]
        assert rhs_path == ["2", "can_bridge", "in_", ""]

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
            (("r1", "can_bridge", "out_", ""), ("mid", "can_bridge", "in_", "")),
            (("mid", "can_bridge", "out_", ""), ("r2", "can_bridge", "in_", "")),
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
        with pytest.raises(
            DslException, match="Field `undefined_field` could not be resolved"
        ):
            build_type(
                """
                #pragma experiment("TRAITS")
                import is_pickable

                module MyModule:
                    trait undefined_field is_pickable
                """,
                link=True,
            )

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

    def test_trait_template_args_numeric_values(self):
        """Template args constrain trait parameters to expected numeric values."""
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from test.compiler.conftest import build_instance

        # Create a test trait with numeric parameter
        class has_numeric_param(fabll.Node):
            is_trait = fabll.Traits.MakeEdge(
                fabll.ImplementsTrait.MakeChild().put_on_type()
            )
            count = F.Parameters.NumericParameter.MakeChild(
                unit=F.Units.Dimensionless,
            )

            @classmethod
            def MakeChild(  # type: ignore[override]
                cls, count: int
            ) -> fabll._ChildField:
                out = fabll._ChildField(cls)
                out.add_dependant(
                    F.Literals.Numbers.MakeChild_SetSingleton(
                        param_ref=[out, cls.count],
                        value=float(count),
                        unit=F.Units.Dimensionless,
                    )
                )
                return out

            def get_count(self) -> int:
                return int(self.count.get().force_extract_superset().get_single())

        # Register the trait and build the ato code
        g, tg, stdlib, result, instance = build_instance(
            """
            #pragma experiment("TRAITS")
            import has_numeric_param

            module MyModule:
                trait has_numeric_param<count=42>
            """,
            root="MyModule",
            stdlib_extra=[has_numeric_param],
        )

        part = fabll.Node.bind_instance(instance)
        trait = part.get_trait(has_numeric_param)

        assert trait.get_count() == 42

    def test_instance_trait_on_child(self):
        """Instance trait applies trait to a child field via dot syntax."""
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from test.compiler.conftest import build_instance

        g, tg, stdlib, result, app_root = build_instance(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("INSTANCE_TRAITS")
            import has_net_name_suggestion
            import Electrical

            module App:
                e1 = new Electrical
                trait e1 has_net_name_suggestion<name="MY_NET", level="SUGGESTED">
            """,
            root="App",
        )

        e1_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_root, child_identifier="e1"
        )
        assert e1_bnode is not None

        e1 = fabll.Node.bind_instance(e1_bnode)
        trait = e1.get_trait(F.has_net_name_suggestion)

        assert trait.name == "MY_NET"
        assert trait.level == F.has_net_name_suggestion.Level.SUGGESTED

    def test_instance_trait_on_childs_child(self):
        """Instance trait applies trait to a childs child field via dot syntax."""
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from test.compiler.conftest import build_instance

        g, tg, stdlib, result, app_root = build_instance(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("INSTANCE_TRAITS")
            import has_net_name_suggestion
            import Resistor

            module App:
                r1 = new Resistor
                trait r1.unnamed[0] has_net_name_suggestion<name="R1_UN0", level="SUGGESTED">
            """,  # noqa: E501
            root="App",
        )

        r1_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_root, child_identifier="r1"
        )
        assert r1_bnode is not None

        r1_unnamed_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=r1_bnode, child_identifier="unnamed[0]"
        )
        assert r1_unnamed_bnode is not None
        r1_unnamed = fabll.Node.bind_instance(r1_unnamed_bnode)
        trait = r1_unnamed.get_trait(F.has_net_name_suggestion)

        assert trait.name == "R1_UN0"
        assert trait.level == F.has_net_name_suggestion.Level.SUGGESTED


class TestAssignments:
    """Tests for parameter assignments in ato."""

    @pytest.mark.parametrize(
        "assignment,param_name,expected_values",
        [
            ("a = 1", "a", [1.0, 1.0]),  # get_values() returns [min, max]
            ("b = 5V", "b", [5.0, 5.0]),
            (
                "c = 100kohm +/- 10%",
                "c",
                [90000.0, 110000.0],
            ),  # 100k +/- 10% in base units (ohms)
            ("d = 3V to 5V", "d", [3.0, 5.0]),
        ],
    )
    def test_top_level_parameter_assignment(
        self, assignment: str, param_name: str, expected_values: list
    ):
        """Test that direct literal assignment creates a top-level parameter.

        When writing `a = 1` in a module, this should create a NumericParameter
        child named "a" and constrain it to the literal value.
        """
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            f"""
            module App:
                {assignment}
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type = result.state.type_roots["App"]

        # Verify the parameter child exists
        make_children = list(tg.collect_make_children(type_node=app_type))
        identifiers = [id for id, _ in make_children if id]
        assert param_name in identifiers, (
            f"Parameter '{param_name}' should be created by `{assignment}`"
        )

        # Instantiate and verify the literal value can be extracted
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type, attributes={})
        )
        param_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier=param_name
        )
        param = F.Parameters.NumericParameter.bind_instance(not_none(param_bnode))

        # The parameter should have an aliased literal with expected values
        literal = param.force_extract_superset()
        assert literal is not None, (
            f"Parameter '{param_name}' should have an aliased literal"
        )
        assert literal.get_values() == expected_values, (
            f"Expected {expected_values}, got {literal.get_values()}"
        )

    def test_assign_single_value_with_unit(self):
        """Test assigning a single value with unit to an existing field."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                r = new Resistor
                r.max_power = 3 mW
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        # Assignments create Is constraints, use try_extract_aliased_literal
        # Value should be 3 mW = 0.003 W in base SI units
        # Due to test order dependency, values may be stored in mW or W
        literal = r.max_power.get().force_extract_superset()
        assert literal is not None, "max_power should have an aliased literal"
        value = literal.get_single()
        multiplier = not_none(literal.get_is_unit())._extract_multiplier()
        base_value = value * multiplier
        assert base_value == 0.003, (
            f"Expected 0.003 W, got {base_value} W "
            f"(raw value={value}, multiplier={multiplier})"
        )
        assert fabll.Traits(r.max_power.get().force_get_units()).get_obj(F.Units.Watt)

    def test_assign_bilateral_tolerance(self):
        """Test assigning a bilateral tolerance value to an existing field."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                r = new Resistor
                r.resistance = 100 ohm +/- 5%
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        # 100 ohm +/- 5% = [95, 105]
        literal = r.resistance.get().force_extract_superset()
        assert literal is not None, "resistance should have an aliased literal"
        assert literal.get_values() == [95.0, 105.0]

    def test_assign_bounded_range(self):
        """Test assigning a bounded range value to an existing field."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                r = new Resistor
                r.max_power = 3 watt to 5 watt
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        literal = r.max_power.get().force_extract_superset()
        assert literal is not None, "max_power should have an aliased literal"
        assert literal.get_values() == [3.0, 5.0]

    def test_assign_bounded_range_with_different_unit_prefixes(self):
        """Test assigning a bounded range with different unit prefixes (e.g., uA to mA).

        This test ensures that unit conversion works correctly when the start
        and end units have different prefixes but are commensurable.
        Regression test for: ValueError: Invalid interval: 2.1 > 0.012
        """
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import ElectricPower

            module App:
                power = new ElectricPower
                # 2.1 uA to 12 mA - different unit prefixes (micro vs milli)
                power.max_current = 2.1uA to 12mA
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        power_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="power"
        )
        power = F.ElectricPower.bind_instance(not_none(power_bnode))

        # The values should be stored in the unit of the start value (uA)
        # 2.1 uA -> 2.1
        # 12 mA -> 12000 uA
        literal = power.max_current.get().force_extract_superset()
        assert literal is not None, "current should have an aliased literal"
        values = power.max_current.get().get_values()
        assert len(values) == 2
        # The values are stored in the start unit (uA)
        assert values[0] == 2.1e-6, f"Expected start value 2.1, got {values[0]}"
        assert values[1] == 12.0e-3, (
            f"Expected end value 0.012 (12mA in A), got {values[1]}"
        )

    def test_assert_within_constraint(self):
        """Test assert within constraint on an existing field."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                r = new Resistor
                assert r.max_voltage within 25 volt to 100 volt
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        assert r.max_voltage.get().force_extract_superset().get_values() == [
            25.0,
            100.0,
        ]

    def test_assert_within_bilateral_tolerance(self):
        """Test assert within with bilateral tolerance."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                r = new Resistor
                assert r.max_voltage within 100kV +/- 1%
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        # 100kV +/- 1% = [99000, 101000] V in base SI units
        # Due to test order dependency, values may be stored in kV or V
        # Check the actual value in base units (value * multiplier)
        literal = r.max_voltage.get().force_extract_superset()
        not_none(literal.get_is_unit())._extract_multiplier()

        values = r.max_voltage.get().get_values()
        assert values == [99000.0, 101000.0], (
            f"Expected [99000.0, 101000.0] V, got {values} V"
        )

    def test_component_parameter_uses_is_constraint(self):
        """Component parameter assignments use Is constraint (not IsSubset).

        In components, parameter assignments should create exact (Is) constraints
        that can be extracted with force_extract_literal(), unlike modules which
        use IsSubset constraints.
        """
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            component App:
                r = new Resistor
                r.resistance = 100 ohm +/- 5%
                r.max_power = 3 mW to 5 mW
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        # Components use Is constraint, so force_extract_literal should work
        resistance_literal = r.resistance.get().force_extract_subset()
        assert resistance_literal is not None, (
            "resistance should have an Is-constrained literal"
        )
        # 100 ohm +/- 5% = [95, 105]
        assert resistance_literal.get_values() == [95.0, 105.0]

        max_power_literal = r.max_power.get().force_extract_subset()
        assert max_power_literal is not None, (
            "max_power should have an Is-constrained literal"
        )
        # 3 mW to 5 mW in base units (watts) = [0.003, 0.005]
        assert max_power_literal.get_values() == [0.003, 0.005]

    def test_module_parameter_uses_issubset_constraint(self):
        """Module parameter assignments use IsSubset constraint (not Is).

        In modules, parameter assignments should create subset constraints
        that allow further refinement in derived modules.
        """
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            import Resistor

            module App:
                r = new Resistor
                r.resistance = 100 ohm +/- 5%
            """
        )

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        app_type_node = result.state.type_roots["App"]
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type_node, attributes={})
        )

        r_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="r"
        )
        r = F.Resistor.bind_instance(not_none(r_bnode))

        # Modules use IsSubset constraint, so force_extract_literal_subset works
        resistance_literal = r.resistance.get().force_extract_superset()
        assert resistance_literal is not None, (
            "resistance should have an IsSubset literal"
        )
        # 100 ohm +/- 5% = [95, 105]
        assert resistance_literal.get_values() == [95.0, 105.0]


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
        """
        Verify `node.lcsc_id = "C12345"` attaches is_pickable_by_supplier_id trait.
        """
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

        assert "_trait_resistor_is_pickable_by_supplier_id" in identifiers

        # Check that the trait was linked to the resistor
        assert _check_make_links(
            tg,
            app_type,
            expected=[(["resistor"], ["_trait_resistor_is_pickable_by_supplier_id"])],
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
        assert len(warning_messages) == 1, (
            f"Expected 1 deprecation warning, got {len(warning_messages)}"
        )
        assert (
            "Multiple imports on one line is deprecated. Please use separate import statements for each module. Found:"  # noqa E501
            in warning_messages[0]
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


class TestDocStrings:
    """Tests for docstring handling in module/component/interface definitions.

    When a block definition starts with a string statement (docstring),
    the has_doc_string trait should be attached to the type.
    """

    def test_module_docstring_attaches_trait(self):
        """Test that a module docstring creates a has_doc_string trait on the type."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            '''
            module MyModule:
                """
                This is the docstring for MyModule.
                It can span multiple lines.
                """
                pass
            ''',
            link=True,
        )

        my_module_type = result.state.type_roots["MyModule"]

        # Check that has_doc_string trait was attached to the type node
        # Type-level traits are instance children, not MakeChild nodes
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=my_module_type, trait_type=has_doc_string_type
        )
        assert trait_impl is not None, "Expected has_doc_string trait on type"

    def test_component_docstring_attaches_trait(self):
        """Test that a component docstring creates a has_doc_string trait."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            '''
            component MyComponent:
                """Component docstring."""
                pin 1
            ''',
            link=True,
        )

        comp_type = result.state.type_roots["MyComponent"]
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=comp_type, trait_type=has_doc_string_type
        )
        assert trait_impl is not None, "Expected has_doc_string trait on component"

    def test_interface_docstring_attaches_trait(self):
        """Test that an interface docstring creates a has_doc_string trait."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            '''
            interface MyInterface:
                """Interface docstring."""
                signal io
            ''',
            link=True,
        )

        interface_type = result.state.type_roots["MyInterface"]
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=interface_type, trait_type=has_doc_string_type
        )
        assert trait_impl is not None, "Expected has_doc_string trait on interface"

    def test_no_docstring_no_trait(self):
        """Test that a module without docstring has no has_doc_string trait."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            """
            module NoDocModule:
                pass
            """,
            link=True,
        )

        module_type = result.state.type_roots["NoDocModule"]
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=module_type, trait_type=has_doc_string_type
        )
        assert trait_impl is None, "Expected no has_doc_string trait"

    def test_string_not_first_is_not_docstring(self):
        """
        Test that a string statement not first in block is not treated as docstring.
        """
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            '''
            module MyModule:
                pass
                """This is NOT a docstring - it comes after pass."""
            ''',
            link=True,
        )

        module_type = result.state.type_roots["MyModule"]
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=module_type, trait_type=has_doc_string_type
        )
        assert trait_impl is None, "Expected no has_doc_string trait"

    def test_single_quoted_docstring(self):
        """Test that single-quoted strings work as docstrings."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            """
            module MyModule:
                'Single quoted docstring.'
                pass
            """,
            link=True,
        )

        module_type = result.state.type_roots["MyModule"]
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=module_type, trait_type=has_doc_string_type
        )
        assert trait_impl is not None, "Expected has_doc_string trait"

    def test_docstring_with_code(self):
        """Test that docstring works with actual code in the module."""
        import faebryk.core.faebrykpy as fbrk
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            '''
            import Resistor

            module MyModule:
                """
                This module has a resistor.
                """
                r = new Resistor
            ''',
            link=True,
        )

        module_type = result.state.type_roots["MyModule"]

        # Check trait exists
        has_doc_string_type = F.has_doc_string.bind_typegraph(tg).get_or_create_type()
        trait_impl = fbrk.Trait.try_get_trait(
            target=module_type, trait_type=has_doc_string_type
        )
        assert trait_impl is not None, "Expected has_doc_string trait"

        # Check resistor also exists (docstring handling doesn't break normal code)
        make_children = list(tg.collect_make_children(type_node=module_type))
        identifiers = [id for id, _ in make_children if id]
        assert "r" in identifiers


class TestBlockInheritance:
    """Tests for block inheritance (module Derived from Base)."""

    def test_basic_inheritance(self):
        """Child type has access to parent's children."""
        g, tg, stdlib, result = build_type(
            """
            import Resistor
            import Capacitor

            module Base:
                r = new Resistor

            module Derived from Base:
                c = new Capacitor
            """,
            link=True,
        )

        derived_type = result.state.type_roots["Derived"]

        # Derived should have both 'r' (inherited) and 'c' (own)
        identifiers = {
            identifier
            for identifier, _ in tg.collect_make_children(type_node=derived_type)
            if identifier is not None
        }
        assert "r" in identifiers, "Inherited field 'r' should exist on Derived"
        assert "c" in identifiers, "Own field 'c' should exist on Derived"

    def test_multi_level_inheritance(self):
        """Inheritance chains flatten correctly."""
        g, tg, stdlib, result = build_type(
            """
            import Electrical

            module Level1:
                a = new Electrical

            module Level2 from Level1:
                b = new Electrical

            module Level3 from Level2:
                c = new Electrical
            """,
            link=True,
        )

        level3_type = result.state.type_roots["Level3"]

        # Level3 should have a, b, and c
        identifiers = {
            identifier
            for identifier, _ in tg.collect_make_children(type_node=level3_type)
            if identifier is not None
        }
        assert "a" in identifiers, "Field 'a' from Level1 should be inherited"
        assert "b" in identifiers, "Field 'b' from Level2 should be inherited"
        assert "c" in identifiers, "Own field 'c' should exist on Level3"

    def test_inheritance_no_user_conflict_with_traits(self):
        """Trait children (like is_ato_module) don't cause conflicts."""
        g, tg, stdlib, result = build_type(
            """
            import Electrical

            module Base:
                x = new Electrical

            module Derived from Base:
                y = new Electrical
            """,
            link=True,
        )

        derived_type = result.state.type_roots["Derived"]
        identifiers = {
            identifier
            for identifier, _ in tg.collect_make_children(type_node=derived_type)
            if identifier is not None
        }
        assert "x" in identifiers
        assert "y" in identifiers

    def test_inheritance_with_connections(self):
        """Connections defined in parent are inherited."""
        g, tg, stdlib, result = build_type(
            """
            import Electrical
            import Resistor

            module Base:
                a = new Electrical
                r = new Resistor
                b = new Electrical
                a ~ b
                a ~> r ~> b

            module Derived from Base:
                pass
            """,
            link=True,
        )

        derived_type = result.state.type_roots["Derived"]

        # Check that the connection from Base is inherited
        links = _collect_make_links(tg, derived_type)
        link_paths = {
            (tuple(lhs_path), tuple(rhs_path)) for _, lhs_path, rhs_path in links
        }

        assert (("a",), ("b",)) in link_paths or (("b",), ("a",)) in link_paths, (
            "Connection a ~ b from Base should be inherited"
        )
        assert (
            ("a", "can_bridge", "out_", ""),
            ("r", "can_bridge", "in_", ""),
        ) in link_paths, "Connection a ~> r ~> b from Base should be inherited"
        assert (
            ("r", "can_bridge", "out_", ""),
            ("b", "can_bridge", "in_", ""),
        ) in link_paths, "Connection a ~> r ~> b from Base should be inherited"

        instance = tg.instantiate_node(type_node=derived_type, attributes={})
        from faebryk.library._F import Electrical, Resistor

        r = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=instance, child_identifier="r"
        )
        a = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=instance, child_identifier="a"
        )
        b = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=instance, child_identifier="b"
        )
        r_bound = Resistor.bind_instance(not_none(r))
        a_bound = Electrical.bind_instance(not_none(a))
        b_bound = Electrical.bind_instance(not_none(b))
        assert a_bound._is_interface.get().is_connected_to(b_bound), (
            "Connection a ~ b from Base should be inherited"
        )
        assert r_bound.unnamed[0].get()._is_interface.get().is_connected_to(a_bound), (
            "Connection a ~> r ~> b from Base should be inherited"
        )

    def test_interface_inheritance(self):
        """Interface inheritance works correctly."""
        g, tg, stdlib, result = build_type(
            """
            import Electrical

            interface BaseInterface:
                a = new Electrical

            interface DerivedInterface from BaseInterface:
                b = new Electrical
            """,
            link=True,
        )

        derived_type = result.state.type_roots["DerivedInterface"]

        identifiers = {
            identifier
            for identifier, _ in tg.collect_make_children(type_node=derived_type)
            if identifier is not None
        }
        assert "a" in identifiers, "Inherited field 'a' should exist"
        assert "b" in identifiers, "Own field 'b' should exist"

    def test_redefinition_overrides_silently(self):
        """Redefining a parent field in derived type: derived wins silently."""
        g, tg, stdlib, result = build_type(
            """
            import Electrical

            module Base:
                x = new Electrical

            module Derived from Base:
                x = new Electrical
            """,
            link=True,
        )

        derived_type = result.state.type_roots["Derived"]
        identifiers = {
            identifier
            for identifier, _ in tg.collect_make_children(type_node=derived_type)
            if identifier is not None
        }
        assert "x" in identifiers, "Derived should have 'x'"


class TestRetypeOperator:
    """Tests for retype operator (target -> NewType)."""

    def test_basic_retype(self):
        """Retype changes the type reference of a field."""
        g, tg, stdlib, result = build_type(
            """
            import Resistor
            import Capacitor

            module App:
                part = new Resistor
                part -> Capacitor
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        type_ref = tg.get_make_child_type_reference_by_identifier(
            type_node=app_type, identifier="part"
        )
        resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
        resolved_name = fbrk.TypeGraph.get_type_name(type_node=resolved)

        assert resolved_name == "Capacitor"

    def test_retype_to_local_type(self):
        """Retype to a locally defined type."""
        g, tg, stdlib, result = build_type(
            """
            import Electrical

            module Base:
                x = new Electrical

            module Specialized:
                y = new Electrical

            module App:
                inner = new Base
                inner -> Specialized
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        type_ref = tg.get_make_child_type_reference_by_identifier(
            type_node=app_type, identifier="inner"
        )
        resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
        resolved_name = fbrk.TypeGraph.get_type_name(type_node=resolved)

        assert "Specialized" in resolved_name

    def test_retype_in_derived_module(self):
        """Retype in derived module changes inherited field's type."""
        g, tg, stdlib, result = build_type(
            """
            import Resistor
            import Capacitor

            module Base:
                part = new Resistor

            module Derived from Base:
                part -> Capacitor
            """,
            link=True,
        )

        derived_type = result.state.type_roots["Derived"]
        type_ref = tg.get_make_child_type_reference_by_identifier(
            type_node=derived_type, identifier="part"
        )
        resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
        resolved_name = fbrk.TypeGraph.get_type_name(type_node=resolved)

        assert resolved_name == "Capacitor"

    def test_retype_nonexistent_field_errors(self):
        """Retype on a field that doesn't exist raises an error."""
        with pytest.raises(DslException, match="does not exist"):
            build_type(
                """
                import Resistor

                module App:
                    missing -> Resistor
                """,
                link=True,
            )

    def test_retype_to_unknown_type_errors(self):
        """Retype to an unknown type raises an error during linking."""
        with pytest.raises(DslRichException, match="not defined") as e:
            build_type(
                """
                import Resistor

                module App:
                    part = new Resistor
                    part -> UnknownType
                """,
                link=True,
            )

        assert isinstance(e.value.original, DslUndefinedSymbolError)


class TestMakeChildDeduplication:
    """Tests for MakeChild creation and inheritance deduplication.

    These tests match the legacy (v0.12) behavior except where noted.

    - Explicit declarations (`resistance: ohm`) create a MakeChild.
    - Implicit assignments (`resistance = 10kohm`) create a MakeChild, unless
      the identifier was already explicitly declared in the same type.
    - Duplicate explicit declarations for the same identifier are an error.
    - Duplicate implicit assignments for the same identifier are an error.
      (Legacy silently kept the first; now an error.)
    - During inheritance, `merge_types` deduplicates: if the derived type already
      has a child with the same identifier as the parent, the derived's version wins.
    """

    def test_explicit_declaration_only(self):
        """Explicit declaration creates a parameter without constraint."""
        g, tg, stdlib, result = build_type(
            """
            module App:
                resistance: ohm
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        identifiers = {
            id for id, _ in tg.collect_make_children(type_node=app_type) if id
        }
        assert "resistance" in identifiers

    def test_implicit_declaration_only(self):
        """Implicit assignment creates parameter with constraint."""
        import faebryk.core.node as fabll
        import faebryk.library._F as F

        g, tg, stdlib, result = build_type(
            """
            module App:
                resistance = 10kohm
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]
        identifiers = {
            id for id, _ in tg.collect_make_children(type_node=app_type) if id
        }
        assert "resistance" in identifiers

        # Verify the constraint is applied
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type, attributes={})
        )
        # The parameter should have a constrained value
        param_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="resistance"
        )
        param = F.Parameters.NumericParameter.bind_instance(not_none(param_bnode))
        literal = param.force_extract_superset()
        assert literal is not None
        assert literal.get_values() == [10000.0, 10000.0]  # 10kohm in base units (ohms)

    def test_explicit_then_implicit_same_block(self):
        """Explicit declaration followed by implicit constraint in same block.

        The explicit MakeChild should be kept, assignment should not create
        a duplicate, and constraint should apply to the declared parameter.
        """
        import faebryk.core.faebrykpy as fbrk
        import faebryk.core.node as fabll
        import faebryk.library._F as F
        from faebryk.libs.util import not_none

        g, tg, stdlib, result = build_type(
            """
            module App:
                resistance: ohm
                resistance = 10kohm
            """,
            link=True,
        )

        app_type = result.state.type_roots["App"]

        # Should have exactly one 'resistance' MakeChild (not two)
        resistance_count = sum(
            1
            for id, _ in tg.collect_make_children(type_node=app_type)
            if id == "resistance"
        )
        assert resistance_count == 1, (
            f"Expected 1 'resistance' MakeChild, got {resistance_count}"
        )

        # The constraint should still be applied
        app_instance = fabll.Node(
            tg.instantiate_node(type_node=app_type, attributes={})
        )
        param_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance.instance, child_identifier="resistance"
        )
        param = F.Parameters.NumericParameter.bind_instance(not_none(param_bnode))
        literal = param.force_extract_superset()
        assert literal is not None
        assert param.get_values() == [10000.0, 10000.0]
        assert param.force_get_display_units().get_symbols() == ["Ω", "ohm", "ohms"]
        assert (
            fabll.Traits(param.force_get_units()).get_obj_raw().get_type_node()
            == F.Units.Ohm.bind_typegraph(tg=tg).as_type_node().instance
        )

    def test_inherited_explicit_with_implicit_constraint(self):
        """Derived type constrains inherited explicit parameter.

        Parent has `resistance: ohm`, derived has `resistance = 10kohm`.
        merge_types deduplicates: derived's MakeChild wins, only one 'resistance'.
        """
        g, tg, stdlib, result = build_type(
            """
            module Base:
                resistance: ohm

            module Derived from Base:
                resistance = 10kohm
            """,
            link=True,
        )

        derived_type = result.state.type_roots["Derived"]

        # Should have exactly one 'resistance' MakeChild (derived wins over parent)
        resistance_count = sum(
            1
            for id, _ in tg.collect_make_children(type_node=derived_type)
            if id == "resistance"
        )
        assert resistance_count == 1, (
            f"Expected 1 'resistance' MakeChild, got {resistance_count}"
        )

    def test_multiple_explicit_same_identifier_errors(self):
        """Multiple explicit declarations for same identifier is an error."""
        with pytest.raises(DslException, match="resistance"):
            build_type(
                """
                module App:
                    resistance: ohm
                    resistance: V
                """,
                link=True,
            )

    def test_multiple_implicit_same_identifier_errors(self):
        """Multiple implicit assignments for same identifier is an error.

        Legacy silently kept the first and discarded the second.
        Now duplicate MakeChild nodes are caught by validate_type.
        """
        with pytest.raises(DslException, match="resistance"):
            build_type(
                """
                module App:
                    resistance = 10kohm
                    resistance = 20kohm
                """,
                link=True,
            )

    def test_inherited_implicit_with_child_implicit(self):
        """Both parent and child have implicit assignments for same identifier.

        Derived's MakeChild wins during merge_types; parent's is skipped.
        """
        g, tg, stdlib, result = build_type(
            """
            module Base:
                resistance = 10kohm

            module Derived from Base:
                resistance = 5kohm
            """,
            link=True,
            validate=False,  # Skip validation - internal expression node refs
        )

        derived_type = result.state.type_roots["Derived"]

        # Should have exactly one 'resistance' MakeChild (derived wins)
        resistance_count = sum(
            1
            for id, _ in tg.collect_make_children(type_node=derived_type)
            if id == "resistance"
        )
        assert resistance_count == 1, (
            f"Expected 1 'resistance' MakeChild, got {resistance_count}"
        )
        import faebryk.library._F as F

        instance = tg.instantiate_node(type_node=derived_type, attributes={})
        assert (
            F.Parameters.NumericParameter.bind_instance(
                not_none(
                    fbrk.EdgeComposition.get_child_by_identifier(
                        bound_node=instance, child_identifier="resistance"
                    )
                )
            )
            .force_extract_superset()
            .get_numeric_set()
            .get_intervals()
            == []
        )


def test_source_chunk_ptr_copy_to_instance():
    """Test that source chunk pointer is copied to instance."""
    g, tg, stdlib, result = build_type(
        """
        import Resistor

        module Resistors:
            r1 = new Resistor
            r2 = new Resistor

        module App:
            resistors = new Resistors
        """,
        link=True,
    )
    import atopile.compiler.ast_types as AST
    import faebryk.library._F as F

    app_type = not_none(result.state.type_roots["App"])
    app_instance = not_none(tg.instantiate_node(type_node=app_type, attributes={}))

    resistor_mc = not_none(
        fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_type, child_identifier="resistors"
        )
    )
    resistor_instance = not_none(
        fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=app_instance, child_identifier="resistors"
        )
    )

    source_chunk_mc = ASTVisitor.get_source_chunk(resistor_mc)
    r_instance = F.Resistor.bind_instance(resistor_instance)
    source_chunk_instance = AST.SourceChunk.bind_instance(
        r_instance.get_trait(F.has_source_chunk).source_ptr.get().deref().instance
    )

    # With source chunk copying disabled, instances may not have source chunks
    # This is acceptable as long as the build works
    assert source_chunk_mc is not None, "MakeChild should have source chunk"
    assert source_chunk_instance is not None, "Instance should have source chunk"


def _build_mutator(source: str) -> Mutator:
    g, tg, _stdlib, _result, _app_root = build_instance(
        source, root="App", import_path="app.ato"
    )
    mutation_map = MutationMap.bootstrap(tg=tg, g=g)
    return Mutator(
        mutation_map=mutation_map,
        algo=transitive_subset,
        iteration=0,
        terminal=False,
    )


def _build_numeric_param_mutator() -> tuple[
    Mutator, F.Parameters.NumericParameter, F.Units.is_unit
]:
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    unit = F.Units.Dimensionless.bind_typegraph(tg).create_instance(g).is_unit.get()
    param = (
        F.Parameters.NumericParameter.bind_typegraph(tg)
        .create_instance(g)
        .setup(is_unit=unit)
    )
    mutation_map = MutationMap.bootstrap(tg=tg, g=g)
    mutator = Mutator(
        mutation_map=mutation_map,
        algo=transitive_subset,
        iteration=0,
        terminal=False,
    )
    return mutator, param, unit


def test_contradiction_empty_intersection_has_sources():
    source = """
    module App:
        resistance: ohm
        assert resistance within 0ohm to 5ohm
        assert resistance within 10ohm to 12ohm
    """
    with pytest.raises(ContradictionByLiteral, match="Empty superset") as exc:
        _build_mutator(source)
    msg = str(exc.value)
    assert "Constraints:" in msg
    # Verify that the constraint range appears (shows tracing is working)
    assert "{0..5}" in msg


def test_contradiction_alias_incompatible_with_subset_has_sources():
    with pytest.raises(
        ContradictionByLiteral, match="Tried alias to literal incompatible with subset"
    ) as exc:
        mutator, param, unit = _build_numeric_param_mutator()
        subset_lit = (
            F.Literals.Numbers.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_in)
            .setup_from_min_max(0, 5, unit=unit)
        )
        subset_expr = (
            F.Expressions.IsSubset.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_in)
            .setup(
                subset=param.is_parameter_operatable.get().as_operand.get(),
                superset=subset_lit.is_literal.get().as_operand.get(),
                assert_=True,
            )
        )
        literal = (
            F.Literals.Numbers.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_in)
            .setup_from_singleton(value=10.0, unit=unit)
        ).is_literal.get()
        raise ContradictionByLiteral(
            "Tried alias to literal incompatible with subset",
            involved=[param.is_parameter_operatable.get()],
            literals=[subset_lit.is_literal.get(), literal],
            mutator=mutator,
            constraint_sources=[subset_expr.is_parameter_operatable.get()],
        )
    msg = str(exc.value)
    assert "Constraints:" in msg
    assert "{0..5}" in msg


def test_contradiction_subset_to_different_literal_has_sources():
    with pytest.raises(
        ContradictionByLiteral, match="Tried subset to different literal"
    ) as exc:
        mutator, param, unit = _build_numeric_param_mutator()
        literal = (
            F.Literals.Numbers.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_in)
            .setup_from_singleton(value=10.0, unit=unit)
        )
        is_expr = (
            F.Expressions.IsSubset.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_in)
            .setup(
                subset=param.is_parameter_operatable.get().as_operand.get(),
                superset=literal.is_literal.get().as_operand.get(),
                assert_=True,
            )
        )
        subset_lit = (
            F.Literals.Numbers.bind_typegraph(mutator.tg_in)
            .create_instance(mutator.G_in)
            .setup_from_min_max(0, 5, unit=unit)
        )
        raise ContradictionByLiteral(
            "Tried subset to different literal",
            involved=[param.is_parameter_operatable.get()],
            literals=[literal.is_literal.get(), subset_lit.is_literal.get()],
            mutator=mutator,
            constraint_sources=[is_expr.is_parameter_operatable.get()],
        )
    msg = str(exc.value)
    assert "Constraints:" in msg
    assert "10" in msg
