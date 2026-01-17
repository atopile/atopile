# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.libs.util import not_none, unique

logger = logging.getLogger(__name__)


def export_power_tree(
    app: fabll.Node,
    solver: Solver,
    *,
    mermaid_path: Path,
) -> None:
    power_interfaces = F.ElectricPower.bind_typegraph(tg=app.tg).get_instances()
    sink_implementors = fabll.Traits.get_implementors(
        F.is_sink.bind_typegraph(tg=app.tg), g=app.g
    )
    sinks = unique(
        [fabll.Traits(impl).get_obj_raw() for impl in sink_implementors],
        key=lambda node: node,
        custom_eq=lambda left, right: left.is_same(right),
    )
    mermaid_lines = ["graph TD"]
    node_counter = 0

    def escape_label(value: str) -> str:
        return value.replace('"', '\\"')

    for power_index, power in enumerate(power_interfaces):
        power_label = power.get_full_name()
        mermaid_lines.append(
            f'  subgraph power_{power_index}["{escape_label(power_label)}"]'
        )

        power_node_id = f"power_{power_index}_node_{node_counter}"
        node_counter += 1

        voltage_param = power.voltage.get()
        voltage_param_obj = not_none(
            voltage_param.try_cast(F.Parameters.NumericParameter)
        )
        voltage_literal = solver.inspect_get_known_supersets(
            voltage_param.get_trait(F.Parameters.is_parameter)
        )
        voltage_numbers = not_none(
            fabll.Traits(voltage_literal).get_obj_raw().try_cast(F.Literals.Numbers)
        )
        voltage = voltage_param_obj.format_literal_for_display(
            voltage_numbers, show_tolerance=True
        )
        voltage_intervals = voltage_numbers.get_numeric_set().get_intervals()
        voltage_interval = (
            voltage_intervals[0].get_min_value(),
            voltage_intervals[0].get_max_value(),
        )

        max_current_param = power.max_current.get()
        max_current_param_obj = not_none(
            max_current_param.try_cast(F.Parameters.NumericParameter)
        )
        max_current_literal = solver.inspect_get_known_supersets(
            max_current_param.get_trait(F.Parameters.is_parameter)
        )
        max_current_numbers = not_none(
            fabll.Traits(max_current_literal).get_obj_raw().try_cast(F.Literals.Numbers)
        )
        max_current = max_current_param_obj.format_literal_for_display(
            max_current_numbers, show_tolerance=True
        )

        max_power_param = power.max_power.get()
        max_power_param_obj = not_none(
            max_power_param.try_cast(F.Parameters.NumericParameter)
        )
        max_power_literal = solver.inspect_get_known_supersets(
            max_power_param.get_trait(F.Parameters.is_parameter)
        )
        max_power_numbers = not_none(
            fabll.Traits(max_power_literal).get_obj_raw().try_cast(F.Literals.Numbers)
        )
        max_power = max_power_param_obj.format_literal_for_display(
            max_power_numbers, show_tolerance=True
        )

        power_node_label = (
            f"{power_label}<br/>V={voltage}<br/>Imax={max_current}<br/>Pmax={max_power}"
        )
        mermaid_lines.append(
            f'    {power_node_id}["{escape_label(power_node_label)}"]'
        )

        if power.has_trait(F.is_source):
            hv_connected = list(
                power.hv.get().get_trait(fabll.is_interface).get_connected().keys()
            )
            lv_connected = list(
                power.lv.get().get_trait(fabll.is_interface).get_connected().keys()
            )

            for sink in sinks:
                if sink.is_same(power):
                    continue
                sink_leads = [
                    child
                    for child in sink.get_children(
                        direct_only=True,
                        types=fabll.Node,
                        required_trait=fabll.is_interface,
                    )
                ]
                if not sink_leads:
                    continue
                has_hv = any(
                    any(lead.is_same(connected) for connected in hv_connected)
                    for lead in sink_leads
                )
                has_lv = any(
                    any(lead.is_same(connected) for connected in lv_connected)
                    for lead in sink_leads
                )
                if not (has_hv and has_lv):
                    continue

                sink_node_id = f"power_{power_index}_node_{node_counter}"
                node_counter += 1

                sink_children = fabll.Node.with_names(
                    sink.get_children(
                        direct_only=True, types=fabll.Node, include_root=False
                    )
                )

                label_lines = [sink.get_full_name()]
                resistance_param = sink_children.get("resistance")
                resistance_interval = None
                sink_max_current_value = None
                sink_max_power_value = None
                if resistance_param is not None:
                    resistance_param_obj = not_none(
                        resistance_param.try_cast(F.Parameters.NumericParameter)
                    )
                    resistance_literal = solver.inspect_get_known_supersets(
                        resistance_param.get_trait(F.Parameters.is_parameter)
                    )
                    resistance_numbers = not_none(
                        fabll.Traits(resistance_literal)
                        .get_obj_raw()
                        .try_cast(F.Literals.Numbers)
                    )
                    resistance = resistance_param_obj.format_literal_for_display(
                        resistance_numbers, show_tolerance=True
                    )
                    resistance_intervals = (
                        resistance_numbers.get_numeric_set().get_intervals()
                    )
                    resistance_interval = (
                        resistance_intervals[0].get_min_value(),
                        resistance_intervals[0].get_max_value(),
                    )
                    label_lines.append(f"R={resistance}")
                else:
                    max_current_param = not_none(sink_children.get("max_current"))
                    max_current_param_obj = not_none(
                        max_current_param.try_cast(F.Parameters.NumericParameter)
                    )
                    max_current_literal = solver.inspect_get_known_supersets(
                        max_current_param.get_trait(F.Parameters.is_parameter)
                    )
                    max_current_numbers = not_none(
                        fabll.Traits(max_current_literal)
                        .get_obj_raw()
                        .try_cast(F.Literals.Numbers)
                    )
                    sink_max_current_value = max_current_param_obj.format_literal_for_display(
                        max_current_numbers, show_tolerance=True
                    )
                    label_lines.append(f"Imax={sink_max_current_value}")

                    max_power_param = not_none(sink_children.get("max_power"))
                    max_power_param_obj = not_none(
                        max_power_param.try_cast(F.Parameters.NumericParameter)
                    )
                    max_power_literal = solver.inspect_get_known_supersets(
                        max_power_param.get_trait(F.Parameters.is_parameter)
                    )
                    max_power_numbers = not_none(
                        fabll.Traits(max_power_literal)
                        .get_obj_raw()
                        .try_cast(F.Literals.Numbers)
                    )
                    sink_max_power_value = max_power_param_obj.format_literal_for_display(
                        max_power_numbers, show_tolerance=True
                    )
                    label_lines.append(f"Pmax={sink_max_power_value}")

                sink_label = "<br/>".join(label_lines)
                mermaid_lines.append(
                    f'    {sink_node_id}["{escape_label(sink_label)}"]'
                )

                if resistance_interval is not None:
                    vmin, vmax = voltage_interval
                    rmin, rmax = resistance_interval
                    current_min = vmin / rmax
                    current_max = vmax / rmin
                    current_label = (
                        F.Literals.Numbers.create_instance(g=power.g, tg=power.tg)
                        .setup_from_min_max(
                            min=current_min,
                            max=current_max,
                            unit=max_current_param_obj.force_get_units(),
                        )
                        .pretty_str(show_tolerance=True)
                    )
                    power_min = (vmin * vmin) / rmax
                    power_max = (vmax * vmax) / rmin
                    edge_power_label = (
                        F.Literals.Numbers.create_instance(g=power.g, tg=power.tg)
                        .setup_from_min_max(
                            min=power_min,
                            max=power_max,
                            unit=max_power_param_obj.force_get_units(),
                        )
                        .pretty_str(show_tolerance=True)
                    )
                else:
                    current_label = not_none(sink_max_current_value)
                    edge_power_label = not_none(sink_max_power_value)

                edge_label = f"I={current_label}, P={edge_power_label}"
                mermaid_lines.append(
                    f'    {power_node_id} -- "{escape_label(edge_label)}" --> '
                    f"{sink_node_id}"
                )

        mermaid_lines.append("  end")

    mermaid_path.parent.mkdir(parents=True, exist_ok=True)

    mermaid_path.write_text(
        "```mermaid\n" + "\n".join(mermaid_lines) + "\n```\n", encoding="utf-8"
    )
    logger.info("Wrote power tree to %s", mermaid_path)
