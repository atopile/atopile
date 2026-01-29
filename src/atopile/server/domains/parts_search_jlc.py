"""JLCPCB public parts search provider (hacky)."""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
from typing import Any

import httpx

from faebryk.libs.http import HTTPError, HTTPStatusError

_JLC_BASE_URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood"
_JLC_SEARCH_PATH = "/selectSmtComponentList/v2"
_DEFAULT_RPS = 5.0
_RETRY_LIMIT = 1
_RETRY_BACKOFF_S = 0.4
_REQUEST_TIMEOUT_S = 10

_LOG = logging.getLogger(__name__)

_rate_lock = threading.Lock()
_last_request_ts = 0.0

_JLC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://jlcpcb.com",
    "Referer": "https://jlcpcb.com/parts",
    "Content-Type": "application/json",
}


def _rate_limit(rps: float = _DEFAULT_RPS) -> None:
    min_interval = 1.0 / max(rps, 0.1)
    with _rate_lock:
        global _last_request_ts
        now = time.time()
        wait_s = min_interval - (now - _last_request_ts)
        if wait_s > 0:
            time.sleep(wait_s)
        _last_request_ts = time.time()


def _resolve_ipv4(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(
            host, port, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
    except socket.gaierror:
        return []
    return list({addr[0] for *_rest, addr in infos})


def _post_jlc(payload: dict[str, Any], timeout_s: float, debug: bool) -> dict[str, Any]:
    host = "jlcpcb.com"
    ips = _resolve_ipv4(host, 443)
    if not ips:
        ips = [host]

    last_error: Exception | None = None
    timeout = httpx.Timeout(timeout_s, connect=min(2.0, timeout_s))

    for ip in ips:
        if ip != host:
            url = f"https://{ip}/api/overseas-pcb-order/v1/shoppingCart/smtGood{_JLC_SEARCH_PATH}"
        else:
            url = f"{_JLC_BASE_URL}{_JLC_SEARCH_PATH}"
        headers = dict(_JLC_HEADERS)
        if ip != host:
            headers["Host"] = host
        try:
            with httpx.Client(headers=headers, timeout=timeout, verify=True) as client:
                start = time.perf_counter()
                response = client.post(
                    url,
                    json=payload,
                    extensions={"sni_hostname": host},
                )
                response.raise_for_status()
                data = response.json()
            if debug:
                elapsed = time.perf_counter() - start
                _LOG.info("JLC search via %s in %.2fs", ip, elapsed)
            return data
        except Exception as exc:
            last_error = exc
            if debug:
                _LOG.warning("JLC search via %s failed: %s", ip, exc)
            continue

    if last_error:
        raise last_error
    raise RuntimeError("JLC search failed: no endpoints resolved")


def _search_payload(query: str, page: int, page_size: int) -> dict[str, Any]:
    return {
        "keyword": query,
        "currentPage": page,
        "pageSize": page_size,
        "presaleType": "stock",
        "searchType": 2,
        "componentLibraryType": None,
        "componentAttributeList": [],
        "componentBrandList": [],
        "componentSpecificationList": [],
        "paramList": [],
        "firstSortName": None,
        "secondSortName": None,
        "searchSource": "search",
        "stockFlag": False,
    }


def _parse_price_list(prices: list[dict]) -> tuple[float | None, list[dict]]:
    if not prices:
        return None, []
    normalized = []
    unit_cost = None
    for price in prices:
        q_from = price.get("startNumber")
        q_to = price.get("endNumber")
        price_value = price.get("productPrice")
        try:
            price_value = float(price_value) if price_value is not None else None
        except (TypeError, ValueError):
            price_value = None
        normalized.append({"qFrom": q_from, "qTo": q_to, "price": price_value})
        if unit_cost is None and q_from in (None, 0, 1):
            unit_cost = price_value
    if unit_cost is None:
        unit_cost = normalized[0]["price"]
    return unit_cost, normalized


def _serialize_part(product: dict[str, Any]) -> dict:
    price_list = product.get("componentPrices") or []
    unit_cost, normalized_prices = _parse_price_list(price_list)

    attributes = {}
    for attr in product.get("attributes") or []:
        name = attr.get("attribute_name_en")
        value = attr.get("attribute_value_name")
        if name:
            attributes[name] = value

    image_url = product.get("componentImageUrl") or ""
    if not image_url:
        access_id = product.get("productBigImageAccessId") or product.get(
            "minImageAccessId"
        )
        if access_id:
            image_url = (
                f"https://jlcpcb.com/api/file/downloadByFileSystemAccessId/{access_id}"
            )

    return {
        "lcsc": product.get("componentCode"),
        "manufacturer": product.get("componentBrandEn") or "",
        "mpn": product.get("componentModelEn") or "",
        "package": product.get("componentSpecificationEn") or "",
        "description": product.get("describe") or "",
        "datasheet_url": product.get("dataManualUrl") or "",
        "image_url": image_url or None,
        "stock": int(product.get("stockCount") or 0),
        "unit_cost": unit_cost,
        "is_basic": False,
        "is_preferred": False,
        "price": normalized_prices,
        "attributes": attributes,
    }


def _fetch_jlc_response(payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_JLC_BASE_URL}{_JLC_SEARCH_PATH}"
    last_error: Exception | None = None
    timeout_s = float(os.getenv("ATOPILE_JLC_TIMEOUT_S", str(_REQUEST_TIMEOUT_S)))
    rps = float(os.getenv("ATOPILE_JLC_RPS", str(_DEFAULT_RPS)))
    retries = int(os.getenv("ATOPILE_JLC_RETRIES", str(_RETRY_LIMIT)))
    debug = os.getenv("ATOPILE_JLC_DEBUG", "").lower() in {"1", "true", "yes"}
    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(_RETRY_BACKOFF_S * (2 ** (attempt - 1)))
        _rate_limit(rps)
        try:
            data = _post_jlc(payload, timeout_s, debug)
        except (HTTPStatusError, HTTPError, ValueError) as exc:
            last_error = exc
            continue

        if data.get("code") != 200:
            message = data.get("message") or "Unknown JLC error"
            raise RuntimeError(f"JLC search failed: {message}")
        if debug:
            code = data.get("code")
            total = (data.get("data") or {}).get("componentPageInfo", {}).get("total")
            _LOG.info("JLC search ok (code=%s total=%s)", code, total)
        return data

    raise RuntimeError(f"JLC search failed: {last_error}")


def search_jlc_parts(query: str, *, limit: int = 50) -> tuple[list[dict], str | None]:
    query = query.strip()
    if not query:
        return [], "Missing query"

    page_size = min(max(limit, 1), 100)
    payload = _search_payload(query, page=1, page_size=page_size)

    try:
        data = _fetch_jlc_response(payload)
    except Exception as exc:
        return [], str(exc)

    page_info = (data.get("data") or {}).get("componentPageInfo") or {}
    products = page_info.get("list") or []

    parts: list[dict] = []
    for product in products:
        part = _serialize_part(product)
        if not part.get("lcsc"):
            continue
        parts.append(part)
        if len(parts) >= limit:
            break

    return parts, None
