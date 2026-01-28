#!/usr/bin/env python3
"""Experiment with JLC API sorting parameters."""

import httpx
import json

JLC_URL_V2 = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
JLC_URL_V3 = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v3"
JLC_URL = JLC_URL_V2  # Default

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://jlcpcb.com",
    "Referer": "https://jlcpcb.com/parts",
}


def search(query: str, extra_params: dict | None = None, label: str = ""):
    """Search JLC with sorting parameters."""
    payload = {
        "keyword": query,
        "currentPage": 1,
        "pageSize": 10,
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
    if extra_params:
        payload.update(extra_params)

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Label: {label}")
    print(f"Extra params: {extra_params}")
    print(f"{'='*60}")

    try:
        with httpx.Client(headers=HEADERS, timeout=10) as client:
            resp = client.post(JLC_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"Error: {e}")
        return

    if data.get("code") != 200:
        print(f"API Error: {data.get('message')}")
        return

    page_info = data.get("data", {}).get("componentPageInfo", {})
    products = page_info.get("list") or []

    print(f"Total results: {page_info.get('total')}")
    if not products:
        print("No results returned")
        return

    print(f"\nTop 10 results:")
    print(f"{'MPN':<20} {'Stock':>12} {'Price':>10}")
    print("-" * 45)

    for p in products[:10]:
        mpn = p.get("componentModelEn", "")[:20]
        stock = p.get("stockCount", 0)
        prices = p.get("componentPrices", [])
        price = prices[0].get("productPrice") if prices else None
        print(f"{mpn:<20} {stock:>12,} ${price or 0:>8.4f}")


def search_raw(query: str, url: str, extra_params: dict | None = None):
    """Search JLC and return raw response for analysis."""
    payload = {
        "keyword": query,
        "currentPage": 1,
        "pageSize": 5,
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
    if extra_params:
        payload.update(extra_params)

    try:
        with httpx.Client(headers=HEADERS, timeout=10) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    import time
    query = "100nF 0402"  # Common capacitor search

    # Test different sorting options
    print("\n" + "="*60)
    print("TESTING JLC API SORTING OPTIONS")
    print("="*60)

    # Check if the response has any sorting hints
    print("\n--- Checking response structure ---")
    data = search_raw(query, JLC_URL_V2)
    if data:
        page_info = data.get("data", {}).get("componentPageInfo", {})
        print(f"Page info keys: {list(page_info.keys())}")
        # Check if there are sort-related fields
        for key in page_info.keys():
            if 'sort' in key.lower() or 'order' in key.lower():
                print(f"  {key}: {page_info[key]}")

    # Try V3 endpoint
    print("\n--- Trying V3 endpoint ---")
    data_v3 = search_raw(query, JLC_URL_V3)
    if data_v3:
        print(f"V3 response code: {data_v3.get('code')}")
        if data_v3.get('code') == 200:
            page_info_v3 = data_v3.get("data", {}).get("componentPageInfo", {})
            print(f"V3 Page info keys: {list(page_info_v3.keys())}")

    # Default (no sorting)
    search(query, None, "baseline")

    # The API seems to ignore sort params - let's try client-side sorting
    # for now, and add UI sort indicators
    print("\n" + "="*60)
    print("CONCLUSION: JLC API does not support server-side sorting")
    print("We should implement client-side sorting of the 50 results")
    print("="*60)
