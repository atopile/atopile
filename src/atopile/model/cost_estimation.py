"""
JLCPCB cost estimation module.

Provides accurate cost estimation based on JLCPCB's pricing structure for:
- PCB fabrication (board size, layer count)
- Assembly (setup fees, stencil, solder joints, loading fees)
- Component costs (basic vs extended parts)

References:
- https://jlcpcb.com/help/article/pcb-assembly-price
- https://jlcpcb.com/help/article/in-what-cases-will-there-be-charged-extra
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# =============================================================================
# JLCPCB Pricing Constants (as of 2025)
# =============================================================================


@dataclass(frozen=True)
class JLCEconomicAssemblyPricing:
    """JLCPCB Economic Assembly pricing constants."""

    setup_fee: float = 8.00
    stencil_fee: float = 1.50
    cost_per_joint: float = 0.0016
    extended_part_loading_fee: float = 3.00  # Per unique extended part
    basic_part_loading_fee: float = 0.00  # Basic parts are free
    # Note: Preferred extended parts may have reduced fees in economic assembly


@dataclass(frozen=True)
class JLCStandardAssemblyPricing:
    """JLCPCB Standard Assembly pricing constants."""

    setup_fee_single_side: float = 25.00
    setup_fee_double_side: float = 50.00
    stencil_fee_single_side: float = 7.86
    stencil_fee_double_side: float = 15.72
    cost_per_joint: float = 0.0016
    extended_part_loading_fee: float = 1.50
    basic_part_loading_fee: float = 1.50


@dataclass(frozen=True)
class JLCPCBFabricationPricing:
    """JLCPCB PCB fabrication pricing estimates."""

    # Base prices for 5 PCBs (prototype quantities)
    base_price_2_layer: float = 2.00
    base_price_4_layer: float = 4.00
    base_price_6_layer: float = 8.00
    base_price_8_layer: float = 12.00

    # Size thresholds
    standard_area_cm2: float = 100.0  # 100x100mm = standard size
    large_board_threshold_cm2: float = 650.0

    # Size-based surcharges
    small_board_fee_per_pc: float = 0.02  # For boards <30mm on one side
    very_small_board_fee_per_pc: float = 0.05  # For boards <15mm on one side
    large_board_fee_per_50cm2: float = 2.00  # Per 50cm² over threshold


# Default pricing instances
ECONOMIC_ASSEMBLY = JLCEconomicAssemblyPricing()
STANDARD_ASSEMBLY = JLCStandardAssemblyPricing()
PCB_FABRICATION = JLCPCBFabricationPricing()


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BoardDimensions:
    """Physical board dimensions."""

    width_mm: float
    height_mm: float
    area_mm2: float
    area_cm2: float

    @property
    def is_small_board(self) -> bool:
        """Board has a side < 30mm."""
        return self.width_mm < 30 or self.height_mm < 30

    @property
    def is_very_small_board(self) -> bool:
        """Board has a side < 15mm."""
        return self.width_mm < 15 or self.height_mm < 15

    @property
    def is_large_board(self) -> bool:
        """Board exceeds 650 cm²."""
        return self.area_cm2 > PCB_FABRICATION.large_board_threshold_cm2


@dataclass
class AssemblySides:
    """Component placement by side."""

    top_count: int = 0
    bottom_count: int = 0

    @property
    def is_double_sided(self) -> bool:
        """True if components on both sides."""
        return self.top_count > 0 and self.bottom_count > 0

    @property
    def total_components(self) -> int:
        return self.top_count + self.bottom_count


@dataclass
class PartsCategorization:
    """Categorization of BOM parts by JLCPCB type."""

    basic_count: int = 0
    preferred_count: int = 0
    extended_count: int = 0
    unknown_count: int = 0  # Parts without LCSC data

    @property
    def total_unique_parts(self) -> int:
        return (
            self.basic_count
            + self.preferred_count
            + self.extended_count
            + self.unknown_count
        )

    @property
    def parts_with_loading_fee(self) -> int:
        """Parts that incur loading fees (extended + unknown)."""
        return self.extended_count + self.unknown_count


@dataclass
class BoardSummary:
    """Complete board summary for cost estimation."""

    # Board physical properties
    dimensions: Optional[BoardDimensions] = None
    layer_count: int = 2
    copper_layers: list[str] = field(default_factory=list)
    total_thickness_mm: Optional[float] = None
    copper_finish: Optional[str] = None

    # Assembly information
    assembly_sides: AssemblySides = field(default_factory=AssemblySides)

    # Parts categorization
    parts: PartsCategorization = field(default_factory=PartsCategorization)

    # Solder joint estimate (for assembly cost)
    estimated_solder_joints: int = 0

    @property
    def is_double_sided_assembly(self) -> bool:
        return self.assembly_sides.is_double_sided


@dataclass
class PCBCostBreakdown:
    """Detailed PCB fabrication cost breakdown."""

    base_cost: float = 0.0
    layer_cost: float = 0.0
    size_cost: float = 0.0
    total: float = 0.0


@dataclass
class AssemblyCostBreakdown:
    """Detailed assembly cost breakdown."""

    setup_fee: float = 0.0
    stencil_fee: float = 0.0
    solder_joints_cost: float = 0.0
    loading_fees: float = 0.0
    loading_fee_parts_count: int = 0
    total: float = 0.0


@dataclass
class ComponentsCostBreakdown:
    """Detailed components cost breakdown."""

    basic_parts_cost: float = 0.0
    extended_parts_cost: float = 0.0
    unknown_parts_cost: float = 0.0
    total: float = 0.0
    unique_parts: int = 0
    total_parts: int = 0


@dataclass
class CostEstimateResult:
    """Complete cost estimation result."""

    # Summary costs
    pcb_cost: float = 0.0
    components_cost: float = 0.0
    assembly_cost: float = 0.0
    total_cost: float = 0.0

    # Metadata
    currency: str = "USD"
    quantity: int = 1
    assembly_type: str = "economic"  # "economic" or "standard"

    # Detailed breakdowns
    pcb_breakdown: PCBCostBreakdown = field(default_factory=PCBCostBreakdown)
    components_breakdown: ComponentsCostBreakdown = field(
        default_factory=ComponentsCostBreakdown
    )
    assembly_breakdown: AssemblyCostBreakdown = field(
        default_factory=AssemblyCostBreakdown
    )

    # Board summary used for estimation
    board_summary: Optional[BoardSummary] = None


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_pcb_summary(summary_path: Path) -> Optional[BoardSummary]:
    """
    Parse pcb_summary.json to extract board information.

    Args:
        summary_path: Path to the pcb_summary.json file

    Returns:
        BoardSummary with extracted data, or None if file doesn't exist
    """
    if not summary_path.exists():
        log.warning(f"PCB summary not found: {summary_path}")
        return None

    try:
        with open(summary_path) as f:
            data = json.load(f)
    except Exception as e:
        log.warning(f"Failed to parse PCB summary: {e}")
        return None

    summary = BoardSummary()

    # Extract dimensions
    dims = data.get("dimensions")
    if dims:
        summary.dimensions = BoardDimensions(
            width_mm=dims.get("width_mm", 0),
            height_mm=dims.get("height_mm", 0),
            area_mm2=dims.get("area_mm2", 0),
            area_cm2=dims.get("area_cm2", 0),
        )

    # Extract stackup info
    stackup = data.get("stackup", {})
    summary.layer_count = stackup.get("layer_count", 2)
    summary.copper_layers = stackup.get("copper_layers", [])
    summary.total_thickness_mm = stackup.get("total_thickness_mm")
    summary.copper_finish = stackup.get("copper_finish")

    return summary


def parse_pick_and_place(pnp_path: Path) -> AssemblySides:
    """
    Parse pick and place CSV to determine assembly sides.

    Supports both KiCad format (Side column) and JLCPCB format (Layer column).

    Args:
        pnp_path: Path to the pick_and_place.csv file

    Returns:
        AssemblySides with component counts per side
    """
    sides = AssemblySides()

    if not pnp_path.exists():
        log.warning(f"Pick and place file not found: {pnp_path}")
        return sides

    try:
        with open(pnp_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Handle both KiCad ("Side") and JLCPCB ("Layer") column names
            for row in reader:
                side = row.get("Side") or row.get("Layer") or ""
                side_lower = side.lower().strip()

                if side_lower in ("top", "front", "f.cu"):
                    sides.top_count += 1
                elif side_lower in ("bottom", "back", "b.cu"):
                    sides.bottom_count += 1
                else:
                    # Default to top if unclear
                    sides.top_count += 1

    except Exception as e:
        log.warning(f"Failed to parse pick and place: {e}")

    return sides


def categorize_bom_parts(
    bom_path: Path,
    lcsc_data: Optional[dict[str, dict]] = None,
) -> tuple[PartsCategorization, float, int]:
    """
    Categorize BOM parts as basic, preferred, or extended.

    Args:
        bom_path: Path to the BOM JSON file
        lcsc_data: Optional dict mapping LCSC IDs to part data
            with is_basic/is_preferred fields

    Returns:
        Tuple of (PartsCategorization, total_component_cost, total_parts_count)
    """
    parts = PartsCategorization()
    total_cost = 0.0
    total_parts = 0

    if not bom_path.exists():
        log.warning(f"BOM file not found: {bom_path}")
        return parts, total_cost, total_parts

    try:
        with open(bom_path) as f:
            bom_data = json.load(f)
    except Exception as e:
        log.warning(f"Failed to parse BOM: {e}")
        return parts, total_cost, total_parts

    lcsc_data = lcsc_data or {}

    for component in bom_data.get("components", []):
        lcsc_id = component.get("lcsc")
        qty = component.get("quantity", 1)
        unit_cost = component.get("unitCost") or component.get("unit_cost", 0)

        total_parts += qty
        total_cost += unit_cost * qty

        # Check component's own fields first, then LCSC data
        is_basic = component.get("isBasic") or component.get("is_basic")
        is_preferred = component.get("isPreferred") or component.get("is_preferred")

        # Fall back to LCSC data lookup
        if lcsc_id and lcsc_id in lcsc_data:
            lcsc_info = lcsc_data[lcsc_id]
            if is_basic is None:
                is_basic = lcsc_info.get("is_basic", False)
            if is_preferred is None:
                is_preferred = lcsc_info.get("is_preferred", False)

        # Categorize the part
        if is_basic:
            parts.basic_count += 1
        elif is_preferred:
            parts.preferred_count += 1
        elif lcsc_id:
            # Has LCSC but not basic/preferred = extended
            parts.extended_count += 1
        else:
            # No LCSC data at all
            parts.unknown_count += 1

    return parts, total_cost, total_parts


def estimate_solder_joints(bom_path: Path) -> int:
    """
    Estimate total solder joints from BOM.

    Uses heuristics based on package type:
    - 0402/0603/0805/1206 passives: 2 joints
    - SOT-23: 3 joints
    - SOIC-8: 8 joints
    - QFP/QFN: pin count from package name
    - Default: 4 joints for unknown packages

    Args:
        bom_path: Path to the BOM JSON file

    Returns:
        Estimated total solder joint count
    """
    if not bom_path.exists():
        return 0

    try:
        with open(bom_path) as f:
            bom_data = json.load(f)
    except Exception:
        return 0

    total_joints = 0

    for component in bom_data.get("components", []):
        qty = component.get("quantity", 1)
        package = (component.get("package") or "").upper()

        # Estimate joints based on package
        joints_per_part = _estimate_joints_for_package(package)
        total_joints += joints_per_part * qty

    return total_joints


def _estimate_joints_for_package(package: str) -> int:
    """Estimate solder joints for a given package type."""
    package = package.upper()

    # Two-terminal passives (resistors, capacitors, inductors)
    if any(
        p in package for p in ["0201", "0402", "0603", "0805", "1206", "1210", "2512"]
    ):
        return 2

    # Three-terminal (transistors, small regulators)
    if "SOT-23" in package or "SOT23" in package:
        return 3
    if "SOT-89" in package or "SOT89" in package:
        return 3
    if "SOT-223" in package or "SOT223" in package:
        return 4

    # SOIC packages
    if "SOIC" in package or "SOP" in package:
        # Try to extract pin count
        for suffix in ["-8", "-14", "-16", "-20", "-24", "-28"]:
            if suffix in package:
                return int(suffix[1:])
        return 8  # Default SOIC

    # TSSOP packages
    if "TSSOP" in package or "MSOP" in package:
        for suffix in ["-8", "-14", "-16", "-20", "-24", "-28"]:
            if suffix in package:
                return int(suffix[1:])
        return 16

    # QFP/QFN/LQFP packages - try to extract pin count
    if any(p in package for p in ["QFP", "QFN", "LQFP", "TQFP", "VQFN", "DFN"]):
        # Look for numbers in the package name
        import re

        numbers = re.findall(r"\d+", package)
        if numbers:
            # Take the largest number as likely pin count
            pin_count = max(int(n) for n in numbers)
            if pin_count >= 8:
                return pin_count
        return 32  # Default QFP

    # BGA packages
    if "BGA" in package:
        import re

        numbers = re.findall(r"\d+", package)
        if numbers:
            return max(int(n) for n in numbers)
        return 64

    # Through-hole / connectors
    if any(p in package for p in ["DIP", "PDIP", "CONNECTOR", "HEADER"]):
        import re

        numbers = re.findall(r"\d+", package)
        if numbers:
            return max(int(n) for n in numbers)
        return 8

    # LED packages
    if "LED" in package:
        return 2

    # Default for unknown packages
    return 4


# =============================================================================
# Cost Calculation Functions
# =============================================================================


def calculate_pcb_cost(
    board_summary: BoardSummary,
    quantity: int = 5,
) -> PCBCostBreakdown:
    """
    Calculate PCB fabrication cost based on board properties.

    Args:
        board_summary: Board information
        quantity: Number of PCBs (default 5 for prototype)

    Returns:
        PCBCostBreakdown with detailed costs
    """
    breakdown = PCBCostBreakdown()
    pricing = PCB_FABRICATION

    # Base cost by layer count
    layer_count = board_summary.layer_count
    if layer_count <= 2:
        breakdown.base_cost = pricing.base_price_2_layer
    elif layer_count <= 4:
        breakdown.base_cost = pricing.base_price_4_layer
        breakdown.layer_cost = pricing.base_price_4_layer - pricing.base_price_2_layer
    elif layer_count <= 6:
        breakdown.base_cost = pricing.base_price_6_layer
        breakdown.layer_cost = pricing.base_price_6_layer - pricing.base_price_2_layer
    else:
        breakdown.base_cost = pricing.base_price_8_layer
        breakdown.layer_cost = pricing.base_price_8_layer - pricing.base_price_2_layer

    # Size-based adjustments
    dims = board_summary.dimensions
    if dims:
        # Small board surcharge
        if dims.is_very_small_board:
            breakdown.size_cost = pricing.very_small_board_fee_per_pc * quantity
        elif dims.is_small_board:
            breakdown.size_cost = pricing.small_board_fee_per_pc * quantity

        # Large board surcharge
        if dims.is_large_board:
            excess_cm2 = dims.area_cm2 - pricing.large_board_threshold_cm2
            increments = int(excess_cm2 / 50) + 1
            breakdown.size_cost += pricing.large_board_fee_per_50cm2 * increments

        # Area-based scaling for boards larger than standard
        if dims.area_cm2 > pricing.standard_area_cm2:
            area_multiplier = dims.area_cm2 / pricing.standard_area_cm2
            # Cap multiplier at reasonable level
            area_multiplier = min(area_multiplier, 5.0)
            breakdown.base_cost *= area_multiplier

    breakdown.total = breakdown.base_cost + breakdown.layer_cost + breakdown.size_cost

    return breakdown


def calculate_assembly_cost(
    board_summary: BoardSummary,
    quantity: int = 1,
    assembly_type: str = "economic",
) -> AssemblyCostBreakdown:
    """
    Calculate assembly cost based on JLCPCB pricing.

    Args:
        board_summary: Board information including parts categorization
        quantity: Number of assemblies
        assembly_type: "economic" or "standard"

    Returns:
        AssemblyCostBreakdown with detailed costs
    """
    breakdown = AssemblyCostBreakdown()

    if assembly_type == "standard":
        pricing = STANDARD_ASSEMBLY
        is_double_sided = board_summary.is_double_sided_assembly

        # Setup fee
        if is_double_sided:
            breakdown.setup_fee = pricing.setup_fee_double_side
            breakdown.stencil_fee = pricing.stencil_fee_double_side
        else:
            breakdown.setup_fee = pricing.setup_fee_single_side
            breakdown.stencil_fee = pricing.stencil_fee_single_side

        # Loading fees (standard charges for both basic and extended)
        parts = board_summary.parts
        breakdown.loading_fee_parts_count = parts.total_unique_parts
        breakdown.loading_fees = (
            parts.basic_count * pricing.basic_part_loading_fee
            + parts.extended_count * pricing.extended_part_loading_fee
            + parts.preferred_count * pricing.extended_part_loading_fee
            + parts.unknown_count * pricing.extended_part_loading_fee
        )
    else:
        # Economic assembly
        pricing = ECONOMIC_ASSEMBLY
        breakdown.setup_fee = pricing.setup_fee
        breakdown.stencil_fee = pricing.stencil_fee

        # Loading fees (only extended parts in economic)
        parts = board_summary.parts
        breakdown.loading_fee_parts_count = parts.parts_with_loading_fee
        breakdown.loading_fees = (
            parts.extended_count * pricing.extended_part_loading_fee
            + parts.unknown_count * pricing.extended_part_loading_fee
            # Preferred parts may have reduced/no fee - treating as free for now
        )

    # Solder joints cost
    joints = board_summary.estimated_solder_joints
    breakdown.solder_joints_cost = joints * pricing.cost_per_joint * quantity

    # Total (setup and stencil are one-time, joints scale with quantity)
    breakdown.total = (
        breakdown.setup_fee
        + breakdown.stencil_fee
        + breakdown.loading_fees
        + breakdown.solder_joints_cost
    )

    return breakdown


def estimate_manufacturing_cost(
    project_root: str,
    target: str,
    quantity: int = 1,
    assembly_type: str = "economic",
    lcsc_data: Optional[dict[str, dict]] = None,
) -> CostEstimateResult:
    """
    Calculate complete manufacturing cost estimate.

    Args:
        project_root: Path to project root
        target: Build target name
        quantity: Number of units to manufacture
        assembly_type: "economic" or "standard" assembly
        lcsc_data: Optional LCSC part data for categorization

    Returns:
        CostEstimateResult with complete breakdown
    """
    project_path = Path(project_root)
    build_dir = project_path / "build" / "builds" / target

    # Initialize result
    result = CostEstimateResult(
        quantity=quantity,
        assembly_type=assembly_type,
    )

    # Parse PCB summary
    summary_path = build_dir / f"{target}.pcb_summary.json"
    board_summary = parse_pcb_summary(summary_path)
    if not board_summary:
        board_summary = BoardSummary()

    # Parse pick and place for assembly sides
    pnp_path = build_dir / f"{target}.pick_and_place.csv"
    if not pnp_path.exists():
        # Try JLCPCB format
        pnp_path = build_dir / f"{target}.jlcpcb_pick_and_place.csv"
    board_summary.assembly_sides = parse_pick_and_place(pnp_path)

    # Categorize BOM parts
    bom_path = build_dir / f"{target}.bom.json"
    parts_cat, components_cost, total_parts = categorize_bom_parts(bom_path, lcsc_data)
    board_summary.parts = parts_cat

    # Estimate solder joints
    board_summary.estimated_solder_joints = estimate_solder_joints(bom_path)

    # Store board summary in result
    result.board_summary = board_summary

    # Calculate PCB cost
    result.pcb_breakdown = calculate_pcb_cost(board_summary, quantity)
    result.pcb_cost = result.pcb_breakdown.total

    # Calculate assembly cost
    result.assembly_breakdown = calculate_assembly_cost(
        board_summary, quantity, assembly_type
    )
    result.assembly_cost = result.assembly_breakdown.total

    # Components cost (scales with quantity)
    result.components_breakdown = ComponentsCostBreakdown(
        total=components_cost * quantity,
        unique_parts=parts_cat.total_unique_parts,
        total_parts=total_parts * quantity,
    )
    result.components_cost = result.components_breakdown.total

    # Total cost
    result.total_cost = result.pcb_cost + result.components_cost + result.assembly_cost

    return result


# =============================================================================
# Serialization
# =============================================================================


def board_summary_to_dict(summary: BoardSummary) -> dict:
    """Convert BoardSummary to a JSON-serializable dict."""
    return {
        "dimensions": {
            "width_mm": summary.dimensions.width_mm,
            "height_mm": summary.dimensions.height_mm,
            "area_mm2": summary.dimensions.area_mm2,
            "area_cm2": summary.dimensions.area_cm2,
            "is_small_board": summary.dimensions.is_small_board,
            "is_large_board": summary.dimensions.is_large_board,
        }
        if summary.dimensions
        else None,
        "layer_count": summary.layer_count,
        "copper_layers": summary.copper_layers,
        "total_thickness_mm": summary.total_thickness_mm,
        "copper_finish": summary.copper_finish,
        "assembly": {
            "top_count": summary.assembly_sides.top_count,
            "bottom_count": summary.assembly_sides.bottom_count,
            "is_double_sided": summary.assembly_sides.is_double_sided,
            "total_components": summary.assembly_sides.total_components,
        },
        "parts": {
            "basic_count": summary.parts.basic_count,
            "preferred_count": summary.parts.preferred_count,
            "extended_count": summary.parts.extended_count,
            "unknown_count": summary.parts.unknown_count,
            "total_unique_parts": summary.parts.total_unique_parts,
            "parts_with_loading_fee": summary.parts.parts_with_loading_fee,
        },
        "estimated_solder_joints": summary.estimated_solder_joints,
    }


def cost_estimate_to_dict(estimate: CostEstimateResult) -> dict:
    """Convert CostEstimateResult to a JSON-serializable dict."""
    return {
        "pcb_cost": round(estimate.pcb_cost, 2),
        "components_cost": round(estimate.components_cost, 2),
        "assembly_cost": round(estimate.assembly_cost, 2),
        "total_cost": round(estimate.total_cost, 2),
        "currency": estimate.currency,
        "quantity": estimate.quantity,
        "assembly_type": estimate.assembly_type,
        "pcb_breakdown": {
            "base_cost": round(estimate.pcb_breakdown.base_cost, 2),
            "layer_cost": round(estimate.pcb_breakdown.layer_cost, 2),
            "size_cost": round(estimate.pcb_breakdown.size_cost, 2),
            "total": round(estimate.pcb_breakdown.total, 2),
        },
        "components_breakdown": {
            "total": round(estimate.components_breakdown.total, 2),
            "unique_parts": estimate.components_breakdown.unique_parts,
            "total_parts": estimate.components_breakdown.total_parts,
        },
        "assembly_breakdown": {
            "setup_fee": round(estimate.assembly_breakdown.setup_fee, 2),
            "stencil_fee": round(estimate.assembly_breakdown.stencil_fee, 2),
            "solder_joints_cost": round(
                estimate.assembly_breakdown.solder_joints_cost, 2
            ),
            "loading_fees": round(estimate.assembly_breakdown.loading_fees, 2),
            "loading_fee_parts_count": (
                estimate.assembly_breakdown.loading_fee_parts_count
            ),
            "total": round(estimate.assembly_breakdown.total, 2),
        },
        "board_summary": board_summary_to_dict(estimate.board_summary)
        if estimate.board_summary
        else None,
    }
