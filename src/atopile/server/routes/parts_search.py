"""Part search/install routes (LCSC/JLCPCB)."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from atopile.server.domains import parts_search as parts_domain

router = APIRouter(tags=["parts-search"])


class PartSearchItem(BaseModel):
    lcsc: str
    manufacturer: str
    mpn: str
    package: str
    description: str
    datasheet_url: str
    image_url: Optional[str] = None
    stock: int
    unit_cost: float
    is_basic: bool
    is_preferred: bool
    price: list[dict]
    attributes: dict


class PartSearchResponse(BaseModel):
    parts: list[PartSearchItem]
    total: int
    query: str
    error: Optional[str] = None


class PartDetailsResponse(BaseModel):
    part: Optional[PartSearchItem] = None


class InstalledPartItem(BaseModel):
    identifier: str
    manufacturer: str
    mpn: str
    lcsc: Optional[str] = None
    datasheet_url: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    package: Optional[str] = None
    stock: Optional[int] = None
    unit_cost: Optional[float] = None
    path: str


class InstalledPartsResponse(BaseModel):
    parts: list[InstalledPartItem]
    total: int


class InstallPartRequest(BaseModel):
    lcsc_id: str = Field(..., description="LCSC part number (e.g. C2040)")
    project_root: str = Field(..., description="Project root directory")


class InstallPartResponse(BaseModel):
    success: bool
    identifier: Optional[str] = None
    path: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("/api/parts/search", response_model=PartSearchResponse)
async def search_parts(
    query: str = Query(
        "", description="Search query (LCSC ID or Manufacturer:PartNumber)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max number of results"),
):
    results, error = await asyncio.to_thread(
        parts_domain.handle_search_parts,
        query,
        limit=limit,
    )
    return PartSearchResponse(
        parts=results,
        total=len(results),
        query=query,
        error=error,
    )


@router.get("/api/parts/{lcsc_id}/details", response_model=PartDetailsResponse)
async def get_part_details(lcsc_id: str):
    try:
        details = await asyncio.to_thread(
            parts_domain.handle_get_part_details,
            lcsc_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not details:
        raise HTTPException(status_code=404, detail=f"Part not found: {lcsc_id}")
    return PartDetailsResponse(part=details)


@router.get("/api/parts/{lcsc_id}/footprint")
async def get_part_footprint(lcsc_id: str):
    """Return the KiCad footprint (.kicad_mod) for a part."""
    try:
        data = await asyncio.to_thread(
            parts_domain.handle_get_part_footprint,
            lcsc_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not data:
        raise HTTPException(status_code=404, detail=f"Footprint not found: {lcsc_id}")
    return Response(
        content=data,
        media_type="application/x-kicad-footprint",
        headers={"Content-Disposition": f"inline; filename={lcsc_id}.kicad_mod"},
    )


@router.get("/api/parts/{lcsc_id}/model")
async def get_part_model(lcsc_id: str):
    """Return the STEP 3D model for a part."""
    try:
        result = await asyncio.to_thread(
            parts_domain.handle_get_part_model,
            lcsc_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail=f"3D model not found: {lcsc_id}")
    data, name = result
    return Response(
        content=data,
        media_type="model/step",
        headers={"Content-Disposition": f"inline; filename={name}"},
    )


@router.get("/api/parts/installed", response_model=InstalledPartsResponse)
async def get_installed_parts(
    project_root: str = Query("", description="Project root to scan"),
):
    if not project_root:
        return InstalledPartsResponse(parts=[], total=0)
    parts = await asyncio.to_thread(
        parts_domain.handle_list_installed_parts,
        project_root,
    )
    return InstalledPartsResponse(parts=parts, total=len(parts))


@router.post("/api/parts/install", response_model=InstallPartResponse)
async def install_part(payload: InstallPartRequest):
    try:
        result = await asyncio.to_thread(
            parts_domain.handle_install_part,
            payload.lcsc_id,
            payload.project_root,
        )
        return InstallPartResponse(
            success=True,
            identifier=result.get("identifier"),
            path=result.get("path"),
            message=f"Installed {payload.lcsc_id}",
        )
    except Exception as exc:
        return InstallPartResponse(success=False, error=str(exc))


@router.post("/api/parts/uninstall", response_model=InstallPartResponse)
async def uninstall_part(payload: InstallPartRequest):
    try:
        result = await asyncio.to_thread(
            parts_domain.handle_uninstall_part,
            payload.lcsc_id,
            payload.project_root,
        )
        return InstallPartResponse(
            success=True,
            identifier=result.get("identifier"),
            path=result.get("path"),
            message=f"Uninstalled {payload.lcsc_id}",
        )
    except Exception as exc:
        return InstallPartResponse(success=False, error=str(exc))
