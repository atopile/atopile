"""Web helper functions for agent tools."""

from __future__ import annotations

import os
from typing import Any

import httpx


def _trim_message(text: str | None, limit: int = 2200) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _get_exa_api_key() -> str:
    for env_var in ("ATOPILE_AGENT_EXA_API_KEY", "EXA_API_KEY"):
        value = os.getenv(env_var)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError(
        "Missing Exa API key. Set ATOPILE_AGENT_EXA_API_KEY or EXA_API_KEY."
    )


def _extract_http_error_detail(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    if response is None:
        return str(exc)
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("detail")
            if isinstance(message, str) and message.strip():
                return message.strip()
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    text = (response.text or "").strip()
    if text:
        return _trim_message(text, 280)
    return str(exc)


def _exa_web_search(
    *,
    query: str,
    num_results: int,
    search_type: str,
    include_domains: list[str],
    exclude_domains: list[str],
    content_mode: str,
    max_characters: int | None,
    max_age_hours: int | None,
    timeout_s: float,
) -> dict[str, Any]:
    api_key = _get_exa_api_key()
    endpoint = os.getenv("ATOPILE_AGENT_EXA_SEARCH_URL", "https://api.exa.ai/search")

    payload: dict[str, Any] = {
        "query": query,
        "numResults": num_results,
        "type": search_type,
    }
    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains
    if content_mode == "text":
        if max_characters is None:
            payload["contents"] = {"text": True}
        else:
            payload["contents"] = {"text": {"max_characters": max_characters}}
    elif content_mode == "highlights":
        highlights_chars = 2_000 if max_characters is None else max_characters
        payload["contents"] = {"highlights": {"max_characters": highlights_chars}}
    if max_age_hours is not None:
        payload["maxAgeHours"] = max_age_hours

    headers = {
        "x-api-key": api_key,
        "authorization": f"Bearer {api_key}",
        "accept": "application/json",
        "content-type": "application/json",
    }
    timeout = httpx.Timeout(timeout_s, connect=min(5.0, timeout_s))

    try:
        with httpx.Client(timeout=timeout, verify=True) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _extract_http_error_detail(exc)
        raise RuntimeError(
            f"Exa search failed ({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Exa search request failed: {exc}") from exc

    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("Exa search response was not a JSON object")

    raw_results = body.get("results")
    if not isinstance(raw_results, list):
        raw_results = []

    normalized_results: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_results, start=1):
        if not isinstance(raw, dict):
            continue
        text = raw.get("text")
        highlights = raw.get("highlights")
        normalized_highlights: list[str] | None = None
        if isinstance(highlights, list):
            normalized_highlights = [
                _trim_message(str(item), 900)
                for item in highlights
                if isinstance(item, str) and item.strip()
            ][:6]
            if not normalized_highlights:
                normalized_highlights = None
        normalized_results.append(
            {
                "rank": index,
                "title": str(raw.get("title", "") or ""),
                "url": str(raw.get("url", "") or ""),
                "published_date": raw.get("publishedDate"),
                "author": raw.get("author"),
                "score": raw.get("score"),
                "highlights": normalized_highlights,
                "text": _trim_message(str(text), 2200)
                if isinstance(text, str) and text
                else None,
            }
        )

    return {
        "query": query,
        "search_type": search_type,
        "content_mode": content_mode,
        "max_characters": max_characters,
        "max_age_hours": max_age_hours,
        "requested_results": num_results,
        "returned_results": len(normalized_results),
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
        "results": normalized_results,
        "request_id": body.get("requestId"),
        "cost_dollars": body.get("costDollars"),
        "source": "exa",
    }
