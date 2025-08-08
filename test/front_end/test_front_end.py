from enum import IntEnum, StrEnum
from pathlib import Path
from textwrap import dedent
from typing import Optional, Union, cast

import pytest

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
from atopile import address, errors
from atopile.datatypes import TypeRef
from atopile.front_end import Bob, _has_ato_cmp_attrs
from atopile.parse import parse_text_as_file
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


def _get_mif(
    bob: Bob, node: L.Node, name: str, key: str | None = None
) -> L.ModuleInterface:
    return cast_assert(
        L.ModuleInterface,
        bob.resolve_field_shortcut(node, name, key),
    )


def test_empty_module_build(bob: Bob):
    text = dedent(
        """
        module A:
            pass
        """
    )
    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))
    assert isinstance(node, L.Module)
    assert isinstance(node, bob.modules[address.AddrStr(":A")])


def test_simple_module_build(bob: Bob):
    text = dedent(
        """
        module A:
            a = 1
        """
    )
    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))
    assert isinstance(node, L.Module)

    param = node.runtime["a"]
    assert isinstance(param, fab_param.ParameterOperatable)
    # TODO: check value


def test_arithmetic(bob: Bob):
    text = dedent(
        """
        module A:
            a = 1 to 2 * 3
            b = a + 4
        """
    )
    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))
    assert isinstance(node, L.Module)

    # TODO: check output
    # Requires params solver to be sane


def test_simple_new(bob: Bob):
    text = dedent(
        """
        component SomeComponent:
            signal a

        module A:
            child = new SomeComponent
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)
    child = bob.resolve_node_shortcut(node, "child")
    assert child.has_trait(_has_ato_cmp_attrs)

    a = bob.resolve_node_shortcut(child, "a")
    assert isinstance(a, F.Electrical)


def test_multiple_new(bob: Bob):
    text = dedent(
        """
        import Resistor

        module A:
            resistors = new Resistor[5]
            resistors[0].package = "R0402"
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)
    resistors = bob.resolve_field_shortcut(node, "resistors")
    assert isinstance(resistors, list)
    assert len(set(resistors)) == 5
    for c in resistors:
        assert isinstance(c, F.Resistor)

    solver = DefaultSolver()
    assert (
        resistors[0].get_trait(F.has_package_requirements).get_sizes(solver)
        == SMDSize.I0402
    )

    assert bob.resolve_node_shortcut(
        node, "resistors", -1
    ) is bob.resolve_node_shortcut(node, "resistors", 4)

    with pytest.raises(AttributeError):
        bob.resolve_node_shortcut(node, "resistors", 5)


def test_invalid_multiple_new_count(bob: Bob):
    with pytest.raises(errors.UserSyntaxError):
        bob.build_ast(
            parse_text_as_file(
                dedent(
                    """
                    module A:
                        resistors = new Resistor[-1]
                    """
                )
            ),
            TypeRef(["A"]),
        )

    with pytest.raises(errors.UserValueError):
        bob.build_ast(
            parse_text_as_file(
                dedent(
                    """
                    module A:
                        resistors = new Resistor[1.0]
                    """
                )
            ),
            TypeRef(["A"]),
        )

    with pytest.raises(errors.UserValueError):
        bob.build_ast(
            parse_text_as_file(
                dedent(
                    """
                    module A:
                        resistors = new Resistor[0x10]
                    """
                )
            ),
            TypeRef(["A"]),
        )


def test_nested_nodes(bob: Bob):
    text = dedent(
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
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)


def test_resistor(bob: Bob, repo_root: Path):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        """
        from "generics/resistors.ato" import Resistor

        component ResistorB from Resistor:
            footprint = "R0805"

        module A:
            r1 = new ResistorB
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    r1 = bob.resolve_node_shortcut(node, "r1")
    assert r1.get_trait(F.has_package_requirements)._size == SMDSize.I0805


def test_standard_library_import(bob: Bob):
    text = dedent(
        """
        import Resistor
        from "interfaces.ato" import PowerAC

        module A:
            r1 = new Resistor
            power_in = new PowerAC
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    r1 = bob.resolve_node_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)

    assert bob.resolve_node_shortcut(node, "power_in")


@pytest.mark.parametrize(
    "import_stmt,class_name,pkg_str,pkg",
    [
        (
            "import Resistor",
            "Resistor",
            "R0402",
            SMDSize.I0402,
        ),
        (
            "from 'generics/resistors.ato' import Resistor",
            "Resistor",
            "0402",
            SMDSize.I0402,
        ),
        (
            "from 'generics/capacitors.ato' import Capacitor",
            "Capacitor",
            "0402",
            SMDSize.I0402,
        ),
    ],
)
def test_reserved_attrs(
    bob: Bob,
    import_stmt: str,
    class_name: str,
    pkg_str: str,
    pkg: SMDSize,
    repo_root: Path,
):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        f"""
        {import_stmt}

        module A:
            a = new {class_name}
            a.package = "{pkg_str}"
            a.mpn = "1234567890"
            a.manufacturer = "Some Manufacturer"
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    a = bob.resolve_node_shortcut(node, "a")
    assert a.get_trait(F.has_package_requirements)._size == pkg
    assert a.get_trait(F.has_explicit_part).mfr == "Some Manufacturer"
    assert a.get_trait(F.has_explicit_part).partno == "1234567890"


def test_import_ato(bob: Bob, tmp_path):
    tmp_path = Path(tmp_path)
    some_module_search_path = tmp_path / "path"
    some_module_path = some_module_search_path / "to" / "some_module.ato"
    some_module_path.parent.mkdir(parents=True)

    some_module_path.write_text(
        dedent(
            """
        import Resistor

        module SpecialResistor from Resistor:
            footprint = "R0805"
        """
        ),
        encoding="utf-8",
    )

    top_module_content = dedent(
        """
        from "to/some_module.ato" import SpecialResistor

        module A:
            r1 = new SpecialResistor
        """
    )

    bob.search_paths.append(some_module_search_path)

    tree = parse_text_as_file(top_module_content)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    r1 = bob.resolve_node_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)


@pytest.mark.parametrize(
    "module,count", [("A", 1), ("B", 3), ("C", 5), ("D", 6), ("E", 6)]
)
def test_traceback(bob: Bob, module: str, count: int):
    text = dedent(
        """
        module A:
            doesnt_exit ~ notta_connectable

        module B:
            a = new A

        module C:
            b = new B

        module D from C:
            pass

        module E from D:
            pass
        """
    )

    tree = parse_text_as_file(text)

    with pytest.raises(errors.UserKeyError) as e:
        bob.build_ast(tree, TypeRef([module]))

    assert e.value.traceback is not None
    assert len(e.value.traceback) == count


# TODO: test connect
# - signal ~ signal
# - higher-level mif
# - duck-typed
def test_signal_connect(bob: Bob):
    text = dedent(
        """
        module App:
            signal a
            signal b
            signal c
            a ~ b
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    b = _get_mif(bob, node, "b")
    c = _get_mif(bob, node, "c")

    assert a.is_connected_to(b)
    assert not a.is_connected_to(c)


def test_interface_connect(bob: Bob):
    text = dedent(
        """
        interface SomeInterface:
            signal one
            signal two

        module App:
            a = new SomeInterface
            b = new SomeInterface
            c = new SomeInterface
            a ~ b
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    b = _get_mif(bob, node, "b")
    c = _get_mif(bob, node, "c")

    assert a.is_connected_to(b)
    assert not a.is_connected_to(c)

    a_one = _get_mif(bob, a, "one")
    b_one = _get_mif(bob, b, "one")
    c_one = _get_mif(bob, c, "one")
    a_two = _get_mif(bob, a, "two")
    b_two = _get_mif(bob, b, "two")
    c_two = _get_mif(bob, c, "two")

    assert a_one.is_connected_to(b_one)
    assert a_two.is_connected_to(b_two)
    assert not any(
        a_one.is_connected_to(other) for other in [a_two, b_two, c_one, c_two]
    )
    assert not any(
        a_two.is_connected_to(other) for other in [a_one, b_one, c_one, c_two]
    )


def test_duck_type_connect(bob: Bob):
    text = dedent(
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
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    b = _get_mif(bob, node, "b")

    a_one = _get_mif(bob, a, "one")
    b_one = _get_mif(bob, b, "one")
    a_two = _get_mif(bob, a, "two")
    b_two = _get_mif(bob, b, "two")

    assert a_one.is_connected_to(b_one)
    assert a_two.is_connected_to(b_two)
    assert not any(a_one.is_connected_to(other) for other in [a_two, b_two])
    assert not any(a_two.is_connected_to(other) for other in [a_one, b_one])


def test_directed_connect_signals(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BRIDGE_CONNECT")

        module App:
            signal a
            signal b

            a ~> b
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    b = _get_mif(bob, node, "b")

    assert a.is_connected_to(b)


def test_directed_connect_power_via_led(bob: Bob):
    text = dedent(
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
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    power = cast_assert(F.ElectricPower, bob.resolve_node_shortcut(node, "power"))
    current_limiting_resistor = cast_assert(
        F.Resistor, bob.resolve_node_shortcut(node, "current_limiting_resistor")
    )
    led = cast_assert(F.LED, bob.resolve_node_shortcut(node, "led"))

    assert power.hv.is_connected_to(current_limiting_resistor.unnamed[0])
    assert current_limiting_resistor.unnamed[1].is_connected_to(led.anode)
    assert led.cathode.is_connected_to(power.lv)


def test_directed_connect_signal_to_resistor(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BRIDGE_CONNECT")

        import Resistor

        module App:
            signal a

            r = new Resistor
            a ~> r
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    r = cast_assert(F.Resistor, bob.resolve_node_shortcut(node, "r"))

    assert a.is_connected_to(r.unnamed[0])


def test_directed_connect_non_bridge(bob: Bob):
    text = dedent(
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
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTypeError, match="not bridgeable"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_directed_connect_mif_as_bridge(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BRIDGE_CONNECT")

        module App:
            signal a
            signal b
            signal c

            a ~> b ~> c
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTypeError, match="not a `Module`"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_shim_power(bob: Bob):
    from atopile.attributes import Power

    a = Power()
    b = F.ElectricPower()

    bob._connect(a, b, None)

    assert a.lv.is_connected_to(b.lv)
    assert a.hv.is_connected_to(b.hv)
    assert not a.lv.is_connected_to(b.hv)


def test_requires(bob: Bob):
    text = dedent(
        """
        module App:
            signal a
            signal b

            a.required = True
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    assert a.has_trait(F.requires_external_usage)


def test_key(bob: Bob):
    text = dedent(
        """
        import Resistor
        module App:
            r = new Resistor
            signal a ~ r.unnamed[0]
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    r = bob.resolve_node_shortcut(node, "r")
    assert isinstance(r, F.Resistor)


def test_pin_ref(bob: Bob):
    text = dedent(
        """
        module Abc:
            pin 1 ~ signal b

        module App:
            abc = new Abc
            signal a ~ abc.1
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)


def test_non_ex_pin_ref(bob: Bob):
    text = dedent(
        """
        import Resistor
        module App:
            r = new Resistor
            signal a ~ r.unnamed[2]
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserKeyError):
        bob.build_ast(tree, TypeRef(["App"]))


def test_regression_pin_refs(bob: Bob):
    text = dedent(
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

            power_in.vcc ~ pin 1
            power_in.gnd ~ pin 2
            power_out.vcc ~ pin 6
            power_out.gnd ~ pin 4
    """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)


def test_pragma_feature_existing(bob: Bob):
    from atopile.front_end import _FeatureFlags

    # add test enum to Feature enum class
    class TestFeatures(StrEnum):
        BLA = "BLA"

    _BACKUP = _FeatureFlags.Feature
    _FeatureFlags.Feature = TestFeatures  # type: ignore

    text = dedent(
        """
        #pragma experiment("BLA")

        module App:
            pass
        """
    )

    tree = parse_text_as_file(text)
    bob.build_ast(tree, TypeRef(["App"]))

    _FeatureFlags.Feature = _BACKUP  # type: ignore


def test_pragma_feature_nonexisting(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BLAB")

        module App:
            pass
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserFeatureNotAvailableError, match="Unknown experiment"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_pragma_feature_multiple_args(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BLAB", 5)

        module App:
            pass
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserSyntaxError, match="takes exactly one argument"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_for_loop_basic(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors:
                r.unnamed[0] ~ r.unnamed[1]
                assert r.resistance is 100 kohm +/- 10%
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    resistors = bob.resolve_field_shortcut(node, "resistors")
    assert isinstance(resistors, list)
    for r in resistors:
        assert isinstance(r, F.Resistor)
        assert r.unnamed[0].is_connected_to(r.unnamed[1])
        assert r.resistance.try_get_literal() == L.Range.from_center_rel(
            100 * P.kohm, 0.1
        )


def test_for_loop_no_pragma(bob: Bob):
    text = dedent(
        """
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors:
                r.unnamed[0] ~ r.unnamed[1]
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(
        errors.UserFeatureNotEnabledError, match="Experimental feature not enabled"
    ):
        bob.build_ast(tree, TypeRef(["App"]))


def test_for_loop_nested_error(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            resistors2 = new Resistor[5]
            for r in resistors:
                for r2 in resistors2:
                    r.unnamed[0] ~ r2.unnamed[0]
        """
    )

    tree = parse_text_as_file(text)

    # nested for loops are not allowed
    with pytest.raises(errors.UserException, match="Nested"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_for_loop_variable_conflict(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r = new Resistor  # Existing attribute
            resistors = new Resistor[3]
            for r in resistors:  # Conflict!
                pass
        """
    )

    tree = parse_text_as_file(text)

    with pytest.raises(errors.UserKeyError, match="conflicts with an existing"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_for_loop_iterate_non_list(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r_single = new Resistor
            for r in r_single: # Cannot iterate over a single component
                pass
        """
    )

    tree = parse_text_as_file(text)

    with pytest.raises(errors.UserTypeError, match="Cannot iterate over type"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_for_loop_empty_list(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor
        import Electrical

        module App:
            resistors = new Resistor[0] # Empty list
            test_pins = new Electrical[2]
            for r in resistors:
                # This should never be reached
                test_pins[0] ~ test_pins[1]
        """
    )

    tree = parse_text_as_file(text)
    # Should build without errors and the assert False should not trigger
    app = bob.build_ast(tree, TypeRef(["App"]))

    # Check that the test_pins are not connected
    test_pins = bob.resolve_field_shortcut(app, "test_pins")
    assert isinstance(test_pins, list)
    for pin in test_pins:
        assert isinstance(pin, F.Electrical)
    test_pins = cast(list[F.Electrical], test_pins)
    assert len(test_pins) == 2
    assert not test_pins[0].is_connected_to(test_pins[1])


def test_for_loop_syntax_error(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors:
            resistors[0].unnamed[0] ~ resistors[1].unnamed[0]
        """
    )

    with pytest.raises(errors.UserSyntaxError, match="missing INDENT"):
        parse_text_as_file(text)


def test_for_loop_stale_ref(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors:
                assert r.resistance is 100 kohm
            r.unnamed[0] ~ r.unnamed[1]
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserKeyError):
        bob.build_ast(tree, TypeRef(["App"]))


@pytest.mark.xfail(reason="This is a bug in the parser")
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
def test_for_loop_illegal_statements(bob: Bob, stmt: str):
    template = dedent(
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
    with pytest.raises(errors.UserSyntaxError):
        parse_text_as_file(text)


def test_list_literal_basic(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r1 = new Resistor
            r2 = new Resistor
            r3 = new Resistor
            for r in [r1, r3]:
                assert r.resistance is 100 kohm
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)
    r2 = bob.resolve_field_shortcut(node, "r2")
    assert isinstance(r2, F.Resistor)
    r3 = bob.resolve_field_shortcut(node, "r3")
    assert isinstance(r3, F.Resistor)
    assert r1.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)
    assert r2.resistance.try_get_literal() is None
    assert r3.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)


def test_list_literal_nested(bob: Bob):
    text = dedent(
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
                assert r.resistance is 100 kohm
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    nested = bob.resolve_field_shortcut(node, "nested")
    assert isinstance(nested, L.Module)
    r1 = bob.resolve_field_shortcut(nested, "r1")
    assert isinstance(r1, F.Resistor)
    r2 = bob.resolve_field_shortcut(nested, "r2")
    assert isinstance(r2, F.Resistor)
    r3 = bob.resolve_field_shortcut(nested, "r3")
    assert isinstance(r3, F.Resistor)
    assert r1.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)
    assert r2.resistance.try_get_literal() is None
    assert r3.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)


def test_list_literal_long(bob: Bob):
    text = dedent(
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
                assert r.resistance is 100 kohm
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)
    r2 = bob.resolve_field_shortcut(node, "r2")
    assert isinstance(r2, F.Resistor)
    r3 = bob.resolve_field_shortcut(node, "r3")
    assert isinstance(r3, F.Resistor)
    assert r1.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)
    assert r2.resistance.try_get_literal() is None
    assert r3.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)


def test_list_literal_empty(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r1 = new Resistor
            for r in []:
                assert r.resistance is 100 kohm
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)
    assert r1.resistance.try_get_literal() is None


def test_list_literal_invalid(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            rs = new Resistor[2]
            for r in [rs]:
                assert r.resistance is 100 kohm
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTypeError, match="Invalid type"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_plain_trait(bob: Bob):
    class test_trait(L.Module.TraitT.decless()):
        pass

    F.test_trait = test_trait  # type: ignore

    text = dedent(
        """
        #pragma experiment("TRAITS")

        import test_trait

        module App:
            trait test_trait
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    assert node.has_trait(test_trait)


def test_unimported_trait(bob: Bob):
    class test_trait(L.Module.TraitT.decless()):
        pass

    F.test_trait = test_trait  # type: ignore

    text = dedent(
        """
        #pragma experiment("TRAITS")

        module App:
            trait test_trait
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitNotFoundError, match="No such trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_nonexistent_trait(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        module App:
            trait this_trait_does_not_exist
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitNotFoundError, match="No such trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_invalid_trait(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import Resistor

        module App:
            trait Resistor
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserInvalidTraitError, match="is not a valid trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_parameterised_trait(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import requires_pulls

        module App:
            trait requires_pulls
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitError, match="Error applying trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_nested_trait_access(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import Symbol

        module App:
            trait Symbol.has_kicad_symbol  # wrong syntax
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitNotFoundError, match="No such trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_nested_trait_namepsace_access(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import Symbol

        module App:
            trait Symbol::has_kicad_symbol  # trait should be moved to the top level
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserInvalidTraitError, match="is not a valid trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_alternate_trait_constructor_dot_access(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_explicit_part

        module App:
            trait has_explicit_part.by_mfr
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitNotFoundError, match="No such trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_alternate_trait_constructor_no_params_params_required(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_explicit_part

        module App:
            trait has_explicit_part::by_mfr
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitError, match="Error applying trait"):
        bob.build_ast(tree, TypeRef(["App"]))


# TODO: find a trait with a parameter-less alternate constructor


def test_alternate_trait_constructor_with_params(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_explicit_part

        module App:
            trait has_explicit_part::by_mfr<mfr="TI", partno="TCA9548APWR">
        """
    )

    tree = parse_text_as_file(text)

    node = bob.build_ast(tree, TypeRef(["App"]))
    trait = node.get_trait(F.has_explicit_part)
    assert trait.mfr == "TI"
    assert trait.partno == "TCA9548APWR"


def test_parameterised_trait_with_pos_args(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_net_name

        module App:
            trait has_net_name<"example">
        """
    )

    with pytest.raises(errors.UserSyntaxError):
        parse_text_as_file(text)


def test_parameterised_trait_with_params(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_net_name

        module App:
            trait has_net_name<name="example">
        """
    )

    tree = parse_text_as_file(text)

    node = bob.build_ast(tree, TypeRef(["App"]))
    trait = node.get_trait(F.has_net_name)
    assert trait.name == "example"
    assert trait.level == F.has_net_name.Level.SUGGESTED


def test_trait_alternate_constructor_precedence(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_net_name

        module App:
            trait has_net_name::expected<name="example">
        """
    )

    tree = parse_text_as_file(text)

    node = bob.build_ast(tree, TypeRef(["App"]))
    trait = node.get_trait(F.has_net_name)
    assert trait.name == "example"
    assert trait.level == F.has_net_name.Level.EXPECTED


def test_parameterised_trait_no_params(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")

        import has_net_name

        module App:
            trait has_net_name
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserTraitError, match="Error applying trait"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_slice_for_loop(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[10]
            resistors2 = new Resistor[2]
            for r in resistors[0:3]:
                assert r.resistance is 100 kohm

            for r in resistors[-3:-1]:
                assert r.resistance is 200 kohm

            for r in resistors[3:6:2]:
                assert r.resistance is 150 kohm

            for r in resistors2[:]:
                assert r.resistance is 250 kohm
    """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    resistors = bob.resolve_field_shortcut(node, "resistors")
    resistors2 = bob.resolve_field_shortcut(node, "resistors2")
    assert isinstance(resistors, list)
    resistors = cast(list[F.Resistor], resistors)
    assert isinstance(resistors2, list)
    resistors2 = cast(list[F.Resistor], resistors2)
    for r in resistors:
        assert isinstance(r, F.Resistor)

    # Check values assigned in the loops
    for r in resistors[0:3]:
        assert r.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)
    for r in resistors[-3:-1]:
        assert r.resistance.try_get_literal() == P_Set.from_value(200 * P.kohm)
    for r in resistors[3:6:2]:
        assert r.resistance.try_get_literal() == P_Set.from_value(150 * P.kohm)

    # Check that other resistors weren't assigned a value in the loop
    for r in resistors[6:-3]:
        assert r.resistance.try_get_literal() is None

    for r in resistors2[:]:
        assert r.resistance.try_get_literal() == P_Set.from_value(250 * P.kohm)


def test_slice_non_list(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            r_single = new Resistor
            for r in r_single[:]: # Attempt to slice a non-list
                pass
        """
    )

    tree = parse_text_as_file(text)
    # We expect a TypeError during iteration setup, not slicing itself
    with pytest.raises(errors.UserTypeError, match="Cannot iterate over type"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_slice_invalid_step(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors[::0]: # Slice step cannot be zero
                pass
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserValueError, match="Slice step cannot be zero"):
        bob.build_ast(tree, TypeRef(["App"]))


def test_slice_bigger_start_than_end(bob: Bob):
    text = dedent(
        """
        #pragma experiment("FOR_LOOP")
        import Resistor

        module App:
            resistors = new Resistor[5]
            for r in resistors[3:1]:
                assert r.resistance is 100 kohm
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    resistors = bob.resolve_field_shortcut(node, "resistors")
    resistors = cast(list[F.Resistor], resistors)
    for r in resistors[3:1]:
        assert r.resistance.try_get_literal() == P_Set.from_value(100 * P.kohm)

    for r in set(resistors) - set(resistors[3:1]):
        assert r.resistance.try_get_literal() is None


def test_directed_connect_reverse_signals(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BRIDGE_CONNECT")

        module App:
            signal a
            signal b

            b <~ a
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    b = _get_mif(bob, node, "b")

    assert a.is_connected_to(b)


def test_directed_connect_reverse_power_via_led(bob: Bob):
    text = dedent(
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
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    power = cast_assert(F.ElectricPower, bob.resolve_node_shortcut(node, "power"))
    current_limiting_resistor = cast_assert(
        F.Resistor, bob.resolve_node_shortcut(node, "current_limiting_resistor")
    )
    led = cast_assert(F.LED, bob.resolve_node_shortcut(node, "led"))

    assert power.hv.is_connected_to(current_limiting_resistor.unnamed[0])
    assert current_limiting_resistor.unnamed[1].is_connected_to(led.anode)
    assert led.cathode.is_connected_to(power.lv)


def test_directed_connect_reverse_resistor_to_signal(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BRIDGE_CONNECT")

        import Resistor

        module App:
            signal a

            r = new Resistor
            r <~ a
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(bob, node, "a")
    r = cast_assert(F.Resistor, bob.resolve_node_shortcut(node, "r"))

    assert a.is_connected_to(r.unnamed[0])


def test_directed_connect_mixed_directions(bob: Bob):
    text = dedent(
        """
        #pragma experiment("BRIDGE_CONNECT")

        import Resistor

        module App:
            signal a
            signal b
            resistor = new Resistor

            a <~ resistor ~> b
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(
        errors.UserSyntaxError,
        match="Only one type of connection direction per statement allowed",
    ):
        bob.build_ast(tree, TypeRef(["App"]))


def test_module_templating(bob: Bob):
    text = dedent(
        """
        #pragma experiment("MODULE_TEMPLATING")
        import Addressor

        module App:
            addressor7 = new Addressor<address_bits=7>
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    addressor7 = bob.resolve_field_shortcut(node, "addressor7")
    assert isinstance(addressor7, F.Addressor)
    assert addressor7._address_bits == 7


def test_module_templating_list(bob: Bob):
    text = dedent(
        """
        #pragma experiment("MODULE_TEMPLATING")
        import Addressor

        module App:
            addressors = new Addressor[3]<address_bits=7>
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    addressors = bob.resolve_field_shortcut(node, "addressors")
    assert isinstance(addressors, list)
    addressors = cast(list[F.Addressor], addressors)
    assert all(isinstance(addressor, F.Addressor) for addressor in addressors)
    assert all(addressor._address_bits == 7 for addressor in addressors)


# see src/atopile/parser/AtoLexer.g4
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
                {name} = 10 V +/- 5%
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
    template = dedent(template)

    # ensure template is otherwise valid
    parse_text_as_file(template.format(name="x"))

    with pytest.raises(errors.UserSyntaxError):
        parse_text_as_file(template.format(name=name))


def test_assign_to_enum_param(bob: Bob):
    text = dedent(
        """
        import Capacitor

        module App:
            cap = new Capacitor
            cap.temperature_coefficient = "X7R"
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    cap = bob.resolve_field_shortcut(node, "cap")
    assert isinstance(cap, F.Capacitor)
    assert cap.temperature_coefficient.try_get_literal_subset() == P_Set.from_value(
        F.Capacitor.TemperatureCoefficient.X7R
    )


def test_trait_template_enum(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")
        #pragma experiment("MODULE_TEMPLATING")

        import Resistor
        import has_package_requirements

        module Resistor0805 from Resistor:
            trait has_package_requirements<size="I0805">

        module App:
            r = new Resistor0805
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    r = bob.resolve_field_shortcut(node, "r")
    assert isinstance(r, F.Resistor)

    solver = DefaultSolver()
    assert r.get_trait(F.has_package_requirements).get_sizes(solver) == SMDSize.I0805


def test_trait_template_enum_invalid(bob: Bob):
    text = dedent(
        """
        #pragma experiment("TRAITS")
        #pragma experiment("MODULE_TEMPLATING")

        import Resistor
        import has_package_requirements

        module Resistor0805 from Resistor:
            trait has_package_requirements<size="<invalid size>">

        module App:
            r = new Resistor0805
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserInvalidValueError):
        bob.build_ast(tree, TypeRef(["App"]))


def test_module_template_enum(bob: Bob):
    class ResistorWithSize(F.Resistor):
        def __init__(self, size: SMDSize):
            super().__init__()
            self._size = size

        def __postinit__(self, *args, **kwargs):
            self.add(F.has_package_requirements(size=self._size))

    F.ResistorWithSize = ResistorWithSize  # type: ignore

    text = dedent(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import ResistorWithSize

        module App:
            r = new ResistorWithSize<size="I0805">
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    r = bob.resolve_field_shortcut(node, "r")
    assert isinstance(r, ResistorWithSize)

    solver = DefaultSolver()
    assert r.get_trait(F.has_package_requirements).get_sizes(solver) == SMDSize.I0805


def test_module_template_enum_invalid(bob: Bob):
    class ResistorWithSize(F.Resistor):
        def __init__(self, size: SMDSize):
            super().__init__()
            self._size = size

        def __postinit__(self, *args, **kwargs):
            self.add(F.has_package_requirements(size=self._size))

    F.ResistorWithSize = ResistorWithSize  # type: ignore

    text = dedent(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import ResistorWithSize

        module App:
            r = new ResistorWithSize<size="<invalid size>">
        """
    )

    tree = parse_text_as_file(text)
    with pytest.raises(errors.UserInvalidValueError):
        bob.build_ast(tree, TypeRef(["App"]))


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
class ModuleWithIntEnum(L.Module):
    def __init__(self, value: _IntEnumForTests):
        super().__init__()
        self._value = value


class ModuleWithStrEnum(L.Module):
    def __init__(self, mode: _StrEnumForTests):
        super().__init__()
        self._mode = mode


class ModuleWithOptionalEnum(L.Module):
    def __init__(self, color: F.LED.Color | None = None):
        super().__init__()
        self._color = color


class ModuleWithTypingOptionalEnum(L.Module):
    def __init__(self, color: Optional[F.LED.Color] = None):
        super().__init__()
        self._color = color


class ModuleWithEnumUnion(L.Module):
    def __init__(
        self,
        value: F.LED.Color | F.MOSFET.ChannelType | F.Capacitor.TemperatureCoefficient,
    ):
        super().__init__()
        self._value = value


class ModuleWithTypingUnionEnum(L.Module):
    def __init__(
        self,
        value: Union[
            F.LED.Color, F.MOSFET.ChannelType, F.Capacitor.TemperatureCoefficient
        ],
    ):
        super().__init__()
        self._value = value


class ModuleWithStrOrEnum(L.Module):
    def __init__(self, label: str | F.LED.Color):
        super().__init__()
        self._label = label


class ModuleWithTypingUnionStrOrEnum(L.Module):
    def __init__(self, label: Union[str, F.LED.Color]):
        super().__init__()
        self._label = label


class ModuleWithStrOrStrEnum(L.Module):
    def __init__(self, config: str | _StrEnumForTests):
        super().__init__()
        self._config = config


class ModuleWithEnumOrNone(L.Module):
    def __init__(self, channel: F.MOSFET.ChannelType | None = None):
        super().__init__()
        self._channel = channel


class ModuleWithTypingUnionEnumOrNone(L.Module):
    def __init__(self, channel: Union[F.MOSFET.ChannelType, None] = None):
        super().__init__()
        self._channel = channel


@pytest.mark.parametrize(
    "module_name,template_args,expected_attrs",
    [
        # Basic enum types
        ("ModuleWithIntEnum", "<value=2>", {"_value": _IntEnumForTests.VALUE_2}),
        (
            "ModuleWithStrEnum",
            '<mode="OPTION_B">',
            {"_mode": _StrEnumForTests.OPTION_B},
        ),
        # Optional enums with modern syntax
        ("ModuleWithOptionalEnum", "", {"_color": None}),
        ("ModuleWithOptionalEnum", '<color="RED">', {"_color": F.LED.Color.RED}),
        # Optional enums with typing syntax
        ("ModuleWithTypingOptionalEnum", "", {"_color": None}),
        ("ModuleWithTypingOptionalEnum", '<color="RED">', {"_color": F.LED.Color.RED}),
        # Enum | None variations
        ("ModuleWithEnumOrNone", "", {"_channel": None}),
        (
            "ModuleWithEnumOrNone",
            '<channel="P_CHANNEL">',
            {"_channel": F.MOSFET.ChannelType.P_CHANNEL},
        ),
        ("ModuleWithTypingUnionEnumOrNone", "", {"_channel": None}),
        (
            "ModuleWithTypingUnionEnumOrNone",
            '<channel="P_CHANNEL">',
            {"_channel": F.MOSFET.ChannelType.P_CHANNEL},
        ),
        # str | Enum unions
        ("ModuleWithStrOrEnum", '<label="custom_label">', {"_label": "custom_label"}),
        ("ModuleWithStrOrEnum", '<label="GREEN">', {"_label": F.LED.Color.GREEN}),
        (
            "ModuleWithTypingUnionStrOrEnum",
            '<label="custom_label">',
            {"_label": "custom_label"},
        ),
        (
            "ModuleWithTypingUnionStrOrEnum",
            '<label="GREEN">',
            {"_label": F.LED.Color.GREEN},
        ),
        # str | StrEnum unions
        (
            "ModuleWithStrOrStrEnum",
            '<config="custom_config">',
            {"_config": "custom_config"},
        ),
        (
            "ModuleWithStrOrStrEnum",
            '<config="PRESET_A">',
            {"_config": _StrEnumForTests.PRESET_A},
        ),
    ],
)
def test_module_template_enum_scenarios(
    bob: Bob, module_name, template_args, expected_attrs
):
    """Test various enum scenarios in module template constructors."""
    # Register the module classes
    F.ModuleWithIntEnum = ModuleWithIntEnum  # type: ignore
    F.ModuleWithStrEnum = ModuleWithStrEnum  # type: ignore
    F.ModuleWithOptionalEnum = ModuleWithOptionalEnum  # type: ignore
    F.ModuleWithTypingOptionalEnum = ModuleWithTypingOptionalEnum  # type: ignore
    F.ModuleWithEnumUnion = ModuleWithEnumUnion  # type: ignore
    F.ModuleWithTypingUnionEnum = ModuleWithTypingUnionEnum  # type: ignore
    F.ModuleWithStrOrEnum = ModuleWithStrOrEnum  # type: ignore
    F.ModuleWithTypingUnionStrOrEnum = ModuleWithTypingUnionStrOrEnum  # type: ignore
    F.ModuleWithStrOrStrEnum = ModuleWithStrOrStrEnum  # type: ignore
    F.ModuleWithEnumOrNone = ModuleWithEnumOrNone  # type: ignore
    F.ModuleWithTypingUnionEnumOrNone = ModuleWithTypingUnionEnumOrNone  # type: ignore
    F._StrEnumForTests = _StrEnumForTests  # type: ignore

    text = dedent(
        f"""
        #pragma experiment("MODULE_TEMPLATING")

        import {module_name}

        module App:
            mod = new {module_name}{template_args}
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    mod = bob.resolve_field_shortcut(node, "mod")
    assert isinstance(mod, eval(module_name))

    for attr, expected_value in expected_attrs.items():
        assert getattr(mod, attr) == expected_value


@pytest.mark.parametrize(
    "module_name,template_args,expected_value,enum_type",
    [
        # Multiple enum type unions - modern syntax
        ("ModuleWithEnumUnion", '<value="RED">', F.LED.Color.RED, "LED"),
        (
            "ModuleWithEnumUnion",
            '<value="N_CHANNEL">',
            F.MOSFET.ChannelType.N_CHANNEL,
            "MOSFET",
        ),
        (
            "ModuleWithEnumUnion",
            '<value="X7R">',
            F.Capacitor.TemperatureCoefficient.X7R,
            "Capacitor",
        ),
        # Multiple enum type unions - typing syntax
        ("ModuleWithTypingUnionEnum", '<value="RED">', F.LED.Color.RED, "LED"),
        (
            "ModuleWithTypingUnionEnum",
            '<value="N_CHANNEL">',
            F.MOSFET.ChannelType.N_CHANNEL,
            "MOSFET",
        ),
        (
            "ModuleWithTypingUnionEnum",
            '<value="X7R">',
            F.Capacitor.TemperatureCoefficient.X7R,
            "Capacitor",
        ),
    ],
)
def test_module_template_enum_union_types(
    bob: Bob, module_name, template_args, expected_value, enum_type
):
    """Test union of multiple enum types in module template constructors."""
    # Register the module classes
    F.ModuleWithEnumUnion = ModuleWithEnumUnion  # type: ignore
    F.ModuleWithTypingUnionEnum = ModuleWithTypingUnionEnum  # type: ignore

    text = dedent(
        f"""
        #pragma experiment("MODULE_TEMPLATING")

        import {module_name}

        module App:
            mod = new {module_name}{template_args}
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)
    mod = bob.resolve_field_shortcut(node, "mod")
    assert isinstance(mod, eval(module_name))
    assert mod._value == expected_value


def test_module_template_multiple_enum_args(bob: Bob):
    """Test multiple enum arguments in module template constructor."""

    class ModuleWithMultipleEnums(L.Module):
        def __init__(
            self,
            color: F.LED.Color,
            channel: F.MOSFET.ChannelType,
            temp_coeff: F.Capacitor.TemperatureCoefficient | None = None,
        ):
            super().__init__()
            self._color = color
            self._channel = channel
            self._temp_coeff = temp_coeff

    F.ModuleWithMultipleEnums = ModuleWithMultipleEnums  # type: ignore

    text = dedent(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import ModuleWithMultipleEnums

        module App:
            mod1 = new ModuleWithMultipleEnums<color="BLUE", channel="N_CHANNEL">
            mod2 = new ModuleWithMultipleEnums<color="RED", channel="P_CHANNEL", temp_coeff="C0G">
        """  # noqa: E501
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    mod1 = bob.resolve_field_shortcut(node, "mod1")
    assert isinstance(mod1, ModuleWithMultipleEnums)
    assert mod1._color == F.LED.Color.BLUE
    assert mod1._channel == F.MOSFET.ChannelType.N_CHANNEL
    assert mod1._temp_coeff is None

    mod2 = bob.resolve_field_shortcut(node, "mod2")
    assert isinstance(mod2, ModuleWithMultipleEnums)
    assert mod2._color == F.LED.Color.RED
    assert mod2._channel == F.MOSFET.ChannelType.P_CHANNEL
    assert mod2._temp_coeff == F.Capacitor.TemperatureCoefficient.C0G


def test_module_template_mixed_syntax_compatibility(bob: Bob):
    """Test that both Optional and | None syntax work in the same context."""

    class ModuleWithModernOptional(L.Module):
        def __init__(self, color: F.LED.Color | None = None):
            super().__init__()
            self._color = color

    class ModuleWithTypingOptional(L.Module):
        def __init__(self, color: Optional[F.LED.Color] = None):
            super().__init__()
            self._color = color

    F.ModuleWithModernOptional = ModuleWithModernOptional  # type: ignore
    F.ModuleWithTypingOptional = ModuleWithTypingOptional  # type: ignore

    text = dedent(
        """
        #pragma experiment("MODULE_TEMPLATING")

        import ModuleWithModernOptional
        import ModuleWithTypingOptional

        module App:
            mod1 = new ModuleWithModernOptional<color="BLUE">
            mod2 = new ModuleWithTypingOptional<color="BLUE">
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    mod1 = bob.resolve_field_shortcut(node, "mod1")
    assert isinstance(mod1, ModuleWithModernOptional)
    assert mod1._color == F.LED.Color.BLUE

    mod2 = bob.resolve_field_shortcut(node, "mod2")
    assert isinstance(mod2, ModuleWithTypingOptional)
    assert mod2._color == F.LED.Color.BLUE
