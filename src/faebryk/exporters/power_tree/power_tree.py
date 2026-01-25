# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.libs.util import unique

logger = logging.getLogger(__name__)


def export_power_tree(
    app: fabll.Node,
    solver: Solver,
    *,
    mermaid_path: Path,
) -> None:
    power_interfaces = [
        power
        for power in F.ElectricPower.bind_typegraph(tg=app.tg).get_instances()
        if power.has_trait(F.is_source)
    ]

    sink_implementors = fabll.Traits.get_implementors(
        F.is_sink.bind_typegraph(tg=app.tg), g=app.g
    )
    sinks = unique(
        [fabll.Traits(impl).get_obj_raw() for impl in sink_implementors],
        key=lambda node: node,
        custom_eq=lambda left, right: left.is_same(right),
    )
    source_implementors = fabll.Traits.get_implementors(
        F.is_source.bind_typegraph(tg=app.tg), g=app.g
    )
    sources = unique(
        [fabll.Traits(impl).get_obj_raw() for impl in source_implementors],
        key=lambda node: node,
        custom_eq=lambda left, right: left.is_same(right),
    )

    def collect_relevant_operands(
        nodes: list[fabll.Node],
    ) -> list[F.Parameters.can_be_operand]:
        operands: set[F.Parameters.can_be_operand] = set()
        for node in nodes:
            for param in node.get_children(
                direct_only=False,
                types=fabll.Node,
                include_root=True,
                required_trait=F.Parameters.is_parameter,
            ):
                param_trait = param.get_trait(F.Parameters.is_parameter)
                operands.add(param_trait.as_operand.get())
        return list(operands)

    relevant_operands = collect_relevant_operands(sources + sinks)
    if relevant_operands:
        solver.simplify_for(*relevant_operands)
    else:
        logger.info("No relevant parameters found for power tree solver pass")
    mermaid_lines = [
        "graph TD",
        "  classDef source fill:#1b4b36,stroke:#5fd07f,stroke-width:2px,color:#d7f5df;",
        "  classDef sink fill:#4a1b1b,stroke:#f06b6b,stroke-width:2px,color:#f7dada;",
    ]
    node_counter = 0

    def escape_label(value: str) -> str:
        return value.replace('"', '\\"')

    def collect_electricals(node: fabll.Node) -> list[F.Electrical]:
        return node.get_children(
            direct_only=False,
            types=F.Electrical,
            include_root=True,
            required_trait=fabll.is_interface,
        )

    def build_bus_index(
        nodes: list[fabll.Node],
    ) -> dict[F.Electrical, F.Electrical]:
        electricals: set[F.Electrical] = set()
        for node in nodes:
            electricals.update(collect_electricals(node))

        buses = fabll.is_interface.group_into_buses(electricals)
        node_to_bus: dict[F.Electrical, F.Electrical] = {}
        for bus_root, members in buses.items():
            for member in members:
                node_to_bus[member] = bus_root

        return node_to_bus

    nodes_for_buses = sources + sinks
    node_to_bus = build_bus_index(nodes_for_buses)

    sink_electricals_map = {sink: collect_electricals(sink) for sink in sinks}

    for power_index, power in enumerate(power_interfaces):
        power_label = power.get_full_name()
        mermaid_lines.append(
            f'  subgraph power_{power_index}["{escape_label(power_label)}"]'
        )

        power_node_id = f"power_{power_index}_node_{node_counter}"
        node_counter += 1

        voltage = power.voltage.get().try_extract_superset().pretty_str()
        max_current = power.max_current.get().try_extract_superset().pretty_str()
        max_power = power.max_power.get().try_extract_superset().pretty_str()

        power_node_label = (
            f"{power_label}<br/>V={voltage}<br/>Imax={max_current}<br/>Pmax={max_power}"
        )

        mermaid_lines.append(f'{power_node_id}(("{escape_label(power_node_label)}"))')
        mermaid_lines.append(f"class {power_node_id} source")

        if power.has_trait(F.is_source):
            power_hv = power.hv.get()
            power_lv = power.lv.get()
            power_hv_bus = node_to_bus.get(power_hv)
            power_lv_bus = node_to_bus.get(power_lv)
            for sink in sinks:
                sink_buses = {
                    node_to_bus.get(electrical)
                    for electrical in sink_electricals_map[sink]
                }
                sink_buses.discard(None)
                if power_hv_bus not in sink_buses and power_lv_bus not in sink_buses:
                    continue
                sink_node_id = f"power_{power_index}_node_{node_counter}"
                node_counter += 1

                label_lines = [sink.get_full_name()]

                sink_label = "<br/>".join(label_lines)
                mermaid_lines.append(f'{sink_node_id}["{escape_label(sink_label)}"]')
                mermaid_lines.append(f"class {sink_node_id} sink")

                current_label = None
                edge_power_label = None

                edge_label = f"I={current_label}, P={edge_power_label}"
                mermaid_lines.append(f'{power_node_id} -- "{escape_label(edge_label)}" --> {sink_node_id}')

        mermaid_lines.append("  end")

    mermaid_path.parent.mkdir(parents=True, exist_ok=True)
    mermaid_path.write_text(
        "```mermaid\n" + "\n".join(mermaid_lines) + "\n```\n", encoding="utf-8"
    )
    logger.info("Wrote power tree to %s", mermaid_path)
