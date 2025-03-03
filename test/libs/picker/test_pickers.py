# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING

import pytest

import faebryk.library._F as F
import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.picker.api.picker_lib import (
    NotCompatibleException,
    check_and_attach_candidates,
    get_candidates,
)
from faebryk.libs.picker.picker import PickError, pick_part_recursively
from faebryk.libs.sets.sets import EnumSet
from faebryk.libs.units import P
from faebryk.libs.util import groupby

sys.path.append(str(Path(__file__).parent))

if TYPE_CHECKING:
    from components import ComponentTestCase

try:
    from components import components_to_test
except ImportError:
    components_to_test = []

logger = logging.getLogger(__name__)

lcsc.LIB_FOLDER = Path(mkdtemp())


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
    module = case.module

    pre_pick_descriptive_properties = {}
    if module.has_trait(F.has_descriptive_properties):
        pre_pick_descriptive_properties = module.get_trait(
            F.has_descriptive_properties
        ).get_properties()

    if case.packages:
        module.add(F.has_package(*case.packages))

    # pick
    solver = DefaultSolver()
    pick_part_recursively(module, solver)

    # Check descriptive properties
    assert module.has_trait(F.has_part_picked)
    part = module.get_trait(F.has_part_picked).get_part()
    assert module.has_trait(F.has_descriptive_properties)
    properties = module.get_trait(F.has_descriptive_properties).get_properties()

    # Sanity check
    assert part.partno
    assert part.partno == properties["LCSC"]

    # Check LCSC & MFR
    for prop, value in pre_pick_descriptive_properties.items():
        assert properties.get(prop) == value

    # Check parameters
    # params = module.get_children(types=Parameter, direct_only=True)
    # TODO check that part params are equal (alias_is) to module params


def test_type_pick():
    module = F.Resistor()

    assert module.has_trait(F.is_pickable_by_type)
    assert module.has_trait(F.is_pickable)
    module.resistance.constrain_subset(L.Range.from_center_rel(100 * P.ohm, 0.1))

    pick_part_recursively(module, DefaultSolver())

    assert module.has_trait(F.has_part_picked)


def test_no_pick():
    module = Module()
    module.add(F.has_part_removed())

    pick_part_recursively(module, DefaultSolver())

    assert module.has_trait(F.has_part_picked)
    assert module.get_trait(F.has_part_picked).removed


def test_no_pick_inherit_override_none():
    class _CapInherit(F.Capacitor):
        pickable = None

    module = _CapInherit()

    assert not module.has_trait(F.is_pickable)

    pick_part_recursively(module, DefaultSolver())

    assert not module.has_trait(F.has_part_picked)


def test_no_pick_inherit_remove():
    class _(F.Capacitor):
        no_pick: F.has_part_removed

    module = _()

    pick_part_recursively(module, DefaultSolver())

    assert module.has_trait(F.has_part_picked)
    assert module.get_trait(F.has_part_picked).removed


@pytest.mark.usefixtures("setup_project_config")
def test_skip_self_pick():
    class _CapInherit(F.Capacitor):
        pickable = None
        inner: F.Capacitor

    module = _CapInherit()

    pick_part_recursively(module, DefaultSolver())

    assert not module.has_trait(F.has_part_picked)
    assert module.inner.has_trait(F.has_part_picked)


def test_pick_led_by_colour():
    color = F.LED.Color.YELLOW
    led = F.LED()
    led.color.constrain_subset(color)
    led.current.alias_is(L.Range.from_center_rel(10 * P.milliamp, 0.1))

    solver = DefaultSolver()
    pick_part_recursively(led, solver)

    assert led.has_trait(F.has_part_picked)
    solver.update_superset_cache(led)
    assert solver.inspect_get_known_supersets(led.color).is_subset_of(
        EnumSet.from_value(color)
    )


def test_reject_diode_for_led():
    led = F.LED()
    led.color.constrain_subset(F.LED.Color.YELLOW)
    led.current.alias_is(L.Range.from_center_rel(10 * P.milliamp, 0.1))

    diode = F.Diode()
    diode.current.alias_is(L.Range.from_center_rel(10 * P.milliamp, 0.1))

    solver = DefaultSolver()
    candidates = get_candidates(diode.get_tree(types=F.Diode), solver)
    with pytest.raises(NotCompatibleException):
        check_and_attach_candidates([(led, c) for c in candidates[diode]], solver)


def test_pick_error_group():
    root = L.Module()

    # Good luck finding a 10 gigafarad capacitor!
    c1 = F.Capacitor()
    c1.capacitance.alias_is(L.Range.from_center_rel(10 * P.GF, 0.1))

    c2 = F.Capacitor()
    c2.capacitance.alias_is(L.Range.from_center_rel(20 * P.GF, 0.1))

    root.add(c1)
    root.add(c2)

    solver = DefaultSolver()

    with pytest.raises(ExceptionGroup) as ex:
        pick_part_recursively(root, solver)

    assert len(ex.value.exceptions) == 1
    assert isinstance(ex.value.exceptions[0], PickError)


def test_pick_dependency_simple():
    class App(Module):
        r1: F.Resistor
        r2: F.Resistor

    app = App()

    solver = DefaultSolver()
    r1r = app.r1.resistance
    r2r = app.r2.resistance
    sum_lit = L.Range.from_center_rel(100 * P.kohm, 0.2)
    (r1r + r2r).constrain_subset(sum_lit)
    r1r.constrain_subset(sum_lit - r2r)
    r2r.constrain_subset(sum_lit - r1r)

    pick_part_recursively(app, solver)
