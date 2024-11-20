from textwrap import dedent

import pytest

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
from atopile import errors
from atopile.datatypes import Ref
from atopile.front_end2 import AtoComponent, Lofty, _write_only_property
from atopile.parse import parse_text_as_file
from faebryk.libs.library import L


@pytest.fixture
def lofty() -> Lofty:
    return Lofty()


def test_empty_module_build(lofty: Lofty):
    text = dedent(
        """
        module A:
            pass
        """
    )
    tree = parse_text_as_file(text)
    node = lofty.build_ast(tree, Ref(["A"]))
    assert isinstance(node, L.Module)


def test_simple_module_build(lofty: Lofty):
    text = dedent(
        """
        module A:
            a = 1
        """
    )
    tree = parse_text_as_file(text)
    node = lofty.build_ast(tree, Ref(["A"]))
    assert isinstance(node, L.Module)

    param = node.runtime["a"]
    assert isinstance(param, fab_param.ParameterOperatable)
    # TODO: check value


def test_arithmetic(lofty: Lofty):
    text = dedent(
        """
        module A:
            a = 1 to 2 * 3
            b = a + 4
        """
    )
    tree = parse_text_as_file(text)
    node = lofty.build_ast(tree, Ref(["A"]))
    assert isinstance(node, L.Module)

    # TODO: check output
    # Requires params solver to be sane


def test_simple_new(lofty: Lofty):
    text = dedent(
        """
        component SomeComponent:
            signal a

        module A:
            child = new SomeComponent
        """
    )

    with errors.log_ato_errors():
        tree = parse_text_as_file(text)
        node = lofty.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)
    child = Lofty.get_node_attr(node, "child")
    assert isinstance(child, AtoComponent)

    a = Lofty.get_node_attr(child, "a")
    assert isinstance(a, F.Electrical)


def test_nested_nodes(lofty: Lofty):
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

    with errors.log_ato_errors():
        tree = parse_text_as_file(text)
        node = lofty.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)


def test_resistor(lofty: Lofty):
    text = dedent(
        """
        from "generics/resistors.ato" import Resistor

        component ResistorB from Resistor:
            footprint = "R0805"

        module A:
            r1 = new ResistorB
        """
    )

    with errors.log_ato_errors():
        tree = parse_text_as_file(text)
        node = lofty.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    r1 = Lofty.get_node_attr(node, "r1")
    assert r1.get_trait(F.has_footprint_requirement).get_footprint_requirement() == [
        ("0805", 2)
    ]


def test_write_only_property():
    """Test that write-only property raises on get and allows set"""

    class TestClass:
        def __init__(self):
            self._value = None

        @_write_only_property
        def write_only(self, value):
            self._value = value

        def get_value(self):
            return self._value

    obj = TestClass()

    # Reading should raise AttributeError
    with pytest.raises(AttributeError) as exc_info:
        _ = obj.write_only
    assert "write_only is write-only" in str(exc_info.value)

    # Writing should work
    test_value = "test"
    obj.write_only = test_value
    assert obj.get_value() == test_value
