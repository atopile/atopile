# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from collections import defaultdict
from typing import cast

from natsort import natsorted

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.exceptions import UserResourceException
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.util import duplicates, groupby, md_list

logger = logging.getLogger(__name__)


def attach_random_designators(tg: fbrk.TypeGraph):
    """
    Sorts nodes by path and then sequentially attaches designators

    This ensures that everything which has a footprint must have a designator.
    """

    nodes = fabll.Traits.get_implementors(F.has_footprint.bind_typegraph(tg))

    in_use = {
        n.get_trait(F.has_designator).get_designator()
        for n in nodes
        if n.has_trait(F.has_designator)
    }
    pattern = re.compile(r"([A-Z]+)([0-9]+)")

    groups = groupby(
        [(m.group(1), int(m.group(2))) for d in in_use if (m := pattern.match(d))],
        key=lambda x: x[0],
    )

    assigned = defaultdict(
        list,
        {k: cast(list[int], [num for _, num in v]) for k, v in groups.items()},
    )

    def _get_first_hole(used: list[int]):
        s_used = sorted(used)
        for i in range(len(used)):
            if i + 1 != s_used[i]:
                return i + 1
        return len(used) + 1

    nodes_sorted = natsorted(nodes, key=lambda x: x.get_full_name())

    for n in nodes_sorted:
        if n.has_trait(F.has_designator):
            continue
        if not n.has_trait(F.has_designator_prefix):
            prefix = type(n).__name__
            logger.warning(f"Node {prefix} has no designator prefix")
        else:
            prefix = n.get_trait(F.has_designator_prefix).get_prefix()

        next_num = _get_first_hole(assigned[prefix])
        designator = f"{prefix}{next_num}"
        fabll.Traits.create_and_add_instance_to(n, F.has_designator).setup(designator)

        assigned[prefix].append(next_num)

    no_designator = {n for n in nodes if not n.has_trait(F.has_designator)}
    assert not no_designator

    dupes = duplicates(nodes, lambda n: n.get_trait(F.has_designator).get_designator())
    assert not dupes, (
        f"Duplicate designators found in layout:\n{md_list(dupes, recursive=True)}"
    )


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
    nodes_traits = {trait.get_parent_force()[0]: trait for trait in traits}

    known_designators = {
        node: ref
        for node, trait in nodes_traits.items()
        if (ref := _get_pcb_designator(trait)) is not None
        and not isinstance(node, F.Footprint)
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
