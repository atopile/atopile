# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
import re
from collections import defaultdict
from pathlib import Path
from typing import cast

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.exporters.netlist.netlist import T2Netlist
from faebryk.libs.kicad.fileformats import C_kicad_pcb_file
from faebryk.libs.library import L
from faebryk.libs.util import FuncDict, duplicates, get_key, groupby

logger = logging.getLogger(__name__)


def attach_random_designators(graph: Graph):
    """
    sorts nodes by path and then sequentially assigns designators
    """

    nodes = {n for n, _ in GraphFunctions(graph).nodes_with_trait(F.has_footprint)}

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

    nodes_sorted = sorted(nodes, key=lambda x: x.get_full_name())

    for n in nodes_sorted:
        if n.has_trait(F.has_designator):
            continue
        if not n.has_trait(F.has_designator_prefix):
            prefix = type(n).__name__
            logger.warning(f"Node {prefix} has no designator prefix")

        prefix = n.get_trait(F.has_designator_prefix).get_prefix()

        next_num = _get_first_hole(assigned[prefix])
        designator = f"{prefix}{next_num}"
        n.add(F.has_designator_defined(designator))

        assigned[prefix].append(next_num)

    no_designator = {n for n in nodes if not n.has_trait(F.has_designator)}
    assert not no_designator

    dupes = duplicates(nodes, lambda n: n.get_trait(F.has_designator).get_designator())
    assert not dupes, f"Duplcicate designators: {dupes}"


def override_names_with_designators(graph: Graph):
    for n, t in GraphFunctions(graph).nodes_with_trait(F.has_designator):
        name = t.get_designator()
        if n.has_trait(F.has_overriden_name):
            logger.warning(
                f"Renaming: {n.get_trait(F.has_overriden_name).get_name()} -> {name}"
            )
        n.add(F.has_overriden_name_defined(name))


def attach_hierarchical_designators(graph: Graph):
    # TODO
    raise NotImplementedError()


def load_designators_from_netlist(
    graph: Graph, t2_netlist_comps: dict[str, T2Netlist.Component]
):
    designators: dict[str, str] = {
        comp.properties["atopile_address"]: comp.name
        for comp in t2_netlist_comps.values()
        if "atopile_address" in comp.properties
    }

    matched_nodes = {
        node_name: (n, designators[node_name])
        for n, node_name in graph.nodes_by_names(designators.keys())
    }

    for _, (n, designator) in matched_nodes.items():
        logger.debug(f"Matched {n} to {designator}")
        n.add(F.has_designator_defined(designator))

    logger.info(f"Matched {len(matched_nodes)}/{len(designators)} designators")
    nomatch = {
        d: get_key(designators, d)
        for d in (set(designators.values()) - {d for _, d in matched_nodes.values()})
    }
    if nomatch:
        logger.info(f"Could not match: {pprint.pformat(nomatch, indent=4)}")


def replace_faebryk_names_with_designators_in_kicad_pcb(graph: Graph, pcbfile: Path):
    logger.info("Load PCB")
    pcb = C_kicad_pcb_file.loads(pcbfile)
    pcb.dumps(pcbfile.with_suffix(".bak"))

    pattern = re.compile(r"^(.*)\[[^\]]*\]$")
    translation = {
        n.get_full_name(): t.get_name()
        for n, t in GraphFunctions(graph).nodes_with_trait(F.has_overriden_name)
    }

    for fp in pcb.kicad_pcb.footprints:
        ref_prop = fp.propertys["Reference"]
        ref = ref_prop.value
        m = pattern.match(ref)
        if not m:
            logger.warning(f"Could not match {ref}")
            continue
        name = m.group(1)
        if name not in translation:
            logger.warning(f"Could not translate {name}")
            continue
        logger.info(f"Translating {name} to {translation[name]}")
        ref_prop.value = translation[name]

    pcb.dumps(pcbfile)


def attach_designators(designators: FuncDict[L.Node, str]):
    for node, designator in designators.items():
        node.add(F.has_designator_defined(designator))
