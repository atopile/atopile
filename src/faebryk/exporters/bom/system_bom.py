# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
System BOM exporter for multi-board designs.

Generates per-board BOMs and a system-level summary JSON that aggregates
component counts across all boards.
"""

import json
import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.bom.json_bom import make_json_bom, write_json_bom

logger = logging.getLogger(__name__)


def write_system_bom(
    app: fabll.Node,
    boards: list[fabll.Node],
    output_dir: Path,
    build_id: str | None = None,
) -> None:
    """
    Generate per-board BOMs and a system-level summary.

    For each board, collects pickable parts from its descendants and writes
    a per-board BOM JSON. Then writes a system summary with board cross-references
    and totals.

    Args:
        app: The top-level application node
        boards: List of board nodes detected in the design
        output_dir: Directory to write BOM files to
        build_id: Optional build ID for tracking
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    board_summaries: dict[str, dict] = {}
    all_part_ids: set[str] = set()
    total_components = 0

    for board in boards:
        board_name = board.get_name()

        # Collect picked parts for this board's descendants
        pickable_parts = [
            part
            for m in board.get_children(
                direct_only=False,
                types=fabll.Node,
                required_trait=F.Pickable.has_part_picked,
            )
            for part in [m.get_trait(F.Pickable.has_part_picked)]
            if not part.is_removed()
        ]

        # Write per-board BOM
        bom_filename = f"{board_name}.bom.json"
        bom_path = output_dir / bom_filename
        write_json_bom(pickable_parts, bom_path, build_id=build_id)

        # Collect stats
        bom_data = make_json_bom(pickable_parts, build_id=build_id)
        component_count = sum(c.quantity for c in bom_data.components)
        for comp in bom_data.components:
            all_part_ids.add(comp.id)

        total_components += component_count
        board_summaries[board_name] = {
            "bom_path": bom_filename,
            "component_count": component_count,
        }

        logger.info("Board '%s': %d components in BOM", board_name, component_count)

    # Write system summary
    system_summary = {
        "version": "1.0",
        "type": "system",
        "build_id": build_id,
        "boards": board_summaries,
        "total_unique_parts": len(all_part_ids),
        "total_components": total_components,
    }

    summary_path = output_dir / "system.bom.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(system_summary, f, indent=2)

    logger.info(
        "System BOM: %d boards, %d unique parts, %d total components → %s",
        len(boards),
        len(all_part_ids),
        total_components,
        summary_path,
    )
