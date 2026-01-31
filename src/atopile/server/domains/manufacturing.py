"""
Manufacturing domain logic.

Handles git status checks, build output retrieval, cost estimation,
and file export for manufacturing.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from atopile.server.domains import cost_estimation
from faebryk.libs.util import has_uncommitted_changes

log = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Git status result."""

    has_uncommitted_changes: bool
    changed_files: list[str]


@dataclass
class BuildOutputs:
    """Paths to build output files."""

    gerbers: Optional[str] = None
    bom_json: Optional[str] = None
    bom_csv: Optional[str] = None
    pick_and_place: Optional[str] = None
    step: Optional[str] = None
    glb: Optional[str] = None
    kicad_pcb: Optional[str] = None
    kicad_sch: Optional[str] = None
    pcb_summary: Optional[str] = None


@dataclass
class CostBreakdown:
    """Detailed cost breakdown."""

    base_cost: float
    area_cost: float = 0.0
    layer_cost: float = 0.0


@dataclass
class ComponentsBreakdown:
    """Components cost breakdown."""

    unique_parts: int
    total_parts: int


@dataclass
class AssemblyBreakdown:
    """Assembly cost breakdown."""

    base_cost: float
    per_part_cost: float


@dataclass
class CostEstimate:
    """Manufacturing cost estimate."""

    pcb_cost: float
    components_cost: float
    assembly_cost: float
    total_cost: float
    currency: str
    quantity: int
    pcb_breakdown: Optional[CostBreakdown] = None
    components_breakdown: Optional[ComponentsBreakdown] = None
    assembly_breakdown: Optional[AssemblyBreakdown] = None


def check_git_status(project_root: str) -> GitStatus:
    """
    Check git status for uncommitted changes.

    Uses faebryk.libs.util.has_uncommitted_changes() for the check.
    """
    project_path = Path(project_root)

    if not project_path.exists():
        return GitStatus(has_uncommitted_changes=False, changed_files=[])

    # Check if it's a git repository
    git_dir = project_path / ".git"
    if not git_dir.exists():
        # Walk up to find git root
        for parent in project_path.parents:
            if (parent / ".git").exists():
                break
        else:
            # Not a git repository
            return GitStatus(has_uncommitted_changes=False, changed_files=[])

    try:
        has_changes = has_uncommitted_changes(project_path)
    except Exception as e:
        log.warning(f"Failed to check git status: {e}")
        return GitStatus(has_uncommitted_changes=False, changed_files=[])

    # Get list of changed files
    changed_files: list[str] = []
    if has_changes:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        # Format: XY filename
                        # Skip first 3 characters (status + space)
                        filename = line[3:].strip()
                        # Handle renamed files (old -> new)
                        if " -> " in filename:
                            filename = filename.split(" -> ")[-1]
                        changed_files.append(filename)
        except Exception as e:
            log.warning(f"Failed to get changed files: {e}")

    return GitStatus(has_uncommitted_changes=has_changes, changed_files=changed_files)


def get_build_outputs(project_root: str, target: str) -> BuildOutputs:
    """
    Get paths to all available build output files for a target.
    """
    project_path = Path(project_root)
    build_dir = project_path / "build" / "builds" / target

    outputs = BuildOutputs()

    if not build_dir.exists():
        return outputs

    # BOM files
    bom_json_path = build_dir / f"{target}.bom.json"
    if bom_json_path.exists():
        outputs.bom_json = str(bom_json_path)

    bom_csv_path = build_dir / f"{target}.bom.csv"
    if bom_csv_path.exists():
        outputs.bom_csv = str(bom_csv_path)

    # Pick and place - try JLCPCB format first, then generic
    jlcpcb_pnp_path = build_dir / f"{target}.jlcpcb_pick_and_place.csv"
    generic_pnp_path = build_dir / f"{target}.pick_and_place.csv"
    if jlcpcb_pnp_path.exists():
        outputs.pick_and_place = str(jlcpcb_pnp_path)
    elif generic_pnp_path.exists():
        outputs.pick_and_place = str(generic_pnp_path)

    # Gerbers - try various naming conventions
    gerber_names = [
        f"{target}.gerber.zip",  # Standard atopile output
        f"{target}.jlcpcb.gerber.zip",  # JLCPCB specific
        f"{target}-gerbers.zip",  # Alternative naming
    ]
    for name in gerber_names:
        gerbers_path = build_dir / name
        if gerbers_path.exists():
            outputs.gerbers = str(gerbers_path)
            break

    # 3D models - PCBA format
    glb_path = build_dir / f"{target}.pcba.glb"
    if glb_path.exists():
        outputs.glb = str(glb_path)

    step_path = build_dir / f"{target}.pcba.step"
    if step_path.exists():
        outputs.step = str(step_path)

    # KiCad files
    kicad_pcb_path = build_dir / f"{target}.kicad_pcb"
    if kicad_pcb_path.exists():
        outputs.kicad_pcb = str(kicad_pcb_path)

    kicad_sch_path = build_dir / f"{target}.kicad_sch"
    if kicad_sch_path.exists():
        outputs.kicad_sch = str(kicad_sch_path)

    # PCB Summary
    pcb_summary_path = build_dir / f"{target}.pcb_summary.json"
    if pcb_summary_path.exists():
        outputs.pcb_summary = str(pcb_summary_path)

    return outputs


def estimate_cost(
    project_root: str,
    targets: list[str],
    quantity: int = 1,
    assembly_type: str = "economic",
    lcsc_data: Optional[dict[str, dict]] = None,
) -> CostEstimate:
    """
    Estimate manufacturing costs based on BOM data and board properties.

    Uses JLCPCB pricing model with accurate calculations for:
    - PCB fabrication (board size, layer count)
    - Assembly (setup fees, stencil, solder joints, loading fees)
    - Component costs (with basic vs extended part categorization)

    Args:
        project_root: Path to project root
        targets: List of build targets
        quantity: Number of units to manufacture
        assembly_type: "economic" or "standard" assembly
        lcsc_data: Optional LCSC part data for categorization
    """
    # For now, use first target (typical case)
    # Future: could aggregate costs across multiple targets
    target = targets[0] if targets else "default"

    estimate = cost_estimation.estimate_manufacturing_cost(
        project_root=project_root,
        target=target,
        quantity=quantity,
        assembly_type=assembly_type,
        lcsc_data=lcsc_data,
    )

    # Convert to legacy CostEstimate format for backwards compatibility
    return CostEstimate(
        pcb_cost=estimate.pcb_cost,
        components_cost=estimate.components_cost,
        assembly_cost=estimate.assembly_cost,
        total_cost=estimate.total_cost,
        currency=estimate.currency,
        quantity=estimate.quantity,
        pcb_breakdown=CostBreakdown(
            base_cost=estimate.pcb_breakdown.base_cost,
            area_cost=estimate.pcb_breakdown.size_cost,
            layer_cost=estimate.pcb_breakdown.layer_cost,
        ),
        components_breakdown=ComponentsBreakdown(
            unique_parts=estimate.components_breakdown.unique_parts,
            total_parts=estimate.components_breakdown.total_parts,
        ),
        assembly_breakdown=AssemblyBreakdown(
            base_cost=estimate.assembly_breakdown.setup_fee
            + estimate.assembly_breakdown.stencil_fee,
            per_part_cost=estimate.assembly_breakdown.loading_fees
            + estimate.assembly_breakdown.solder_joints_cost,
        ),
    )


def get_board_summary(
    project_root: str,
    target: str,
    lcsc_data: Optional[dict[str, dict]] = None,
) -> Optional[dict]:
    """
    Get board summary information for display.

    Returns board dimensions, layer count, assembly sides, parts categorization.

    Args:
        project_root: Path to project root
        target: Build target name
        lcsc_data: Optional LCSC part data for categorization

    Returns:
        Dict with board summary or None if unavailable
    """
    project_path = Path(project_root)
    build_dir = project_path / "build" / "builds" / target

    # Parse PCB summary
    summary_path = build_dir / f"{target}.pcb_summary.json"
    board_summary = cost_estimation.parse_pcb_summary(summary_path)
    if not board_summary:
        board_summary = cost_estimation.BoardSummary()

    # Parse pick and place for assembly sides
    pnp_path = build_dir / f"{target}.pick_and_place.csv"
    if not pnp_path.exists():
        pnp_path = build_dir / f"{target}.jlcpcb_pick_and_place.csv"
    board_summary.assembly_sides = cost_estimation.parse_pick_and_place(pnp_path)

    # Categorize BOM parts
    bom_path = build_dir / f"{target}.bom.json"
    parts_cat, _, _ = cost_estimation.categorize_bom_parts(bom_path, lcsc_data)
    board_summary.parts = parts_cat

    # Estimate solder joints
    board_summary.estimated_solder_joints = cost_estimation.estimate_solder_joints(
        bom_path
    )

    return cost_estimation.board_summary_to_dict(board_summary)


def get_detailed_cost_estimate(
    project_root: str,
    target: str,
    quantity: int = 1,
    assembly_type: str = "economic",
    lcsc_data: Optional[dict[str, dict]] = None,
) -> dict:
    """
    Get detailed cost estimate with full breakdown.

    Args:
        project_root: Path to project root
        target: Build target name
        quantity: Number of units to manufacture
        assembly_type: "economic" or "standard" assembly
        lcsc_data: Optional LCSC part data for categorization

    Returns:
        Dict with full cost breakdown and board summary
    """
    estimate = cost_estimation.estimate_manufacturing_cost(
        project_root=project_root,
        target=target,
        quantity=quantity,
        assembly_type=assembly_type,
        lcsc_data=lcsc_data,
    )

    return cost_estimation.cost_estimate_to_dict(estimate)


def export_files(
    project_root: str,
    targets: list[str],
    directory: str,
    file_types: list[str],
) -> dict:
    """
    Export manufacturing files to the specified directory.

    Args:
        project_root: Path to the project
        targets: List of build targets to export
        directory: Destination directory
        file_types: List of file types to export

    Returns:
        Dict with success status, list of exported files, and any errors
    """
    Path(project_root)
    dest_path = Path(directory)

    if not dest_path.exists():
        try:
            dest_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create directory: {e}",
                "files": [],
            }

    exported_files: list[str] = []
    errors: list[str] = []

    for target in targets:
        outputs = get_build_outputs(project_root, target)

        # Create target subdirectory
        target_dir = dest_path / target
        target_dir.mkdir(exist_ok=True)

        # Export each selected file type
        for file_type in file_types:
            source_path = None
            dest_name = None

            if file_type == "gerbers" and outputs.gerbers:
                source_path = Path(outputs.gerbers)
                if source_path.is_dir():
                    # Copy directory
                    dest_name = f"{target}-gerbers"
                    dest_file = target_dir / dest_name
                    try:
                        if dest_file.exists():
                            shutil.rmtree(dest_file)
                        shutil.copytree(source_path, dest_file)
                        exported_files.append(str(dest_file))
                    except Exception as e:
                        errors.append(f"Failed to copy gerbers: {e}")
                    continue
                else:
                    dest_name = source_path.name

            elif file_type == "bom_csv" and outputs.bom_csv:
                source_path = Path(outputs.bom_csv)
                dest_name = f"{target}.bom.csv"

            elif file_type == "bom_json" and outputs.bom_json:
                source_path = Path(outputs.bom_json)
                dest_name = f"{target}.bom.json"

            elif file_type == "pick_and_place" and outputs.pick_and_place:
                source_path = Path(outputs.pick_and_place)
                dest_name = f"{target}.pnp.csv"

            elif file_type == "step" and outputs.step:
                source_path = Path(outputs.step)
                dest_name = f"{target}.step"

            elif file_type == "glb" and outputs.glb:
                source_path = Path(outputs.glb)
                dest_name = f"{target}.glb"

            elif file_type == "kicad_pcb" and outputs.kicad_pcb:
                source_path = Path(outputs.kicad_pcb)
                dest_name = f"{target}.kicad_pcb"

            elif file_type == "kicad_sch" and outputs.kicad_sch:
                source_path = Path(outputs.kicad_sch)
                dest_name = f"{target}.kicad_sch"

            if source_path and dest_name:
                try:
                    dest_file = target_dir / dest_name
                    shutil.copy2(source_path, dest_file)
                    exported_files.append(str(dest_file))
                except Exception as e:
                    errors.append(f"Failed to copy {file_type}: {e}")

    return {
        "success": len(errors) == 0,
        "files": exported_files,
        "errors": errors if errors else None,
    }
