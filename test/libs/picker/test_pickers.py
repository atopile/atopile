# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Callable

import pytest

import faebryk.library._F as F
import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.defaultsolver import DefaultSolver
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB
from faebryk.libs.picker.jlcpcb.pickers import add_jlcpcb_pickers
from faebryk.libs.picker.picker import has_part_picked, pick_part_recursively

sys.path.append(str(Path(__file__).parent))

try:
    from components import ComponentTestCase, components_to_test
except ImportError:
    components_to_test = []

logger = logging.getLogger(__name__)

lcsc.LIB_FOLDER = Path(mkdtemp())


def test_load_components():
    assert components_to_test, "Failed to load components"


@dataclass
class PickerTestCase:
    add_pickers_fn: Callable[[Module], None]
    check_skip: Callable[[], Any] = lambda: False


def is_db_available():
    return JLCPCB_DB.config.db_path.exists()


pickers = [
    PickerTestCase(
        add_jlcpcb_pickers,
        lambda: None if is_db_available() else pytest.skip("DB not available"),
    ),
    PickerTestCase(add_api_pickers),
]


@pytest.mark.skipif(components_to_test is None, reason="Failed to load components")
@pytest.mark.parametrize(
    "case,picker",
    [(m, p) for p in pickers for m in components_to_test],
    ids=[
        f"{p.add_pickers_fn.__name__.split('_')[1]}"
        "-"
        f"{type(m.module).__name__}[{components_to_test.index(m)}]"
        for p in pickers
        for m in components_to_test
    ],
)
def test_pick_module(case: ComponentTestCase, picker: PickerTestCase):
    picker.check_skip()
    module = case.module
    picker.add_pickers_fn(module)

    pre_pick_descriptive_properties = {}
    if module.has_trait(F.has_descriptive_properties):
        pre_pick_descriptive_properties = module.get_trait(
            F.has_descriptive_properties
        ).get_properties()

    if case.footprint:
        module.add(F.has_footprint_requirement_defined(case.footprint))

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
    params = module.get_children(types=Parameter, direct_only=True)
    for param in params:
        # Test if all params are aliased to Literal
        param.get_literal()
    # TODO check that part params are equal (alias_is) to module params

    # Check footprint
    fp = module.get_trait(F.has_footprint)
    kicad_fp = fp.get_trait(F.has_kicad_footprint)
    assert len(kicad_fp.get_pin_names()) == case.footprint[0][1]
    # TODO check footprint is correct


@pytest.fixture(autouse=True)
def cleanup_db():
    # Run test first
    yield
    # in test atexit not triggered, thus need to close DB manually
    JLCPCB_DB.close()
