"""Part data routes (LCSC stock/pricing)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from atopile.server.domains import parts as parts_domain

router = APIRouter(tags=["parts"])


class LcscPartsRequest(BaseModel):
    lcsc_ids: list[str] = Field(..., min_items=1)
    project_root: str | None = None
    target: str | None = None


@router.post("/api/parts/lcsc")
async def get_lcsc_parts(payload: LcscPartsRequest):
    """Fetch LCSC stock/pricing data for a list of part numbers."""
    try:
        return await asyncio.to_thread(
            parts_domain.handle_get_lcsc_parts,
            payload.lcsc_ids,
            project_root=payload.project_root,
            target=payload.target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
