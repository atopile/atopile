# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from collections import defaultdict

from natsort import natsorted

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserResourceException
from faebryk.core import graph
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.util import duplicates, md_list

logger = logging.getLogger(__name__)

# TODO rename designator -> part_designator
# TODO rename designator_prefix -> part_designator_prefix


def attach_random_designators(tg: fbrk.TypeGraph):
    """
    Assigns sequential designators (R1, R2, C1, etc.) to parts.

    Parts with has_designator_prefix get a has_designator trait if missing,
    then any part without a designator value gets one assigned.
    """

    def _get_first_available_number(used: list[int]) -> int:
        """Find the first gap in the sequence, or the next number after the highest."""
        sorted_used = sorted(used)
        for i, num in enumerate(sorted_used):
            if i + 1 != num:
                return i + 1
        return len(used) + 1

    parts = fabll.Traits.get_implementors(F.Pickable.has_part_picked.bind_typegraph(tg))
    part_modules = [p.get_sibling_trait(fabll.is_module) for p in parts]

    parts_with_prefix = {
        m: prefix.get_prefix()
        for m in part_modules
        if (prefix := m.try_get_sibling_trait(F.has_designator_prefix))
    }

    # Sort by name only (not by designator) for stable ordering
    part_modules_sorted = dict(
        natsorted(parts_with_prefix.items(), key=lambda c: c[0].get_module_locator())
    )

    assigned: dict[str, list[int]] = defaultdict(list)

    # Parse existing designators to track which numbers are used per prefix
    pattern = re.compile(r"([A-Z]+)([0-9]+)")
    for module in part_modules_sorted:
        if (designator_trait := module.try_get_sibling_trait(F.has_designator)) is None:
            continue
        # manual designator might match prefix or not
        existing = designator_trait.get_designator()
        if not (match := pattern.match(existing)):
            continue

        prefix = match.group(1)
        number = int(match.group(2))
        assigned[prefix].append(number)

    # Assign designators to components that don't have one yet
    for module, prefix in part_modules_sorted.items():
        if module.try_get_sibling_trait(F.has_designator):
            continue

        # Assign next available number for this prefix
        next_num = _get_first_available_number(assigned[prefix])
        designator = f"{prefix}{next_num}"

        module_name = module.get_module_locator()
        logger.info(f"Setting designator {designator}({prefix=}) to {module_name}")
        fabll.Traits.create_and_add_instance_to(
            module.get_obj(), F.has_designator
        ).setup(designator=designator)
        assigned[prefix].append(next_num)

    # Verify all designators are set and unique
    designators = fabll.Traits.get_implementors(F.has_designator.bind_typegraph(tg))

    logger.info(f"{sum(len(v) for v in assigned.values())} prefix designators assigned")

    dupes = duplicates(designators, lambda d: d.get_designator())
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


class TestAppDesignators:
    @staticmethod
    def test_attach_random_designators():
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _TestComponent(fabll.Node):
            is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            has_designator_prefix_ = fabll.Traits.MakeEdge(
                F.has_designator_prefix.MakeChild(prefix="TEST")
            )
            has_part_picked_ = fabll.Traits.MakeEdge(
                fabll._ChildField(F.Pickable.has_part_picked)
            )

        TC = _TestComponent.bind_typegraph(tg)

        test_component_1 = TC.create_instance(g=g)
        test_component_2 = TC.create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(
            test_component_2, F.has_designator
        ).setup(designator="COMPONENT2")

        attach_random_designators(tg)

        assert test_component_1.get_trait(F.has_designator).get_designator() == "TEST1"
        assert (
            test_component_2.get_trait(F.has_designator).get_designator()
            == "COMPONENT2"
        )

    @staticmethod
    def test_load_kicad_pcb_designators():
        from src.faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
        from src.faebryk.libs.test.fileformats import PCBFILE

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
        fp = pcb.footprints[1]

        class _TestComponent(fabll.Node):
            is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        class _TestApp(fabll.Node):
            component = _TestComponent.MakeChild()

        test_app = _TestApp.bind_typegraph(tg).create_instance(g=g)

        transformer = PCB_Transformer(pcb=pcb, app=test_app)

        fabll.Traits.create_and_add_instance_to(
            test_app.component.get(),
            F.KiCadFootprints.has_associated_kicad_pcb_footprint,
        ).setup(fp, transformer)

        load_kicad_pcb_designators(tg, attach=True)

        assert (
            test_app.component.get().get_trait(F.has_designator).get_designator()
            == "R1"
        )
