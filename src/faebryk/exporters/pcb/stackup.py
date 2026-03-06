# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.PCBManu import PCBLayer

logger = logging.getLogger(__name__)


def _safe_get_thickness_mm(layer: PCBLayer) -> str:
    """Get layer thickness in mm, or '-' if not set."""
    try:
        thickness_m = layer.thickness.get().force_extract_superset().get_single()
        return f"{thickness_m * 1000:.4f}"
    except Exception:
        return "-"


def _safe_get_enum(param: F.Parameters.EnumParameter) -> str:
    """Get enum parameter value as string, or '-' if not set."""
    try:
        return param.force_extract_singleton()
    except Exception:
        return "-"


def _safe_get_numeric(param: F.Parameters.NumericParameter) -> str:
    """Get numeric parameter value, or '-' if not set."""
    try:
        return f"{param.force_extract_superset().get_single():.4f}"
    except Exception:
        return "-"


def export_stackup_markdown(app: fabll.Node, path: Path) -> None:
    """
    Export the PCB stackup as a Markdown table.

    Finds the is_pcb trait on the app, retrieves the stackup layers,
    and writes a markdown file with a table of layer properties.
    """
    board_nodes = app.get_children(
        direct_only=False, types=fabll.Node, required_trait=F.PCBManu.is_pcb
    )
    if not board_nodes:
        logger.warning("No PCB found in design, skipping stackup export")
        return

    board = board_nodes[0].get_trait(F.PCBManu.is_pcb)
    stackup_trait = board.get_stackup()
    layers = stackup_trait.get_layers()

    if not layers:
        logger.warning("Stackup has no layers, skipping stackup export")
        return

    stackup_name = (
        st.split("::")[-1]
        if (st := stackup_trait.get_stackup().get_type_name())
        else "Unknown"
    )

    # Find manufacturer info from the stackup's children
    stackup_node = stackup_trait.get_stackup()
    manufacturer_nodes = stackup_node.get_children(
        direct_only=False, types=fabll.Node, required_trait=F.PCBManu.is_company
    )

    lines: list[str] = []
    lines.append(f"# PCB Stackup: {stackup_name}")
    lines.append("")

    if manufacturer_nodes:
        company = manufacturer_nodes[0].get_trait(F.PCBManu.is_company)
        try:
            name = company.get_company_name()
        except Exception:
            name = "-"
        try:
            website = company.get_website()
        except Exception:
            website = None
        try:
            country = company.get_country_code()
            country_str = country.name if country else "-"
        except Exception:
            country_str = "-"

        lines.append(f"**Manufacturer:** {name}  ")
        lines.append(f"**Country:** {country_str}  ")
        if website:
            lines.append(f"**Website:** {website}  ")
        lines.append("")

    lines.append("| # | Layer Type | Material | Thickness (mm) | Er | Loss Tangent |")
    lines.append("|---|------------|----------|-----------------|-----|--------------|")

    for i, layer in enumerate(layers):
        layer_type = _safe_get_enum(layer.layer_type.get())
        material = _safe_get_enum(layer.material.get())
        thickness = _safe_get_thickness_mm(layer)
        er = _safe_get_numeric(layer.relative_permittivity.get())
        loss = _safe_get_numeric(layer.loss_tangent.get())

        lines.append(
            f"| {i} | {layer_type} | {material} | {thickness} | {er} | {loss} |"
        )

    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    logger.info(f"Exported stackup to {path}")
