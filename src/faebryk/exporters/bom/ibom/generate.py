"""Generate a self-contained interactive BOM viewer HTML file."""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from atopile.buildutil import get_ato_version, get_git_describe
from atopile.layout_server.pcb_manager import PcbManager
from faebryk.exporters.bom.json_bom import build_ref_to_bom_id, make_json_bom
from faebryk.library._F import Pickable

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent


def _round_floats(obj: object, decimals: int = 3) -> object:
    """Recursively round floats in a JSON-serializable structure."""
    if isinstance(obj, float):
        return round(obj, decimals)
    if isinstance(obj, dict):
        return {k: _round_floats(v, decimals) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v, decimals) for v in obj]
    return obj


def generate_ibom_html(
    pcb_path: Path,
    pickable_parts: list[Pickable.has_part_picked],
    output_path: Path,
    project_name: str = "",
    include_zones: bool = True,
) -> Path:
    """Generate a self-contained interactive BOM HTML file.

    Args:
        pcb_path: Path to the .kicad_pcb file.
        pickable_parts: List of picked part traits from the build.
        output_path: Where to write the .ibom.html file.
        project_name: Project name shown in the viewer header.
        include_zones: If True, include filled zone polygons (increases file size).

    Returns:
        The output path.
    """
    # Extract PCB render model
    pcb_mgr = PcbManager()
    pcb_mgr.load(pcb_path)
    render_model = pcb_mgr.get_render_model()
    pcb_data = render_model.model_dump()

    # Strip zones if not requested
    if not include_zones:
        pcb_data["zones"] = []

    pcb_data = _round_floats(pcb_data)

    # Generate BOM data
    bom = make_json_bom(pickable_parts)
    bom_data = asdict(bom)

    # Build cross-reference
    ref_to_bom_id = build_ref_to_bom_id(bom)

    # Combined data blob
    ibom_data = {
        "projectName": project_name or pcb_path.stem,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gitDescribe": get_git_describe(pcb_path),
        "atoVersion": get_ato_version(),
        "pcb": pcb_data,
        "bom": bom_data,
        "refToBomId": ref_to_bom_id,
    }

    data_json = json.dumps(ibom_data, separators=(",", ":"))
    # Escape </script> sequences to prevent XSS when embedded in <script> tags
    data_json = data_json.replace("</", r"<\/")

    # Read template and assets
    template_html = (_TEMPLATE_DIR / "template.html").read_text()
    renderer_js = (_TEMPLATE_DIR / "renderer.js").read_text()
    bom_ui_js = (_TEMPLATE_DIR / "bom_ui.js").read_text()
    styles_css = (_TEMPLATE_DIR / "styles.css").read_text()

    # Assemble self-contained HTML
    html = template_html
    html = html.replace("/* %%STYLES%% */", styles_css)
    html = html.replace("/* %%IBOM_DATA%% */", f"var ibomData = {data_json};")
    html = html.replace("/* %%RENDERER_JS%% */", renderer_js)
    html = html.replace("/* %%BOM_UI_JS%% */", bom_ui_js)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Wrote interactive BOM to {output_path}")
    return output_path
