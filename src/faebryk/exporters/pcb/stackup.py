# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.PCBManu import PCBLayer

logger = logging.getLogger(__name__)

# Maps from IntEnum numeric value to name
_LAYER_TYPE_NAMES: dict[int, str] = {e.value: e.name for e in PCBLayer.LayerType}
_MATERIAL_NAMES: dict[int, str] = {e.value: e.name for e in PCBLayer.Material}


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


def _enum_value_to_name(value: str | float, names: dict[int, str]) -> str:
    """Convert a numeric enum value to its name, or return the value as-is."""
    try:
        return names[int(value)]
    except ValueError, KeyError:
        return str(value)


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
            country_str = country.full_name if country else "-"
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
        layer_type_raw = _safe_get_enum(layer.layer_type.get())
        material_raw = _safe_get_enum(layer.material.get())
        layer_type = (
            _enum_value_to_name(layer_type_raw, _LAYER_TYPE_NAMES)
            if layer_type_raw != "-"
            else "-"
        )
        material = (
            _enum_value_to_name(material_raw, _MATERIAL_NAMES)
            if material_raw != "-"
            else "-"
        )
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


def _safe_get_thickness_mm_float(layer: PCBLayer) -> float | None:
    """Get layer thickness in mm as a float, or None if not set."""
    try:
        thickness_m = layer.thickness.get().force_extract_superset().get_single()
        return thickness_m * 1000
    except Exception:
        return None


def _safe_get_numeric_float(param: F.Parameters.NumericParameter) -> float | None:
    """Get numeric parameter value as float, or None if not set."""
    try:
        return param.force_extract_superset().get_single()
    except Exception:
        return None


def export_stackup_json(app: fabll.Node, path: Path) -> None:
    """
    Export the PCB stackup as a JSON file for the stackup viewer.
    """
    board_nodes = app.get_children(
        direct_only=False, types=fabll.Node, required_trait=F.PCBManu.is_pcb
    )
    if not board_nodes:
        logger.warning("No PCB found in design, skipping stackup JSON export")
        return

    board = board_nodes[0].get_trait(F.PCBManu.is_pcb)
    stackup_trait = board.get_stackup()
    layers = stackup_trait.get_layers()

    if not layers:
        logger.warning("Stackup has no layers, skipping stackup JSON export")
        return

    stackup_name = (
        st.split("::")[-1]
        if (st := stackup_trait.get_stackup().get_type_name())
        else "Unknown"
    )

    # Manufacturer info
    stackup_node = stackup_trait.get_stackup()
    manufacturer_nodes = stackup_node.get_children(
        direct_only=False, types=fabll.Node, required_trait=F.PCBManu.is_company
    )

    manufacturer = None
    if manufacturer_nodes:
        company = manufacturer_nodes[0].get_trait(F.PCBManu.is_company)
        manufacturer = {}
        try:
            manufacturer["name"] = company.get_company_name()
        except Exception:
            manufacturer["name"] = None
        try:
            country = company.get_country_code()
            manufacturer["country"] = country.full_name if country else None
        except Exception:
            manufacturer["country"] = None
        try:
            manufacturer["website"] = company.get_website()
        except Exception:
            manufacturer["website"] = None

    # Build layers list
    layer_list = []
    total_thickness = 0.0
    for i, layer in enumerate(layers):
        layer_type = _safe_get_enum(layer.layer_type.get())
        material = _safe_get_enum(layer.material.get())
        thickness = _safe_get_thickness_mm_float(layer)
        er = _safe_get_numeric_float(layer.relative_permittivity.get())
        loss = _safe_get_numeric_float(layer.loss_tangent.get())

        if thickness is not None:
            total_thickness += thickness

        layer_list.append(
            {
                "index": i,
                "layerType": _enum_value_to_name(layer_type, _LAYER_TYPE_NAMES)
                if layer_type != "-"
                else None,
                "material": _enum_value_to_name(material, _MATERIAL_NAMES)
                if material != "-"
                else None,
                "thicknessMm": round(thickness, 4) if thickness is not None else None,
                "relativePermittivity": round(er, 4) if er is not None else None,
                "lossTangent": round(loss, 6) if loss is not None else None,
            }
        )

    data = {
        "stackupName": stackup_name,
        "manufacturer": manufacturer,
        "layers": layer_list,
        "totalThicknessMm": round(total_thickness, 4),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    logger.info(f"Exported stackup JSON to {path}")
