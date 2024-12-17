# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path
from tempfile import mkdtemp

import pytest

import faebryk.library._F as F
import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.picker.picker import has_part_picked, pick_part_recursively
from faebryk.libs.util import groupby

sys.path.append(str(Path(__file__).parent))

try:
    from components import ComponentTestCase, components_to_test
except ImportError:
    components_to_test = []

logger = logging.getLogger(__name__)

lcsc.LIB_FOLDER = Path(mkdtemp())


def test_load_components():
    assert components_to_test, "Failed to load components"


def _make_id(m: ComponentTestCase):
    if m.override_test_name:
        module_name = m.override_test_name
    else:
        module_name = type(m.module).__name__
        gouped_by_type = groupby(components_to_test, lambda c: type(c.module))
        group_for_module = gouped_by_type[type(m.module)]
        if len(group_for_module) > 1:
            module_name += f"[{group_for_module.index(m)}]"

    return module_name


@pytest.mark.skipif(components_to_test is None, reason="Failed to load components")
@pytest.mark.parametrize(
    "case",
    components_to_test,
    ids=[_make_id(m) for m in components_to_test],
)
def test_pick_module(case: ComponentTestCase):
    module = case.module

    pre_pick_descriptive_properties = {}
    if module.has_trait(F.has_descriptive_properties):
        pre_pick_descriptive_properties = module.get_trait(
            F.has_descriptive_properties
        ).get_properties()

    if case.packages:
        module.add(F.has_package_requirement(*case.packages))

    # pick
    solver = DefaultSolver()
    pick_part_recursively(module, solver)

    # Check descriptive properties
    assert module.has_trait(has_part_picked)
    part = module.get_trait(has_part_picked).get_part()
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
