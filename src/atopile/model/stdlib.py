"""Stdlib domain logic - business logic for standard library operations."""

from __future__ import annotations

from atopile.server.stdlib import (
    StdLibItem,
    StdLibItemType,
    StdLibResponse,
    get_standard_library,
)


def handle_get_stdlib(
    type_filter: str | None = None,
    search: str | None = None,
    refresh: bool = False,
    max_depth: int | None = None,
) -> StdLibResponse:
    """
    Get the atopile standard library.

    Args:
        type_filter: Filter by item type (interface, module, trait, component)
        search: Search query to filter items by name or description
        refresh: Force refresh the library cache
        max_depth: Maximum depth for nested children

    Returns:
        StdLibResponse with items and total count
    """
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


def handle_get_stdlib_item(item_id: str) -> StdLibItem | None:
    """
    Get details for a specific stdlib item.

    Args:
        item_id: The ID of the item to retrieve

    Returns:
        StdLibItem if found, None otherwise
    """
    items = get_standard_library()
    for item in items:
        if item.id == item_id:
            return item
    return None


__all__ = [
    "handle_get_stdlib",
    "handle_get_stdlib_item",
]
