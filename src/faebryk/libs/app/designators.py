# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from collections import defaultdict

from natsort import natsorted

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
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
    components_with_designator = fabll.Traits.get_implementor_objects(
        F.has_designator.bind_typegraph(tg)
    )

    # Step 3: Parse existing designators to track which numbers are used per prefix
    pattern = re.compile(r"([A-Z]+)([0-9]+)")
    assigned: dict[str, list[int]] = defaultdict(list)

    for component in components_with_designator:
        designator_trait = component.get_trait(F.has_designator)
        existing = designator_trait.get_designator()
        if existing and (match := pattern.match(existing)):
            prefix = match.group(1)
            number = int(match.group(2))
            assigned[prefix].append(number)

    # Step 4: Assign designators to components that don't have one yet
    # Sort by name for deterministic ordering
    components_sorted = natsorted(
        components_with_designator,
        key=lambda c: c.get_full_name() or ""
    )

    for component in components_sorted:
        designator_trait = component.get_trait(F.has_designator)

        # Skip if already has a designator
        if designator_trait.get_designator() is not None:
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

        logger.info(f"Setting designator {designator} for {component}")
        designator_trait.setup(designator)
        assigned[prefix].append(next_num)

    # Step 5: Verify all designators are set and unique
    all_designators = [
        component.get_trait(F.has_designator).get_designator()
        for component in components_with_designator
    ]

    missing = [d for d in all_designators if d is None]
    assert not missing, f"Components without designators: {missing}"

    dupes = duplicates(all_designators, lambda d: d)
    assert not dupes, f"Duplicate designators: {md_list(dupes, recursive=True)}"


def load_designators(tg: fbrk.TypeGraph, attach: bool = False) -> dict[fabll.Node, str]:
    """
    Load designators from attached footprints and attach them to the nodes.
    """

    def _get_reference(fp: kicad.pcb.Footprint):
        return Property.try_get_property(fp.propertys, "Reference")

    def _get_pcb_designator(fp_trait: F.PCBTransformer.has_linked_kicad_footprint):
        fp = fp_trait.get_fp()
        if not fp.name:
            return None
        return _get_reference(fp)

    traits = fabll.Traits.get_implementors(
        F.PCBTransformer.has_linked_kicad_footprint.bind_typegraph(tg)
    )
    nodes_traits = {fabll.Traits(trait).get_obj_raw(): trait for trait in traits}

    known_designators = {
        node: ref
        for node, trait in nodes_traits.items()
        if (ref := _get_pcb_designator(trait)) is not None
        and not isinstance(node, F.Footprints.Footprint)
    }

    if attach:
        if dups := duplicates(known_designators, lambda x: known_designators[x]):
            dups_fmt = {k: [f"`{m}`" for m in v] for k, v in dups.items()}
            raise UserResourceException(
                f"Duplicate designators found in layout:\n"
                f"{md_list(dups_fmt, recursive=True)}"
            )
        for node, designator in known_designators.items():
            fabll.Traits.create_and_add_instance_to(node, F.has_designator).setup(
                designator
            )

    return known_designators
