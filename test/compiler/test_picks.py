import textwrap
from pathlib import Path

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.build import Linker, StdlibRegistry, build_file
from faebryk.core.faebrykpy import EdgeComposition
from faebryk.core.solver.solver import Solver
from faebryk.libs.picker.picker import pick_parts_recursively
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import not_none
from test.compiler.conftest import build_instance

E = BoundExpressions()


def _get_child(node: graph.BoundNode, name: str) -> graph.BoundNode:
    return not_none(
        EdgeComposition.get_child_by_identifier(bound_node=node, child_identifier=name)
    )


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_resistor():
    _, _, _, result, app_instance = build_instance(
        """
        import Resistor

        module A:
            r1 = new Resistor
            r1.package = "R0805"
        """,
        "A",
    )

    r1 = F.Resistor.bind_instance(_get_child(app_instance, "r1"))
    assert (
        r1.get_trait(F.has_package_requirements)
        .size.get()
        .force_extract_singleton_typed(SMDSize)
        == SMDSize.I0805
    )

    pick_parts_recursively(r1, Solver())

    assert r1.has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_ato_pick_capacitor():
    _, _, _, result, app_instance = build_instance(
        """
            import Capacitor

            module A:
                r1 = new Capacitor
                r1.package = "C0402"
                r1.capacitance = 100nF +/- 20%
            """,
        "A",
    )

    r1 = F.Capacitor.bind_instance(_get_child(app_instance, "r1"))
    assert (
        r1.get_trait(F.has_package_requirements)
        .size.get()
        .force_extract_singleton_typed(SMDSize)
        == SMDSize.I0402
    )

    pick_parts_recursively(r1, Solver())

    assert r1.has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.parametrize(
    "package,package_str,inductance_str,inductance_literal",
    [
        (
            SMDSize.I0402,
            "L0402",
            "100nH +/- 30%",
            E.lit_op_range_from_center_rel((100, E.U.nH), 0.3),
        ),
        (
            SMDSize.SMD4x4mm,
            "SMD4x4mm",
            "2.2uH +/- 30%",
            E.lit_op_range_from_center_rel((2.2, E.U.uH), 0.3),
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
        f"""
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
    assert (
        inductor.get_trait(F.has_package_requirements)
        .size.get()
        .force_extract_singleton_typed(SMDSize)
        == package
    )

    pick_parts_recursively(inductor, Solver())

    assert inductor.has_trait(F.Pickable.has_part_picked)

    # Verify the picked part has an inductance value
    picked_inductance = inductor.inductance.get().try_extract_subset()
    assert picked_inductance is not None, "Picked part should have inductance value"


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.skip(reason="to_fix")  # FIXME
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

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)

    result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
    assert "App" in result.state.type_roots

    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)

    # Instantiate and pick
    app_type = result.state.type_roots["App"]
    app_instance = tg.instantiate_node(type_node=app_type, attributes={})

    solver = Solver()
    pick_parts_recursively(fabll.Node.bind_instance(app_instance), solver)

    r1 = fabll.Node.bind_instance(_get_child(app_instance, "r1"))
    r2 = fabll.Node.bind_instance(_get_child(app_instance, "r2"))
    assert r1.has_trait(F.Pickable.has_part_picked)
    assert r2.has_trait(F.Pickable.has_part_picked)
