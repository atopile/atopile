"""
Manufacturing routes for the build server.

Provides REST endpoints for the manufacturing export wizard.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from atopile.server.domains import manufacturing as manufacturing_domain

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/manufacturing", tags=["manufacturing"])


class GitStatusResponse(BaseModel):
    """Response for git status check."""

    has_uncommitted_changes: bool = Field(alias="hasUncommittedChanges")
    changed_files: list[str] = Field(alias="changedFiles")

    class Config:
        populate_by_name = True


class BuildOutputsResponse(BaseModel):
    """Response for build outputs."""

    gerbers: Optional[str] = None
    bom_json: Optional[str] = Field(None, alias="bomJson")
    bom_csv: Optional[str] = Field(None, alias="bomCsv")
    pick_and_place: Optional[str] = Field(None, alias="pickAndPlace")
    step: Optional[str] = None
    glb: Optional[str] = None
    kicad_pcb: Optional[str] = Field(None, alias="kicadPcb")
    kicad_sch: Optional[str] = Field(None, alias="kicadSch")
    pcb_summary: Optional[str] = Field(None, alias="pcbSummary")

    class Config:
        populate_by_name = True


class CostBreakdownResponse(BaseModel):
    """PCB cost breakdown."""

    base_cost: float = Field(alias="baseCost")
    area_cost: float = Field(alias="areaCost")
    layer_cost: float = Field(alias="layerCost")

    class Config:
        populate_by_name = True


class ComponentsBreakdownResponse(BaseModel):
    """Components cost breakdown."""

    unique_parts: int = Field(alias="uniqueParts")
    total_parts: int = Field(alias="totalParts")

    class Config:
        populate_by_name = True


class AssemblyBreakdownResponse(BaseModel):
    """Assembly cost breakdown (legacy format)."""

    base_cost: float = Field(alias="baseCost")
    per_part_cost: float = Field(alias="perPartCost")

    class Config:
        populate_by_name = True


class DetailedAssemblyBreakdownResponse(BaseModel):
    """Detailed assembly cost breakdown with JLC pricing."""

    setup_fee: float = Field(alias="setupFee")
    stencil_fee: float = Field(alias="stencilFee")
    solder_joints_cost: float = Field(alias="solderJointsCost")
    loading_fees: float = Field(alias="loadingFees")
    loading_fee_parts_count: int = Field(alias="loadingFeePartsCount")
    total: float

    class Config:
        populate_by_name = True


class DetailedPCBBreakdownResponse(BaseModel):
    """Detailed PCB cost breakdown."""

    base_cost: float = Field(alias="baseCost")
    layer_cost: float = Field(alias="layerCost")
    size_cost: float = Field(alias="sizeCost")
    total: float

    class Config:
        populate_by_name = True


class BoardDimensionsResponse(BaseModel):
    """Board dimensions."""

    width_mm: float = Field(alias="widthMm")
    height_mm: float = Field(alias="heightMm")
    area_mm2: float = Field(alias="areaMm2")
    area_cm2: float = Field(alias="areaCm2")
    is_small_board: bool = Field(alias="isSmallBoard")
    is_large_board: bool = Field(alias="isLargeBoard")

    class Config:
        populate_by_name = True


class AssemblySidesResponse(BaseModel):
    """Assembly sides information."""

    top_count: int = Field(alias="topCount")
    bottom_count: int = Field(alias="bottomCount")
    is_double_sided: bool = Field(alias="isDoubleSided")
    total_components: int = Field(alias="totalComponents")

    class Config:
        populate_by_name = True


class PartsCategorization(BaseModel):
    """Parts categorization by JLCPCB type."""

    basic_count: int = Field(alias="basicCount")
    preferred_count: int = Field(alias="preferredCount")
    extended_count: int = Field(alias="extendedCount")
    unknown_count: int = Field(alias="unknownCount")
    total_unique_parts: int = Field(alias="totalUniqueParts")
    parts_with_loading_fee: int = Field(alias="partsWithLoadingFee")

    class Config:
        populate_by_name = True


class BoardSummaryResponse(BaseModel):
    """Board summary for display."""

    dimensions: Optional[BoardDimensionsResponse] = None
    layer_count: int = Field(alias="layerCount")
    copper_layers: list[str] = Field(alias="copperLayers")
    total_thickness_mm: Optional[float] = Field(None, alias="totalThicknessMm")
    copper_finish: Optional[str] = Field(None, alias="copperFinish")
    assembly: AssemblySidesResponse
    parts: PartsCategorization
    estimated_solder_joints: int = Field(alias="estimatedSolderJoints")

    class Config:
        populate_by_name = True


class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""

    pcb_cost: float = Field(alias="pcbCost")
    components_cost: float = Field(alias="componentsCost")
    assembly_cost: float = Field(alias="assemblyCost")
    total_cost: float = Field(alias="totalCost")
    currency: str
    quantity: int
    pcb_breakdown: Optional[CostBreakdownResponse] = Field(None, alias="pcbBreakdown")
    components_breakdown: Optional[ComponentsBreakdownResponse] = Field(
        None, alias="componentsBreakdown"
    )
    assembly_breakdown: Optional[AssemblyBreakdownResponse] = Field(
        None, alias="assemblyBreakdown"
    )

    class Config:
        populate_by_name = True


class DetailedCostEstimateResponse(BaseModel):
    """Detailed cost estimate with full breakdown."""

    pcb_cost: float = Field(alias="pcbCost")
    components_cost: float = Field(alias="componentsCost")
    assembly_cost: float = Field(alias="assemblyCost")
    total_cost: float = Field(alias="totalCost")
    currency: str
    quantity: int
    assembly_type: str = Field(alias="assemblyType")
    pcb_breakdown: DetailedPCBBreakdownResponse = Field(alias="pcbBreakdown")
    components_breakdown: ComponentsBreakdownResponse = Field(
        alias="componentsBreakdown"
    )
    assembly_breakdown: DetailedAssemblyBreakdownResponse = Field(
        alias="assemblyBreakdown"
    )
    board_summary: Optional[BoardSummaryResponse] = Field(None, alias="boardSummary")

    class Config:
        populate_by_name = True


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    project_root: str = Field(alias="projectRoot")
    targets: list[str]
    quantity: int = 1
    assembly_type: str = Field("economic", alias="assemblyType")

    class Config:
        populate_by_name = True


class ExportRequest(BaseModel):
    """Request for file export."""

    project_root: str = Field(alias="projectRoot")
    targets: list[str]
    directory: str
    file_types: list[str] = Field(alias="fileTypes")

    class Config:
        populate_by_name = True


class ExportResponse(BaseModel):
    """Response for file export."""

    success: bool
    files: list[str]
    errors: Optional[list[str]] = None


@router.get("/git-status")
async def get_git_status(
    project_root: str = Query(..., alias="project_root"),
) -> GitStatusResponse:
    """
    Check git status for uncommitted changes.

    Returns whether there are uncommitted changes and a list of changed files.
    """
    if not project_root:
        raise HTTPException(status_code=400, detail="Missing project_root parameter")

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    result = manufacturing_domain.check_git_status(project_root)

    return GitStatusResponse(
        hasUncommittedChanges=result.has_uncommitted_changes,
        changedFiles=result.changed_files,
    )


@router.get("/outputs")
async def get_build_outputs(
    project_root: str = Query(..., alias="project_root"),
    target: str = Query(...),
) -> BuildOutputsResponse:
    """
    Get available build output files for a target.

    Returns paths to gerbers, BOM, pick-and-place, 3D models, etc.
    """
    if not project_root or not target:
        raise HTTPException(
            status_code=400, detail="Missing project_root or target parameter"
        )

    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    outputs = manufacturing_domain.get_build_outputs(project_root, target)

    return BuildOutputsResponse(
        gerbers=outputs.gerbers,
        bomJson=outputs.bom_json,
        bomCsv=outputs.bom_csv,
        pickAndPlace=outputs.pick_and_place,
        step=outputs.step,
        glb=outputs.glb,
        kicadPcb=outputs.kicad_pcb,
        kicadSch=outputs.kicad_sch,
        pcbSummary=outputs.pcb_summary,
    )


@router.post("/estimate-cost")
async def estimate_cost(request: CostEstimateRequest) -> CostEstimateResponse:
    """
    Calculate manufacturing cost estimate.

    Based on BOM data and quantity, estimates PCB, component, and assembly costs.
    """
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {request.project_root}"
        )

    estimate = manufacturing_domain.estimate_cost(
        request.project_root,
        request.targets,
        request.quantity,
    )

    response = CostEstimateResponse(
        pcbCost=estimate.pcb_cost,
        componentsCost=estimate.components_cost,
        assemblyCost=estimate.assembly_cost,
        totalCost=estimate.total_cost,
        currency=estimate.currency,
        quantity=estimate.quantity,
    )

    if estimate.pcb_breakdown:
        response.pcb_breakdown = CostBreakdownResponse(
            baseCost=estimate.pcb_breakdown.base_cost,
            areaCost=estimate.pcb_breakdown.area_cost,
            layerCost=estimate.pcb_breakdown.layer_cost,
        )

    if estimate.components_breakdown:
        response.components_breakdown = ComponentsBreakdownResponse(
            uniqueParts=estimate.components_breakdown.unique_parts,
            totalParts=estimate.components_breakdown.total_parts,
        )

    if estimate.assembly_breakdown:
        response.assembly_breakdown = AssemblyBreakdownResponse(
            baseCost=estimate.assembly_breakdown.base_cost,
            perPartCost=estimate.assembly_breakdown.per_part_cost,
        )

    return response


@router.post("/export")
async def export_files(request: ExportRequest) -> ExportResponse:
    """
    Export manufacturing files to the specified directory.

    Copies selected file types (gerbers, BOM, etc.) to the export directory.
    """
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {request.project_root}"
        )

    result = manufacturing_domain.export_files(
        request.project_root,
        request.targets,
        request.directory,
        request.file_types,
    )

    return ExportResponse(
        success=result["success"],
        files=result["files"],
        errors=result.get("errors"),
    )


@router.get("/board-summary")
async def get_board_summary(
    project_root: str = Query(..., alias="project_root"),
    target: str = Query(...),
) -> BoardSummaryResponse:
    """
    Get board summary information.

    Returns board dimensions, layer count, assembly sides, and parts categorization.
    Useful for displaying board properties before ordering.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    summary = manufacturing_domain.get_board_summary(project_root, target)
    if not summary:
        raise HTTPException(
            status_code=404, detail=f"Board summary not available for {target}"
        )

    # Convert to response model
    dimensions = None
    if summary.get("dimensions"):
        dims = summary["dimensions"]
        dimensions = BoardDimensionsResponse(
            widthMm=dims["width_mm"],
            heightMm=dims["height_mm"],
            areaMm2=dims["area_mm2"],
            areaCm2=dims["area_cm2"],
            isSmallBoard=dims["is_small_board"],
            isLargeBoard=dims["is_large_board"],
        )

    assembly = summary.get("assembly", {})
    parts = summary.get("parts", {})

    return BoardSummaryResponse(
        dimensions=dimensions,
        layerCount=summary.get("layer_count", 2),
        copperLayers=summary.get("copper_layers", []),
        totalThicknessMm=summary.get("total_thickness_mm"),
        copperFinish=summary.get("copper_finish"),
        assembly=AssemblySidesResponse(
            topCount=assembly.get("top_count", 0),
            bottomCount=assembly.get("bottom_count", 0),
            isDoubleSided=assembly.get("is_double_sided", False),
            totalComponents=assembly.get("total_components", 0),
        ),
        parts=PartsCategorization(
            basicCount=parts.get("basic_count", 0),
            preferredCount=parts.get("preferred_count", 0),
            extendedCount=parts.get("extended_count", 0),
            unknownCount=parts.get("unknown_count", 0),
            totalUniqueParts=parts.get("total_unique_parts", 0),
            partsWithLoadingFee=parts.get("parts_with_loading_fee", 0),
        ),
        estimatedSolderJoints=summary.get("estimated_solder_joints", 0),
    )


@router.post("/detailed-estimate")
async def get_detailed_cost_estimate(
    request: CostEstimateRequest,
) -> DetailedCostEstimateResponse:
    """
    Get detailed cost estimate with full JLCPCB pricing breakdown.

    Includes:
    - PCB cost by layer count and board size
    - Assembly cost with setup fees, stencil, solder joints, loading fees
    - Parts categorization (basic vs extended)
    - Board summary
    """
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {request.project_root}"
        )

    target = request.targets[0] if request.targets else "default"

    estimate = manufacturing_domain.get_detailed_cost_estimate(
        project_root=request.project_root,
        target=target,
        quantity=request.quantity,
        assembly_type=request.assembly_type,
    )

    # Convert nested dicts to response models
    pcb = estimate.get("pcb_breakdown", {})
    components = estimate.get("components_breakdown", {})
    assembly = estimate.get("assembly_breakdown", {})
    board = estimate.get("board_summary")

    board_summary = None
    if board:
        dims = board.get("dimensions")
        dimensions = None
        if dims:
            dimensions = BoardDimensionsResponse(
                widthMm=dims["width_mm"],
                heightMm=dims["height_mm"],
                areaMm2=dims["area_mm2"],
                areaCm2=dims["area_cm2"],
                isSmallBoard=dims["is_small_board"],
                isLargeBoard=dims["is_large_board"],
            )

        asm = board.get("assembly", {})
        parts = board.get("parts", {})

        board_summary = BoardSummaryResponse(
            dimensions=dimensions,
            layerCount=board.get("layer_count", 2),
            copperLayers=board.get("copper_layers", []),
            totalThicknessMm=board.get("total_thickness_mm"),
            copperFinish=board.get("copper_finish"),
            assembly=AssemblySidesResponse(
                topCount=asm.get("top_count", 0),
                bottomCount=asm.get("bottom_count", 0),
                isDoubleSided=asm.get("is_double_sided", False),
                totalComponents=asm.get("total_components", 0),
            ),
            parts=PartsCategorization(
                basicCount=parts.get("basic_count", 0),
                preferredCount=parts.get("preferred_count", 0),
                extendedCount=parts.get("extended_count", 0),
                unknownCount=parts.get("unknown_count", 0),
                totalUniqueParts=parts.get("total_unique_parts", 0),
                partsWithLoadingFee=parts.get("parts_with_loading_fee", 0),
            ),
            estimatedSolderJoints=board.get("estimated_solder_joints", 0),
        )

    return DetailedCostEstimateResponse(
        pcbCost=estimate.get("pcb_cost", 0),
        componentsCost=estimate.get("components_cost", 0),
        assemblyCost=estimate.get("assembly_cost", 0),
        totalCost=estimate.get("total_cost", 0),
        currency=estimate.get("currency", "USD"),
        quantity=estimate.get("quantity", 1),
        assemblyType=estimate.get("assembly_type", "economic"),
        pcbBreakdown=DetailedPCBBreakdownResponse(
            baseCost=pcb.get("base_cost", 0),
            layerCost=pcb.get("layer_cost", 0),
            sizeCost=pcb.get("size_cost", 0),
            total=pcb.get("total", 0),
        ),
        componentsBreakdown=ComponentsBreakdownResponse(
            uniqueParts=components.get("unique_parts", 0),
            totalParts=components.get("total_parts", 0),
        ),
        assemblyBreakdown=DetailedAssemblyBreakdownResponse(
            setupFee=assembly.get("setup_fee", 0),
            stencilFee=assembly.get("stencil_fee", 0),
            solderJointsCost=assembly.get("solder_joints_cost", 0),
            loadingFees=assembly.get("loading_fees", 0),
            loadingFeePartsCount=assembly.get("loading_fee_parts_count", 0),
            total=assembly.get("total", 0),
        ),
        boardSummary=board_summary,
    )
