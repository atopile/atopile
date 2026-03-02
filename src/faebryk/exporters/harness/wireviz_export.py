"""
Export harness data to WireViz YAML format.

WireViz is a tool for creating wiring harness documentation.
See: https://github.com/formatc1702/WireViz
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from faebryk.exporters.harness.harness_data import ConnectorInfo, HarnessData

logger = logging.getLogger(__name__)


def _gender_to_wireviz_subtype(gender: str | None) -> str | None:
    """Convert our gender string to WireViz subtype."""
    if gender == "plug":
        return "male"
    if gender == "receptacle":
        return "female"
    return None


def _pin_to_index(pin_name: str, connector: ConnectorInfo) -> int:
    """Convert a pin name to a 1-based index within the connector's pin list."""
    try:
        return connector.pin_names.index(pin_name) + 1
    except ValueError:
        # Fall back to parsing numeric suffix
        digits = "".join(c for c in pin_name if c.isdigit())
        return int(digits) if digits else 1


def export_wireviz_yaml(data: HarnessData, output_path: Path) -> None:
    """
    Export HarnessData to WireViz YAML format.

    Args:
        data: The extracted harness data.
        output_path: Path to write the YAML file.
    """
    lines: list[str] = []

    # Build connector lookup
    conn_by_name: dict[str, ConnectorInfo] = {c.name: c for c in data.connectors}

    # Connectors section
    if data.connectors:
        lines.append("connectors:")
        for conn in data.connectors:
            lines.append(f"  {conn.name}:")
            if conn.gender:
                subtype = _gender_to_wireviz_subtype(conn.gender)
                if subtype:
                    lines.append(f"    subtype: {subtype}")
            if conn.pin_names:
                pin_labels = ", ".join(conn.pin_names)
                lines.append(f"    pinlabels: [{pin_labels}]")

    # Cables section
    if data.cables:
        lines.append("")
        lines.append("cables:")
        for cable in data.cables:
            lines.append(f"  {cable.name}:")
            lines.append(f"    wirecount: {cable.wire_count}")
            if cable.length_m is not None:
                lines.append(f"    length: {cable.length_m}")

    # Connections section
    if data.connections:
        lines.append("")
        lines.append("connections:")

        # Group connections by (cable, from_connector, to_connector)
        group_key_type = tuple[str | None, str, str]
        grouped: dict[group_key_type, list] = defaultdict(list)
        for conn in data.connections:
            key = (conn.via_cable, conn.from_connector, conn.to_connector)
            grouped[key].append(conn)

        for (cable_name, from_conn_name, to_conn_name), conns in grouped.items():
            from_conn = conn_by_name.get(from_conn_name)
            to_conn = conn_by_name.get(to_conn_name)

            if cable_name:
                from_pins = []
                to_pins = []
                cable_wires = []

                for i, c in enumerate(conns):
                    from_idx = (
                        _pin_to_index(c.from_pin, from_conn)
                        if from_conn
                        else i + 1
                    )
                    to_idx = (
                        _pin_to_index(c.to_pin, to_conn) if to_conn else i + 1
                    )
                    from_pins.append(str(from_idx))
                    to_pins.append(str(to_idx))
                    cable_wires.append(str(i + 1))

                from_pins_str = ",".join(from_pins)
                to_pins_str = ",".join(to_pins)
                cable_wires_str = ",".join(cable_wires)

                lines.append(
                    f"  - [{from_conn_name}, [{from_pins_str}], "
                    f"{cable_name}, [{cable_wires_str}], "
                    f"{to_conn_name}, [{to_pins_str}]]"
                )
            else:
                # Direct connections (no cable)
                for c in conns:
                    from_idx = (
                        _pin_to_index(c.from_pin, from_conn)
                        if from_conn
                        else 1
                    )
                    to_idx = (
                        _pin_to_index(c.to_pin, to_conn) if to_conn else 1
                    )
                    lines.append(
                        f"  - [{c.from_connector}, [{from_idx}], "
                        f"{c.to_connector}, [{to_idx}]]"
                    )

    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote WireViz YAML to %s", output_path)
