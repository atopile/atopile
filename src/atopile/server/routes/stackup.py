"""
Stackup viewer routes for the build server.

Provides a REST endpoint to serve stackup JSON data for the 2D viewer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stackup", tags=["stackup"])


class ManufacturerResponse(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None


class StackupLayerResponse(BaseModel):
    index: int
    layer_type: Optional[str] = Field(None, alias="layerType")
    material: Optional[str] = None
    thickness_mm: Optional[float] = Field(None, alias="thicknessMm")
    relative_permittivity: Optional[float] = Field(None, alias="relativePermittivity")
    loss_tangent: Optional[float] = Field(None, alias="lossTangent")

    class Config:
        populate_by_name = True


class StackupResponse(BaseModel):
    stackup_name: str = Field(alias="stackupName")
    manufacturer: Optional[ManufacturerResponse] = None
    layers: list[StackupLayerResponse]
    total_thickness_mm: float = Field(alias="totalThicknessMm")

    class Config:
        populate_by_name = True


@router.get("")
async def get_stackup(
    project_root: str = Query(..., alias="project_root"),
    target: str = Query(...),
) -> StackupResponse:
    """
    Get the PCB stackup data for the 2D viewer.

    Reads the .stackup.json artifact produced during build.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_root}"
        )

    build_dir = project_path / "build" / "builds" / target
    stackup_file = build_dir / f"{target}.stackup.json"

    if not stackup_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Stackup data not found. Run a build first.",
        )

    try:
        data = json.loads(stackup_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read stackup data: {e}")

    layers = [
        StackupLayerResponse(
            index=layer["index"],
            layerType=layer.get("layerType"),
            material=layer.get("material"),
            thicknessMm=layer.get("thicknessMm"),
            relativePermittivity=layer.get("relativePermittivity"),
            lossTangent=layer.get("lossTangent"),
        )
        for layer in data.get("layers", [])
    ]

    manufacturer = None
    if data.get("manufacturer"):
        m = data["manufacturer"]
        manufacturer = ManufacturerResponse(
            name=m.get("name"),
            country=m.get("country"),
            website=m.get("website"),
        )

    return StackupResponse(
        stackupName=data.get("stackupName", "Unknown"),
        manufacturer=manufacturer,
        layers=layers,
        totalThicknessMm=data.get("totalThicknessMm", 0),
    )
