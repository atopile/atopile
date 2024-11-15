from textwrap import dedent

from atopile import errors
from faebryk.libs.library import L
import faebryk.library._F as F
import pytest

from atopile.datatypes import Ref
from atopile.front_end2 import Lofty, AtoComponent
from atopile.parse import parse_text_as_file
import faebryk.core.parameter as fab_param


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
    assert isinstance(param, fab_param.Parameter)
    assert list(param.within)[0].min_elem() == 1


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
