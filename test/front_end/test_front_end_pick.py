from pathlib import Path
from textwrap import dedent

import pytest

import faebryk.library._F as F
from atopile.datatypes import Ref
from atopile.front_end import Bob
from atopile.parse import parse_text_as_file
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.picker.picker import pick_part_recursively


@pytest.fixture
def bob() -> Bob:
    return Bob()


@pytest.fixture
def repo_root() -> Path:
    repo_root = Path(__file__)
    while not (repo_root / "pyproject.toml").exists():
        repo_root = repo_root.parent
    return repo_root


def test_ato_pick_resistor(bob: Bob, repo_root: Path):
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
    assert isinstance(r1, F.Resistor)
    assert r1.get_trait(F.has_package_requirement).get_package_candidates() == ["0805"]

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


def test_ato_pick_capacitor(bob: Bob, repo_root: Path):
    bob.search_paths.append(repo_root / "examples" / ".ato" / "modules")

    text = dedent(
        """
        from "generics/capacitors.ato" import Capacitor

        module A:
            r1 = new BypassCap100nF

        component BypassCap from Capacitor:
            footprint = "R0402"

        component BypassCap100nF from BypassCap:
            value = 100nF +/- 20%
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, Ref(["A"]))

    assert isinstance(node, L.Module)

    r1 = Bob.get_node_attr(node, "r1")
    assert isinstance(r1, F.Capacitor)
    assert r1.get_trait(F.has_package_requirement).get_package_candidates() == ["0402"]

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)
