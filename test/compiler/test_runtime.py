import logging
import math
import tempfile
import textwrap
from enum import IntEnum, StrEnum
from pathlib import Path
from types import SimpleNamespace

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler import DslRichException
from atopile.compiler.ast_types import SourceChunk, SourceInfo
from atopile.compiler.ast_visitor import (
    STDLIB_ALLOWLIST,
    ASTVisitor,
    DslException,
    is_ato_component,
    is_ato_interface,
    is_ato_module,
)
from atopile.compiler.build import Linker, StdlibRegistry, build_file, build_stage_2
from atopile.errors import UserSyntaxError
from faebryk.core import graph
from faebryk.core.faebrykpy import EdgeComposition, EdgeType
from faebryk.core.graph import BoundNode, GraphView
from faebryk.core.solver.solver import Solver
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import cast_assert, not_none
from test.compiler.conftest import build_instance, build_type

E = BoundExpressions()

NULL_CONFIG = SimpleNamespace(project=None)


def _get_child(node: BoundNode, name: str) -> BoundNode:
    return not_none(
        EdgeComposition.get_child_by_identifier(bound_node=node, child_identifier=name)
    )


def _check_connected(
    node: BoundNode | fabll.Node, other: BoundNode | fabll.Node
) -> bool:
    source = node.instance if isinstance(node, fabll.Node) else node
    target = other.instance if isinstance(other, fabll.Node) else other
    path = fbrk.EdgeInterfaceConnection.is_connected_to(source=source, target=target)
    return path.get_end_node().node().is_same(other=target.node())


def _get_type_name(node: BoundNode) -> str:
    type_edge = not_none(EdgeType.get_type_edge(bound_node=node))
    type_node = EdgeType.get_type_node(edge=type_edge.edge())
    return cast_assert(str, type_node.get_attr(key="type_identifier"))


def test_signal_connect():
    """Test that signals are connected."""
    g, tg, stdlib, result, app_instance = build_instance(
        """
        module App:
            signal a
            signal b
            signal c
            a ~ b
        """,
        "App",
    )

    a = _get_child(app_instance, "a")
    b = _get_child(app_instance, "b")
    c = _get_child(app_instance, "c")

    assert _check_connected(a, b)
    assert not _check_connected(a, c)


def test_interface_connect():
    """Test that interfaces are connected."""
    _, _, _, _, app_instance = build_instance(
        """
            interface SomeInterface:
                signal one
                signal two

            module App:
                a = new SomeInterface
                b = new SomeInterface
                c = new SomeInterface
                a ~ b
            """,
        "App",
    )
    a = _get_child(app_instance, "a")
    b = _get_child(app_instance, "b")
    c = _get_child(app_instance, "c")

    assert _check_connected(a, b)
    assert not _check_connected(a, c)

    a_one = _get_child(a, "one")
    b_one = _get_child(b, "one")
    c_one = _get_child(c, "one")
    a_two = _get_child(a, "two")
    b_two = _get_child(b, "two")
    c_two = _get_child(c, "two")

    assert _check_connected(a_one, b_one)
    assert _check_connected(a_two, b_two)
    assert not any(
        _check_connected(a_one, other) for other in [a_two, b_two, c_one, c_two]
    )
    assert not any(
        _check_connected(a_two, other) for other in [a_one, b_one, c_one, c_two]
    )


@pytest.mark.skip(reason="to_fix")  # FIXME
def test_duck_type_connect():
    """Duck-typed interfaces are not supported anymore."""
    _, _, _, _, app_instance = build_instance(
        """
            interface SomeInterface:
                signal one
                signal two

            interface SomeOtherInterface:
                signal one
                signal two

            module App:
                a = new SomeInterface
                b = new SomeOtherInterface
                a ~ b
            """,
        "App",
    )
    a = _get_child(app_instance, "a")
    b = _get_child(app_instance, "b")

    a_one = _get_child(a, "one")
    b_one = _get_child(b, "one")
    a_two = _get_child(a, "two")
    b_two = _get_child(b, "two")

    # not supported anymore
    assert not _check_connected(a, b)
    assert not _check_connected(a_one, b_one)
    assert not _check_connected(a_two, b_two)
    assert not any(_check_connected(a_one, other) for other in [a_two, b_two])
    assert not any(_check_connected(a_two, other) for other in [a_one, b_one])


def test_directed_connect_power_via_led():
    """Test directed connect through bridgeable modules."""
    _, _, _, _, app_instance = build_instance(
        """
            #pragma experiment("BRIDGE_CONNECT")

            import ElectricPower
            import Resistor
            import LED

            module App:
                power = new ElectricPower
                current_limiting_resistor = new Resistor
                led = new LED

                power.hv ~> current_limiting_resistor ~> led ~> power.lv
            """,
        "App",
    )
    power = F.ElectricPower.bind_instance(_get_child(app_instance, "power"))
    current_limiting_resistor = F.Resistor.bind_instance(
        _get_child(app_instance, "current_limiting_resistor")
    )
    led = F.LED.bind_instance(_get_child(app_instance, "led"))

    assert _check_connected(power.hv.get(), current_limiting_resistor.unnamed[0].get())
    assert _check_connected(
        current_limiting_resistor.unnamed[1].get(), led.diode.get().anode.get()
    )
    assert _check_connected(led.diode.get().cathode.get(), power.lv.get())


def test_requires():
    """Test that .required = True adds the requires_external_usage trait."""
    _, _, _, _, app_instance = build_instance(
        """
            module App:
                signal a
                signal b
                a.required = True
            """,
        "App",
    )
    a = _get_child(app_instance, "a")
    assert fabll.Node.bind_instance(a).has_trait(F.requires_external_usage)


class TestForLoopsRuntime:
    def test_for_loop_basic(self):
        """Test for loop creates correct connections."""
        _, _, _, _, app_instance = build_instance(
            """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module App:
                    resistors = new Resistor[5]
                    for r in resistors:
                        r.unnamed[0] ~ r.unnamed[1]
                        assert r.resistance is 100kohm +/- 10%
                """,
            "App",
        )

        resistors = F.Collections.PointerSequence.bind_instance(
            _get_child(app_instance, "resistors")
        )
        for r_node in resistors.as_list():
            r = r_node.cast(F.Resistor)
            assert _check_connected(r.unnamed[0].get(), r.unnamed[1].get())
            # TODO: check resistance is 100kohm +/- 10%

    def test_for_loop_empty_list(self):
        """Test empty for loop doesn't execute body."""
        _, _, _, _, app_instance = build_instance(
            """
                #pragma experiment("FOR_LOOP")
                import Resistor
                import Electrical

                module App:
                    resistors = new Resistor[0]
                    test_pins = new Electrical[2]
                    for r in resistors:
                        test_pins[0] ~ test_pins[1]
                """,
            "App",
        )
        test_pin_0 = _get_child(app_instance, "test_pins[0]")
        test_pin_1 = _get_child(app_instance, "test_pins[1]")
        assert test_pin_0 is not None
        assert test_pin_1 is not None
        assert not _check_connected(test_pin_0, test_pin_1)

    def test_for_loop_no_pragma(self):
        with pytest.raises(DslException, match="is not enabled"):
            build_instance(
                """
                import Resistor

                module App:
                    resistors = new Resistor[5]
                    for r in resistors:
                        r.unnamed[0] ~ r.unnamed[1]
                """,
                "App",
            )

    def test_for_loop_nested_error(self):
        with pytest.raises(
            DslException, match="Invalid/Unsupported statement in for loop"
        ):
            build_instance(
                """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module App:
                    resistors = new Resistor[5]
                    resistors2 = new Resistor[5]
                    for r in resistors:
                        # nested for loops are not allowed
                        for r2 in resistors2:
                            r.unnamed[0] ~ r2.unnamed[0]
                """,
                "App",
            )

    def test_for_loop_variable_conflict(self):
        with pytest.raises(DslException, match="conflicts with an existing"):
            build_instance(
                """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module App:
                    r = new Resistor
                    resistors = new Resistor[3]
                    for r in resistors:
                        pass
                """,
                "App",
            )

    def test_for_loop_iterate_non_list(self):
        with pytest.raises(DslException, match="expected a sequence"):
            build_instance(
                """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module App:
                    r_single = new Resistor
                    for r in r_single:
                        pass
                """,
                "App",
            )

    def test_for_loop_syntax_error(self):
        from atopile.compiler.parse import parse_text_as_file

        with pytest.raises(UserSyntaxError, match="missing INDENT"):
            parse_text_as_file(
                textwrap.dedent(
                    """
                    #pragma experiment("FOR_LOOP")
                    import Resistor

                    module App:
                        resistors = new Resistor[5]
                        for r in resistors:
                        resistors[0].unnamed[0] ~ resistors[1].unnamed[0]
                    """
                )
            )

    def test_for_loop_stale_ref(self):
        with pytest.raises((DslException, ExceptionGroup)):
            build_instance(
                """
                #pragma experiment("FOR_LOOP")
                import Resistor

                module App:
                    resistors = new Resistor[5]
                    for r in resistors:
                        assert r.resistance is 100kohm
                    r.unnamed[0] ~ r.unnamed[1]
                """,
                "App",
            )

    @pytest.mark.parametrize(
        "stmt",
        [
            "import Resistor",
            "pin 1",
            "signal a",
            "trait test_trait",
        ],
    )
    def test_for_loop_illegal_statements(self, stmt: str):
        template = textwrap.dedent(
            """
            #pragma experiment("FOR_LOOP")
            #pragma experiment("TRAITS")

            import Resistor

            module App:
                nodes = new Resistor[10]
                for x in nodes:
                    {stmt}
            """
        )

        text = template.format(stmt=stmt)
        with pytest.raises(DslException, match="Invalid/Unsupported statement"):
            build_instance(text, "App")

    def test_for_loop_large(self):
        """Test for loop with large number of elements."""

        template = textwrap.dedent(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module _App:
                resistors = new Resistor[{n:d}]

                for r in resistors:
                    assert r.resistance within 100kohm +/- 10%
            """,
        )

        for n in [
            2**4,
            2**7 + 1,  # > 2**7 (originally limited by 7-bit order field)
        ]:
            g, tg, _, _, _ = build_instance(template.format(n=n), "_App")
            resistors = F.Resistor.bind_typegraph(tg).get_instances(g=g)
            assert len(resistors) == n
            for r in resistors:
                assert (
                    E.lit_op_range_from_center_rel((100, E.U.kohm), rel=0.1)
                    .as_literal.force_get()
                    .op_setic_equals(r.resistance.get().force_extract_superset())
                )

        # current limit is 2**16
        with pytest.raises(DslException, match="List exceeds maximum size"):
            build_instance(template.format(n=2**16 + 1), "App")


def test_for_loop_over_imported_sequence(tmp_path: Path):
    """Test iterating over a sequence defined in an imported module."""
    child_path = tmp_path / "child.ato"
    child_path.write_text(
        textwrap.dedent(
            """
            import Electrical

            module Widget:
                items = new Electrical[3]
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            #pragma experiment("FOR_LOOP")

            from "child.ato" import Widget
            import Electrical

            module App:
                widget = new Widget
                sink = new Electrical

                for item in widget.items:
                    item ~ sink
            """
        ),
        encoding="utf-8",
    )

    g = GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)

    linker = Linker(tmp_path, stdlib, tg)
    linker.link_imports(g, result.state)

    from atopile.compiler.deferred_executor import DeferredExecutor

    DeferredExecutor(g=g, tg=tg, state=result.state, visitor=result.visitor).execute()

    # Verify the for-loop created the expected connections
    app_type = result.state.type_roots["App"]
    make_links = tg.collect_make_links(type_node=app_type)

    # Find connections from widget.items elements to sink
    connections = [
        (lhs, rhs)
        for _, lhs, rhs in make_links
        if lhs and lhs[0] == "widget" and "sink" in rhs
    ]

    assert len(connections) == 3, f"Expected 3 connections, got {len(connections)}"


def test_assign_to_enum_param():
    """Test enum assignment to parameter."""
    _, _, _, _, app_instance = build_instance(
        """
            import Capacitor

            module App:
                cap = new Capacitor
                cap.temperature_coefficient = "X7R"
            """,
        "App",
    )
    cap = _get_child(app_instance, "cap")
    temp_coeff = F.Capacitor.bind_instance(cap).temperature_coefficient.get()
    lit = temp_coeff.is_parameter_operatable.get().try_extract_superset()
    assert lit is not None
    enum_lit = fabll.Traits(lit).get_obj(F.Literals.AbstractEnums)
    assert (
        enum_lit.get_single_value_typed(F.Capacitor.TemperatureCoefficient)
        == F.Capacitor.TemperatureCoefficient.X7R
    )


def test_assert_is():
    """Test assert is constraints."""
    _, _, _, _, app_instance = build_instance(
        """
            module App:
                a: volt
                b: dimensionless
                c: dimensionless
                d: dimensionless
                e: dimensionless
                f: dimensionless

                assert a within 2mV +/- 10%
                assert b is c
                # assert d is e is f
            """,
        "App",
    )

    a = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "a"))
    _ = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "b"))
    _ = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "c"))
    _ = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "d"))
    _ = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "e"))
    _ = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "f"))

    # Check constraints are applied
    assert a.force_get_units().compact_repr() == "V"
    assert (
        E.lit_op_range_from_center_rel((2, E.U.mV), rel=0.1)
        .as_literal.force_get()
        .op_setic_equals(a.force_extract_superset().is_literal.get())
    )
    # TODO: check b is c; d is e is f


def test_numeric_literals():
    """Test that numeric literals parse and evaluate correctly."""
    _, _, _, _, app_instance = build_instance(
        """
            module App:
                a = 1
                b = 1V
                c = 5V
                d = 5V to 8V
                e = 100mV +/- 10%
                f = 3.3V +/- 50mV
            """,
        "App",
    )
    a = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "a"))
    assert (
        E.lit_op_single(1)
        .as_literal.force_get()
        .op_setic_equals(not_none(a.force_extract_superset()))
    )

    b = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "b"))
    assert (
        E.lit_op_single((1, E.U.V))
        .as_literal.force_get()
        .op_setic_equals(not_none(b.force_extract_superset()))
    )

    c = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "c"))
    assert (
        E.lit_op_single((5, E.U.V))
        .as_literal.force_get()
        .op_setic_equals(not_none(c.force_extract_superset()))
    )

    d = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "d"))
    assert (
        E.lit_op_ranges(((5, E.U.V), (8, E.U.V)))
        .as_literal.force_get()
        .op_setic_equals(not_none(d.force_extract_superset()))
    )

    e = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "e"))
    assert (
        E.lit_op_range_from_center_rel((100, E.U.mV), rel=0.1)
        .as_literal.force_get()
        .op_setic_equals(not_none(e.force_extract_superset()))
    )

    f = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "f"))
    assert (
        E.lit_op_range_from_center((3.3, E.U.V), (0.05, E.U.V))
        .as_literal.force_get()
        .op_setic_equals(not_none(f.force_extract_superset()))
    )


def test_basic_arithmetic():
    g, tg, _, result, app_instance = build_instance(
        """
        module A:
            a = 1 to 2 * 3
            b = a + 4
        """,
        "A",
    )
    app = fabll.Node.bind_instance(app_instance)
    F.Parameters.NumericParameter.infer_units_in_tree(app)

    solver = Solver()
    solver_result = solver.simplify(tg, g, terminal=True)
    repr_map = solver_result.data.mutation_map

    a = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "a"))
    b = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "b"))

    assert (
        E.lit_op_range((3, 6))
        .as_literal.force_get()
        .op_setic_equals(
            not_none(repr_map.try_extract_superset(a.is_parameter_operatable.get()))
        )
    )
    assert (
        E.lit_op_range((7, 10))
        .as_literal.force_get()
        .op_setic_equals(
            not_none(repr_map.try_extract_superset(b.is_parameter_operatable.get()))
        )
    )


def test_empty_module_build():
    g, tg, _, result, app_instance = build_instance(
        """
        module A:
            pass
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    app = fabll.Node.bind_instance(app_instance)
    assert app.has_trait(fabll.is_module)
    assert app.has_trait(is_ato_module)


def test_empty_component_build():
    g, tg, _, result, app_instance = build_instance(
        """
        component A:
            pass
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    app = fabll.Node.bind_instance(app_instance)
    assert not app.has_trait(is_ato_module)
    assert app.has_trait(is_ato_component)


def test_empty_interface_build():
    g, tg, _, result, app_instance = build_instance(
        """
        interface A:
            pass
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    app = fabll.Node.bind_instance(app_instance)
    assert not app.has_trait(fabll.is_module)
    assert app.has_trait(fabll.is_interface)
    assert not app.has_trait(is_ato_module)
    assert app.has_trait(is_ato_interface)
    # TODO: assert mif compatibility trait?


def test_simple_module_build():
    g, tg, _, result, app_instance = build_instance(
        """
        module A:
            a = 1
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    app = fabll.Node.bind_instance(app_instance)
    assert app.has_trait(fabll.is_module)
    assert app.has_trait(is_ato_module)
    a = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "a"))
    assert (
        E.lit_op_single(1)
        .as_literal.force_get()
        .op_setic_equals(not_none(a.force_extract_superset()))
    )


def test_simple_new():
    g, tg, _, result, app_instance = build_instance(
        """
        component SomeComponent:
            signal a

        module A:
            child = new SomeComponent
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    assert "SomeComponent" in result.state.type_roots
    child = _get_child(app_instance, "child")

    assert _get_type_name(child).endswith("SomeComponent")
    a = _get_child(child, "a")
    assert fabll.Node.bind_instance(a).isinstance(F.Electrical)


def test_multiple_new():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        import Resistor

        module A:
            resistors = new Resistor[5]
            resistors[0].package = "R0402"
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    resistors_container = _get_child(app_instance, "resistors")
    assert resistors_container is not None
    for i in range(5):
        r_node = _get_child(app_instance, f"resistors[{i}]")
        assert isinstance(r_node, BoundNode)
        r = fabll.Node.bind_instance(r_node)
        assert r.isinstance(F.Resistor)

        if i == 0:
            assert (
                r.get_trait(F.has_package_requirements)
                .size.get()
                .force_extract_singleton_typed(SMDSize)
                == SMDSize.I0402
            )
        else:
            assert not r.has_trait(F.has_package_requirements)


def test_invalid_multiple_new_count_negative():
    with pytest.raises(UserSyntaxError):
        build_instance(
            """
            module Inner:
                pass

            module A:
                resistors = new Inner[-1]
            """,
            "A",
        )


def test_invalid_multiple_new_count_float():
    with pytest.raises(DslException):
        build_instance(
            """
            module Inner:
                pass

            module A:
                resistors = new Inner[1.0]
            """,
            "A",
        )


def test_invalid_multiple_new_count_hex():
    _, _, _, result, app_instance = build_instance(
        """
            module Inner:
                pass

            module A:
                resistors = new Inner[0x10]
            """,
        "A",
    )
    assert "A" in result.state.type_roots
    resistors = F.Collections.PointerSequence.bind_instance(
        _get_child(app_instance, "resistors")
    )
    assert len(resistors.as_list()) == 16


def test_nested_nodes():
    _, tg, _, result, app_instance = build_instance(
        """
        interface SomeInterface:
            signal d
            signal e

        component SomeComponent:
            pin A1
            signal a
            a ~ A1
            signal b ~ pin 2
            signal c ~ pin "C3"

        module SomeModule:
            cmp = new SomeComponent
            intf = new SomeInterface

        module ChildModule from SomeModule:
            signal child_signal

        module A:
            child = new ChildModule
            intf = new SomeInterface
            intf ~ child.intf
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    assert "SomeInterface" in result.state.type_roots
    assert "SomeComponent" in result.state.type_roots
    assert "SomeModule" in result.state.type_roots
    assert "ChildModule" in result.state.type_roots

    child = _get_child(app_instance, "child")
    intf = _get_child(app_instance, "intf")

    assert _check_connected(intf, _get_child(child, "intf"))


def test_standard_library_import():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        import Resistor

        module A:
            r1 = new Resistor
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    r1_node = _get_child(app_instance, "r1")
    assert fabll.Node.bind_instance(r1_node).isinstance(F.Resistor)


@pytest.mark.parametrize(
    "import_stmt,class_name,pkg_str,pkg",
    [
        ("import Resistor", "Resistor", "R0402", SMDSize.I0402),
        ("import Capacitor", "Capacitor", "C0402", SMDSize.I0402),
    ],
)
def test_reserved_attrs(import_stmt: str, class_name: str, pkg_str: str, pkg: SMDSize):
    mfr = "Some Manufacturer"
    mpn = "1234567890"

    g, tg, stdlib, result, app_instance = build_instance(
        f"""
        {import_stmt}

        module A:
            a = new {class_name}
            a.package = "{pkg_str}"
            a.mpn = "{mpn}"
            a.manufacturer = "{mfr}"
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    a = _get_child(app_instance, "a")
    a_node = fabll.Node.bind_instance(a)
    a_module = a_node.get_trait(fabll.is_module)
    match class_name:
        case "Resistor":
            assert fabll.Node.bind_instance(a).isinstance(F.Resistor)
        case "Capacitor":
            assert fabll.Node.bind_instance(a).isinstance(F.Capacitor)
        case _:
            assert False
    assert (
        fabll.Node.bind_instance(a)
        .get_trait(F.has_package_requirements)
        .size.get()
        .force_extract_singleton_typed(SMDSize)
        == pkg
    )
    is_pbpn = F.Pickable.is_pickable_by_part_number.try_check_or_convert(a_module)
    assert is_pbpn is not None
    assert is_pbpn.get_manufacturer() == mfr
    assert is_pbpn.get_partno() == mpn


def test_import_ato(tmp_path: Path):
    some_module_path = tmp_path / "to" / "some_module.ato"
    some_module_path.parent.mkdir(parents=True)

    some_module_path.write_text(
        textwrap.dedent(
            """
            import Resistor

            module SpecialResistor from Resistor:
                package = "R0805"
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            from "to/some_module.ato" import SpecialResistor

            module A:
                r1 = new SpecialResistor
            """
        ),
        encoding="utf-8",
    )

    g = GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    assert "A" in result.state.type_roots

    linker = Linker(NULL_CONFIG, stdlib, tg)
    linker.link_imports(g, result.state)

    app_instance = tg.instantiate_node(
        type_node=result.state.type_roots["A"], attributes={}
    )
    r1_node = _get_child(app_instance, "r1")

    print(
        fabll.Node.bind_instance(r1_node)
        .get_trait(F.has_package_requirements)
        .get_sizes()
        == [SMDSize.I0805]
    )


@pytest.mark.skip(reason="xfail")  # TODO: traceback handling
@pytest.mark.parametrize(
    "module,count", [("A", 1), ("B", 3), ("C", 5), ("D", 6), ("E", 6)]
)
def test_traceback(module: str, count: int):
    with pytest.raises(DslException) as e:
        build_instance(
            f"""
            module A:
                missing_field ~ another_missing_field

            module B:
                a = new A

            module C:
                b = new B

            module D from C:
                pass

            module E from D:
                pass

            module App:
                entry = new {module}
            """
            "",
            "App",
        )

    # FIXME: tracebacks from DslException
    assert e.value.traceback is not None
    assert len(e.value.traceback) == count


def test_directed_connect_signals():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        #pragma experiment("BRIDGE_CONNECT")

        module App:
            signal a
            signal b

            a ~> b
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    a = _get_child(app_instance, "a")
    b = _get_child(app_instance, "b")
    assert _check_connected(a, b)


def test_directed_connect_signal_to_resistor():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        #pragma experiment("BRIDGE_CONNECT")
        import Resistor

        module App:
            signal a

            r = new Resistor
            a ~> r
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    a = _get_child(app_instance, "a")
    r_node = _get_child(app_instance, "r")
    r = F.Resistor.bind_instance(cast_assert(BoundNode, r_node))
    assert _check_connected(a, r.unnamed[0].get())


@pytest.mark.skip(reason="Error handling not implemented yet")
def test_directed_connect_non_bridge():
    with pytest.raises(DslException, match="not bridgeable"):
        build_instance(
            """
            #pragma experiment("BRIDGE_CONNECT")
            import Resistor

            module A:
                pass

            module App:
                signal a
                signal b
                bridge = new A
                a ~> bridge ~> b
            """,
            "App",
        )


def test_directed_connect_can_bridge():
    _, _, _, result, app_instance = build_instance(
        """
            #pragma experiment("BRIDGE_CONNECT")
            #pragma experiment("TRAITS")
            import can_bridge_by_name

            module Abridge:
                signal a
                signal b
                trait can_bridge_by_name<input_name="a", output_name="b">

            module App:
                signal c
                signal d
                bridge = new Abridge
                c ~> bridge ~> d
            """,
        "App",
    )
    assert "App" in result.state.type_roots
    c = _get_child(app_instance, "c")
    d = _get_child(app_instance, "d")
    bridge = _get_child(app_instance, "bridge")
    a = F.Electrical.bind_instance(_get_child(bridge, "a"))
    b = F.Electrical.bind_instance(_get_child(bridge, "b"))
    assert _check_connected(c, a)
    assert _check_connected(b, d)


def test_directed_connect_mif_as_bridge():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        #pragma experiment("BRIDGE_CONNECT")

        module App:
            signal a
            signal b
            signal c

            a ~> b ~> c
        """,
        "App",
    )
    a = _get_child(app_instance, "a")
    b = _get_child(app_instance, "b")
    c = _get_child(app_instance, "c")
    # All three should be connected in a chain via their can_bridge trait
    assert _check_connected(a, b)
    assert _check_connected(b, c)
    assert _check_connected(a, c)


def test_key():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        import Resistor
        module App:
            r = new Resistor
            signal a ~ r.unnamed[0]
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    r = _get_child(app_instance, "r")
    assert fabll.Node.bind_instance(r).isinstance(F.Resistor)


def test_pin_ref():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        module Abc:
            pin 1 ~ signal b

        module App:
            abc = new Abc
            signal a ~ abc.1
        """,
        "App",
    )
    assert "App" in result.state.type_roots


def test_missing_pin_ref_raises():
    with pytest.raises(DslException):
        build_instance(
            """
            import Resistor
            module App:
                r = new Resistor
                signal a ~ r.unnamed[2]
            """,
            "App",
        )


def test_regression_pin_refs():
    g, tg, stdlib, result, app_instance = build_instance(
        """
        import ElectricPower

        component App:
            signal CNT ~ pin 3
            signal NP ~ pin 5
            signal VIN_ ~ pin 2
            signal VINplus ~ pin 1
            signal VO_ ~ pin 4
            signal VOplus ~ pin 6

            power_in = new ElectricPower
            power_out = new ElectricPower

            power_in.hv ~ pin 1
            power_in.lv ~ pin 2
            power_out.hv ~ pin 6
            power_out.lv ~ pin 4
        """,
        "App",
    )
    assert "App" in result.state.type_roots


def test_pragma_feature_existing():
    EXPERIMENT_NAME = "BLA"

    class TestFeatures(StrEnum):
        BLA = EXPERIMENT_NAME

    _BACKUP = ASTVisitor._Experiment
    ASTVisitor._Experiment = TestFeatures  # type: ignore

    g, tg, stdlib, result, app_instance = build_instance(
        f"""
        #pragma experiment("{EXPERIMENT_NAME}")

        module App:
            pass
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    ASTVisitor._Experiment = _BACKUP  # type: ignore


def test_pragma_feature_nonexisting():
    with pytest.raises(DslException, match="Experiment not recognized: `BLAB`"):
        build_instance(
            """
            #pragma experiment("BLAB")

            module App:
                pass
            """,
            "App",
        )


def test_pragma_feature_multiple_args():
    with pytest.raises(DslException, match="one argument"):
        build_instance(
            """
            #pragma experiment("BLAB", 5)

            module App:
                pass
            """,
            "App",
        )


def test_list_literal_basic():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r1 = new Resistor
            r2 = new Resistor
            r3 = new Resistor
            for r in [r1, r3]:
                assert r.resistance within 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    r1_node = _get_child(app_instance, "r1")
    assert fabll.Node.bind_instance(r1_node).isinstance(F.Resistor)
    r1 = F.Resistor.bind_instance(r1_node)
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.force_get()
        .op_setic_equals(not_none(r1.resistance.get().try_extract_superset()))
    )

    r2_node = _get_child(app_instance, "r2")
    assert fabll.Node.bind_instance(r2_node).isinstance(F.Resistor)
    r2 = F.Resistor.bind_instance(r2_node)
    assert (
        E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
        .as_literal.force_get()
        .op_setic_equals(not_none(r2.resistance.get().try_extract_superset()))
    )

    r3_node = _get_child(app_instance, "r3")
    assert fabll.Node.bind_instance(r3_node).isinstance(F.Resistor)
    r3 = F.Resistor.bind_instance(r3_node)
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.force_get()
        .op_setic_equals(not_none(r3.resistance.get().try_extract_superset()))
    )


def test_list_literal_nested():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module Nested:
            r1 = new Resistor
            r2 = new Resistor
            r3 = new Resistor

        module App:
            nested = new Nested
            for r in [nested.r1, nested.r3]:
                assert r.resistance within 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    nested_node = _get_child(app_instance, "nested")

    r1 = F.Resistor.bind_instance(_get_child(nested_node, "r1"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.force_get()
        .op_setic_equals(not_none(r1.resistance.get().try_extract_superset()))
    )

    r2 = F.Resistor.bind_instance(_get_child(nested_node, "r2"))
    assert (
        E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
        .as_literal.force_get()
        .op_setic_equals(not_none(r2.resistance.get().try_extract_superset()))
    )

    r3 = F.Resistor.bind_instance(_get_child(nested_node, "r3"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.force_get()
        .op_setic_equals(not_none(r3.resistance.get().try_extract_superset()))
    )


def test_list_literal_long():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r1 = new Resistor
            r2 = new Resistor
            r3 = new Resistor
            for r in [
                r1,
                r3,
            ]:
                assert r.resistance within 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    r1 = F.Resistor.bind_instance(_get_child(app_instance, "r1"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.force_get()
        .op_setic_equals(not_none(r1.resistance.get().try_extract_superset()))
    )
    r2 = F.Resistor.bind_instance(_get_child(app_instance, "r2"))
    assert (
        E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
        .as_literal.force_get()
        .op_setic_equals(not_none(r2.resistance.get().try_extract_superset()))
    )
    r3 = F.Resistor.bind_instance(_get_child(app_instance, "r3"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.force_get()
        .op_setic_equals(not_none(r3.resistance.get().try_extract_superset()))
    )


def test_list_literal_empty():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r1 = new Resistor
            for r in []:
                assert r.resistance within 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    r1 = F.Resistor.bind_instance(_get_child(app_instance, "r1"))
    assert (
        E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
        .as_literal.force_get()
        .op_setic_equals(not_none(r1.resistance.get().try_extract_superset()))
    )


def test_list_literal_invalid():
    with pytest.raises(
        UserSyntaxError,
        match=r"mismatched input '\"A\"' expecting {NUMBER, NAME, '\(', '\+', '\-'}",
    ):
        _, _, _, result, app_instance = build_instance(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module App:
                rs = new Resistor[2]
                for r in [rs]:
                    assert r.resistance is "A"
            """
            "",
            "App",
        )


def test_plain_trait():
    class test_trait(fabll.Node):
        is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import test_trait

        module App:
            trait test_trait
        """,
        "App",
        stdlib_extra=[test_trait],
    )
    assert "App" in result.state.type_roots
    app = fabll.Node.bind_instance(app_instance)
    assert app.has_trait(test_trait)


def test_unimported_trait():
    class _test_trait(fabll.Node):
        is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    with pytest.raises(
        DslException, match="Trait `test_trait` must be imported before use"
    ):
        build_instance(
            """
            #pragma experiment("TRAITS")

            module App:
                trait test_trait
            """,
            "App",
            stdlib_extra=[_test_trait],
        )


def test_nonexistent_trait():
    with pytest.raises(
        DslException,
        match="Trait `this_trait_does_not_exist` must be imported before use",
    ):
        build_instance(
            """
            #pragma experiment("TRAITS")

            module App:
                trait this_trait_does_not_exist
            """,
            "App",
        )


def test_invalid_trait():
    with pytest.raises(DslException, match="not a valid trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import Resistor

            module App:
                trait Resistor
            """,
            "App",
        )


def test_parameterised_trait_no_params():
    """Test that trait without required params is accepted (no constraint added)."""
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_datasheet

        module App:
            trait has_datasheet
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    # Trait is created but with no constraint on datasheet
    trait = fabll.Node.bind_instance(app_instance).get_trait(F.has_datasheet)
    # datasheet_ parameter exists but is unconstrained
    assert trait.datasheet_.get().try_extract_singleton() is None


def test_nested_trait_access():
    pass  # we currently don't have any nested traits
    # with pytest.raises(UserSyntaxError):
    #     build_instance(
    #         """
    #         #pragma experiment("TRAITS")

    #         import Symbol

    #         module App:
    #             trait Symbol.has_kicad_symbol  # wrong syntax
    #         """,
    #         "App",
    #     )


def test_nested_trait_namespace_access():
    pass  # we currently don't have any nested traits
    # with pytest.raises(DslException, match="not a valid trait"):
    # build_instance(
    #     """
    #     #pragma experiment("TRAITS")

    #     import Symbol

    #     module App:
    #         trait Symbol::has_kicad_symbol # trait should be moved to the top level
    #     """,
    #     "App",
    # )


def test_alternate_trait_constructor_dot_access():
    with pytest.raises(UserSyntaxError):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import has_part_picked

            module App:
                trait has_part_picked.by_supplier
            """,
            "App",
        )


def test_alternate_trait_constructor_with_params():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_part_picked

        module App:
            trait has_part_picked::by_supplier<supplier_id="lcsc", supplier_partno="C123456", manufacturer="Example Inc.", partno="123456">
        """,  # noqa: E501
        "App",
    )
    assert "App" in result.state.type_roots

    trait = fabll.Node.bind_instance(app_instance).get_trait(F.Pickable.has_part_picked)
    assert trait.supplier_id.get().extract_singleton() == "lcsc"
    assert trait.supplier_partno.get().extract_singleton() == "C123456"


def test_parameterised_trait_with_pos_args():
    with pytest.raises(UserSyntaxError):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import has_net_name

            module App:
                trait has_net_name<"example">
            """,
            "App",
        )


def test_parameterised_trait_with_params():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_net_name_suggestion

        module App:
            trait has_net_name_suggestion<name="example", level="SUGGESTED">
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    trait = fabll.Node.bind_instance(app_instance).get_trait(F.has_net_name_suggestion)
    assert trait.name == "example"
    assert trait.level == F.has_net_name_suggestion.Level.SUGGESTED


def test_trait_alternate_constructor_precedence():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_part_picked

        module App:
            trait has_part_picked::by_supplier<supplier_id="1234", supplier_partno="2345", manufacturer="good_company", partno="amazing_part">
        """,  # noqa: E501
        "App",
    )
    assert "App" in result.state.type_roots
    trait = fabll.Node.bind_instance(app_instance).get_trait(F.Pickable.has_part_picked)
    assert trait.supplier_id.get().extract_singleton() == "1234"
    assert trait.supplier_partno.get().extract_singleton() == "2345"
    assert trait.manufacturer.get().extract_singleton() == "good_company"
    assert trait.partno.get().extract_singleton() == "amazing_part"


def test_parameterised_trait_no_params_net_name():
    """Test that trait without required params is accepted (no constraint added)."""
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_net_name_suggestion

        module App:
            trait has_net_name_suggestion
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    # Trait is created but with no constraints
    trait = fabll.Node.bind_instance(app_instance).get_trait(F.has_net_name_suggestion)
    assert trait.name_.get().try_extract_singleton() is None


def test_nested_override_trait():
    """Test if we can use overrides nested"""
    _, _, _, result, app_instance = build_instance(
        """
        module App:
            power = new ElectricPower
            power.hv.required = True
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    power = F.ElectricPower.bind_instance(_get_child(app_instance, "power"))
    assert power.hv.get().has_trait(F.requires_external_usage)


def test_slice_for_loop():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[10]
            resistors2 = new Resistor[2]
            for r in resistors[0:3]:
                assert r.resistance within 100kohm

            for r in resistors[-3:-1]:
                assert r.resistance within 200kohm

            for r in resistors[3:6:2]:
                assert r.resistance within 150kohm

            for r in resistors2[:]:
                assert r.resistance within 250kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    resistors = F.Collections.PointerSequence.bind_instance(
        _get_child(app_instance, "resistors")
    )
    resistors2 = F.Collections.PointerSequence.bind_instance(
        _get_child(app_instance, "resistors2")
    )

    for r_node in resistors.as_list()[0:3]:
        r = r_node.cast(F.Resistor)
        assert (
            E.lit_op_single((100, E.U.kohm))
            .as_literal.force_get()
            .op_setic_equals(r.resistance.get().force_extract_superset())
        )

    for r_node in resistors.as_list()[-3:-1]:
        r = r_node.cast(F.Resistor)
        assert (
            E.lit_op_single((200, E.U.kohm))
            .as_literal.force_get()
            .op_setic_equals(r.resistance.get().force_extract_superset())
        )

    for r_node in resistors.as_list()[3:6:2]:
        r = r_node.cast(F.Resistor)
        assert (
            E.lit_op_single((150, E.U.kohm))
            .as_literal.force_get()
            .op_setic_equals(r.resistance.get().force_extract_superset())
        )

    # Check that other resistors weren't assigned a value in the loop
    for r_node in resistors.as_list()[6:-3]:
        r = r_node.cast(F.Resistor)
        assert (
            E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
            .as_literal.force_get()
            .op_setic_equals(not_none(r.resistance.get().try_extract_superset()))
        )

    for r_node in resistors2.as_list()[:]:
        r = r_node.cast(F.Resistor)
        assert (
            E.lit_op_single((250, E.U.kohm))
            .as_literal.force_get()
            .op_setic_equals(r.resistance.get().force_extract_superset())
        )


def test_assign_to_child_parameter():
    _, _, _, result, app_instance = build_instance(
        """
        import Resistor

        module CustomResistor:
            resistance: ohms

        module App:
            r = new Resistor
            r -> CustomResistor
            r.resistance = 150kohm +/- 10%
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    r = F.Resistor.bind_instance(_get_child(app_instance, "r"))
    # Get values from parameter directly ensures values are in display units
    res_param = r.resistance.get()
    assert res_param.get_values() == [135000, 165000]
    # Ensure that the resistance parameter display units are correct
    assert (
        fabll.Traits(res_param.force_get_display_units()).get_obj_raw().get_type_name()
        == "Ohm"
    )


def test_slice_non_list():
    with pytest.raises(
        DslException,
        match="Cannot iterate over `r_single`: expected a sequence, got `Resistor`",
    ):
        build_instance(
            """
            #pragma experiment("FOR_LOOP")

            module App:
                r_single = new Resistor
                for r in r_single[:]:  # Attempt to slice a non-list
                    pass
            """,
            "App",
        )


def test_slice_invalid_step():
    with pytest.raises(DslException, match="Slice step cannot be zero"):
        build_instance(
            """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors[::0]: # Slice step cannot be zero
                pass
        """,
            "App",
        )


def test_slice_bigger_start_than_end():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors[3:1]:
                assert r.resistance within 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    resistors = _get_child(app_instance, "resistors")
    rs = F.Collections.PointerSequence.bind_instance(cast_assert(BoundNode, resistors))
    resistor_list = rs.as_list()
    assert isinstance(resistor_list, list)
    for r_node in resistor_list[3:1]:
        assert (
            E.lit_op_single((100, E.U.kohm))
            .as_literal.force_get()
            .op_setic_equals(
                r_node.cast(F.Resistor).resistance.get().force_extract_superset()
            )
        )

    for r_node in set(resistor_list) - set(resistor_list[3:1]):
        r = r_node.cast(F.Resistor)
        assert (
            E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
            .as_literal.force_get()
            .op_setic_equals(not_none(r.resistance.get().try_extract_superset()))
        )


def test_directed_connect_reverse_signals():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("BRIDGE_CONNECT")

        module App:
            signal a
            signal b

            b <~ a
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    assert _check_connected(
        _get_child(app_instance, "a"), _get_child(app_instance, "b")
    )


def test_directed_connect_reverse_power_via_led():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("BRIDGE_CONNECT")

        import ElectricPower
        import Resistor
        import LED

        module App:
            power = new ElectricPower
            current_limiting_resistor = new Resistor
            led = new LED

            power.lv <~ led <~ current_limiting_resistor <~ power.hv
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    power = F.ElectricPower.bind_instance(_get_child(app_instance, "power"))
    current_limiting_resistor = F.Resistor.bind_instance(
        _get_child(app_instance, "current_limiting_resistor")
    )
    led = F.LED.bind_instance(_get_child(app_instance, "led"))
    # Reverse: power.hv -> resistor[0], resistor[1] -> led.anode, cathode -> power.lv
    assert _check_connected(power.lv.get(), led.diode.get().cathode.get())
    assert _check_connected(
        led.diode.get().anode.get(), current_limiting_resistor.unnamed[1].get()
    )
    assert _check_connected(current_limiting_resistor.unnamed[0].get(), power.hv.get())


def test_directed_connect_reverse_resistor_to_signal():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("BRIDGE_CONNECT")

        import Resistor

        module App:
            signal a
            r = new Resistor
            r <~ a
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    a = _get_child(app_instance, "a")
    r_node = _get_child(app_instance, "r")
    r = F.Resistor.bind_instance(cast_assert(BoundNode, r_node))
    assert _check_connected(a, r.unnamed[0].get())


def test_directed_connect_mixed_directions():
    with pytest.raises(
        DslException,
        match="Only one connection direction per statement allowed",
    ):
        build_instance(
            """
            #pragma experiment("BRIDGE_CONNECT")

            import Resistor

            module App:
                signal a
                signal b
                resistor = new Resistor

                a <~ resistor ~> b
            """,
            "App",
        )


def test_module_templating():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import Addressor

        module App:
            addressor7 = new Addressor<address_bits=7>
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    addressor7 = _get_child(app_instance, "addressor7")
    # Get address_lines directly as a PointerSequence
    address_lines = F.Collections.PointerSequence.bind_instance(
        _get_child(addressor7, "address_lines")
    )
    assert len(address_lines.as_list()) == 7


def test_module_templating_list():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import Addressor

        module App:
            addressors = new Addressor[3]<address_bits=7>
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    # Arrays are stored as PointerSequence nodes in the graph
    addressors_seq = F.Collections.PointerSequence.bind_instance(
        _get_child(app_instance, "addressors")
    )
    addressor_nodes = [
        cast_assert(BoundNode, node.instance) for node in addressors_seq.as_list()
    ]
    assert len(addressor_nodes) == 3
    # Check each addressor has 7 address lines
    for addressor_node in addressor_nodes:
        address_lines = F.Collections.PointerSequence.bind_instance(
            _get_child(addressor_node, "address_lines")
        )
        assert len(address_lines.as_list()) == 7


def test_trait_template_enum():
    """Test trait templating with enum parameter via has_package_requirements."""
    # Test has_package_requirements.MakeChild directly in Python
    # since ato inheritance from stdlib Resistor is problematic in test context
    g = GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        r = F.Resistor.MakeChild()
        _trait = fabll.Traits.MakeEdge(
            F.has_package_requirements.MakeChild(size="I0805")
        )

    _App._handle_cls_attr(
        "_link_trait",
        fabll._EdgeField(
            [_App.r],
            [_App._trait],
            edge=fbrk.EdgeTrait.build(),
        ),
    )

    app = _App.bind_typegraph(tg).create_instance(g)
    r = app.r.get()

    # Verify the trait is attached and has correct size
    trait = r.get_trait(F.has_package_requirements)
    assert trait.size.get().force_extract_singleton_typed(SMDSize) == SMDSize.I0805


def test_trait_template_enum_invalid():
    """Test that invalid enum value raises DslException."""
    with pytest.raises(
        DslException,
        match="Invalid value for template arguments 'size' for has_package_requirements",  # noqa: E501
    ):
        F.has_package_requirements.MakeChild(size="<invalid size>")


def test_module_template_enum():
    class _Module(fabll.Node):
        size = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)
        _override_type_identifier = "Module"

        @classmethod
        def MakeChild(cls, size: str) -> fabll._ChildField:
            """Custom MakeChild that accepts string size and converts to enum."""
            out = fabll._ChildField(cls)
            try:
                size_enum = SMDSize[size]
            except KeyError:
                raise DslException(f"Invalid size: '{size}'")
            out.add_dependant(
                F.Literals.AbstractEnums.MakeChild_SetSuperset(
                    [out, cls.size], size_enum
                )
            )
            return out

    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import Module

        module App:
            r = new Module<size="I0805">
        """,
        "App",
        stdlib_extra=[_Module],
    )

    assert "App" in result.state.type_roots
    r = _get_child(app_instance, "r")
    r = _Module.bind_instance(r)
    # Use get_single_value_typed for enum comparison
    assert r.size.get().force_extract_singleton_typed(SMDSize) == SMDSize.I0805


def test_module_template_enum_invalid():
    class _TestModule(fabll.Node):
        size = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

        @classmethod
        def MakeChild(cls, size: str) -> fabll._ChildField:
            """Custom MakeChild that accepts string size and converts to enum."""
            out = fabll._ChildField(cls)
            try:
                size_enum = SMDSize[size]
            except KeyError:
                raise DslException(f"Invalid size: '{size}'")
            out.add_dependant(
                F.Literals.AbstractEnums.MakeChild_SetSuperset(
                    [out, cls.size], size_enum
                )
            )
            return out

    module_name = _TestModule._type_identifier()

    with pytest.raises(DslException, match="Invalid size: '<invalid size>'"):
        build_instance(
            f"""
            #pragma experiment("MODULE_TEMPLATING")

            import {module_name}

            module App:
                r = new {module_name}<size="<invalid size>">
            """,
            "App",
            stdlib_extra=[_TestModule],
        )


# Helper classes for enum tests
class _IntEnumForTests(IntEnum):
    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3


class _StrEnumForTests(StrEnum):
    OPTION_A = "option_a"
    OPTION_B = "option_b"
    OPTION_C = "option_c"
    PRESET_A = "preset_a"
    PRESET_B = "preset_b"


# Test classes for enum template tests
class ModuleWithIntEnum(fabll.Node):
    _value = F.Parameters.EnumParameter.MakeChild(enum_t=_IntEnumForTests)

    @classmethod
    def MakeChild(cls, value: int) -> fabll._ChildField:
        """Custom MakeChild that accepts int value and converts to enum."""
        out = fabll._ChildField(cls)
        try:
            value_enum = _IntEnumForTests(value)
        except ValueError:
            raise DslException(f"Invalid value: '{value}'")
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls._value], value_enum
            )
        )
        return out


class ModuleWithStrEnum(fabll.Node):
    _value = F.Parameters.EnumParameter.MakeChild(enum_t=_StrEnumForTests)

    @classmethod
    def MakeChild(cls, mode: str) -> fabll._ChildField:
        """Custom MakeChild that accepts string mode and converts to enum."""
        out = fabll._ChildField(cls)
        try:
            mode_enum = _StrEnumForTests[mode]
        except KeyError:
            raise DslException(f"Invalid mode: '{mode}'")
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset([out, cls._value], mode_enum)
        )
        return out


@pytest.mark.parametrize(
    "module_name,module_cls,template_args,expected_value",
    [
        # Basic enum types
        (
            "ModuleWithIntEnum",
            ModuleWithIntEnum,
            "<value=2>",
            _IntEnumForTests.VALUE_2,
        ),
        (
            "ModuleWithStrEnum",
            ModuleWithStrEnum,
            '<mode="OPTION_B">',
            _StrEnumForTests.OPTION_B,
        ),
    ],
)
def test_module_template_enum_scenarios(
    module_name, module_cls, template_args, expected_value
):
    """Test various enum scenarios in module template constructors."""

    _, _, _, result, app_instance = build_instance(
        f"""
        #pragma experiment("MODULE_TEMPLATING")

        import {module_name}

        module App:
            mod = new {module_name}{template_args}
        """,
        "App",
        stdlib_extra=[ModuleWithIntEnum, ModuleWithStrEnum],
    )

    mod = _get_child(app_instance, "mod")
    mod = module_cls.bind_instance(mod)
    # Use get_single_value_typed for enum comparison
    assert (
        mod._value.get()
        .force_extract_superset()
        .get_single_value_typed(type(expected_value))
        == expected_value
    )


def test_module_template_multiple_enum_args():
    class _TestModule(fabll.Node):
        _color = F.Parameters.EnumParameter.MakeChild(enum_t=F.LED.Color)
        _channel = F.Parameters.EnumParameter.MakeChild(enum_t=F.MOSFET.ChannelType)
        _temp_coeff = F.Parameters.EnumParameter.MakeChild(
            enum_t=F.Capacitor.TemperatureCoefficient
        )

        @classmethod
        def MakeChild(
            cls,
            color: str | None = None,
            channel: str | None = None,
            temp_coeff: str | None = None,
        ) -> fabll._ChildField:
            """Custom MakeChild that accepts string enums and converts them."""
            out = fabll._ChildField(cls)

            if color is not None:
                try:
                    color_enum = F.LED.Color[color]
                except KeyError:
                    raise DslException(f"Invalid color: '{color}'")
                out.add_dependant(
                    F.Literals.AbstractEnums.MakeChild_SetSuperset(
                        [out, cls._color], color_enum
                    )
                )

            if channel is not None:
                try:
                    channel_enum = F.MOSFET.ChannelType[channel]
                except KeyError:
                    raise DslException(f"Invalid channel: '{channel}'")
                out.add_dependant(
                    F.Literals.AbstractEnums.MakeChild_SetSuperset(
                        [out, cls._channel], channel_enum
                    )
                )

            if temp_coeff is not None:
                try:
                    temp_coeff_enum = F.Capacitor.TemperatureCoefficient[temp_coeff]
                except KeyError:
                    raise DslException(f"Invalid temp_coeff: '{temp_coeff}'")
                out.add_dependant(
                    F.Literals.AbstractEnums.MakeChild_SetSuperset(
                        [out, cls._temp_coeff], temp_coeff_enum
                    )
                )

            return out

    module_name = _TestModule._type_identifier()

    _, _, _, result, app_instance = build_instance(
        f"""
        #pragma experiment("MODULE_TEMPLATING")

        import {module_name}

        module App:
            mod1 = new {module_name}<color="BLUE", channel="N_CHANNEL">
            mod2 = new {module_name}<color="RED", channel="P_CHANNEL", temp_coeff="C0G">
        """,
        "App",
        stdlib_extra=[_TestModule],
    )
    assert "App" in result.state.type_roots

    mod1 = _get_child(app_instance, "mod1")
    mod1 = _TestModule.bind_instance(mod1)
    assert (
        mod1._color.get().force_extract_singleton_typed(F.LED.Color) == F.LED.Color.BLUE
    )
    assert (
        mod1._channel.get().force_extract_singleton_typed(F.MOSFET.ChannelType)
        == F.MOSFET.ChannelType.N_CHANNEL
    )
    # temp_coeff not constrained - check it returns the full domain
    temp_coeff_superset = not_none(mod1._temp_coeff.get().try_extract_superset())
    assert set(temp_coeff_superset.get_values()) == {
        e.value for e in F.Capacitor.TemperatureCoefficient
    }

    mod2 = _get_child(app_instance, "mod2")
    mod2 = _TestModule.bind_instance(mod2)
    assert (
        mod2._color.get().force_extract_singleton_typed(F.LED.Color) == F.LED.Color.RED
    )
    assert (
        mod2._channel.get().force_extract_singleton_typed(F.MOSFET.ChannelType)
        == F.MOSFET.ChannelType.P_CHANNEL
    )
    assert (
        mod2._temp_coeff.get().force_extract_singleton_typed(
            F.Capacitor.TemperatureCoefficient
        )
        == F.Capacitor.TemperatureCoefficient.C0G
    )


@pytest.mark.parametrize(
    "value,literal",
    [
        ("1", E.lit_op_single(1)),
        ("1V", E.lit_op_single((1, E.U.V))),
        ("5V", E.lit_op_single((5, E.U.V))),
        ("5V to 8V", E.lit_op_ranges(((5, E.U.V), (8, E.U.V)))),
        ("5 to 8V", E.lit_op_ranges(((5, E.U.V), (8, E.U.V)))),
        ("5V to 8", E.lit_op_ranges(((5, E.U.V), (8, E.U.V)))),
        ("100mV +/- 10%", E.lit_op_range_from_center_rel((100, E.U.mV), rel=0.1)),
        ("3.3V +/- 50mV", E.lit_op_range_from_center((3.3, E.U.V), (50, E.U.mV))),
        ("3300 +/- 50mV", E.lit_op_range_from_center((3300, E.U.mV), (50, E.U.mV))),
    ],
)
def test_literals(value: str, literal: F.Parameters.can_be_operand):
    g, tg, _, result, app_instance = build_instance(
        f"""
        module App:
            a = {value}
        """,
        "App",
    )
    a_node = _get_child(app_instance, "a")
    a = F.Parameters.NumericParameter.bind_instance(a_node)
    assert literal.as_literal.force_get().op_setic_equals(
        not_none(a.force_extract_superset())
    )


class TestInheritanceRuntime:
    """Runtime tests for block inheritance."""

    def test_inherited_children_exist(self):
        """Inherited children exist on instantiated derived type."""
        _, _, _, _, app_instance = build_instance(
            """
            import Electrical

            module Base:
                a = new Electrical

            module Derived from Base:
                b = new Electrical

            module App:
                derived = new Derived
            """,
            "App",
        )

        derived = _get_child(app_instance, "derived")
        a = _get_child(derived, "a")
        b = _get_child(derived, "b")

        assert a is not None, "Inherited field 'a' should exist on instance"
        assert b is not None, "Own field 'b' should exist on instance"

    def test_inherited_connections_work(self):
        """Connections defined in parent work on derived instances."""
        _, _, _, _, app_instance = build_instance(
            """
            import Electrical

            module Base:
                a = new Electrical
                b = new Electrical
                a ~ b

            module Derived from Base:
                c = new Electrical

            module App:
                derived = new Derived
            """,
            "App",
        )

        derived = _get_child(app_instance, "derived")
        a = _get_child(derived, "a")
        b = _get_child(derived, "b")
        c = _get_child(derived, "c")

        assert _check_connected(a, b), (
            "a and b should be connected (inherited from Base)"
        )
        assert not _check_connected(a, c), "a and c should not be connected"

    def test_multi_level_inheritance_runtime(self):
        """Multi-level inheritance produces correct instance structure."""
        _, _, _, _, app_instance = build_instance(
            """
            import Electrical

            module Level1:
                x = new Electrical

            module Level2 from Level1:
                y = new Electrical

            module Level3 from Level2:
                z = new Electrical

            module App:
                level3 = new Level3
            """,
            "App",
        )

        level3 = _get_child(app_instance, "level3")
        x = _get_child(level3, "x")
        y = _get_child(level3, "y")
        z = _get_child(level3, "z")

        assert x is not None, "Field 'x' from Level1 should exist"
        assert y is not None, "Field 'y' from Level2 should exist"
        assert z is not None, "Own field 'z' should exist"

    def test_inherited_type_correct(self):
        """Inherited children have correct types."""
        _, _, _, _, app_instance = build_instance(
            """
            import Resistor
            import Capacitor

            module Base:
                r = new Resistor

            module Derived from Base:
                c = new Capacitor

            module App:
                derived = new Derived
            """,
            "App",
        )

        derived = _get_child(app_instance, "derived")
        r = _get_child(derived, "r")
        c = _get_child(derived, "c")

        assert _get_type_name(r) == "Resistor", (
            f"r should be Resistor, got {_get_type_name(r)}"
        )
        assert _get_type_name(c) == "Capacitor", (
            f"c should be Capacitor, got {_get_type_name(c)}"
        )

    def test_derived_override_field(self):
        """Derived module can add its own field with the same name as parent."""
        # The derived module's own field takes precedence (parent's is skipped)
        _, _, _, _, app_instance = build_instance(
            """
            import Resistor
            import Capacitor

            module Base:
                x = new Resistor

            module Derived from Base:
                y = new Capacitor

            module App:
                base = new Base
                derived = new Derived
            """,
            "App",
        )

        base = _get_child(app_instance, "base")
        derived = _get_child(app_instance, "derived")

        # Base has 'x'
        base_x = _get_child(base, "x")
        assert _get_type_name(base_x) == "Resistor"

        # Derived has both 'x' (inherited) and 'y' (own)
        derived_x = _get_child(derived, "x")
        derived_y = _get_child(derived, "y")
        assert _get_type_name(derived_x) == "Resistor"
        assert _get_type_name(derived_y) == "Capacitor"


class TestRetypeRuntime:
    """Runtime tests for retype operator."""

    def test_basic_retype_instance(self):
        """Retyped field has the new type at runtime."""
        _, _, _, _, app_instance = build_instance(
            """
            import Resistor
            import Capacitor

            module App:
                cmp = new Resistor
                cmp -> Capacitor
            """,
            "App",
        )

        cmp = _get_child(app_instance, "cmp")
        assert _get_type_name(cmp) == "Capacitor", (
            f"cmp should be Capacitor, got {_get_type_name(cmp)}"
        )

    def test_retype_in_derived_instance(self):
        """Retype in derived module produces correct instance type."""
        _, _, _, _, app_instance = build_instance(
            """
            import Resistor
            import Capacitor

            module Base:
                cmp = new Resistor

            module Derived from Base:
                cmp -> Capacitor

            module App:
                derived = new Derived
            """,
            "App",
        )

        derived = _get_child(app_instance, "derived")
        cmp = _get_child(derived, "cmp")
        assert _get_type_name(cmp) == "Capacitor", (
            f"cmp should be Capacitor after retype, got {_get_type_name(cmp)}"
        )

    def test_retype_to_local_type_instance(self):
        """Retype to a locally defined type produces correct instance."""
        _, _, _, _, app_instance = build_instance(
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
            "App",
        )

        inner = _get_child(app_instance, "inner")
        # The inner should now be of type Specialized
        inner_type = _get_type_name(inner)
        assert "Specialized" in inner_type, (
            f"inner should be Specialized, got {inner_type}"
        )


class TestImplicitParameterUnitInference:
    """Tests for implicit parameter unit inference from arithmetic expressions."""

    def test_declared_param_still_works(self):
        """Ensure explicitly declared params with arithmetic expressions still work."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                a: dimensionless
                b: dimensionless
                a = 1 to 2 * 3
                b = a + 4
            """,
            "App",
        )
        a = _get_child(app_instance, "a")
        b = _get_child(app_instance, "b")

        a_param = F.Parameters.NumericParameter.bind_instance(a)
        b_param = F.Parameters.NumericParameter.bind_instance(b)

        assert a_param is not None
        assert b_param is not None

        # dimensionless = no unit
        assert not a_param.has_trait(F.Units.has_unit)
        assert not b_param.has_trait(F.Units.has_unit)

    def test_implicit_dimensionless(self):
        """Test implicit parameter declaration from literal addition."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                a = 1 to 2
                b = a + 3
            """,
            "App",
        )

        a = _get_child(app_instance, "a")
        b = _get_child(app_instance, "b")

        a_param = F.Parameters.NumericParameter.bind_instance(a)
        b_param = F.Parameters.NumericParameter.bind_instance(b)

        assert a_param is not None
        assert b_param is not None

        assert not a_param.has_trait(F.Units.has_unit)
        assert not b_param.has_trait(F.Units.has_unit)

    def test_implicit_param_from_literal_addition(self):
        """Test implicit parameter declaration from literal addition."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                a = 1V + 2V
            """,
            "App",
        )
        a = _get_child(app_instance, "a")
        a_param = F.Parameters.NumericParameter.bind_instance(a)
        assert a_param is not None

        # Verify unit is Volt (basis vector for voltage)
        unit_trait = a_param.has_trait(F.Units.has_unit)
        assert unit_trait is not None

    def test_implicit_param_from_field_ref_arithmetic(self):
        """Test implicit parameter with field reference operand."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x: V
                x = 5V
                y = x * 2
            """,
            "App",
        )
        y = _get_child(app_instance, "y")
        y_param = F.Parameters.NumericParameter.bind_instance(y)
        assert y_param is not None

    def test_implicit_param_derived_unit_multiply(self):
        """Test unit inference for multiplication producing derived unit (V * A = W)."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                v: V
                v = 5V
                i: A
                i = 1A
                p = v * i
            """,
            "App",
        )
        p = _get_child(app_instance, "p")
        p_param = F.Parameters.NumericParameter.bind_instance(p)
        assert p_param is not None

        # Power = Voltage * Current should have Watt basis vector
        unit_trait = p_param.has_trait(F.Units.has_unit)
        assert unit_trait is not None

    def test_implicit_param_derived_unit_divide(self):
        """Test unit inference for division producing derived unit (V / A = Ohm)."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                v: V
                v = 10V
                i: A
                i = 2A
                r = v / i
            """,
            "App",
        )
        r = _get_child(app_instance, "r")
        r_param = F.Parameters.NumericParameter.bind_instance(r)
        assert r_param is not None


class TestUnitConflicts:
    """Tests for unit conflict detection and error handling."""

    def test_add_incommensurable_units_raises(self):
        """Adding V + A should raise UnitsNotCommensurableError."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    x = 1V + 1A
                """,
                "App",
            )

    def test_subtract_incommensurable_units_raises(self):
        """Subtracting V - A should raise UnitsNotCommensurableError."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    x = 5V - 2A
                """,
                "App",
            )

    def test_add_same_units_succeeds(self):
        """Adding V + V should succeed."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 1V + 2V
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_subtract_same_units_succeeds(self):
        """Subtracting V - V should succeed."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 5V - 2V
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_add_commensurable_scaled_units(self):
        """Adding mV + V should succeed (same basis vector, different multiplier)."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 100mV + 1V
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_multiply_different_units_succeeds(self):
        """Multiplying V * A should succeed and produce W."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 5V * 2A
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_divide_different_units_succeeds(self):
        """Dividing V / A should succeed and produce Ohm."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 10V / 2A
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_assert_incompatible_units_raises(self):
        """Assert constraint with incompatible units should raise."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    x = 5V
                    assert x within 1A + 2A
                """,
                "App",
            )

    def test_assert_compatible_units_succeeds(self):
        """Assert constraint with compatible units should succeed."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 5V
                assert x within 3V to 7V
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_expression_with_multiple_parameters_compatible(self):
        """Expression involving multiple parameters with compatible units."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                a = 3V
                b = 2V
                c = a + b
            """,
            "App",
        )
        c = _get_child(app_instance, "c")
        c_param = F.Parameters.NumericParameter.bind_instance(c)
        assert c_param is not None

    def test_expression_with_multiple_parameters_incompatible(self):
        """Expression involving multiple parameters with incompatible units."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    a = 3V
                    b = 2A
                    c = a + b
                """,
                "App",
            )

    def test_nested_expression_incompatible(self):
        """Nested expression with incompatible units in inner expression."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    x = (1V + 1A) * 2
                """,
                "App",
            )

    def test_chained_addition_all_compatible(self):
        """Chained addition with all compatible units."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = 1V + 2V + 3V
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_chained_addition_one_incompatible(self):
        """Chained addition with one incompatible unit in the chain."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    x = 1V + 2V + 3A
                """,
                "App",
            )

    def test_mixed_multiply_then_add_incompatible(self):
        """Multiply produces derived unit, then add with incompatible."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module App:
                    x = (1V * 1A) + 1V
                """,
                "App",
            )

    def test_mixed_multiply_then_add_compatible(self):
        """Multiply produces derived unit (W), then add with compatible (W)."""
        _, _, _, _, app_instance = build_instance(
            """
            module App:
                x = (1V * 1A) + 1W
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_parameter_from_child_module_compatible(self):
        """Parameter from child module used in compatible expression."""
        _, _, _, _, app_instance = build_instance(
            """
            module Child:
                v = 5V

            module App:
                child = new Child
                x = child.v + 3V
            """,
            "App",
        )
        x = _get_child(app_instance, "x")
        x_param = F.Parameters.NumericParameter.bind_instance(x)
        assert x_param is not None

    def test_parameter_from_child_module_incompatible(self):
        """Parameter from child module used in incompatible expression."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module Child:
                    v = 5V

                module App:
                    child = new Child
                    x = child.v + 3A
                """,
                "App",
            )

    def test_cross_module_parameter_addition_compatible(self):
        """Parameters from different modules added together compatibly."""
        _, _, _, _, app_instance = build_instance(
            """
            module ModuleA:
                voltage = 3V

            module ModuleB:
                voltage = 2V

            module App:
                a = new ModuleA
                b = new ModuleB
                total = a.voltage + b.voltage
            """,
            "App",
        )
        total = _get_child(app_instance, "total")
        total_param = F.Parameters.NumericParameter.bind_instance(total)
        assert total_param is not None

    def test_cross_module_parameter_addition_incompatible(self):
        """Parameters from different modules with incompatible units."""
        from faebryk.library.Units import UnitsNotCommensurableError

        with pytest.raises(UnitsNotCommensurableError):
            build_instance(
                """
                module ModuleA:
                    voltage = 3V

                module ModuleB:
                    current = 2A

                module App:
                    a = new ModuleA
                    b = new ModuleB
                    bad = a.voltage + b.current
                """,
                "App",
            )


class TestParameterConstraintTypes:
    """Tests for Is vs IsSubset constraint types based on block type."""

    def test_module_uses_issubset_for_parameter_constraint(self):
        """Modules should use IsSubset for parameter constraints (refinable)."""
        g, tg, _, _, app_instance = build_instance(
            """
            module App:
                voltage = 5V
            """,
            "App",
        )
        voltage = _get_child(app_instance, "voltage")
        voltage_param = F.Parameters.NumericParameter.bind_instance(voltage)

        # Modules use IsSubset - should find literal via subset extraction
        assert (
            E.lit_op_single((5, E.U.V))
            .as_literal.force_get()
            .op_setic_equals(
                not_none(voltage_param.try_extract_superset()).is_literal.get()
            )
        )

        # Should NOT find literal via exact Is extraction (modules use IsSubset)
        assert voltage_param.try_extract_subset() is None

    def test_component_uses_is_for_parameter_constraint(self):
        """Components should use Is for parameter constraints (exact)."""
        g, tg, _, _, app_instance = build_instance(
            """
            component App:
                voltage = 5V
            """,
            "App",
        )
        voltage = _get_child(app_instance, "voltage")
        voltage_param = F.Parameters.NumericParameter.bind_instance(voltage)

        # Components use Is - should find literal via exact extraction
        assert (
            E.lit_op_single((5, E.U.V))
            .as_literal.force_get()
            .op_setic_equals(not_none(voltage_param.try_extract_subset()))
        )
        # Should NOT find literal via subset extraction
        assert (
            E.lit_op_ranges(((0, E.U.V), (math.inf, E.U.V)))
            .as_literal.force_get()
            .op_setic_equals(
                not_none(voltage_param.try_extract_superset()).is_literal.get()
            )
        )

    def test_module_with_toleranced_value_uses_issubset(self):
        """Module with toleranced value should use IsSubset."""
        g, tg, _, _, app_instance = build_instance(
            """
            module App:
                resistance = 10kohm +/- 5%
            """,
            "App",
        )
        resistance = _get_child(app_instance, "resistance")
        resistance_param = F.Parameters.NumericParameter.bind_instance(resistance)

        assert (
            E.lit_op_range_from_center_rel((10000, E.U.Ohm), rel=0.05)
            .as_literal.force_get()
            .op_setic_equals(not_none(resistance_param.try_extract_superset()))
        )
        # Should NOT find literal via exact Is extraction (modules use IsSubset)
        assert resistance_param.try_extract_subset() is None

    def test_component_with_toleranced_value_uses_is(self):
        """Component with toleranced value should use Is."""
        g, tg, _, _, app_instance = build_instance(
            """
            component App:
                resistance = 10kohm +/- 5%
            """,
            "App",
        )
        resistance = _get_child(app_instance, "resistance")
        resistance_param = F.Parameters.NumericParameter.bind_instance(resistance)

        assert (
            E.lit_op_range_from_center_rel((10000, E.U.Ohm), rel=0.05)
            .as_literal.force_get()
            .op_setic_equals(
                not_none(resistance_param.try_extract_subset()).is_literal.get()
            )
        )
        assert (
            E.lit_op_ranges(((0, E.U.Ohm), (math.inf, E.U.Ohm)))
            .as_literal.force_get()
            .op_setic_equals(
                not_none(resistance_param.try_extract_superset()).is_literal.get()
            )
        )

    def test_nested_module_in_component_uses_issubset(self):
        """Module nested inside component should still use IsSubset."""
        g, tg, _, _, app_instance = build_instance(
            """
            module Inner:
                value = 3V

            component App:
                inner = new Inner
            """,
            "App",
        )
        inner = _get_child(app_instance, "inner")
        value = _get_child(inner, "value")
        value_param = F.Parameters.NumericParameter.bind_instance(value)

        # Inner is a module, so it uses IsSubset
        assert (
            E.lit_op_single((3, E.U.V))
            .as_literal.force_get()
            .op_setic_equals(
                not_none(value_param.try_extract_superset()).is_literal.get()
            )
        )
        # Should NOT find literal via exact Is extraction (modules use IsSubset)
        assert value_param.try_extract_subset() is None

    def test_nested_component_in_module_uses_is(self):
        """Component nested inside module should still use Is."""
        g, tg, _, _, app_instance = build_instance(
            """
            component Inner:
                value = 3V

            module App:
                inner = new Inner
            """,
            "App",
        )
        inner = _get_child(app_instance, "inner")
        value = _get_child(inner, "value")
        value_param = F.Parameters.NumericParameter.bind_instance(value)

        # Inner is a component, so it uses Is
        assert (
            E.lit_op_single((3, E.U.V))
            .as_literal.force_get()
            .op_setic_equals(not_none(value_param.try_extract_subset()))
        )
        assert (
            E.lit_op_ranges(((0, E.U.V), (math.inf, E.U.V)))
            .as_literal.force_get()
            .op_setic_equals(
                not_none(value_param.try_extract_superset()).is_literal.get()
            )
        )

    def test_module_range_value_uses_issubset(self):
        """Module with range value should use IsSubset."""
        g, tg, _, _, app_instance = build_instance(
            """
            module App:
                voltage = 3V to 5V
            """,
            "App",
        )
        voltage = _get_child(app_instance, "voltage")
        voltage_param = F.Parameters.NumericParameter.bind_instance(voltage)

        assert (
            E.lit_op_ranges(((3, E.U.V), (5, E.U.V)))
            .as_literal.force_get()
            .op_setic_equals(not_none(voltage_param.try_extract_superset()))
        )
        # Should NOT find literal via exact Is extraction (modules use IsSubset)
        assert voltage_param.try_extract_subset() is None

    def test_component_range_value_uses_is(self):
        """Component with range value should use Is."""
        g, tg, _, _, app_instance = build_instance(
            """
            component App:
                voltage = 3V to 5V
            """,
            "App",
        )
        voltage = _get_child(app_instance, "voltage")
        voltage_param = F.Parameters.NumericParameter.bind_instance(voltage)

        assert (
            E.lit_op_ranges(((3, E.U.V), (5, E.U.V)))
            .as_literal.force_get()
            .op_setic_equals(
                not_none(voltage_param.try_extract_subset()).is_literal.get()
            )
        )
        assert (
            E.lit_op_ranges(((0, E.U.V), (math.inf, E.U.V)))
            .as_literal.force_get()
            .op_setic_equals(not_none(voltage_param.try_extract_superset()))
        )


# =============================================================================
# Inheritance + Traits/Directed Connect Tests
# These test issues discovered while debugging ESP32 minimal example
# =============================================================================


class TestInheritanceWithTraits:
    """
    Tests for trait inheritance issues.

    Key finding: When copy_type_structure copies MakeLinks during inheritance,
    it only preserves string identifiers, losing edge type information
    (EdgeTrait, EdgePointer traversals become EdgeComposition).
    """

    def test_trait_inherited_via_module_inheritance(self):
        """
        Test 1: Verify traits are properly inherited when a module inherits from another

        This tests a simpler trait (requires_external_usage via .required = True)
        to verify the basic trait inheritance mechanism works.

        Issue: Traits defined on a parent module may not be visible on derived
        module instances if copy_type_structure doesn't properly copy trait edges.
        """
        _, _, _, _, app_instance = build_instance(
            """
            module BaseModule:
                signal input_signal
                input_signal.required = True

            module DerivedModule from BaseModule:
                pass

            module App:
                derived = new DerivedModule
            """,
            "App",
        )
        derived = _get_child(app_instance, "derived")
        input_signal = _get_child(derived, "input_signal")

        # The derived module should inherit the .required = True trait
        # from BaseModule's input_signal
        assert fabll.Node.bind_instance(input_signal).has_trait(
            F.requires_external_usage
        )

    def test_directed_connect_inherited_from_parent_module(self):
        """
        Test 2: Directed connect (~>) with inheritance and abstraction layers.

        Simulates the TLV75901_driver / AdjustableRegulator pattern:
        - BaseRegulator has power_in, power_out and can_bridge trait
        - CustomRegulator inherits from BaseRegulator
        - App uses CustomRegulator with directed connect across it

        Issue: Directed connects use reference chains with EdgeTrait and EdgePointer
        traversals. When parent's MakeLinks are copied to derived types,
        these edge types are lost (all become EdgeComposition), causing
        resolution failures during instantiation.
        """
        _, _, _, _, app_instance = build_instance(
            """
            #pragma experiment("BRIDGE_CONNECT")
            #pragma experiment("TRAITS")

            import ElectricPower
            import Resistor
            import can_bridge_by_name

            module BaseRegulator:
                power_in = new ElectricPower
                power_out = new ElectricPower
                internal_resistor = new Resistor
                # Internal connection within the regulator
                power_in.hv ~> internal_resistor ~> power_out.hv
                power_in.lv ~ power_out.lv

                # Define can_bridge trait so ~> works ACROSS this module
                trait can_bridge_by_name<input_name="power_in", output_name="power_out">

            module CustomRegulator from BaseRegulator:
                # Derived regulator adds nothing, just inherits
                pass

            module App:
                input_power = new ElectricPower
                output_power = new ElectricPower
                regulator = new CustomRegulator

                # Bridge connect ACROSS the inherited regulator
                input_power ~> regulator ~> output_power
            """,
            "App",
        )
        input_power = F.ElectricPower.bind_instance(
            _get_child(app_instance, "input_power")
        )
        output_power = F.ElectricPower.bind_instance(
            _get_child(app_instance, "output_power")
        )
        regulator = _get_child(app_instance, "regulator")
        reg_power_in = F.ElectricPower.bind_instance(_get_child(regulator, "power_in"))
        reg_power_out = F.ElectricPower.bind_instance(
            _get_child(regulator, "power_out")
        )

        # Verify the directed connect created the expected connections:
        # input_power.hv -> regulator.power_in.hv
        assert _check_connected(input_power.hv.get(), reg_power_in.hv.get())
        # regulator.power_out.hv -> output_power.hv
        assert _check_connected(reg_power_out.hv.get(), output_power.hv.get())
        # Ground connections
        assert _check_connected(input_power.lv.get(), reg_power_in.lv.get())
        assert _check_connected(reg_power_out.lv.get(), output_power.lv.get())

    def test_assert_on_inherited_field(self):
        """
        Test 3: Assert statement on a field inherited from parent module.

        Issue: Assert statements that reference inherited fields may fail
        because they're executed after inheritance resolution but the
        field references may not resolve correctly.
        """
        _, _, _, _, app_instance = build_instance(
            """
            module BaseRegulator:
                output_voltage: V

            module CustomRegulator from BaseRegulator:
                # Assert on inherited field
                assert output_voltage is 3.3V +/- 5%

            module App:
                regulator = new CustomRegulator
                regulator.output_voltage = 3.3V +/- 5%
            """,
            "App",
        )
        regulator = _get_child(app_instance, "regulator")
        output_voltage = _get_child(regulator, "output_voltage")
        output_voltage_param = F.Parameters.NumericParameter.bind_instance(
            output_voltage
        )

        # The assert should have been applied and the parameter should be constrained
        # If the assert failed to resolve the inherited field, this would error
        # during build or the constraint wouldn't be applied
        assert output_voltage_param is not None


class TestCollections:
    def test_large_collection(self):
        template = textwrap.dedent(
            """
            import Resistor

            module _App:
                resistors = new Resistor[{n:d}]
            """,
        )

        for n in [
            2**4,
            2**7 + 1,  # > 2**7 (originally limited by 7-bit order field)
        ]:
            g, tg, _, _, app_instance = build_instance(template.format(n=n), "_App")
            resistors = F.Resistor.bind_typegraph(tg).get_instances(g=g)
            assert len(resistors) == n

        with pytest.raises(DslException, match="List exceeds maximum size"):
            build_instance(template.format(n=2**16 + 1), "_App")


# =============================================================================
# Reference Override Tests
# Tests for ReferenceOverrideRegistry which handles virtual fields like
# `reference_shim` that resolve to trait-owned children
# =============================================================================


class TestReferenceOverrides:
    """
    Tests for ReferenceOverrideRegistry.

    Reference overrides allow virtual fields that access trait-owned children,
    such as `reference_shim` which resolves to the ElectricPower `reference`
    from has_single_electric_reference trait.
    """

    def test_reference_shim_at_end_of_path(self):
        """
        Test reference_shim used at the end of a field path.

        When `i2c.reference_shim` is used, it should resolve to the ElectricPower
        reference from the has_single_electric_reference trait and allow connecting
        it to another ElectricPower interface.
        """
        _, _, _, _, app_instance = build_instance(
            """
            import I2C
            import ElectricPower

            module App:
                i2c = new I2C
                power = new ElectricPower

                # Connect the I2C's internal reference to an external power rail
                i2c.reference_shim ~ power
            """,
            "App",
        )
        i2c = _get_child(app_instance, "i2c")
        power = F.ElectricPower.bind_instance(_get_child(app_instance, "power"))

        # Get the I2C's has_single_electric_reference trait and its reference
        i2c_bound = fabll.Node.bind_instance(i2c)
        trait = i2c_bound.get_trait(F.has_single_electric_reference)
        trait_reference = trait.reference.get()

        # The trait's reference should be connected to the external power
        assert _check_connected(trait_reference, power)
        assert _check_connected(trait_reference.hv.get(), power.hv.get())
        assert _check_connected(trait_reference.lv.get(), power.lv.get())

    def test_reference_shim_deprecation_warning(self, caplog):
        caplog.set_level(logging.WARNING)

        _, _, _, _, _ = build_instance(
            """
            import I2C
            import ElectricPower

            module App:
                i2c = new I2C
                power = new ElectricPower

                # Deprecated syntax: should still work, but warn
                i2c.reference_shim ~ power
            """,
            "App",
        )

        assert "reference_shim" in caplog.text
        assert "has_single_electric_reference.reference" in caplog.text

    def test_reference_shim_in_middle_of_path(self):
        """
        Test reference_shim used in the middle of a field path.

        When `i2c.reference_shim.hv` is used, it should resolve to the hv pin
        of the ElectricPower reference from has_single_electric_reference trait.
        """
        _, _, _, _, app_instance = build_instance(
            """
            import I2C
            import ElectricPower
            import Electrical

            module App:
                i2c = new I2C
                power = new ElectricPower
                hv_only = new Electrical

                # Connect just the hv pin of the I2C's internal reference
                i2c.reference_shim.hv ~ hv_only
            """,
            "App",
        )
        i2c = _get_child(app_instance, "i2c")
        hv_only = _get_child(app_instance, "hv_only")

        # Get the I2C's has_single_electric_reference trait and its reference
        i2c_bound = fabll.Node.bind_instance(i2c)
        trait = i2c_bound.get_trait(F.has_single_electric_reference)
        trait_reference = trait.reference.get()

        # The trait's reference.hv should be connected to hv_only
        assert _check_connected(trait_reference.hv.get(), hv_only)

    def test_reference_shim_in_middle_with_lv(self):
        """
        Test reference_shim with lv suffix.

        When `i2c.reference_shim.lv` is used, it should resolve to the lv pin
        of the ElectricPower reference from has_single_electric_reference trait.
        """
        _, _, _, _, app_instance = build_instance(
            """
            import I2C
            import Electrical

            module App:
                i2c = new I2C
                gnd = new Electrical

                # Connect just the lv (ground) pin of the I2C's internal reference
                i2c.reference_shim.lv ~ gnd
            """,
            "App",
        )
        i2c = _get_child(app_instance, "i2c")
        gnd = _get_child(app_instance, "gnd")

        # Get the I2C's has_single_electric_reference trait and its reference
        i2c_bound = fabll.Node.bind_instance(i2c)
        trait = i2c_bound.get_trait(F.has_single_electric_reference)
        trait_reference = trait.reference.get()

        # The trait's reference.lv should be connected to gnd
        assert _check_connected(trait_reference.lv.get(), gnd)

    def test_reference_shim_nested_module(self):
        """
        Test reference_shim on a nested module's interface.

        When `sensor.i2c.reference_shim` is used, it should resolve through
        the nested module and connect properly.
        """
        _, _, _, _, app_instance = build_instance(
            """
            import I2C
            import ElectricPower

            module Sensor:
                i2c = new I2C

            module App:
                sensor = new Sensor
                power = new ElectricPower

                # Connect nested module's I2C reference to external power
                sensor.i2c.reference_shim ~ power
            """,
            "App",
        )
        sensor = _get_child(app_instance, "sensor")
        sensor_i2c = _get_child(sensor, "i2c")
        power = F.ElectricPower.bind_instance(_get_child(app_instance, "power"))

        # Get the I2C's has_single_electric_reference trait and its reference
        i2c_bound = fabll.Node.bind_instance(sensor_i2c)
        trait = i2c_bound.get_trait(F.has_single_electric_reference)
        trait_reference = trait.reference.get()

        # The trait's reference should be connected to the external power
        assert _check_connected(trait_reference, power)

    def test_trait_pointer_access_has_single_electric_reference_reference(self):
        """
        Test explicit trait-pointer syntax:

            has_single_electric_reference.reference ~ power_io

        This should traverse the has_single_electric_reference trait on the current
        node and then access its `reference` child.
        """
        _, _, _, _, app_instance = build_instance(
            """
            #pragma experiment("TRAITS")
            import ElectricPower
            import has_single_electric_reference

            module App:
                trait has_single_electric_reference
                power_io = new ElectricPower

                has_single_electric_reference.reference ~ power_io
            """,
            "App",
        )

        power = F.ElectricPower.bind_instance(_get_child(app_instance, "power_io"))
        app_bound = fabll.Node.bind_instance(app_instance)
        trait = app_bound.get_trait(F.has_single_electric_reference)
        trait_reference = trait.reference.get()

        assert _check_connected(trait_reference, power)


class TestDSLExceptionTracebacks:
    def test_get_source_chunk(self):
        _, tg, _, result = build_type(
            """
            import Resistor

            module _App:
                r = new Resistor

                r2 = new Resistor
                r2.resistance = 1kohm +/-5%
            """,
            "A",
        )
        app_type = result.state.type_roots["_App"]

        r = _get_child(app_type, "r")
        r2 = _get_child(app_type, "r2")
        make_children = tg.collect_make_children(type_node=app_type)

        source_chunk_r1 = ASTVisitor.get_source_chunk(r)
        assert source_chunk_r1 is not None
        assert source_chunk_r1.loc.get().get_start_line() == 5
        assert source_chunk_r1.loc.get().get_end_line() == 5

        source_chunk_r2 = ASTVisitor.get_source_chunk(r2)
        assert source_chunk_r2 is not None
        assert source_chunk_r2.loc.get().get_start_line() == 7
        assert source_chunk_r2.loc.get().get_end_line() == 7

        # Directly grab the constraint node for r2.resistance
        # It's named constraint_r2_resistance_<unique_id>
        r2_res_constraint = next(
            node
            for id_, node in make_children
            if id_ is not None and id_.startswith("constraint_r2_resistance")
        )
        source_chunk_is = ASTVisitor.get_source_chunk(r2_res_constraint)
        assert source_chunk_is is not None
        assert source_chunk_is.loc.get().get_start_line() == 8
        assert source_chunk_is.loc.get().get_end_line() == 8

    def test_traceback_from_dsl_exception(self):
        with pytest.raises(DslException) as e:
            build_instance(
                """
            module C:
                pass

            module B:
                Bs = new C[2]

            module A:
                b = new B
                b[5] = 5V

            module App:
                a = new A
            """,
                "App",
            )

        assert e.value.message == "Field `b[5]` is not defined in scope"

    def test_traceback_from_invalid_pragma(self):
        with pytest.raises(DslException) as e:
            build_instance(
                """
            #pragma experiment("INVALID_EXPERIMENT")

            module App:
                pass
            """,
                "App",
            )
        assert e.value.message == "Experiment not recognized: `INVALID_EXPERIMENT`"

    def test_traceback_from_validation_error(self):
        with pytest.raises(DslException) as e:
            build_instance(
                """
            module App:
                signal s1
                power.missing = 5V
                # s1 ~ power.missing
            """,
                "App",
            )
        assert (
            e.value.message
            == "Field `power.missing.can_be_operand` could not be resolved"
        )

    def test_missing_field_in_make_link(self):
        with pytest.raises(DslException) as e:
            build_instance(
                """
            import Resistor
            import LED

            module _App from LED:
                resistor = new Resistor
                diode.anode ~ resistor.unnamed[0]
                dcathode ~ resistor.unnamed[1]
            """,
                "_App",
            )
        assert e.value.message == "Field `dcathode` could not be resolved"

    def test_error_filepath_in_main_file(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "main.ato"
            main_file.write_text("""
module TestModule:
                # Reference a non-existent symbol to trigger an error
                child = new NonExistentModule
            """)
            result = build_file(
                g=g,
                tg=tg,
                import_path="test",
                path=main_file,
            )

        # This should raise an error about undefined symbol
        with pytest.raises(DslRichException) as exc_info:
            stdlib = StdlibRegistry(tg=tg, allowlist=STDLIB_ALLOWLIST)
            linker = Linker(
                config_obj=None,
                stdlib=stdlib,
                tg=tg,
            )
            build_stage_2(g=g, tg=tg, linker=linker, result=result)

        # Check that the error has the correct filepath
        assert exc_info.value.file_path is not None
        assert exc_info.value.file_path == main_file
        assert "NonExistentModule" in str(exc_info.value)

    def test_error_filepath_in_imported_file(self):
        """Test that errors in imported files show the correct filepath."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an imported file with an error
            imported_file = Path(tmpdir) / "imported.ato"
            imported_file.write_text("""
module ImportedModule:
    # Reference a non-existent symbol
    child = new AnotherNonExistent
    """)

            # Create main file that imports the problematic module
            main_file = Path(tmpdir) / "main.ato"
            main_file.write_text("""
from "imported.ato" import ImportedModule

module MainModule:
    imported = new ImportedModule
    """)

            result = build_file(
                g=g,
                tg=tg,
                import_path="test",
                path=main_file,
            )

            stdlib = StdlibRegistry(tg=tg, allowlist=STDLIB_ALLOWLIST)
            linker = Linker(
                config_obj=None,
                stdlib=stdlib,
                tg=tg,
            )

            # This should raise an error about undefined symbol in imported file
            with pytest.raises(DslRichException) as exc_info:
                build_stage_2(g=g, tg=tg, linker=linker, result=result)

            # Check that the error has the correct filepath (should be imported_file)
            assert exc_info.value.file_path is not None
            # The error should reference the imported file, not the main file
            # Use resolve() to handle symlinks (e.g., /private/var vs /var on macOS)
            assert exc_info.value.file_path.resolve() == imported_file.resolve()
            assert "AnotherNonExistent" in str(exc_info.value)

    def test_error_rendering_uses_source_chunk_filepath(self):
        """Test that error rendering extracts filepath from
        source chunk when not provided."""

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Create a SourceChunk with a filepath
        source_chunk_type = SourceChunk.bind_typegraph(tg)
        source_chunk = source_chunk_type.create_instance(g)

        test_filepath = "/path/to/test_file.ato"
        source_info = SourceInfo(
            text="test = new Something",
            start_line=42,
            start_col=4,
            end_line=42,
            end_col=24,
            filepath=test_filepath,
        )
        source_chunk.setup(source_info)

        # Create an exception with file_path=None
        # The rendering should extract it from source_chunk
        exc = DslRichException(
            "Test error message",
            original=DslException("Test error"),
            source_node=source_chunk,
            file_path=None,  # Explicitly None
            traceback=[],
        )

        # Render the exception
        renderables = exc._render_ast_source(source_chunk, None)

        # Check that the filepath was extracted and used in rendering
        # The header should contain the filepath
        header_text = str(renderables[0])
        assert test_filepath in header_text or "test_file.ato" in header_text

    def test_filepath_extraction_from_source_chunk(self):
        """Test that filepath can be extracted from source chunk nodes."""

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Create a SourceChunk with various filepaths
        test_cases = [
            "/absolute/path/to/file.ato",
            "relative/path/to/file.ato",
            "/path/with/subdirs/deep/file.ato",
        ]

        for test_path in test_cases:
            source_chunk_type = SourceChunk.bind_typegraph(tg)
            source_chunk = source_chunk_type.create_instance(g)

            source_info = SourceInfo(
                text="module Test: pass",
                start_line=1,
                start_col=0,
                end_line=1,
                end_col=20,
                filepath=test_path,
            )
            source_chunk.setup(source_info)

            # Extract filepath
            extracted = ASTVisitor._extract_filepath_from_source_node(source_chunk)

            assert extracted is not None
            assert str(extracted) == test_path
