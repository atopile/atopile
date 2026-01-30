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
    """Assembly cost breakdown."""

    base_cost: float = Field(alias="baseCost")
    per_part_cost: float = Field(alias="perPartCost")

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


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    project_root: str = Field(alias="projectRoot")
    targets: list[str]
    quantity: int = 1

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
        raise HTTPException(status_code=404, detail=f"Project not found: {project_root}")

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
        raise HTTPException(status_code=404, detail=f"Project not found: {project_root}")

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
