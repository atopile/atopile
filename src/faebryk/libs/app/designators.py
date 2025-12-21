# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from collections import defaultdict

from natsort import natsorted

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.libs.exceptions import UserResourceException
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.util import duplicates, md_list

logger = logging.getLogger(__name__)


def attach_random_designators(tg: fbrk.TypeGraph):
    """
    Assigns sequential designators (R1, R2, C1, etc.) to components.

    Components with has_designator_prefix get a has_designator trait if missing,
    then any component without a designator value gets one assigned.
    """

    def _get_first_available_number(used: list[int]) -> int:
        """Find the first gap in the sequence, or the next number after the highest."""
        sorted_used = sorted(used)
        for i, num in enumerate(sorted_used):
            if i + 1 != num:
                return i + 1
        return len(used) + 1

    # Step 1: Ensure all components with a prefix also have a has_designator trait
    components_with_prefix = fabll.Traits.get_implementor_objects(
        F.has_designator_prefix.bind_typegraph(tg)
    )
    for component in components_with_prefix:
        if not component.has_trait(F.has_designator):
            fabll.Traits.create_and_add_instance_to(component, F.has_designator)

    # Step 2: Get all components that have has_designator trait
    all_components_with_designator = fabll.Traits.get_implementor_objects(
        F.has_designator.bind_typegraph(tg)
    )
    # Sort by name only (not by designator) for stable ordering
    components_sorted = natsorted(
        all_components_with_designator,
        key=lambda c: c.get_full_name(include_uuid=False) or "",
    )

    # Step 3: Parse existing designators to track which numbers are used per prefix
    pattern = re.compile(r"([A-Z]+)([0-9]+)")
    assigned: dict[str, list[int]] = defaultdict(list)

    for component in components_sorted:
        designator_trait = component.get_trait(F.has_designator)
        existing = designator_trait.get_designator()
        if existing and (match := pattern.match(existing)):
            prefix = match.group(1)
            number = int(match.group(2))
            assigned[prefix].append(number)

    # Step 4: Assign designators to components that don't have one yet
    for component in components_sorted:
        designator_trait = component.get_trait(F.has_designator)
        existing_designator = designator_trait.get_designator()

        # Skip if already has a designator
        if existing_designator is not None:
            continue

        # Get prefix from has_designator_prefix trait, or use class name as fallback
        if component.has_trait(F.has_designator_prefix):
            prefix = component.get_trait(F.has_designator_prefix).get_prefix()
        else:
            prefix = type(component).__name__
            logger.warning(
                f"Component {component} has no designator prefix, using {prefix}"
            )

        # Assign next available number for this prefix
        next_num = _get_first_available_number(assigned[prefix])
        designator = f"{prefix}{next_num}"

        # Double-check that designator wasn't set between check and assignment
        # (shouldn't happen, but defensive programming)
        if designator_trait.get_designator() is not None:
            continue

        logger.info(f"Setting designator {designator} for {component}")
        designator_trait.setup(designator)
        assigned[prefix].append(next_num)

    # Step 5: Verify all designators are set and unique
    all_designators = [
        component.get_trait(F.has_designator).get_designator()
        for component in all_components_with_designator
    ]

    logger.info(f"{len(all_designators)} designators assigned")

    missing = [d for d in all_designators if d is None]
    assert not missing, f"Components without designators: {missing}"

    dupes = duplicates(all_designators, lambda d: d)
    assert not dupes, f"Duplicate designators: {md_list(dupes, recursive=True)}"


def load_kicad_pcb_designators(
    tg: fbrk.TypeGraph, attach: bool = False
) -> dict[fabll.Node, str]:
    """Load designators from kicad pcb footprints and attach them to the nodes."""

    def _get_reference(fp: kicad.pcb.Footprint):
        return Property.try_get_property(fp.propertys, "Reference")

    traits = fabll.Traits.get_implementors(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint.bind_typegraph(tg)
    )
    if not traits:
        return {}

    # Use map_footprints to get module->footprint mapping, then iterate sorted
    transformer = traits[0].get_transformer()
    pcb = transformer.pcb
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

    footprint_map = PCB_Transformer.map_footprints(tg, pcb)

    # Sort modules by atopile_address / full_name for deterministic iteration
    modules_sorted = natsorted(
        footprint_map.keys(),
        key=lambda m: m.get_full_name(include_uuid=False) or "",
    )

    known_designators: dict[fabll.Node, str] = {}
    for module in modules_sorted:
        fp = footprint_map[module]
        if ref := _get_reference(fp):
            known_designators[module] = ref
    if attach:
        if dups := duplicates(known_designators, lambda x: known_designators[x]):
            dups_fmt = {k: [f"`{m}`" for m in v] for k, v in dups.items()}
            raise UserResourceException(
                f"Duplicate designators found in layout:\n"
                f"{md_list(dups_fmt, recursive=True)}"
            )
        for node, designator in known_designators.items():
            if node.has_trait(F.has_designator):
                node.get_trait(F.has_designator).setup(designator)
            else:
                fabll.Traits.create_and_add_instance_to(node, F.has_designator).setup(
                    designator
                )

    return known_designators


def test_attach_random_designators():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestComponent(fabll.Node):
        is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        has_designator_prefix_ = fabll.Traits.MakeEdge(
            F.has_designator_prefix.MakeChild(prefix="TEST")
        )

    test_component_1 = TestComponent.bind_typegraph(tg).create_instance(g=g)
    test_component_2 = TestComponent.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(test_component_2, F.has_designator).setup(
        designator="COMPONENT2"
    )

    attach_random_designators(tg)

    assert test_component_1.get_trait(F.has_designator).get_designator() == "TEST1"
    assert test_component_2.get_trait(F.has_designator).get_designator() == "COMPONENT2"


def test_load_kicad_pcb_designators():
    from src.faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from src.faebryk.libs.test.fileformats import PCBFILE

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
    fp = pcb.footprints[1]

    class TestComponent(fabll.Node):
        is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    class TestApp(fabll.Node):
        component = TestComponent.MakeChild()

    test_app = TestApp.bind_typegraph(tg).create_instance(g=g)

    transformer = PCB_Transformer(pcb=pcb, app=test_app)

    fabll.Traits.create_and_add_instance_to(
        test_app.component.get(), F.KiCadFootprints.has_associated_kicad_pcb_footprint
    ).setup(fp, transformer)

    load_kicad_pcb_designators(tg, attach=True)

    assert test_app.component.get().get_trait(F.has_designator).get_designator() == "R1"
