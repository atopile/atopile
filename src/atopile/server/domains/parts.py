"""Part data domain helpers (LCSC stock/pricing)."""

from __future__ import annotations

import re
import time
from typing import Iterable, Optional

from atopile.dataclasses import Log
from atopile.logging import BuildLogger
from atopile.model import build_history
from faebryk.libs.picker.api.api import get_api_client
from faebryk.libs.picker.api.models import Component, LCSCParams

_LCSC_RE = re.compile(r"^C\d+$", re.IGNORECASE)
_OUT_OF_STOCK_TTL_S = 24 * 60 * 60
_out_of_stock_cache: dict[tuple[str, str], float] = {}


def _normalize_lcsc_id(lcsc_id: str) -> tuple[str, int]:
    candidate = lcsc_id.strip().upper()
    if not _LCSC_RE.match(candidate):
        raise ValueError(f"Invalid LCSC part number: {lcsc_id}")
    return candidate, int(candidate[1:])


def _serialize_component(component: Component) -> dict:
    return {
        "lcsc": component.lcsc_display,
        "manufacturer": component.manufacturer_name,
        "mpn": component.part_number,
        "package": component.package,
        "description": component.description,
        "datasheet_url": component.datasheet_url,
        "stock": component.stock,
        "unit_cost": component.get_price(1),
        "is_basic": bool(component.is_basic),
        "is_preferred": bool(component.is_preferred),
        "price": [
            {"qFrom": price.qFrom, "qTo": price.qTo, "price": price.price}
            for price in component.price
        ],
    }


def _latest_build_for(
    project_root: Optional[str],
    target: Optional[str],
) -> dict | None:
    if not project_root:
        return None
    builds = build_history.get_builds_by_project_target(
        project_root=project_root,
        target=target,
        limit=1,
    )
    return builds[0] if builds else None


def _log_out_of_stock(
    *,
    build_id: str,
    project_root: str,
    target: str | None,
    component: Component,
) -> bool:
    if component.stock != 0:
        return False

    cache_key = (build_id, component.lcsc_display)
    now = time.time()
    last_logged = _out_of_stock_cache.get(cache_key)
    if last_logged and now - last_logged < _OUT_OF_STOCK_TTL_S:
        return False

    logger = BuildLogger.get(
        project_root,
        target or "default",
        stage="bom",
        build_id=build_id,
    )
    logger.warning(
        f"Out of stock: {component.lcsc_display} ({component.part_number})",
        audience=Log.Audience.USER,
        objects={
            "project_root": project_root,
            "target": target,
            "lcsc": component.lcsc_display,
            "mpn": component.part_number,
            "manufacturer": component.manufacturer_name,
            "stock": component.stock,
            "description": component.description,
        },
    )

    _out_of_stock_cache[cache_key] = now
    return True


def handle_get_lcsc_parts(
    lcsc_ids: Iterable[str],
    *,
    project_root: str | None = None,
    target: str | None = None,
) -> dict:
    normalized: list[tuple[str, int]] = []
    seen: set[str] = set()
    for lcsc_id in lcsc_ids:
        display, numeric = _normalize_lcsc_id(lcsc_id)
        if display in seen:
            continue
        seen.add(display)
        normalized.append((display, numeric))

    if not normalized:
        return {"parts": {}}

    client = get_api_client()
    params = [LCSCParams(lcsc=numeric, quantity=1) for _display, numeric in normalized]
    results = client.fetch_parts_multiple(params)

    parts: dict[str, dict | None] = {}
    latest_build = _latest_build_for(project_root, target)
    build_id = latest_build.get("build_id") if latest_build else None
    logged_warning = False
    for (display, _numeric), components in zip(normalized, results, strict=False):
        if components:
            component = components[0]
            parts[display] = _serialize_component(component)
            if build_id and project_root and component.stock == 0:
                logged_warning = (
                    _log_out_of_stock(
                        build_id=build_id,
                        project_root=project_root,
                        target=target,
                        component=component,
                    )
                    or logged_warning
                )
        else:
            parts[display] = None

    if logged_warning:
        from atopile.server import problem_parser

        problem_parser.sync_problems_to_state()

    return {"parts": parts}
