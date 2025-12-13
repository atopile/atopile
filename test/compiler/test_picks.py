import textwrap
from pathlib import Path

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.build import Linker, StdlibRegistry, build_file, build_source
from faebryk.core.faebrykpy import EdgeComposition
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import not_none
from test.compiler.conftest import build_instance

E = BoundExpressions()


def _get_child(node: BoundNode, name: str) -> BoundNode:
    return not_none(
        EdgeComposition.get_child_by_identifier(bound_node=node, child_identifier=name)
    )


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_shim(tmp_path: Path):
    child_path = tmp_path / "generics" / "resistors.ato"
    child_path.parent.mkdir(parents=True)
    child_path.write_text(
        textwrap.dedent(
            """
            import Resistor

            component ResistorGeneric from Resistor:
                pass
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            from "generics/resistors.ato" import ResistorGeneric

            component ResistorB from ResistorGeneric:
                footprint = "R0805"

            module A:
                r1 = new ResistorB
            """
        ),
        encoding="utf-8",
    )

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    assert "A" in result.state.type_roots

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    # Instantiate and pick
    app_type = result.state.type_roots["A"]
    app_instance = tg.instantiate_node(type_node=app_type, attributes={})

    r1 = _get_child(app_instance, "r1")
    assert isinstance(r1, F.Resistor)
    assert r1.get_trait(F.has_package_requirements).size_.get() == SMDSize.I0805

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor():
    _, _, _, result, app_instance = build_instance(
        """
        import Resistor

        module A:
            r1 = new Resistor
            r1.package = 'R0805'
        """,
        "A",
    )

    # Instantiate and pick
    app_instance = result.state.type_roots["A"]

    r1 = _get_child(app_instance, "r1")
    assert isinstance(r1, F.Resistor)
    assert r1.get_trait(F.has_package_requirements).size_.get() == SMDSize.I0805

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_capacitor_shim(tmp_path: Path):
    child_path = tmp_path / "generics" / "capacitors.ato"
    child_path.parent.mkdir(parents=True)
    child_path.write_text(
        textwrap.dedent(
            """
            import Capacitor

            component CapacitorGeneric from Capacitor:
                pass
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            from "generics/capacitors.ato" import CapacitorGeneric

            module A:
                r1 = new BypassCap100nF

            component BypassCap from CapacitorGeneric:
                footprint = "C0402"

            component BypassCap100nF from BypassCap:
                value = 100nF +/- 20%
            """
        ),
        encoding="utf-8",
    )

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    assert "A" in result.state.type_roots

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    # Instantiate and pick
    app_type = result.state.type_roots["A"]
    app_instance = tg.instantiate_node(type_node=app_type, attributes={})

    r1 = _get_child(app_instance, "r1")
    assert isinstance(r1, F.Capacitor)
    assert r1.get_trait(F.has_package_requirements).size_.get() == SMDSize.I0402

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_capacitor():
    _, _, _, result, app_instance = build_instance(
        """
            import Capacitor

            module A:
                r1 = new Capacitor
                r1.package = 'C0402'
                r1.capacitance = 100nF +/- 20%
            """,
        "A",
    )

    r1 = _get_child(app_instance, "r1")
    assert isinstance(r1, F.Capacitor)
    assert r1.get_trait(F.has_package_requirements).size_.get() == SMDSize.I0402

    pick_part_recursively(r1, DefaultSolver())

    assert r1.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.parametrize(
    "package,package_str,inductance_str,inductance_literal",
    [
        (
            SMDSize.I0402,
            "L0402",
            "100nH +/- 20%",
            E.lit_op_range_from_center_rel((100, E.U.nH), 0.2),
        ),
        (
            SMDSize.SMD4x4mm,
            "SMD4x4mm",
            "2.2uH +/- 20%",
            E.lit_op_range_from_center_rel((2.2, E.U.uH), 0.2),
        ),
    ],
)
def test_ato_pick_inductor(
    package: SMDSize,
    package_str: str,
    inductance_str: str,
    inductance_literal: F.Parameters.can_be_operand,
):
    _, _, _, result, app_instance = build_instance(
        """
            import Inductor

            module A:
                inductor = new Inductor
                inductor.package = '{package_str}'
                inductor.inductance = {inductance_str}
            """,
        "A",
    )
    assert "A" in result.state.type_roots

    inductor = F.Inductor.bind_instance(_get_child(app_instance, "inductor"))
    assert inductor.get_trait(F.has_package_requirements).size_.get() == package

    pick_part_recursively(inductor, DefaultSolver())

    assert inductor.has_trait(F.has_part_picked)

    assert inductance_literal.as_literal.get().equals(
        not_none(inductor.inductance.get().try_extract_aliased_literal())
    )


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_dependency(tmp_path: Path):
    child_path = tmp_path / "generics" / "resistors.ato"
    child_path.parent.mkdir(parents=True)
    child_path.write_text(
        textwrap.dedent(
            """
            import Resistor

            component ResistorGeneric from Resistor:
                pass
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            from "generics/resistors.ato" import ResistorGeneric

            module App:
                r1 = new ResistorGeneric
                r2 = new ResistorGeneric

                assert r1.resistance + r2.resistance within 100kohm +/- 20%
                assert r1.resistance within 100kohm +/- 20% - r2.resistance
                assert r2.resistance within 100kohm +/- 20% - r1.resistance
            """
        ),
        encoding="utf-8",
    )

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    assert "App" in result.state.type_roots

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    # Instantiate and pick
    app_type = result.state.type_roots["App"]
    app_instance = tg.instantiate_node(type_node=app_type, attributes={})

    solver = DefaultSolver()
    pick_part_recursively(fabll.Node.bind_instance(app_instance), solver)

    r1 = fabll.Node.bind_instance(_get_child(app_instance, "r1"))
    r2 = fabll.Node.bind_instance(_get_child(app_instance, "r2"))
    assert r1.has_trait(F.has_part_picked)
    assert r2.has_trait(F.has_part_picked)


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_voltage_divider_fab():
    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_source(
        g=g,
        tg=tg,
        source=textwrap.dedent(
            """
            import ResistorVoltageDivider

            module App:
                vdiv = new ResistorVoltageDivider

                vdiv.v_in = 10V +/- 1%
                assert vdiv.v_out within 3V to 3.2V
                assert vdiv.max_current within 1mA to 3mA
            """
        ),
    )
    assert "App" in result.state.type_roots

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    # Instantiate and pick
    app_type = result.state.type_roots["App"]
    app_instance = tg.instantiate_node(type_node=app_type, attributes={})

    solver = DefaultSolver()
    pick_part_recursively(fabll.Node.bind_instance(app_instance), solver)

    # Check all resistors have parts picked
    vdiv = fabll.Node.bind_instance(_get_child(app_instance, "vdiv"))
    r_top = fabll.Node.bind_instance(_get_child(vdiv.instance, "r_top"))
    r_bottom = fabll.Node.bind_instance(_get_child(vdiv.instance, "r_bottom"))
    assert r_top.has_trait(F.has_part_picked)
    assert r_bottom.has_trait(F.has_part_picked)


@pytest.mark.slow
@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor_voltage_divider_ato(tmp_path: Path):
    child_path = tmp_path / "vdivs.ato"
    child_path.write_text(
        textwrap.dedent(
            """
            import ResistorVoltageDivider

            module VDiv from ResistorVoltageDivider:
                pass
            """
        ),
        encoding="utf-8",
    )

    main_path = tmp_path / "main.ato"
    main_path.write_text(
        textwrap.dedent(
            """
            from "vdivs.ato" import VDiv

            module App:
                vdiv = new VDiv

                vdiv.v_in = 10V +/- 1%
                assert vdiv.v_out within 3V to 3.2V
                assert vdiv.i_q within 1mA to 3mA
            """
        ),
        encoding="utf-8",
    )

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    assert "App" in result.state.type_roots

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    # Instantiate and pick
    app_type = result.state.type_roots["App"]
    app_instance = tg.instantiate_node(type_node=app_type, attributes={})

    solver = DefaultSolver()
    pick_part_recursively(fabll.Node.bind_instance(app_instance), solver)

    # Check all resistors have parts picked
    vdiv = fabll.Node.bind_instance(_get_child(app_instance, "vdiv"))
    r_top = fabll.Node.bind_instance(_get_child(vdiv.instance, "r_top"))
    r_bottom = fabll.Node.bind_instance(_get_child(vdiv.instance, "r_bottom"))
    assert r_top.has_trait(F.has_part_picked)
    assert r_bottom.has_trait(F.has_part_picked)
