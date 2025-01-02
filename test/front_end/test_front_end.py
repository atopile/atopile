from pathlib import Path
from textwrap import dedent

import pytest
from antlr4 import ParserRuleContext

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
from atopile import errors
from atopile.datatypes import Ref
from atopile.front_end import Bob, has_ato_cmp_attrs
from atopile.parse import parse_text_as_file
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.util import cast_assert


@pytest.fixture
def bob() -> Bob:
    return Bob()


@pytest.fixture
def repo_root() -> Path:
    repo_root = Path(__file__)
    while not (repo_root / "pyproject.toml").exists():
        repo_root = repo_root.parent
    return repo_root


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

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)
    child = Bob.get_node_attr(node, "child")
    assert child.has_trait(has_ato_cmp_attrs)

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

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)


def test_resistor(bob: Bob, repo_root: Path):
    bob.search_paths.append(repo_root / "examples" / ".ato" / "modules")

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
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    r1 = Bob.get_node_attr(node, "r1")
    assert r1.get_trait(F.has_package_requirement).get_package_candidates() == ["0805"]


def test_standard_library_import(bob: Bob):
    text = dedent(
        """
        import Resistor

        module A:
            r1 = new Resistor
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    r1 = Bob.get_node_attr(node, "r1")
    assert isinstance(r1, F.Resistor)


@pytest.mark.parametrize(
    "import_stmt,class_name",
    [
        ("import Resistor", "Resistor"),
        ("from 'generics/resistors.ato' import Resistor", "Resistor"),
        ("from 'generics/capacitors.ato' import Capacitor", "Capacitor"),
    ],
)
def test_reserved_attrs(bob: Bob, import_stmt: str, class_name: str, repo_root: Path):
    bob.search_paths.append(repo_root / "examples" / ".ato" / "modules")

    text = dedent(
        f"""
        {import_stmt}

        module A:
            a = new {class_name}
            a.package = "0402"
            a.mpn = "1234567890"
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    a = Bob.get_node_attr(node, "a")
    assert a.get_trait(F.has_package_requirement).get_package_candidates()[0] == "0402"
    assert a.get_trait(F.has_descriptive_properties).get_properties() == {
        DescriptiveProperties.partno: "1234567890"
    }


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
        )
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
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    r1 = Bob.get_node_attr(node, "r1")
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
        bob.build_ast(tree, Ref([module]))

    assert e.value.traceback is not None
    assert len(e.value.traceback) == count


# TODO: test connect
# - signal ~ signal
# - higher-level mif
# - duck-typed
def _get_mif(node: L.Node, name: str) -> L.ModuleInterface:
    return cast_assert(L.ModuleInterface, Bob.get_node_attr(node, name))


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
    node = bob.build_ast(tree, Ref(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(node, "a")
    b = _get_mif(node, "b")
    c = _get_mif(node, "c")

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
    node = bob.build_ast(tree, Ref(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(node, "a")
    b = _get_mif(node, "b")
    c = _get_mif(node, "c")

    assert a.is_connected_to(b)
    assert not a.is_connected_to(c)

    a_one = _get_mif(a, "one")
    b_one = _get_mif(b, "one")
    c_one = _get_mif(c, "one")
    a_two = _get_mif(a, "two")
    b_two = _get_mif(b, "two")
    c_two = _get_mif(c, "two")

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
    node = bob.build_ast(tree, Ref(["App"]))

    assert isinstance(node, L.Module)

    a = _get_mif(node, "a")
    b = _get_mif(node, "b")

    a_one = _get_mif(a, "one")
    b_one = _get_mif(b, "one")
    a_two = _get_mif(a, "two")
    b_two = _get_mif(b, "two")

    assert a_one.is_connected_to(b_one)
    assert a_two.is_connected_to(b_two)
    assert not any(a_one.is_connected_to(other) for other in [a_two, b_two])
    assert not any(a_two.is_connected_to(other) for other in [a_one, b_one])


def test_shim_power(bob: Bob):
    from atopile._shim import ShimPower

    ctx = ParserRuleContext()

    a = ShimPower()
    b = F.ElectricPower()

    bob._connect(a, b, ctx)

    assert a.lv.is_connected_to(b.lv)
    assert a.hv.is_connected_to(b.hv)
    assert not a.lv.is_connected_to(b.hv)
