"""Standard library endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from atopile.server.stdlib import (
    StdLibItem,
    StdLibItemType,
    StdLibResponse,
    get_standard_library,
)

router = APIRouter(tags=["stdlib"])


@router.get("/api/stdlib", response_model=StdLibResponse)
async def get_stdlib(
    type_filter: str | None = Query(
        None,
        description="Filter by item type: interface, module, trait, component",
    ),
    search: str | None = Query(
        None, description="Search query to filter items by name or description"
    ),
    refresh: bool = Query(False, description="Force refresh the library cache"),
    max_depth: int | None = Query(
        None,
        description="Maximum depth for nested children. 0=none, 1=one level, 2=default.",
        ge=0,
        le=5,
    ),
):
    items = get_standard_library(force_refresh=refresh, max_depth=max_depth)

    if type_filter:
        try:
            filter_type = StdLibItemType(type_filter.lower())
            items = [item for item in items if item.type == filter_type]
        except ValueError:
            pass

    if search:
        search_lower = search.lower()
        items = [
            item
            for item in items
            if search_lower in item.name.lower()
            or search_lower in item.description.lower()
        ]

    return StdLibResponse(items=items, total=len(items))


@router.get("/api/stdlib/{item_id}", response_model=StdLibItem)
async def get_stdlib_item(item_id: str):
    items = get_standard_library()
    for item in items:
        if item.id == item_id:
            return item

    raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
