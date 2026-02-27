"""Standard library introspection and query logic.

Introspects the STDLIB_ALLOWLIST types using the TypeGraph and returns
them as StdLibItem objects for the Library panel.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from atopile.dataclasses import StdLibChild, StdLibData, StdLibItem, StdLibItemType

if TYPE_CHECKING:
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph

log = logging.getLogger(__name__)

# Module-level cache
_cache: list[StdLibItem] | None = None


# -- TypeGraph introspection helpers -----------------------------------------


def _get_item_type_for_stdlib(
    tg: "fbrk.TypeGraph",
    type_node: "graph.BoundNode",
    type_name: str,
) -> StdLibItemType:
    """Determine the StdLibItemType from the TypeGraph."""
    import faebryk.core.node as fabll
    import faebryk.library._F as F
    from faebryk.library.Pickable import (
        is_pickable_by_part_number,
        is_pickable_by_supplier_id,
        is_pickable_by_type,
    )

    try:
        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, fabll.ImplementsTrait
        ):
            return StdLibItemType.TRAIT

        is_pickable = (
            fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
                type_node, is_pickable_by_type
            )
            or fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
                type_node, is_pickable_by_supplier_id
            )
            or fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
                type_node, is_pickable_by_part_number
            )
        )
        if is_pickable:
            return StdLibItemType.COMPONENT

        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, fabll.is_module
        ):
            return StdLibItemType.MODULE

        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, F.Parameters.is_parameter
        ):
            return StdLibItemType.PARAMETER

        if fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
            type_node, fabll.is_interface
        ):
            return StdLibItemType.INTERFACE
    except Exception as exc:
        log.debug("Failed to determine type for %s: %s", type_name, exc)

    return StdLibItemType.MODULE


def _extract_children(
    tg: "fbrk.TypeGraph",
    type_node: "graph.BoundNode",
    depth: int = 0,
    max_depth: int = 2,
) -> list[StdLibChild]:
    """Extract children from the TypeGraph for a stdlib type."""
    import faebryk.core.faebrykpy as fbrk

    children: list[StdLibChild] = []
    if depth >= max_depth:
        return children

    try:
        make_children = tg.collect_make_children(type_node=type_node)
    except Exception:
        return children

    for identifier, make_child in make_children:
        if not identifier or identifier.startswith("_"):
            continue
        if identifier.startswith(("is_", "has_", "can_", "implements_", "anon")):
            continue

        try:
            type_ref = tg.get_make_child_type_reference(make_child=make_child)
            resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
            if resolved is not None:
                child_type_name = fbrk.TypeGraph.get_type_name(type_node=resolved)
            else:
                child_type_name = fbrk.TypeGraph.get_type_reference_identifier(
                    type_reference=type_ref
                )
        except Exception:
            child_type_name = "Unknown"
            resolved = None

        # Skip internal types
        if (
            "pointer" in child_type_name.lower()
            or "sequence" in child_type_name.lower()
        ):
            continue

        item_type = StdLibItemType.MODULE
        if resolved is not None:
            item_type = _get_item_type_for_stdlib(tg, resolved, child_type_name)

        nested = []
        if resolved is not None and depth + 1 < max_depth:
            nested = _extract_children(tg, resolved, depth + 1, max_depth)

        children.append(
            StdLibChild(
                name=identifier,
                type=child_type_name,
                item_type=item_type,
                children=nested,
                enum_values=[],
            )
        )

    return children


def _build_stdlib_items(max_depth: int | None = None) -> list[StdLibItem]:
    """Build StdLibItem list by introspecting STDLIB_ALLOWLIST via TypeGraph."""
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph
    import faebryk.core.node as fabll
    from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    effective_depth = max_depth if max_depth is not None else 2
    items: list[StdLibItem] = []

    for cls in STDLIB_ALLOWLIST:
        type_id = cls._type_identifier()
        try:
            type_node = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg, cls)
        except Exception as exc:
            log.debug("Failed to create type node for %s: %s", type_id, exc)
            continue

        item_type = _get_item_type_for_stdlib(tg, type_node, type_id)

        # Extract children
        children = _extract_children(tg, type_node, max_depth=effective_depth)

        # Build usage example
        usage = f'from "stdlib" import {type_id}\nnew {type_id}'

        # Try to get docstring
        description = ""
        try:
            doc = getattr(cls, "__doc__", None)
            if doc:
                description = doc.strip().split("\n")[0]
        except Exception:
            pass

        items.append(
            StdLibItem(
                id=type_id,
                name=type_id,
                type=item_type,
                description=description,
                usage=usage,
                children=children,
                parameters=[],
            )
        )

    # Sort: components first, then modules, interfaces, traits
    type_order = {
        StdLibItemType.COMPONENT: 0,
        StdLibItemType.MODULE: 1,
        StdLibItemType.INTERFACE: 2,
        StdLibItemType.TRAIT: 3,
        StdLibItemType.PARAMETER: 4,
    }
    items.sort(key=lambda i: (type_order.get(i.type, 99), i.name))

    return items


# -- Public API --------------------------------------------------------------


def get_standard_library(
    force_refresh: bool = False,
    max_depth: int | None = None,
) -> list[StdLibItem]:
    """Get the standard library items, with caching.

    Args:
        force_refresh: Bypass cache and rebuild.
        max_depth: Max depth for children introspection.

    Returns:
        List of StdLibItem objects.
    """
    global _cache

    if _cache is not None and not force_refresh:
        return _cache

    try:
        _cache = _build_stdlib_items(max_depth=max_depth)
    except Exception as exc:
        log.warning("Failed to build stdlib items: %s", exc)
        _cache = []

    return _cache


def handle_get_stdlib(
    type_filter: str | None = None,
    search: str | None = None,
    refresh: bool = False,
    max_depth: int | None = None,
) -> StdLibData:
    """
    Get the atopile standard library.

    Args:
        type_filter: Filter by item type (interface, module, trait, component)
        search: Search query to filter items by name or description
        refresh: Force refresh the library cache
        max_depth: Maximum depth for nested children

    Returns:
        StdLibData with items and total count
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

    return StdLibData(items=items, total=len(items))


__all__ = [
    "get_standard_library",
    "handle_get_stdlib",
]
