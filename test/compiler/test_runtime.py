import textwrap
from enum import IntEnum, StrEnum
from pathlib import Path
from types import SimpleNamespace

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.ast_visitor import (
    ASTVisitor,
    DslException,
    is_ato_component,
    is_ato_interface,
    is_ato_module,
)
from atopile.compiler.build import Linker, StdlibRegistry, build_file
from faebryk.core.faebrykpy import EdgeComposition, EdgeType
from faebryk.core.graph import BoundNode, GraphView
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import cast_assert, not_none
from test.compiler.conftest import build_instance

E = BoundExpressions()

NULL_CONFIG = SimpleNamespace(project=None)


# FIXME: compiler should expose a SyntaxError exception
class SyntaxError(Exception):
    pass


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


def test_duck_type_connect():
    """Test that duck-typed interfaces are connected."""
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

    assert _check_connected(a_one, b_one)
    assert _check_connected(a_two, b_two)
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


def test_for_loop_basic():
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

    resistors = _get_child(app_instance, "resistors")
    assert isinstance(resistors, list)
    for r_node in resistors:
        r = F.Resistor.bind_instance(cast_assert(BoundNode, r_node))
        assert _check_connected(r.unnamed[0].get(), r.unnamed[1].get())
        # TODO: check resistance is 100kohm +/- 10%


def test_for_loop_empty_list():
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
    test_pins = _get_child(app_instance, "test_pins")
    assert isinstance(test_pins, list)
    assert len(test_pins) == 2
    assert not _check_connected(test_pins[0], test_pins[1])


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
    assert (
        F.Capacitor.bind_instance(cap)
        .temperature_coefficient.get()
        .try_extract_constrained_literal()
        == F.Capacitor.TemperatureCoefficient.X7R
    )


def test_assert_is():
    """Test assert is constraints."""
    _, _, _, _, app_instance = build_instance(
        """
            module App:
                a: voltage
                b: dimensionless
                c: dimensionless
                d: dimensionless
                e: dimensionless
                f: dimensionless

                assert a is 2mV +/- 10%
                assert b is c
                assert d is e is f
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
    assert a.get_units().compact_repr() == "mV"
    assert (
        E.lit_op_range_from_center_rel((2, E.U.mV), rel=0.1)
        .as_literal.get()
        .equals(not_none(a.try_extract_aliased_literal()))
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
        .as_literal.get()
        .equals(not_none(a.try_extract_aliased_literal()))
    )

    b = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "b"))
    assert (
        E.lit_op_single((1, E.U.V))
        .as_literal.get()
        .equals(not_none(b.try_extract_aliased_literal()))
    )

    c = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "c"))
    assert (
        E.lit_op_single((5, E.U.V))
        .as_literal.get()
        .equals(not_none(c.try_extract_aliased_literal()))
    )

    d = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "d"))
    assert (
        E.lit_op_ranges(((5, E.U.V), (8, E.U.V)))
        .as_literal.get()
        .equals(not_none(d.try_extract_aliased_literal()))
    )

    e = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "e"))
    assert (
        E.lit_op_range_from_center_rel((100, E.U.mV), rel=0.1)
        .as_literal.get()
        .equals(not_none(e.try_extract_aliased_literal()))
    )

    f = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "f"))
    assert (
        E.lit_op_range_from_center_rel((3.3, E.U.V), rel=0.05)
        .as_literal.get()
        .equals(not_none(f.try_extract_aliased_literal()))
    )


def test_basic_arithmetic():
    _, _, _, result, app_instance = build_instance(
        """
        module A:
            a = 1 to 2 * 3
            b = a + 4
        """,
        "A",
    )
    assert "A" in result.state.type_roots
    a = _get_child(app_instance, "a")
    b = _get_child(app_instance, "b")

    a = F.Parameters.NumericParameter.bind_instance(a)
    b = F.Parameters.NumericParameter.bind_instance(b)

    assert (
        E.lit_op_range((1, 6))
        .as_literal.get()
        .equals(not_none(a.try_extract_aliased_literal()))
    )
    assert (
        E.lit_op_range((5, 10))
        .as_literal.get()
        .equals(not_none(b.try_extract_aliased_literal()))
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
    assert not app.has_trait(fabll.is_module)  # TODO: is this correct?
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
        .as_literal.get()
        .equals(not_none(a.try_extract_aliased_literal()))
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

    assert _get_type_name(child) == "SomeComponent"
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
    resistors = _get_child(app_instance, "resistors")
    assert isinstance(resistors, list)
    assert len(resistors) == 5
    for i, r_node in enumerate(resistors):
        assert isinstance(r_node, BoundNode)
        r = fabll.Node.bind_instance(r_node)
        assert r.isinstance(F.Resistor)

        if i == 0:
            assert (
                r.get_trait(F.has_package_requirements)
                .size_.get()
                .force_extract_literal()
                .get_single_value_typed(SMDSize)
                == SMDSize.I0402
            )
        else:
            assert not r.has_trait(F.has_package_requirements)


def test_invalid_multiple_new_count_negative():
    with pytest.raises(DslException):
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
    with pytest.raises(DslException):
        build_instance(
            """
            module Inner:
                pass

            module A:
                resistors = new Inner[0x10]
            """,
            "A",
        )


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
        .size_.get()
        .force_extract_literal()
        == pkg
    )
    assert fabll.Node.bind_instance(a).get_trait(F.has_explicit_part).mfr == mfr
    assert fabll.Node.bind_instance(a).get_trait(F.has_explicit_part).partno == mpn


def test_import_ato(tmp_path: Path):
    some_module_path = tmp_path / "to" / "some_module.ato"
    some_module_path.parent.mkdir(parents=True)

    some_module_path.write_text(
        textwrap.dedent(
            """
            import Resistor

            module SpecialResistor from Resistor:
                footprint = "R0805"
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
    assert fabll.Node.bind_instance(r1_node).isinstance(F.Resistor)
    assert (
        fabll.Node.bind_instance(r1_node)
        .get_trait(F.has_package_requirements)
        .size_.get()
        .force_extract_literal()
        == SMDSize.I0805
    )


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


def test_directed_connect_mif_as_bridge():
    with pytest.raises(DslException, match="not a `Module`"):
        build_instance(
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


def test_shim_power():
    # FIXME: either delete and break compatiblity or re-implement shim
    assert False
    # from atopile.attributes import Power

    # a = Power()
    # b = F.ElectricPower()

    # bob._connect(a, b, None)

    # assert a.lv.is_connected_to(b.lv)
    # assert a.hv.is_connected_to(b.hv)
    # assert not a.lv.is_connected_to(b.hv)


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
    # TODO: test something here


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
    with pytest.raises(DslException, match="[Uu]nknown experiment"):
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


def test_for_loop_no_pragma():
    with pytest.raises(DslException, match="Experimental feature not enabled"):
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


def test_for_loop_nested_error():
    with pytest.raises(DslException, match="[Nn]ested"):
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


def test_for_loop_variable_conflict():
    with pytest.raises(DslException, match="conflicts with an existing"):
        build_instance(
            """
            #pragma experiment("FOR_LOOP")
            module App:
                r = new Resistor
                resistors = new Resistor[3]
                for r in resistors:
                    pass
            """,
            "App",
        )


def test_for_loop_iterate_non_list():
    with pytest.raises(DslException, match="Cannot iterate over type"):
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


def test_for_loop_syntax_error():
    from atopile.compiler.parse import parse_text_as_file

    with pytest.raises(DslException, match="missing INDENT"):
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


def test_for_loop_stale_ref():
    with pytest.raises(DslException):
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
        "r = new Resistor",
    ],
)
def test_for_loop_illegal_statements(stmt: str):
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
    with pytest.raises(DslException, match="Invalid statement"):
        build_instance(text, "App")


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
                assert r.resistance is 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    r1_node = _get_child(app_instance, "r1")
    assert fabll.Node.bind_instance(r1_node).isinstance(F.Resistor)
    r1 = F.Resistor.bind_instance(r1_node)
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.get()
        .equals(not_none(r1.resistance.get().try_extract_aliased_literal()))
    )

    r2_node = _get_child(app_instance, "r2")
    assert fabll.Node.bind_instance(r2_node).isinstance(F.Resistor)
    r2 = F.Resistor.bind_instance(r2_node)
    assert r2.resistance.get().try_extract_aliased_literal() is None

    r3_node = _get_child(app_instance, "r3")
    assert fabll.Node.bind_instance(r3_node).isinstance(F.Resistor)
    r3 = F.Resistor.bind_instance(r3_node)
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.get()
        .equals(not_none(r3.resistance.get().try_extract_aliased_literal()))
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
                assert r.resistance is 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    nested_node = _get_child(app_instance, "nested")

    r1 = F.Resistor.bind_instance(_get_child(nested_node, "r1"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.get()
        .equals(not_none(r1.resistance.get().try_extract_aliased_literal()))
    )

    r2 = F.Resistor.bind_instance(_get_child(nested_node, "r2"))
    assert r2.resistance.get().try_extract_aliased_literal() is None

    r3 = F.Resistor.bind_instance(_get_child(nested_node, "r3"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.get()
        .equals(not_none(r3.resistance.get().try_extract_aliased_literal()))
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
                assert r.resistance is 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    r1 = F.Resistor.bind_instance(_get_child(app_instance, "r1"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.get()
        .equals(not_none(r1.resistance.get().try_extract_aliased_literal()))
    )
    r2 = F.Resistor.bind_instance(_get_child(app_instance, "r2"))
    assert r2.resistance.get().try_extract_aliased_literal() is None
    r3 = F.Resistor.bind_instance(_get_child(app_instance, "r3"))
    assert (
        E.lit_op_single((100, E.U.kohm))
        .as_literal.get()
        .equals(not_none(r3.resistance.get().try_extract_aliased_literal()))
    )


def test_list_literal_empty():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r1 = new Resistor
            for r in []:
                assert r.resistance is 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    r1 = F.Resistor.bind_instance(_get_child(app_instance, "r1"))
    assert r1.resistance.get().try_extract_aliased_literal() is None


def test_list_literal_invalid():
    with pytest.raises(DslException, match="[Ii]nvalid type"):
        _, _, _, result, app_instance = build_instance(
            """
            #pragma experiment("FOR_LOOP")
            import Resistor

            module App:
                rs = new Resistor[2]
                for r in [rs]:
                    assert r.resistance is 100kohm
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
    class test_trait(fabll.Node):
        is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    with pytest.raises(DslException, match="[Nn]o such trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            module App:
                trait test_trait
            """,
            "App",
            stdlib_extra=[test_trait],
        )


def test_nonexistent_trait():
    with pytest.raises(DslException, match="[Nn]o such trait"):
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


def test_parameterised_trait():
    with pytest.raises(DslException, match="[Ee]rror applying trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import requires_pulls

            module App:
                trait requires_pulls
            """,
            "App",
        )


def test_nested_trait_access():
    with pytest.raises(DslException, match="[Nn]o such trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import Symbol

            module App:
                trait Symbol.has_kicad_symbol  # wrong syntax
            """,
            "App",
        )


def test_nested_trait_namespace_access():
    with pytest.raises(DslException, match="not a valid trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import Symbol

            module App:
                trait Symbol::has_kicad_symbol # trait should be moved to the top level
            """,
            "App",
        )


def test_alternate_trait_constructor_dot_access():
    with pytest.raises(DslException, match="[Nn]o such trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import has_explicit_part

            module App:
                trait has_explicit_part.by_mfr
            """,
            "App",
        )


def test_alternate_trait_constructor_no_params_params_required():
    with pytest.raises(DslException, match="[Ee]rror applying trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import has_explicit_part

            module App:
                trait has_explicit_part::by_mfr
            """,
            "App",
        )


# TODO: find a trait with a parameter-less alternate constructor


def test_alternate_trait_constructor_with_params():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_explicit_part

        module App:
            trait has_explicit_part::by_mfr<mfr="TI", partno="TCA9548APWR">
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    trait = fabll.Node.bind_instance(app_instance).get_trait(F.has_explicit_part)
    assert trait.mfr == "TI"
    assert trait.partno == "TCA9548APWR"


def test_parameterised_trait_with_pos_args():
    with pytest.raises(SyntaxError):
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
    assert False  # FIXME: find / make a trait to test this with
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")

        import has_net_name

        module App:
            trait has_net_name::expected<name="example">
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    # TODO: check trait.name == "example"
    # TODO: check trait.level == F.has_net_name.Level.EXPECTED


def test_parameterised_trait_no_params():
    with pytest.raises(DslException, match="[Ee]rror applying trait"):
        build_instance(
            """
            #pragma experiment("TRAITS")

            import has_net_name_suggestion

            module App:
                trait has_net_name_suggestion
            """,
            "App",
        )


def test_slice_for_loop():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("FOR LOOP")
        import Resistor

        module App:
            resistors = new Resistor[10]
            resistors2 = new Resistor[2]
            for r in resistors[0:3]:
                assert r.resistance is 100kohm

            for r in resistors[-3:-1]:
                assert r.resistance is 200kohm

            for r in resistors[3:6:2]:
                assert r.resistance is 150kohm

            for r in resistors2[:]:
                assert r.resistance is 250kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    resistors = _get_child(app_instance, "resistors")
    assert isinstance(resistors, list)
    resistors2 = _get_child(app_instance, "resistors2")
    assert isinstance(resistors2, list)

    for r_node in resistors[0:3]:
        r = F.Resistor.bind_instance(r_node)
        assert (
            E.lit_op_single((100, E.U.kohm))
            .as_literal.get()
            .equals(r.resistance.get().force_extract_literal())
        )

    for r_node in resistors[-3:-1]:
        r = F.Resistor.bind_instance(r_node)
        assert (
            E.lit_op_single((200, E.U.kohm))
            .as_literal.get()
            .equals(r.resistance.get().force_extract_literal())
        )

    for r_node in resistors[3:6:2]:
        r = F.Resistor.bind_instance(r_node)
        assert (
            E.lit_op_single((150, E.U.kohm))
            .as_literal.get()
            .equals(r.resistance.get().force_extract_literal())
        )

    # Check that other resistors weren't assigned a value in the loop
    for r_node in resistors[6:-3]:
        r = F.Resistor.bind_instance(r_node)
        assert r.resistance.get().try_extract_aliased_literal() is None

    for r_node in resistors2[:]:
        r = F.Resistor.bind_instance(r_node)
        assert (
            E.lit_op_single((250, E.U.kohm))
            .as_literal.get()
            .equals(r.resistance.get().force_extract_literal())
        )


def test_slice_non_list():
    with pytest.raises(DslException, match="[Cc]annot iterate over type"):
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
                assert r.resistance is 100kohm
        """,
        "App",
    )
    assert "App" in result.state.type_roots

    resistors = _get_child(app_instance, "resistors")
    assert isinstance(resistors, list)
    for r_node in resistors[3:1]:
        r = F.Resistor.bind_instance(r_node)
        assert (
            E.lit_op_single((100, E.U.kohm))
            .as_literal.get()
            .equals(r.resistance.get().force_extract_literal())
        )

    for r_node in set(resistors) - set(resistors[3:1]):
        r = F.Resistor.bind_instance(r_node)
        assert r.resistance.get().try_extract_aliased_literal() is None


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
    assert not _check_connected(
        _get_child(app_instance, "b"), _get_child(app_instance, "a")
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
    assert _check_connected(power.lv.get(), led.diode.get().anode.get())
    assert _check_connected(
        led.diode.get().cathode.get(), current_limiting_resistor.unnamed[0].get()
    )
    assert _check_connected(current_limiting_resistor.unnamed[1].get(), power.hv.get())


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
        SyntaxError, match="Only one type of connection direction per statement allowed"
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
    addressor7 = F.Addressor.bind_instance(addressor7)
    assert addressor7.address_bits_.get().force_extract_literal().get_single() == 7


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
    addressors = _get_child(app_instance, "addressors")
    assert isinstance(addressors, list)
    addressors = [
        F.Addressor.bind_instance(cast_assert(BoundNode, addressor))
        for addressor in addressors
    ]
    assert all(isinstance(addressor, F.Addressor) for addressor in addressors)
    assert all(
        addressor.address_bits_.get().force_extract_literal().get_single() == 7
        for addressor in addressors
    )


# see src/atopile/compiler/parser/AtoLexer.g4
@pytest.mark.parametrize(
    "name,template",
    [
        (name, template)
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
                {name} = 10V +/- 5%
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
    build_instance(template.format(name="x"), "App")

    with pytest.raises(SyntaxError):
        build_instance(template.format(name=name), "App")


def test_trait_template_enum():
    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("TRAITS")
        #pragma experiment("MODULE_TEMPLATING")

        import Resistor
        import has_package_requirements

        module Resistor0805 from Resistor:
            trait has_package_requirements<size="I0805">

        module App:
            r = new Resistor0805
        """,
        "App",
    )
    assert "App" in result.state.type_roots
    r = _get_child(app_instance, "r")
    r = F.Resistor.bind_instance(r)
    assert (
        r.get_trait(F.has_package_requirements)
        .size_.get()
        .force_extract_literal()
        .get_single()
        == SMDSize.I0805
    )


def test_trait_template_enum_invalid():
    with pytest.raises(DslException):
        build_instance(
            """
            #pragma experiment("TRAITS")
            #pragma experiment("MODULE_TEMPLATING")

            import Resistor
            import has_package_requirements

            module Resistor0805 from Resistor:
                trait has_package_requirements<size="<invalid size>">

            module App:
                r = new Resistor0805
            """,
            "App",
        )


def test_module_template_enum():
    class Module(fabll.Node):
        size_ = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import Module

        module App:
            r = new Module<size="I0805">
        """,
        "App",
        stdlib_extra=[Module],
    )

    assert "App" in result.state.type_roots
    r = _get_child(app_instance, "r")
    r = Module.bind_instance(r)
    assert r.size_.get().force_extract_literal().get_single() == SMDSize.I0805


def test_module_template_enum_invalid():
    class Module(fabll.Node):
        size_ = F.Parameters.EnumParameter.MakeChild(enum_t=SMDSize)

    with pytest.raises(DslException, match="Invalid size: '<invalid size>'"):
        build_instance(
            """
            #pragma experiment("MODULE_TEMPLATING")

            import Module

            module App:
                r = new Module<size="<invalid size>">
            """,
            "App",
            stdlib_extra=[Module],
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


class ModuleWithStrEnum(fabll.Node):
    _value = F.Parameters.EnumParameter.MakeChild(enum_t=_StrEnumForTests)


@pytest.mark.parametrize(
    "module_name,template_args,expected_value",
    [
        # Basic enum types
        ("ModuleWithIntEnum", "<value=2>", _IntEnumForTests.VALUE_2),
        ("ModuleWithStrEnum", '<mode="OPTION_B">', _StrEnumForTests.OPTION_B),
    ],
)
def test_module_template_enum_scenarios(module_name, template_args, expected_value):
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
    mod = ModuleWithIntEnum.bind_instance(mod)
    assert mod._value.get().force_extract_literal().get_single() == expected_value


def test_module_template_multiple_enum_args():
    class Module(fabll.Node):
        _color = F.Parameters.EnumParameter.MakeChild(enum_t=F.LED.Color)
        _channel = F.Parameters.EnumParameter.MakeChild(enum_t=F.MOSFET.ChannelType)
        _temp_coeff = F.Parameters.EnumParameter.MakeChild(
            enum_t=F.Capacitor.TemperatureCoefficient
        )

    _, _, _, result, app_instance = build_instance(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import Module

        module App:
            mod1 = new Module<color="BLUE", channel="N_CHANNEL">
            mod2 = new Module<color="RED", channel="P_CHANNEL", temp_coeff="C0G">
        """,
        "App",
        stdlib_extra=[Module],
    )
    assert "App" in result.state.type_roots
    mod1 = _get_child(app_instance, "mod1")
    mod1 = Module.bind_instance(mod1)
    assert mod1._color.get().force_extract_literal().get_single() == F.LED.Color.BLUE
    assert (
        mod1._channel.get().force_extract_literal().get_single()
        == F.MOSFET.ChannelType.N_CHANNEL
    )
    assert mod1._temp_coeff.get().force_extract_literal().get_single() is None
    mod2 = _get_child(app_instance, "mod2")
    mod2 = Module.bind_instance(mod2)
    assert mod2._color.get().force_extract_literal().get_single() == F.LED.Color.RED
    assert (
        mod2._channel.get().force_extract_literal().get_single()
        == F.MOSFET.ChannelType.P_CHANNEL
    )
    assert (
        mod2._temp_coeff.get().force_extract_literal().get_single()
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
        ("3.3V +/- 50mV", E.lit_op_range_from_center_rel((3.3, E.U.V), rel=0.05)),
        ("3300 +/- 50mV", E.lit_op_range_from_center_rel((3300, E.U.mV), rel=0.05)),
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
    a = F.Parameters.NumericParameter.bind_instance(_get_child(app_instance, "a"))
    assert literal.as_literal.get().equals(not_none(a.try_extract_aliased_literal()))
