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
from faebryk.core.solver.solver import Solver
from faebryk.libs.picker.picker import PickedPart, PickError, pick_part_recursively
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import cast_assert, groupby, indented_container

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
    solver = Solver()
    pick_part_recursively(module, solver)

    assert module.has_trait(F.Pickable.has_part_picked)
    part = module.get_trait(F.Pickable.has_part_picked).get_part()

    # Sanity check
    assert part.partno

    # Check LCSC & MFR
    if case.lcsc_id:
        assert cast_assert(PickedPart, part).supplier_partno == case.lcsc_id
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

    fabll.Traits.create_and_add_instance_to(module, F.Pickable.is_pickable)

    assert module.has_trait(F.Pickable.is_pickable_by_type)
    # assert module.has_trait(F.Pickable.is_pickable)
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

    pick_part_recursively(module, Solver())

    assert module.has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_no_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(module, fabll.is_module)
    fabll.Traits.create_and_add_instance_to(module, F.has_part_removed)

    pick_part_recursively(module, Solver())

    assert module.has_trait(F.Pickable.has_part_picked)
    assert module.get_trait(F.Pickable.has_part_picked).is_removed()


def test_construct_pick_tree_simple():
    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(module, F.Pickable.is_pickable)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    tree = get_pick_tree(app)
    assert len(tree) == 2
    assert (
        app.r1.get()
        .get_trait(F.Pickable.is_pickable_by_type)
        .get_trait(F.Pickable.is_pickable)
        in tree
    )
    assert (
        app.r2.get()
        .get_trait(F.Pickable.is_pickable_by_type)
        .get_trait(F.Pickable.is_pickable)
        in tree
    )


def test_construct_pick_tree_multiple_children():
    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(module, F.Pickable.is_pickable)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

        class _NestedInterface(fabll.Node):
            _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
            r3 = F.Resistor.MakeChild()

        nested_interface = _NestedInterface.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    tree = get_pick_tree(app)
    assert len(tree) == 3
    print(indented_container(tree))
    assert (
        app.nested_interface.get()
        .r3.get()
        .get_trait(F.Pickable.is_pickable_by_type)
        .get_trait(F.Pickable.is_pickable)
        in tree
    )


def test_check_missing_picks_no_footprint_no_picker(caplog):
    import logging

    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a minimal module with no picker, no footprint, and no child modules
    # This should trigger the "No pickers and no footprint" warning
    class _ModuleWithoutPicker(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        # Only interfaces, no child modules
        pin = F.Electrical.MakeChild()

    class _App(fabll.Node):
        unpickable = _ModuleWithoutPicker.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Optionally set log level to capture WARNING messages
    with caplog.at_level(logging.WARNING):
        get_pick_tree(app)

    # Assert on logs
    assert "No pickers and no footprint for" in caplog.text


def test_check_missing_picks_with_footprint_with_picker(caplog):
    import logging

    from faebryk.libs.picker.picker import get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(
        app.r1.get(), F.Footprints.has_associated_footprint
    )
    fabll.Traits.create_and_add_instance_to(app.r1.get(), F.Pickable.has_part_picked)

    with caplog.at_level(logging.DEBUG):
        get_pick_tree(app)

    assert caplog.text == ""


# Waiting on footprint attach to work
@pytest.mark.usefixtures("setup_project_config")
def test_pick_explicit_modules():
    from faebryk.libs.picker.picker import get_pick_tree, pick_topologically

    solver = Solver()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()

        @classmethod
        def MakeChild(cls):  # type: ignore[invalid-method-override]
            out = fabll._ChildField(cls)
            out.add_dependant(
                fabll.Traits.MakeEdge(
                    F.Pickable.is_pickable_by_supplier_id.MakeChild(
                        supplier_part_id="C173561",
                        supplier=F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC,
                    ),
                    [out, cls.r1],
                )
            )
            return out

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)
    tree = get_pick_tree(app)
    pick_topologically(tree, solver)
    assert app.r1.get().has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_pick_resistor_by_params():
    from faebryk.libs.picker.picker import get_pick_tree, pick_topologically

    solver = Solver()

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        _r1_pkg = fabll.Traits.MakeEdge(
            F.has_package_requirements.MakeChild(size=SMDSize.I0805), [r1]
        )

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Constrain resistance
    resistance_op = E.lit_op_range(((100, E.U.Ohm), (110, E.U.Ohm)))
    E.is_subset(
        app.r1.get().resistance.get().can_be_operand.get(), resistance_op, assert_=True
    )

    tree = get_pick_tree(app)
    pick_topologically(tree, solver)
    assert app.r1.get().has_trait(F.Pickable.has_part_picked)
    assert (
        app.r1.get()
        .resistance.get()
        .force_extract_subset()
        .op_setic_is_subset_of(
            F.Literals.Numbers(resistance_op.get_raw_obj().instance),
            g=g,
            tg=tg,
        )
    )
    assert app.r1.get().get_trait(F.has_package_requirements).get_sizes() == [
        SMDSize.I0805
    ]


@pytest.mark.usefixtures("setup_project_config")
def test_skip_self_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _CapInherit(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        inner = F.Capacitor.MakeChild()

    module = _CapInherit.bind_typegraph(tg=tg).create_instance(g=g)

    pick_part_recursively(module, Solver())

    assert not module.has_trait(F.Pickable.has_part_picked)
    assert module.inner.get().has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.skip(reason="xfail")  # TODO: add support for diodes
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
    E.is_subset(
        led.diode.get().current.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.mA), 0.1),
        assert_=True,
    )

    solver = Solver()
    pick_part_recursively(led, solver)

    assert led.has_trait(F.Pickable.has_part_picked)
    assert solver.simplify_and_extract_superset(
        led.color.get().is_parameter.get()
    ).op_setic_is_subset_of(E.lit_op_enum(color).as_literal.force_get())


@pytest.mark.usefixtures("setup_project_config")
def test_pick_error_group():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        c1 = F.Capacitor.MakeChild()
        c2 = F.Capacitor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Good luck finding a 10 gigafarad capacitor!
    E.is_subset(
        app.c1.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((10, E.U.GF), 0.1),
        assert_=True,
    )
    E.is_subset(
        app.c2.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range_from_center_rel((20, E.U.GF), 0.1),
        assert_=True,
    )

    solver = Solver()

    with pytest.raises(ExceptionGroup) as ex:
        pick_part_recursively(app, solver)

    assert len(ex.value.exceptions) == 1
    assert isinstance(ex.value.exceptions[0], PickError)


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.skip(reason="to_fix")  # FIXME
def test_pick_dependency_simple():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    solver = Solver()
    r1r = app.r1.get().resistance.get().can_be_operand.get()
    r2r = app.r2.get().resistance.get().can_be_operand.get()
    sum_lit = E.lit_op_range_from_center_rel((100000, E.U.Ohm), 0.2)
    E.is_subset(E.add(r1r, r2r), sum_lit, assert_=True)
    E.is_subset(r1r, E.subtract(sum_lit, r2r), assert_=True)
    E.is_subset(r2r, E.subtract(sum_lit, r1r), assert_=True)

    pick_part_recursively(app, solver)

    # assert app.r1.has_trait(F.Pickable.has_part_picked)
    # assert app.r2.has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_pick_capacitor_temperature_coefficient():
    # the picker backend must have access to the same enum definition for this to work
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    cap = F.Capacitor.bind_typegraph(tg=tg).create_instance(g=g)
    cap.temperature_coefficient.get().set_superset(
        F.Capacitor.TemperatureCoefficient.X7R
    )

    solver = Solver()
    pick_part_recursively(cap, solver)

    assert cap.has_trait(F.Pickable.has_part_picked)


def test_get_anticorrelated_pairs_basic():
    """
    Not(Correlated(p1, p2)) should create an anticorrelated pair.
    """
    from faebryk.libs.picker.picker import _get_anticorrelated_pairs

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)

    E.not_(E.correlated(p1, p2))

    pairs = _get_anticorrelated_pairs(tg)

    assert len(pairs) == 1
    p1_param = p1.as_parameter_operatable.force_get().as_parameter.force_get()
    p2_param = p2.as_parameter_operatable.force_get().as_parameter.force_get()
    assert frozenset({p1_param, p2_param}) in pairs


def test_get_anticorrelated_pairs_multi():
    """
    Not(Correlated(p1, p2, p3)) should create all pairwise anticorrelated pairs.
    """
    from faebryk.libs.picker.picker import _get_anticorrelated_pairs

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)
    p3 = E.parameter_op(units=E.U.Ohm)

    E.not_(E.correlated(p1, p2, p3))
    pairs = _get_anticorrelated_pairs(tg)

    assert len(pairs) == 3

    p1_param = p1.as_parameter_operatable.force_get().as_parameter.force_get()
    p2_param = p2.as_parameter_operatable.force_get().as_parameter.force_get()
    p3_param = p3.as_parameter_operatable.force_get().as_parameter.force_get()

    assert frozenset({p1_param, p2_param}) in pairs
    assert frozenset({p1_param, p3_param}) in pairs
    assert frozenset({p2_param, p3_param}) in pairs


def test_not_correlated_doesnt_group():
    """
    Not(Correlated(p1, p2)) should not itself cause parameters to be grouped.
    Two independent parameters with Not(Correlated) should remain separate.
    """
    from faebryk.libs.picker.picker import find_independent_groups, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    r1_resistance = app.r1.get().resistance.get().can_be_operand.get()
    r2_resistance = app.r2.get().resistance.get().can_be_operand.get()

    E.not_(E.correlated(r1_resistance, r2_resistance))

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    assert len(groups) == 2


def test_find_groups_transitive_override():
    """
    Not(Correlated(p1, p3)) should break transitive chain even when
    p1-p2 and p2-p3 are expression-related.
    """
    from faebryk.libs.picker.picker import find_independent_groups, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()
        r3 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    r1_r = app.r1.get().resistance.get().can_be_operand.get()
    r2_r = app.r2.get().resistance.get().can_be_operand.get()
    r3_r = app.r3.get().resistance.get().can_be_operand.get()

    # Relate r1 and r2
    E.is_subset(
        E.add(r1_r, r2_r),
        E.lit_op_range(((1000, E.U.Ohm), (2000, E.U.Ohm))),
        assert_=True,
    )

    # Relate r2 and r3
    E.is_subset(
        E.add(r2_r, r3_r),
        E.lit_op_range(((1000, E.U.Ohm), (2000, E.U.Ohm))),
        assert_=True,
    )

    # Break transitive relationship
    E.not_(E.correlated(r1_r, r3_r))

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    pickables = list(tree.keys())
    r1_pickable = next(p for p in pickables if p.get_pickable_node() == app.r1.get())
    r3_pickable = next(p for p in pickables if p.get_pickable_node() == app.r3.get())

    for group in groups:
        assert {r1_pickable, r3_pickable} not in group


@pytest.mark.usefixtures("setup_project_config")
def test_infer_uncorrelated_params():
    """
    _infer_uncorrelated_params should create Not(Correlated) for all picking params.
    """
    from faebryk.libs.picker.picker import (
        _get_anticorrelated_pairs,
        _infer_uncorrelated_params,
        get_pick_tree,
    )

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()
        r3 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    tree = get_pick_tree(app)

    pairs_before = _get_anticorrelated_pairs(tg)
    assert len(pairs_before) == 0
    _infer_uncorrelated_params(tree)

    # After inference, should have pairs for all picking params
    pairs_after = _get_anticorrelated_pairs(tg)
    assert len(pairs_after) > 0
