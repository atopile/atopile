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
from faebryk.libs.picker.picker import PickedPart, PickError, pick_parts_recursively
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
    pick_parts_recursively(module, solver)

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

    pick_parts_recursively(module, Solver())

    assert module.has_trait(F.Pickable.has_part_picked)


@pytest.mark.usefixtures("setup_project_config")
def test_no_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(module, fabll.is_module)
    fabll.Traits.create_and_add_instance_to(module, F.has_part_removed)

    pick_parts_recursively(module, Solver())

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
            F.Literals.Numbers(resistance_op.get_obj_raw().instance),
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

    pick_parts_recursively(module, Solver())

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
    pick_parts_recursively(led, solver)

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
        pick_parts_recursively(app, solver)

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

    pick_parts_recursively(app, solver)

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
    pick_parts_recursively(cap, solver)

    assert cap.has_trait(F.Pickable.has_part_picked)


def test_get_anticorrelated_pairs():
    """
    Not(Correlated(...)) should create pairwise anticorrelated pairs.
    """
    from faebryk.core.solver.utils import MutatorUtils

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)
    p3 = E.parameter_op(units=E.U.Ohm)

    E.not_(E.correlated(p1, p2, p3), assert_=True)
    pairs = MutatorUtils.get_anticorrelated_pairs(tg)

    # 3 params -> 3 pairwise combinations
    assert len(pairs) == 3

    p1_param = p1.as_parameter_operatable.force_get().as_parameter.force_get()
    p2_param = p2.as_parameter_operatable.force_get().as_parameter.force_get()
    p3_param = p3.as_parameter_operatable.force_get().as_parameter.force_get()

    assert frozenset({p1_param, p2_param}) in pairs
    assert frozenset({p1_param, p3_param}) in pairs
    assert frozenset({p2_param, p3_param}) in pairs


@pytest.mark.usefixtures("setup_project_config")
def test_infer_uncorrelated_params():
    """
    _infer_uncorrelated_params should create Not(Correlated) for all picking params.
    """
    from faebryk.core.solver.utils import MutatorUtils
    from faebryk.libs.picker.picker import _infer_uncorrelated_params, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()
        r3 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    tree = get_pick_tree(app)

    pairs_before = MutatorUtils.get_anticorrelated_pairs(tg)
    assert len(pairs_before) == 0
    _infer_uncorrelated_params(tree)

    # After inference, should have pairs for all picking params
    pairs_after = MutatorUtils.get_anticorrelated_pairs(tg)
    assert len(pairs_after) > 0


def test_find_groups_two_independent_modules():
    """
    Two modules with no constraints between them should be in separate groups.
    """
    from faebryk.libs.picker.picker import find_independent_groups, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Constrain each independently with separate literals
    E.is_subset(
        app.r1.get().resistance.get().can_be_operand.get(),
        E.lit_op_range(((100, E.U.Ohm), (110, E.U.Ohm))),
        assert_=True,
    )
    E.is_subset(
        app.r2.get().resistance.get().can_be_operand.get(),
        E.lit_op_range(((200, E.U.Ohm), (220, E.U.Ohm))),
        assert_=True,
    )

    # Mark as uncorrelated
    E.not_(
        E.correlated(
            app.r1.get().resistance.get().can_be_operand.get(),
            app.r2.get().resistance.get().can_be_operand.get(),
        ),
        assert_=True,
    )

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    assert len(groups) == 2


def test_find_groups_two_connected_modules():
    """
    Two modules connected by a constraint should be in the same group.
    """
    from faebryk.libs.picker.picker import find_independent_groups, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    r1_r = app.r1.get().resistance.get().can_be_operand.get()
    r2_r = app.r2.get().resistance.get().can_be_operand.get()

    # Connect  via a shared constraint
    E.is_subset(
        E.add(r1_r, r2_r),
        E.lit_op_range(((300, E.U.Ohm), (330, E.U.Ohm))),
        assert_=True,
    )

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    assert len(groups) == 1


def test_find_groups_transitive_connectivity():
    """
    A-B connected and B-C connected means A,B,C should all be in same group.
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

    # Connect r1-r2
    E.is_subset(
        E.add(r1_r, r2_r),
        E.lit_op_range(((200, E.U.Ohm), (220, E.U.Ohm))),
        assert_=True,
    )

    # Connect r2-r3
    E.is_subset(
        E.add(r2_r, r3_r),
        E.lit_op_range(((300, E.U.Ohm), (330, E.U.Ohm))),
        assert_=True,
    )

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    # All three should be in one group due to transitive connectivity
    assert len(groups) == 1


def test_find_groups_mixed_connected_and_independent():
    """
    Three modules where r1-r2 are connected and r3 is independent.
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

    # Connect r1-r2
    E.is_subset(
        E.add(r1_r, r2_r),
        E.lit_op_range(((200, E.U.Ohm), (220, E.U.Ohm))),
        assert_=True,
    )

    # r3 is independent
    E.is_subset(
        r3_r,
        E.lit_op_range(((100, E.U.Ohm), (110, E.U.Ohm))),
        assert_=True,
    )

    # Mark all as uncorrelated
    E.not_(E.correlated(r1_r, r2_r, r3_r), assert_=True)

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    # Should be 2 groups: {r1, r2} and {r3}
    assert len(groups) == 2

    # Find which group has which pickables
    pickables = list(tree.keys())
    r1_pickable = next(p for p in pickables if p.get_pickable_node() == app.r1.get())
    r2_pickable = next(p for p in pickables if p.get_pickable_node() == app.r2.get())
    r3_pickable = next(p for p in pickables if p.get_pickable_node() == app.r3.get())

    # r1 and r2 should be in the same group
    r1_group = next(g for g in groups if r1_pickable in g)
    assert r2_pickable in r1_group

    # r3 should be in a different group
    r3_group = next(g for g in groups if r3_pickable in g)
    assert r3_group != r1_group


def test_non_constraining_expr_detection():
    """
    is_non_constraining should detect Not(Correlated(...)) predicates.
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)

    corr = E.correlated(p1, p2)
    not_corr = E.not_(corr)

    not_expr = not_corr.as_parameter_operatable.force_get().as_expression.force_get()

    assert not_expr.is_non_constraining(), (
        f"Failed to detect Not(Correlated(...)) predicate. "
        f"Expression type: {type(not_expr)}, operands: {list(not_expr.get_operands())}"
    )

    corr_expr = corr.as_parameter_operatable.force_get().as_expression.force_get()
    assert corr_expr.is_non_constraining(), "Failed to detect Correlated predicate"


def test_find_groups_array_modules_independent():
    """
    Multiple instances of similar module structures should be independent
    when they have no shared constraints. This mimics real-world cases like
    LED strips where each LED driver has its own resistor and capacitor.
    """
    from faebryk.libs.picker.picker import find_independent_groups, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    # Create a structure like: App with multiple "LED drivers", each having
    # a resistor and capacitor with independent constraints
    class _LedDriver(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        resistor = F.Resistor.MakeChild()
        capacitor = F.Capacitor.MakeChild()

    class _App(fabll.Node):
        # Multiple independent LED drivers
        driver1 = _LedDriver.MakeChild()
        driver2 = _LedDriver.MakeChild()
        driver3 = _LedDriver.MakeChild()
        # Plus a completely unrelated resistor
        standalone_resistor = F.Resistor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    # Constrain each component independently with DIFFERENT literal values
    # Driver 1
    E.is_subset(
        app.driver1.get().resistor.get().resistance.get().can_be_operand.get(),
        E.lit_op_range(((100, E.U.Ohm), (110, E.U.Ohm))),
        assert_=True,
    )
    E.is_subset(
        app.driver1.get().capacitor.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range(((100, E.U.nF), (110, E.U.nF))),
        assert_=True,
    )

    # Driver 2 - different values
    E.is_subset(
        app.driver2.get().resistor.get().resistance.get().can_be_operand.get(),
        E.lit_op_range(((200, E.U.Ohm), (220, E.U.Ohm))),
        assert_=True,
    )
    E.is_subset(
        app.driver2.get().capacitor.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range(((200, E.U.nF), (220, E.U.nF))),
        assert_=True,
    )

    # Driver 3 - different values
    E.is_subset(
        app.driver3.get().resistor.get().resistance.get().can_be_operand.get(),
        E.lit_op_range(((300, E.U.Ohm), (330, E.U.Ohm))),
        assert_=True,
    )
    E.is_subset(
        app.driver3.get().capacitor.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range(((300, E.U.nF), (330, E.U.nF))),
        assert_=True,
    )

    # Standalone resistor - completely independent
    E.is_subset(
        app.standalone_resistor.get().resistance.get().can_be_operand.get(),
        E.lit_op_range(((1000, E.U.Ohm), (1100, E.U.Ohm))),
        assert_=True,
    )

    # Mark all as uncorrelated
    all_params = [
        app.driver1.get().resistor.get().resistance.get().can_be_operand.get(),
        app.driver1.get().capacitor.get().capacitance.get().can_be_operand.get(),
        app.driver2.get().resistor.get().resistance.get().can_be_operand.get(),
        app.driver2.get().capacitor.get().capacitance.get().can_be_operand.get(),
        app.driver3.get().resistor.get().resistance.get().can_be_operand.get(),
        app.driver3.get().capacitor.get().capacitance.get().can_be_operand.get(),
        app.standalone_resistor.get().resistance.get().can_be_operand.get(),
    ]
    E.not_(E.correlated(*all_params), assert_=True)

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    assert len(groups) == 7, (
        f"Expected 7 independent groups but got {len(groups)}. "
        f"Components with independent constraints are being incorrectly grouped."
    )


def test_find_groups_nested_modules_with_shared_constraint():
    """
    When modules share a constraint (e.g., voltage divider), they should
    be grouped together, but unrelated modules should remain independent.
    """
    from faebryk.libs.picker.picker import find_independent_groups, get_pick_tree

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    E = BoundExpressions(g=g, tg=tg)

    class _App(fabll.Node):
        # Voltage divider - two resistors with shared constraint
        r_top = F.Resistor.MakeChild()
        r_bottom = F.Resistor.MakeChild()
        # Independent components
        decoupling_cap = F.Capacitor.MakeChild()
        filter_inductor = F.Inductor.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    r_top_r = app.r_top.get().resistance.get().can_be_operand.get()
    r_bottom_r = app.r_bottom.get().resistance.get().can_be_operand.get()

    # Voltage divider constraint: r_top + r_bottom within range
    E.is_subset(
        E.add(r_top_r, r_bottom_r),
        E.lit_op_range(((10000, E.U.Ohm), (11000, E.U.Ohm))),
        assert_=True,
    )

    # Independent constraints for cap and inductor
    E.is_subset(
        app.decoupling_cap.get().capacitance.get().can_be_operand.get(),
        E.lit_op_range(((100, E.U.nF), (110, E.U.nF))),
        assert_=True,
    )
    E.is_subset(
        app.filter_inductor.get().inductance.get().can_be_operand.get(),
        E.lit_op_range(((10, E.U.uH), (11, E.U.uH))),
        assert_=True,
    )

    # Mark unrelated params as uncorrelated
    E.not_(
        E.correlated(
            r_top_r,
            r_bottom_r,
            app.decoupling_cap.get().capacitance.get().can_be_operand.get(),
            app.filter_inductor.get().inductance.get().can_be_operand.get(),
        )
    )

    tree = get_pick_tree(app)
    groups = find_independent_groups(tree.keys())

    # Should have 3 groups:
    # - {r_top, r_bottom} (connected via voltage divider constraint)
    # - {decoupling_cap}
    # - {filter_inductor}
    assert len(groups) == 3, (
        f"Expected 3 groups but got {len(groups)}. "
        f"Voltage divider resistors should be grouped, others independent."
    )

    # Verify r_top and r_bottom are in the same group
    pickables = list(tree.keys())
    r_top_pickable = next(
        p for p in pickables if p.get_pickable_node() == app.r_top.get()
    )
    r_bottom_pickable = next(
        p for p in pickables if p.get_pickable_node() == app.r_bottom.get()
    )
    r_top_group = next(g for g in groups if r_top_pickable in g)
    assert r_bottom_pickable in r_top_group, (
        "Voltage divider resistors should be grouped"
    )
