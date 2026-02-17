"""Autolayout, screenshot, and web-search helper functions for agent tools."""

from __future__ import annotations

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from atopile.server.agent.tool_layout import _footprint_reference
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
)

_AUTOLAYOUT_MAX_TIMEOUT_MINUTES = 2


def _trim_message(text: str | None, limit: int = 2200) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def _extract_candidate_id(candidate: Any) -> str | None:
    if isinstance(candidate, AutolayoutCandidate):
        return candidate.candidate_id
    if isinstance(candidate, dict):
        raw = candidate.get("candidate_id") or candidate.get("candidateId")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None
    raw = getattr(candidate, "candidate_id", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _extract_candidate_score(candidate: Any) -> float | None:
    if isinstance(candidate, AutolayoutCandidate):
        return candidate.score
    if isinstance(candidate, dict):
        raw = candidate.get("score")
        if isinstance(raw, (int, float)):
            return float(raw)
        return None
    raw = getattr(candidate, "score", None)
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _autolayout_state_value(raw: Any) -> str:
    if isinstance(raw, AutolayoutState):
        return raw.value
    if isinstance(raw, str):
        return raw
    return str(raw or "")


def _recommended_autolayout_check_back_seconds(
    *,
    state: str,
    candidate_count: int,
) -> int:
    state_clean = state.strip().lower()
    if state_clean == AutolayoutState.QUEUED.value:
        return 20
    if state_clean == AutolayoutState.RUNNING.value and candidate_count <= 0:
        return 15
    if state_clean == AutolayoutState.RUNNING.value and candidate_count > 0:
        return 10
    return 10


def _autolayout_recommended_action(
    *,
    state_value: str,
    candidate_count: int,
    provider_job_ref: str | None,
) -> str:
    if state_value in {AutolayoutState.QUEUED.value, AutolayoutState.RUNNING.value}:
        return "continue_monitoring"
    if candidate_count > 0:
        return "fetch_candidate_to_layout"
    if state_value == AutolayoutState.FAILED.value:
        return "retry_or_resume_with_adjusted_options"
    if provider_job_ref:
        return "resume_with_additional_timeout"
    return "inspect_job_details"


def _summarize_autolayout_job(job: AutolayoutJob) -> dict[str, Any]:
    state_value = _autolayout_state_value(job.state)
    candidate_count = len(job.candidates)
    return {
        "job_id": job.job_id,
        "build_target": job.build_target,
        "provider": job.provider,
        "provider_job_ref": job.provider_job_ref,
        "state": state_value,
        "updated_at": job.updated_at,
        "created_at": job.created_at,
        "candidate_count": candidate_count,
        "selected_candidate_id": job.selected_candidate_id,
        "applied_candidate_id": job.applied_candidate_id,
        "recommended_action": _autolayout_recommended_action(
            state_value=state_value,
            candidate_count=candidate_count,
            provider_job_ref=job.provider_job_ref,
        ),
    }


def _select_latest_fetchable_job(jobs: list[AutolayoutJob]) -> AutolayoutJob | None:
    if not jobs:
        return None
    preferred_states = {
        AutolayoutState.AWAITING_SELECTION.value,
        AutolayoutState.COMPLETED.value,
    }
    for job in jobs:
        state_value = _autolayout_state_value(job.state)
        if state_value in preferred_states and (
            job.candidates or isinstance(job.provider_job_ref, str)
        ):
            return job
    for job in jobs:
        state_value = _autolayout_state_value(job.state)
        if state_value in {
            AutolayoutState.QUEUED.value,
            AutolayoutState.RUNNING.value,
        }:
            continue
        return job
    return jobs[0]


def _choose_autolayout_candidate_id(
    *,
    candidates: list[Any],
    requested_id: str | None,
) -> str | None:
    if requested_id:
        return requested_id
    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda item: (
            _extract_candidate_score(item)
            if _extract_candidate_score(item) is not None
            else float("-inf")
        ),
        reverse=True,
    )
    chosen = _extract_candidate_id(ranked[0])
    if chosen:
        return chosen
    return _extract_candidate_id(candidates[0])


def _safe_name_token(value: str, *, fallback: str) -> str:
    token = "".join(
        char if char.isalnum() or char in {".", "_", "-"} else "_"
        for char in value.strip()
    ).strip("._-")
    if not token:
        return fallback
    return token[:120]


def _archive_autolayout_iteration(
    *,
    source_layout: Path,
    destination_layout_dir: Path,
    layout_stem: str,
    build_target: str,
    job_id: str,
    candidate_id: str,
) -> Path:
    archive_dir = destination_layout_dir / "autolayout_iterations"
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_target = _safe_name_token(build_target, fallback="target")
    safe_job = _safe_name_token(job_id, fallback="job")
    safe_candidate = _safe_name_token(candidate_id, fallback="candidate")

    archive_path = archive_dir / (
        f"{layout_stem}.{safe_target}.{safe_job}.{safe_candidate}.{timestamp}.kicad_pcb"
    )
    shutil.copy2(source_layout, archive_path)
    return archive_path


def _discover_downloaded_artifacts(
    *,
    downloads_dir: Path,
    candidate_id: str,
) -> dict[str, str]:
    if not downloads_dir.exists():
        return {}

    artifacts: dict[str, str] = {}

    # Prefer candidate-id-prefixed artifacts, then fallback to the newest file
    # by suffix for provider responses that do not preserve candidate_id in name.
    def _pick_path(suffix: str) -> Path | None:
        preferred = downloads_dir / f"{candidate_id}{suffix}"
        if preferred.exists():
            return preferred

        matches = sorted(
            downloads_dir.glob(f"*{suffix}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]
        return None

    for key, suffix in (
        ("kicad_pcb", ".kicad_pcb"),
        ("zip", ".zip"),
    ):
        chosen = _pick_path(suffix)
        if chosen is not None:
            artifacts[key] = str(chosen)

    return artifacts


def _normalize_screenshot_layers(raw_layers: Any) -> list[str] | None:
    if raw_layers is None:
        return None

    tokens: list[str] = []
    if isinstance(raw_layers, str):
        tokens = [part.strip() for part in raw_layers.split(",")]
    elif isinstance(raw_layers, list):
        for entry in raw_layers:
            if not isinstance(entry, str):
                raise ValueError("layers entries must be strings")
            tokens.append(entry.strip())
    else:
        raise ValueError("layers must be an array of KiCad layer names")

    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if not token:
            continue
        if not all(char.isalnum() or char in {".", "_", "-"} for char in token):
            raise ValueError(
                "layers entries may contain only letters, digits, '.', '_' and '-'"
            )
        if token in seen:
            continue
        seen.add(token)
        cleaned.append(token)

    if not cleaned:
        raise ValueError("layers cannot be empty when provided")
    return cleaned


def _default_screenshot_layers(side: str) -> list[str]:
    if side == "bottom":
        return ["B.Cu", "B.Paste", "B.Mask", "Edge.Cuts"]
    if side == "both":
        return ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "Edge.Cuts"]
    return ["F.Cu", "F.Paste", "F.Mask", "Edge.Cuts"]


def _normalize_highlight_components(raw: Any) -> list[str]:
    if raw is None:
        return []

    tokens: list[str] = []
    if isinstance(raw, str):
        token = raw.strip()
        if token:
            tokens.append(token)
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, str):
                raise ValueError("highlight_components entries must be strings")
            token = item.strip()
            if token:
                tokens.append(token)
    else:
        raise ValueError("highlight_components must be a string or array of strings")

    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(token)
    return deduped


def _parse_svg_viewbox(root: ET.Element) -> tuple[float, float, float, float] | None:
    raw = root.attrib.get("viewBox")
    if not raw:
        return None

    parts = raw.replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        x_min, y_min, width, height = (float(part) for part in parts)
    except ValueError:
        return None
    return x_min, y_min, width, height


def _svg_namespace_from_tag(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1 : tag.find("}")]
    return ""


def _svg_tag(namespace: str, local_name: str) -> str:
    if namespace:
        return f"{{{namespace}}}{local_name}"
    return local_name




def _apply_component_highlight_overlay(
    *,
    base_svg_path: Path,
    layout_path: Path,
    project_dir: Path,
    layers: list[str],
    highlighted_references: set[str],
    dim_opacity: float,
) -> dict[str, Any]:
    from faebryk.exporters.pcb.kicad.artifacts import export_svg
    from faebryk.libs.kicad.fileformats import kicad

    if not highlighted_references:
        return {"applied": False, "reason": "no_highlighted_references"}

    with tempfile.TemporaryDirectory(prefix="ato-highlight-") as tmpdir:
        try:
            tmp_root = Path(tmpdir)
            overlay_layout_path = tmp_root / "highlight.kicad_pcb"
            overlay_svg_path = tmp_root / "highlight.svg"

            if hasattr(kicad.loads, "cache"):
                kicad.loads.cache.pop(layout_path, None)
            pcb_file = kicad.loads(kicad.pcb.PcbFile, layout_path)
            pcb = pcb_file.kicad_pcb

            selected_footprints = []
            for footprint in pcb.footprints:
                if _footprint_reference(footprint) in highlighted_references:
                    selected_footprints.append(footprint)
            if not selected_footprints:
                return {"applied": False, "reason": "highlight_components_not_found"}

            pcb.footprints = selected_footprints
            kicad.dumps(pcb_file, overlay_layout_path)
            if hasattr(kicad.loads, "cache"):
                kicad.loads.cache.pop(overlay_layout_path, None)

            highlight_layers = [layer for layer in layers if layer != "Edge.Cuts"]
            if not highlight_layers:
                highlight_layers = list(layers)
            export_svg(
                pcb_file=overlay_layout_path,
                svg_file=overlay_svg_path,
                project_dir=project_dir,
                layers=",".join(highlight_layers),
            )

            base_tree = ET.parse(base_svg_path)
            base_root = base_tree.getroot()
            overlay_root = ET.parse(overlay_svg_path).getroot()

            viewbox = _parse_svg_viewbox(base_root)
            if viewbox is None:
                return {"applied": False, "reason": "missing_viewbox"}
            x_min, y_min, width, height = viewbox

            namespace = _svg_namespace_from_tag(base_root.tag)
            rect = ET.Element(
                _svg_tag(namespace, "rect"),
                {
                    "x": f"{x_min:.4f}",
                    "y": f"{y_min:.4f}",
                    "width": f"{width:.4f}",
                    "height": f"{height:.4f}",
                    "fill": "#000000",
                    "fill-opacity": f"{dim_opacity:.3f}",
                    "id": "atopile-dim-overlay",
                },
            )
            base_root.append(rect)

            highlight_group = ET.Element(
                _svg_tag(namespace, "g"),
                {
                    "id": "atopile-highlight-components",
                },
            )
            overlay_namespace = _svg_namespace_from_tag(overlay_root.tag)
            skip_tags = {
                _svg_tag(overlay_namespace, "title"),
                _svg_tag(overlay_namespace, "desc"),
            }
            for child in list(overlay_root):
                if child.tag in skip_tags:
                    continue
                highlight_group.append(deepcopy(child))
            base_root.append(highlight_group)

            if namespace:
                ET.register_namespace("", namespace)
            base_tree.write(base_svg_path, encoding="utf-8", xml_declaration=True)
        finally:
            if hasattr(kicad.loads, "cache"):
                kicad.loads.cache.pop(layout_path, None)

    return {
        "applied": True,
        "highlight_count": len(highlighted_references),
        "dim_opacity": dim_opacity,
    }


def _estimate_layout_component_count(layout_path: Path) -> int | None:
    if not layout_path.exists():
        return None
    try:
        text = layout_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return text.count("(footprint ")


def _recommended_autolayout_timeout(
    *,
    component_count: int | None,
    job_type: str,
) -> dict[str, Any]:
    normalized_job_type = job_type.strip().lower()
    if component_count is None:
        bucket = "unknown"
    elif component_count <= 50:
        bucket = "simple"
    elif component_count <= 100:
        bucket = "medium"
    elif component_count <= 200:
        bucket = "complex"
    else:
        bucket = "very_complex"

    return {
        "component_count": component_count,
        "bucket": bucket,
        "job_type": normalized_job_type or "routing",
        "start_timeout_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        "resume_increment_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        "per_run_cap_minutes": _AUTOLAYOUT_MAX_TIMEOUT_MINUTES,
        "note": (
            "Per-run timeout is capped to 2 minutes. Run a short pass, review "
            "candidate quality with autolayout_status/screenshots, then resume with "
            "resume_board_id if quality is not yet sufficient."
        ),
    }


def _normalize_plane_nets(raw: Any) -> list[str]:
    if raw is None:
        return ["GND"]
    if not isinstance(raw, list):
        raise ValueError("plane_nets must be an array of net names")
    normalized: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError("plane_nets entries must be strings")
        token = item.strip()
        if not token:
            continue
        if token not in normalized:
            normalized.append(token)
    if not normalized:
        normalized = ["GND"]
    return normalized


def _to_float_or_none(value: Any, *, field_name: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _to_int_or_none(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _normalize_domain_filters(raw: Any, *, field_name: str) -> list[str]:
    if raw is None:
        return []

    tokens: list[str] = []
    if isinstance(raw, str):
        tokens = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, str):
                raise ValueError(f"{field_name} entries must be strings")
            tokens.append(item.strip())
    else:
        raise ValueError(f"{field_name} must be an array of domains")

    normalized: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if not token:
            continue
        cleaned = token.lower()
        if cleaned.startswith("https://"):
            cleaned = cleaned[len("https://") :]
        elif cleaned.startswith("http://"):
            cleaned = cleaned[len("http://") :]
        cleaned = cleaned.strip().strip("/")
        if not cleaned:
            continue
        if any(char.isspace() for char in cleaned):
            raise ValueError(
                f"{field_name} entries must not contain whitespace: '{token}'"
            )
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _get_exa_api_key() -> str:
    api_key = os.getenv("ATOPILE_AGENT_EXA_API_KEY") or os.getenv("EXA_API_KEY")
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()
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
        payload["contents"] = {
            "highlights": {"max_characters": highlights_chars}
        }
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


