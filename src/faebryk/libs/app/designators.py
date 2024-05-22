# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
import re
from collections import defaultdict
from pathlib import Path
from typing import cast

from faebryk.core.graph import Graph
from faebryk.core.util import (
    get_all_highest_parents_graph,
    get_all_nodes_graph,
)
from faebryk.exporters.netlist.netlist import Component
from faebryk.library.has_designator import has_designator
from faebryk.library.has_designator_defined import has_designator_defined
from faebryk.library.has_designator_prefix import has_designator_prefix
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined
from faebryk.libs.util import duplicates, get_key, groupby

logger = logging.getLogger(__name__)


def attach_random_designators(graph: Graph):
    """
    sorts nodes by path and then sequentially assigns designators
    """

    nodes = {n for n in get_all_nodes_graph(graph.G) if n.has_trait(has_footprint)}

    in_use = {
        n.get_trait(has_designator).get_designator()
        for n in nodes
        if n.has_trait(has_designator)
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

    nodes_sorted = sorted(nodes, key=lambda x: x.get_full_name())

    for n in nodes_sorted:
        if n.has_trait(has_designator):
            continue
        if not n.has_trait(has_designator_prefix):
            prefix = type(n).__name__
            logger.warning(f"Node {prefix} has no designator prefix")

        prefix = n.get_trait(has_designator_prefix).get_prefix()

        next_num = _get_first_hole(assigned[prefix])
        designator = f"{prefix}{next_num}"
        n.add_trait(has_designator_defined(designator))

        assigned[prefix].append(next_num)

    no_designator = {n for n in nodes if not n.has_trait(has_designator)}
    assert not no_designator

    dupes = duplicates(nodes, lambda n: n.get_trait(has_designator).get_designator())
    assert not dupes, f"Duplcicate designators: {dupes}"


def override_names_with_designators(graph: Graph):
    nodes = {n for n in get_all_nodes_graph(graph.G) if n.has_trait(has_designator)}

    for n in nodes:
        if not n.has_trait(has_designator):
            continue
        name = n.get_trait(has_designator).get_designator()
        if n.has_trait(has_overriden_name):
            logger.warning(
                f"Renaming: {n.get_trait(has_overriden_name).get_name()} -> {name}"
            )
        n.add_trait(has_overriden_name_defined(name))


def attach_hierarchical_designators(graph: Graph):
    root_modules = get_all_highest_parents_graph(graph.G)

    # TODO
    raise NotImplementedError()

    for m in root_modules:
        ...


def load_designators_from_netlist(graph: Graph, t2_netlist_comps: dict[str, Component]):
    designators: dict[str, str] = {
        comp.properties["faebryk_name"]: comp.name
        for comp in t2_netlist_comps.values()
        if "faebryk_name" in comp.properties
    }

    matched_nodes = {
        node_name: (n, designators[node_name])
        for n in get_all_nodes_graph(graph.G)
        if (node_name := n.get_full_name()) in designators
    }

    for node_name, (n, designator) in matched_nodes.items():
        logger.debug(f"Matched {n} to {designator}")
        n.add_trait(has_designator_defined(designator))

    logger.info(f"Matched {len(matched_nodes)}/{len(designators)} designators")
    nomatch = {
        d: get_key(designators, d)
        for d in (set(designators.values()) - {d for _, d in matched_nodes.values()})
    }
    if nomatch:
        logger.info(f"Could not match: {pprint.pformat(nomatch, indent=4)}")


def replace_faebryk_names_with_designators_in_kicad_pcb(graph: Graph, pcbfile: Path):
    from faebryk.libs.kicad.pcb import PCB

    logger.info("Load PCB")
    pcb = PCB.load(pcbfile)
    pcb.dump(pcbfile.with_suffix(".bak"))

    pattern = re.compile(r"^(.*)\[[^\]]*\]$")
    translation = {
        n.get_full_name(): n.get_trait(has_overriden_name).get_name()
        for n in get_all_nodes_graph(graph.G)
        if n.has_trait(has_overriden_name)
    }

    for fp in pcb.footprints:
        ref = fp.reference.text
        m = pattern.match(ref)
        if not m:
            logger.warning(f"Could not match {ref}")
            continue
        name = m.group(1)
        if name not in translation:
            logger.warning(f"Could not translate {name}")
            continue
        logger.info(f"Translating {name} to {translation[name]}")
        fp.reference.text = translation[name]

    pcb.dump(pcbfile)
