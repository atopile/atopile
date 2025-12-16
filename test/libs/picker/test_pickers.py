# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.nullsolver import NullSolver
from faebryk.libs.picker.api.picker_lib import (
    NotCompatibleException,
    check_and_attach_candidates,
    get_candidates,
)
from faebryk.libs.picker.lcsc import PickedPartLCSC
from faebryk.libs.picker.picker import PickError, pick_part_recursively
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import cast_assert, groupby

sys.path.append(str(Path(__file__).parent))

if TYPE_CHECKING:
    from test.libs.picker.components import ComponentTestCase

from test.libs.picker.components import components_to_test

logger = logging.getLogger(__name__)


def test_load_components():
    assert components_to_test, "Failed to load components"


def _make_id(m: "ComponentTestCase"):
    if m.override_test_name:
        module_name = m.override_test_name
    else:
        module_name = type(m.module).__name__
        gouped_by_type = groupby(components_to_test, lambda c: type(c.module))
        group_for_module = gouped_by_type[type(m.module)]
        if len(group_for_module) > 1:
            module_name += f"[{group_for_module.index(m)}]"

    return module_name


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.skipif(components_to_test is None, reason="Failed to load components")
@pytest.mark.parametrize(
    "case",
    components_to_test,
    ids=[_make_id(m) for m in components_to_test],
)
def test_pick_module(case: "ComponentTestCase"):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = case.get_module(g=g, tg=tg)
    # if case.packages:
    #     module.create_and_add_instance_to(
    #         F.has_package_requirements(size=fabll.EnumSet.from_values(*case.packages))
    #     )

    # pick
    solver = DefaultSolver()
    pick_part_recursively(module, solver)

    assert module.has_trait(F.has_part_picked)
    part = module.get_trait(F.has_part_picked).get_part()

    # Sanity check
    assert part.partno

    # Check LCSC & MFR
    if case.lcsc_id:
        assert cast_assert(PickedPartLCSC, part).lcsc_id == case.lcsc_id
    elif case.mfr_mpn:
        assert part.manufacturer == case.mfr_mpn[0]
        assert part.partno == case.mfr_mpn[1]

    # Check parameters
    # params = module.get_children(types=Parameter, direct_only=True)
    # TODO check that part params are equal (alias_is) to module params


@pytest.mark.usefixtures("setup_project_config")
def test_type_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(module, F.is_pickable)

    assert module.has_trait(F.is_pickable_by_type)
    # assert module.has_trait(F.is_pickable)
    is_subset = F.Expressions.IsSubset.bind_typegraph(tg=module.tg).create_instance(
        g=module.g
    )
    is_subset.setup(
        subset=module.resistance.get().can_be_operand.get(),
        superset=F.Literals.Numbers.bind_typegraph(tg=module.tg)
        .create_instance(g=module.g)
        .setup_from_center_rel(
            center=100,
            rel=0.1,
            unit=F.Units.Ohm.bind_typegraph(tg=module.tg)
            .create_instance(g=module.g)
            .is_unit.get(),
        )
        .is_literal.get()
        .as_operand.get(),
        # assert_=True,
    )

    pick_part_recursively(module, DefaultSolver())

    assert module.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_no_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(module, F.has_part_removed)

    pick_part_recursively(module, DefaultSolver())

    assert module.has_trait(F.has_part_picked)
    assert module.get_trait(F.has_part_picked).removed


def test_construct_pick_tree_simple():
    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(module, F.is_pickable)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    tree = get_pick_tree(app)
    assert len(tree) == 2
    assert (
        app.r1.get().get_trait(F.is_pickable_by_type).get_trait(F.is_pickable) in tree
    )
    assert (
        app.r2.get().get_trait(F.is_pickable_by_type).get_trait(F.is_pickable) in tree
    )


def test_construct_pick_tree_multiple_children():
    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(module, F.is_pickable)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

        class App2(fabll.Node):
            r3 = F.Resistor.MakeChild()

        app2 = App2.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    tree = get_pick_tree(app)
    assert len(tree) == 3
    assert (
        app.r1.get().get_trait(F.is_pickable_by_type).get_trait(F.is_pickable) in tree
    )
    assert (
        app.r2.get().get_trait(F.is_pickable_by_type).get_trait(F.is_pickable) in tree
    )
    assert (
        app.app2.get()
        .r3.get()
        .get_trait(F.is_pickable_by_type)
        .get_trait(F.is_pickable)
        in tree
    )


def test_check_missing_picks_no_footprint_no_picker(caplog):
    import logging

    from faebryk.libs.picker.picker import check_missing_picks

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    # Optionally set log level to capture DEBUG messages
    with caplog.at_level(logging.DEBUG):
        check_missing_picks(app)

    # Assert on logs
    assert "No pickers and no footprint for" in caplog.text


def test_check_missing_picks_with_footprint_with_picker(caplog):
    import logging

    from faebryk.libs.picker.picker import check_missing_picks

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(
        app.r1.get(), F.Footprints.has_associated_footprint
    )
    fabll.Traits.create_and_add_instance_to(app.r1.get(), F.has_part_picked)

    with caplog.at_level(logging.DEBUG):
        check_missing_picks(app)

    assert caplog.text == ""


# Waiting on footprint attach to work
@pytest.mark.usefixtures("setup_project_config")
def test_pick_explicit_modules():
    from faebryk.libs.picker.picker import get_pick_tree, pick_topologically

    solver = DefaultSolver()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()

        @classmethod
        def MakeChild(cls):  # type: ignore[invalid-method-override]
            out = fabll._ChildField(cls)
            out.add_dependant(
                fabll.Traits.MakeEdge(
                    F.is_pickable_by_supplier_id.MakeChild(
                        supplier_part_id="C173561",
                        supplier=F.is_pickable_by_supplier_id.Supplier.LCSC,
                    ),
                    [out, cls.r1],
                )
            )
            return out

    app = App.bind_typegraph(tg=tg).create_instance(g=g)
    tree = get_pick_tree(app)
    pick_topologically(tree, solver)
    assert app.r1.get().has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_pick_resistor_by_params():
    from faebryk.libs.picker.picker import get_pick_tree, pick_topologically

    solver = DefaultSolver()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    E = BoundExpressions(g=g, tg=tg)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    # Constrain resistance
    resistance_op = E.lit_op_range(((100, E.U.Ohm), (110, E.U.Ohm)))
    E.is_(
        app.r1.get().resistance.get().can_be_operand.get(), resistance_op, assert_=True
    )

    # Constrain package
    fabll.Traits.create_and_add_instance_to(app.r1.get(), F.has_package_requirements)
    app.r1.get().get_trait(F.has_package_requirements).setup(SMDSize.I0805)

    tree = get_pick_tree(app)
    pick_topologically(tree, solver)
    assert app.r1.get().has_trait(F.has_part_picked)
    assert (
        app.r1.get()
        .resistance.get()
        .force_extract_literal()
        .is_subset_of(
            F.Literals.Numbers(resistance_op.get_raw_obj().instance),
            g=g,
            tg=tg,
        )
    )
    assert app.r1.get().get_trait(F.has_package_requirements).get_sizes() == [
        SMDSize.I0805
    ]


# I guess we need to support something like this?
# @pytest.mark.usefixtures("setup_project_config")
# def test_no_pick_inherit_override_none():
#     class _CapInherit(F.Capacitor):
#         pickable = None  # type: ignore

#     module = _CapInherit()

#     assert not module.has_trait(F.is_pickable)

#     pick_part_recursively(module, DefaultSolver())

#     assert not module.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_no_pick_inherit_remove():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    module = _.bind_typegraph(tg=tg).create_instance(g=g)

    pick_part_recursively(module, DefaultSolver())

    assert module.has_trait(F.has_part_picked)
    assert module.get_trait(F.has_part_picked).removed


@pytest.mark.usefixtures("setup_project_config")
def test_skip_self_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _CapInherit(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        inner = F.Capacitor.MakeChild()

    module = _CapInherit.bind_typegraph(tg=tg).create_instance(g=g)

    pick_part_recursively(module, DefaultSolver())

    assert not module.has_trait(F.has_part_picked)
    assert module.inner.get().has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.xfail(reason="TODO: add support for diodes")
def test_pick_led_by_colour():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    color = F.LED.Color.YELLOW
    led = F.LED.bind_typegraph(tg=tg).create_instance(g=g)

    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(color),
        assert_=True,
    )
    E.is_(
        led.diode.get().current.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.mA), 0.1),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(led, solver)

    assert led.has_trait(F.has_part_picked)
    solver.update_superset_cache(led)
    assert solver.inspect_get_known_supersets(led.color).is_subset_of(
        EnumSet.from_value(color)
    )


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.xfail(reason="TODO: add support for diodes")
def test_reject_diode_for_led():
    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    led = F.LED.bind_typegraph(tg=tg).create_instance(g=g)
    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.YELLOW),
        assert_=True,
    )
    E.is_(
        led.diode.get().current.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.mA), 0.1),
        assert_=True,
    )

    diode = F.Diode.bind_typegraph(tg=tg).create_instance(g=g)
    E.is_(
        diode.current.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.mA), 0.1),
        assert_=True,
    )

    solver = DefaultSolver()
    diode_tree = get_pick_tree(diode)
    diode_pickable = next(iter(diode_tree.keys()))
    candidates = get_candidates(diode_tree, solver)
    with pytest.raises(NotCompatibleException):
        check_and_attach_candidates(
            [(led, c) for c in candidates[diode_pickable]], solver
        )


@pytest.mark.usefixtures("setup_project_config")
def test_pick_error_group():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        c1 = F.Capacitor.MakeChild()
        c2 = F.Capacitor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    # Good luck finding a 10 gigafarad capacitor!
    E.is_(
        app.c1.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.GF), 0.1),
        assert_=True,
    )
    E.is_(
        app.c2.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((20, E.U.GF), 0.1),
        assert_=True,
    )

    solver = DefaultSolver()

    with pytest.raises(ExceptionGroup) as ex:
        pick_part_recursively(app, solver)

    assert len(ex.value.exceptions) == 1
    assert isinstance(ex.value.exceptions[0], PickError)


@pytest.mark.usefixtures("setup_project_config")
def test_pick_dependency_simple():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    solver = DefaultSolver()
    r1r = app.r1.get().resistance.get().can_be_operand.get()
    r2r = app.r2.get().resistance.get().can_be_operand.get()
    sum_lit = E.lit_op_range_from_center_rel((100000, E.U.Ohm), 0.2)
    E.is_(E.add(r1r, r2r), sum_lit, assert_=True)
    E.is_subset(r1r, E.subtract(sum_lit, r2r), assert_=True)
    E.is_subset(r2r, E.subtract(sum_lit, r1r), assert_=True)

    pick_part_recursively(app, solver)

    # assert app.r1.has_trait(F.has_part_picked)
    # assert app.r2.has_trait(F.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.slow
def test_pick_dependency_advanced_1():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    rdiv = F.ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

    E.is_subset(
        rdiv.total_resistance.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((100, E.U.kOhm), 0.1),
        assert_=True,
    )
    E.is_subset(
        rdiv.ratio.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((0.1, E.U.dl), 0.2),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(rdiv, solver)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.slow
def test_pick_dependency_advanced_2():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    rdiv = F.ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

    E.is_(
        rdiv.v_in.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.V), 0.1),
        assert_=True,
    )
    E.is_subset(
        rdiv.v_out.get().can_be_operand.get(),
        E.lit_op_range(((3, E.U.V), (3.2, E.U.V))),
        assert_=True,
    )
    E.is_subset(
        rdiv.max_current.get().can_be_operand.get(),
        E.lit_op_range(((1, E.U.mA), (3, E.U.mA))),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(rdiv, solver)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.slow
def test_pick_dependency_div_negative():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    rdiv = F.ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

    E.is_(
        rdiv.v_in.get().can_be_operand.get(),
        E.lit_op_range(((-10, E.U.V), (-9, E.U.V))),
        assert_=True,
    )
    E.is_subset(
        rdiv.v_out.get().can_be_operand.get(),
        E.lit_op_range(((-3.2, E.U.V), (-3, E.U.V))),
        assert_=True,
    )
    E.is_subset(
        rdiv.max_current.get().can_be_operand.get(),
        E.lit_op_range(((1, E.U.mA), (3, E.U.mA))),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(rdiv, solver)


@pytest.mark.usefixtures("setup_project_config")
def test_null_solver():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)
    capacitance = E.lit_op_range_from_center_rel(center=(10**-9, E.U.Fa), rel=0.2)

    class App(fabll.Node):
        cap = F.Capacitor.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(
        app.cap.get(), F.has_package_requirements
    ).setup(SMDSize.I0805)
    E.is_(
        app.cap.get().capacitance.get().can_be_operand.get(),
        capacitance,
        assert_=True,
    )

    solver = NullSolver()
    pick_part_recursively(app, solver)

    assert app.cap.get().has_trait(F.has_part_picked)
    assert app.cap.get().get_trait(F.has_package_requirements).get_sizes() == [
        SMDSize.I0805
    ]
    assert (
        (solver)
        .inspect_get_known_supersets(app.cap.get().capacitance.get().is_parameter.get())
        .is_subset_of(capacitance.as_literal.force_get())
    )


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.slow
def test_pick_voltage_divider_complex():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        supply = F.ElectricPower.MakeChild()
        rdiv = F.ResistorVoltageDivider.MakeChild()
        adc_input = F.ElectricSignal.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    # Connect interfaces
    app.supply.get()._is_interface.get().connect_to(app.rdiv.get().power.get())
    app.rdiv.get().output.get()._is_interface.get().connect_to(app.adc_input.get())

    # Set constraints
    E.is_(
        app.supply.get().voltage.get().can_be_operand.get(),
        E.lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
        assert_=True,
    )
    E.is_subset(
        app.adc_input.get().reference.get().voltage.get().can_be_operand.get(),
        E.lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
        assert_=True,
    )
    E.is_subset(
        app.rdiv.get().max_current.get().can_be_operand.get(),
        E.lit_op_range(((1, E.U.mA), (2, E.U.mA))),
        assert_=True,
    )

    solver = DefaultSolver()

    solver.simplify_symbolically(tg, g)

    # pick_part_recursively(app, solver)

    # for m in app.get_children_modules(types=fabll.Module):
    #    if not m.has_trait(F.has_part_picked):
    #        continue
    #    print(m.get_full_name(), m.pretty_params(solver))


@pytest.mark.usefixtures("setup_project_config")
def test_pick_capacitor_temperature_coefficient():
    # the picker backend must have access to the same enum definition for this to work
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    cap = F.Capacitor.bind_typegraph(tg=tg).create_instance(g=g)
    cap.temperature_coefficient.get().alias_to_literal(
        F.Capacitor.TemperatureCoefficient.X7R
    )

    solver = DefaultSolver()
    pick_part_recursively(cap, solver)

    assert cap.has_trait(F.has_part_picked)
