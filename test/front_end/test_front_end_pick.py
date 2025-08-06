from pathlib import Path
from textwrap import dedent

import pytest

import faebryk.library._F as F
from atopile.datatypes import TypeRef
from atopile.front_end import Bob
from atopile.parse import parse_text_as_file
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_shim(bob: Bob, repo_root: Path):
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

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)
    assert r1.get_trait(F.has_package_requirements)._size == SMDSize.I0805

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor(bob: Bob, repo_root: Path):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        """
        import Resistor

        module A:
            r1 = new Resistor
            r1.package = 'R0805'
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Resistor)
    assert r1.get_trait(F.has_package_requirements)._size == SMDSize.I0805

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_capacitor_shim(bob: Bob, repo_root: Path):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        """
        from "generics/capacitors.ato" import Capacitor

        module A:
            r1 = new BypassCap100nF

        component BypassCap from Capacitor:
            footprint = "C0402"

        component BypassCap100nF from BypassCap:
            value = 100nF +/- 20%
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Capacitor)
    assert r1.get_trait(F.has_package_requirements)._size == SMDSize.I0402

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_capacitor(bob: Bob, repo_root: Path):
    text = dedent(
        """
        import Capacitor

        module A:
            r1 = new Capacitor
            r1.package = 'C0402'
            r1.capacitance = 100nF +/- 20%
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    r1 = bob.resolve_field_shortcut(node, "r1")
    assert isinstance(r1, F.Capacitor)
    assert r1.get_trait(F.has_package_requirements)._size == SMDSize.I0402

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.parametrize(
    "package,package_str",
    [
        (SMDSize.I0402, "L0402"),
        (SMDSize.SMD1_1x1_8mm, "SMD1_1x1_8mm"),
    ],
)
def test_ato_pick_inductor(
    bob: Bob, repo_root: Path, package: SMDSize, package_str: str
):
    text = dedent(
        f"""
        import Inductor

        module A:
            inductor = new Inductor
            inductor.package = '{package_str}'
            inductor.inductance = 100nH +/- 20%
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["A"]))

    assert isinstance(node, L.Module)

    inductor = bob.resolve_field_shortcut(node, "inductor")
    assert isinstance(inductor, F.Inductor)
    assert inductor.get_trait(F.has_package_requirements)._size == package

    pick_part_recursively(inductor, DefaultSolver())

    assert inductor.has_trait(F.has_part_picked)

    inductance_lit = inductor.inductance.try_get_literal()
    assert inductance_lit is not None
    assert isinstance(inductance_lit, P_Set)
    assert inductance_lit.is_subset_of(L.Range.from_center_rel(100 * P.nH, 0.2))


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_dependency(bob: Bob, repo_root: Path):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        """
        from "generics/resistors.ato" import Resistor

        module App:
            r1 = new Resistor
            r2 = new Resistor

            assert r1.resistance + r2.resistance within 100kohm +/- 20%
            assert r1.resistance within 100kohm +/- 20% - r2.resistance
            assert r2.resistance within 100kohm +/- 20% - r1.resistance
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    solver = DefaultSolver()
    pick_part_recursively(node, solver)

    r1, r2 = node.get_children_modules(direct_only=True, types=Module)
    assert r1.has_trait(F.has_part_picked)
    assert r2.has_trait(F.has_part_picked)


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_voltage_divider_fab(bob: Bob, repo_root: Path):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        """
        import ResistorVoltageDivider

        module App:
            vdiv = new ResistorVoltageDivider

            vdiv.v_in = 10V +/- 1%
            assert vdiv.v_out within 3V to 3.2V
            assert vdiv.max_current within 1mA to 3mA
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    solver = DefaultSolver()
    pick_part_recursively(node, solver)

    rs = node.get_children_modules(direct_only=False, types=F.Resistor)
    for r in rs:
        assert r.has_trait(F.has_part_picked)


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_voltage_divider_ato(bob: Bob, repo_root: Path):
    bob.search_paths.append(
        repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    )

    text = dedent(
        """
        from "vdivs.ato" import VDiv

        module App:
            vdiv = new VDiv

            vdiv.v_in = 10V +/- 1%
            assert vdiv.v_out within 3V to 3.2V
            assert vdiv.i_q within 1mA to 3mA
        """
    )

    tree = parse_text_as_file(text)
    node = bob.build_ast(tree, TypeRef(["App"]))

    assert isinstance(node, L.Module)

    solver = DefaultSolver()
    pick_part_recursively(node, solver)

    rs = node.get_children_modules(direct_only=False, types=F.Resistor)
    for r in rs:
        assert r.has_trait(F.has_part_picked)
