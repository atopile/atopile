from pathlib import Path
from textwrap import dedent

import pytest

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
from atopile import errors
from atopile.datatypes import Ref
from atopile.front_end import Bob, Component
from atopile.parse import parse_text_as_file
from faebryk.libs.library import L


@pytest.fixture
def bob() -> Bob:
    return Bob()


def test_empty_module_build(bob: Bob):
    text = dedent(
        """
        module A:
            pass
        """
    )
    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))
    assert isinstance(node, L.Module)
    assert isinstance(node, bob.modules[":A"])


@pytest.mark.skip
def test_simple_module_build(bob: Bob):
    text = dedent(
        """
        module A:
            a = 1
        """
    )
    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))
    assert isinstance(node, L.Module)

    param = node.runtime["a"]
    assert isinstance(param, fab_param.ParameterOperatable)
    # TODO: check value


@pytest.mark.skip
def test_arithmetic(bob: Bob):
    text = dedent(
        """
        module A:
            a = 1 to 2 * 3
            b = a + 4
        """
    )
    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))
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

    with errors.log_ato_errors():
        tree = parse_text_as_file(text)
        node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)
    child = Bob.get_node_attr(node, "child")
    assert isinstance(child, Component)

    a = Bob.get_node_attr(child, "a")
    assert isinstance(a, F.Electrical)


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

    with errors.log_ato_errors():
        tree = parse_text_as_file(text)
        node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)


def test_resistor(bob: Bob):
    prj_root = Path(__file__)
    while not (prj_root / "pyproject.toml").exists():
        prj_root = prj_root.parent

    bob.search_paths.append(prj_root / "examples" / "project" / ".ato" / "modules")

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
        node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    r1 = Bob.get_node_attr(node, "r1")
    assert r1.get_trait(F.has_footprint_requirement).get_footprint_requirement() == [
        ("0805", 2)
    ]
