# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


def _parameter_value(param: fabll.Node, solver: Solver) -> str:
    if not param.has_trait(F.Parameters.is_parameter):
        return "unknown"
    literal = solver.inspect_get_known_supersets(
        param.get_trait(F.Parameters.is_parameter)
    )
    numbers = fabll.Traits(literal).get_obj_raw().try_cast(F.Literals.Numbers)
    if numbers is None:
        return literal.pretty_str()
    param_obj = param.try_cast(F.Parameters.NumericParameter)
    if param_obj is not None:
        return param_obj.format_literal_for_display(numbers, show_tolerance=True)
    return numbers.pretty_str(show_tolerance=True)


def _parameter_interval(
    param: fabll.Node, solver: Solver
) -> tuple[float, float] | None:
    if not param.has_trait(F.Parameters.is_parameter):
        return None
    literal = solver.inspect_get_known_supersets(
        param.get_trait(F.Parameters.is_parameter)
    )
    numbers = fabll.Traits(literal).get_obj_raw().try_cast(F.Literals.Numbers)
    if numbers is None:
        return None
    numeric_set = numbers.get_numeric_set()
    intervals = numeric_set.get_intervals()
    if len(intervals) != 1:
        return None
    interval = intervals[0]
    if not interval.is_finite():
        return None
    return interval.get_min_value(), interval.get_max_value()


def _escape_label(value: str) -> str:
    return value.replace('"', '\\"')


def _node_in_list(node: fabll.Node, nodes: list[fabll.Node]) -> bool:
    return any(node.is_same(other) for other in nodes)


def export_power_tree(
    app: fabll.Node,
    solver: Solver,
    *,
    mermaid_path: Path,
    json_path: Path,
) -> None:
    power_interfaces = F.ElectricPower.bind_typegraph(tg=app.tg).get_instances()
    resistors = F.Resistor.bind_typegraph(tg=app.tg).get_instances()
    ampere_unit = (
        F.Units.Ampere.bind_typegraph(tg=app.tg)
        .create_instance(g=app.g)
        .is_unit.get()
    )
    watt_unit = (
        F.Units.Watt.bind_typegraph(tg=app.tg)
        .create_instance(g=app.g)
        .is_unit.get()
    )

    mermaid_lines = ["graph TD"]
    json_buses: list[dict[str, object]] = []
    node_counter = 0

    for power_index, power in enumerate(power_interfaces):
        power_label = power.get_full_name()
        mermaid_lines.append(
            f'  subgraph power_{power_index}["{_escape_label(power_label)}"]'
        )

        power_node_id = f"power_{power_index}_node_{node_counter}"
        node_counter += 1

        voltage = _parameter_value(power.voltage.get(), solver)
        max_current = _parameter_value(power.max_current.get(), solver)
        max_power = _parameter_value(power.max_power.get(), solver)
        mermaid_lines.append(
            f'    {power_node_id}["{_escape_label(power_label)}'
            f'<br/>V={voltage}<br/>Imax={max_current}<br/>Pmax={max_power}"]'
        )

        hv_connected = list(
            power.hv.get().get_trait(fabll.is_interface).get_connected().keys()
        )
        lv_connected = list(
            power.lv.get().get_trait(fabll.is_interface).get_connected().keys()
        )

        edges_payload = []

        for resistor in resistors:
            resistor_leads = [
                child
                for child in resistor.get_children(
                    direct_only=True, types=fabll.Node, required_trait=fabll.is_interface
                )
            ]
            if not resistor_leads:
                continue
            has_hv = any(_node_in_list(lead, hv_connected) for lead in resistor_leads)
            has_lv = any(_node_in_list(lead, lv_connected) for lead in resistor_leads)
            if not (has_hv and has_lv):
                continue

            resistor_node_id = f"power_{power_index}_node_{node_counter}"
            node_counter += 1

            resistance = _parameter_value(resistor.resistance.get(), solver)
            mermaid_lines.append(
                f'    {resistor_node_id}["{_escape_label(resistor.get_full_name())}'
                f'<br/>R={resistance}"]'
            )

            current_label = "unknown"
            edge_power_label = "unknown"
            voltage_interval = _parameter_interval(power.voltage.get(), solver)
            resistance_interval = _parameter_interval(
                resistor.resistance.get(), solver
            )
            if voltage_interval is not None and resistance_interval is not None:
                vmin, vmax = voltage_interval
                rmin, rmax = resistance_interval
                if rmin > 0 and rmax > 0:
                    current_min = vmin / rmax
                    current_max = vmax / rmin
                    current_label = (
                        F.Literals.Numbers.create_instance(g=power.g, tg=power.tg)
                        .setup_from_min_max(
                            min=current_min, max=current_max, unit=ampere_unit
                        )
                        .pretty_str(show_tolerance=True)
                    )
                    power_min = (vmin * vmin) / rmax
                    power_max = (vmax * vmax) / rmin
                    edge_power_label = (
                        F.Literals.Numbers.create_instance(g=power.g, tg=power.tg)
                        .setup_from_min_max(
                            min=power_min, max=power_max, unit=watt_unit
                        )
                        .pretty_str(show_tolerance=True)
                    )

            mermaid_lines.append(
                f'    {power_node_id} -- "I={current_label}, P={edge_power_label}" --> '
                f"{resistor_node_id}"
            )

            edges_payload.append(
                {
                    "from": power.get_full_name(),
                    "to": resistor.get_full_name(),
                    "current": current_label,
                    "power": edge_power_label,
                }
            )

        mermaid_lines.append("  end")

        json_buses.append(
            {
                "name": power_label,
                "voltage": voltage,
                "max_current": max_current,
                "max_power": max_power,
                "edges": edges_payload,
            }
        )

    mermaid_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    mermaid_path.write_text("\n".join(mermaid_lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(json_buses, indent=2), encoding="utf-8")
    logger.info("Wrote power tree to %s and %s", mermaid_path, json_path)
