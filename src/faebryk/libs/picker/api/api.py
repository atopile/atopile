# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import json
import logging
import re
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as email_policy_default
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Any
from urllib.parse import quote

import zstd

import faebryk.library._F as F
from atopile.config import config
from atopile.errors import UserInfraError
from faebryk.libs.http import HTTPStatusError, Response, http_client
from faebryk.libs.picker.api.models import (
    BaseParams,
    Component,
    ComponentPrice,
    LCSCParams,
    ManufacturerPartParams,
)
from faebryk.libs.util import ConfigFlag, once

logger = logging.getLogger(__name__)

DEFAULT_API_TIMEOUT_SECONDS = 30
_FULL_COMPONENTS_MAX_IDS = 1000

API_LOG = ConfigFlag("API_LOG", descr="Log API calls (very verbose)", default=False)
_V1_METHOD_TO_TYPE = {
    str(F.Pickable.is_pickable_by_type.Endpoint.RESISTORS): "resistor",
    str(F.Pickable.is_pickable_by_type.Endpoint.CAPACITORS): "capacitor",
    str(
        F.Pickable.is_pickable_by_type.Endpoint.CAPACITORS_POLARIZED
    ): "capacitor_polarized",
    str(F.Pickable.is_pickable_by_type.Endpoint.INDUCTORS): "inductor",
    str(F.Pickable.is_pickable_by_type.Endpoint.DIODES): "diode",
    str(F.Pickable.is_pickable_by_type.Endpoint.LEDS): "led",
    str(F.Pickable.is_pickable_by_type.Endpoint.BJTS): "bjt",
    str(F.Pickable.is_pickable_by_type.Endpoint.MOSFETS): "mosfet",
    str(F.Pickable.is_pickable_by_type.Endpoint.CRYSTALS): "crystal",
    str(F.Pickable.is_pickable_by_type.Endpoint.FERRITE_BEADS): "ferrite_bead",
    str(F.Pickable.is_pickable_by_type.Endpoint.LDOS): "ldo",
}
_PACKAGE_NUMERIC_RE = re.compile(r"^\d{4,5}$")
_PACKAGE_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_COMPONENT_PACKAGE_PREFIX = {
    "resistor": "R",
    "capacitor": "C",
    "capacitor_polarized": "C",
    "inductor": "L",
    "ferrite_bead": "L",
}


class ApiError(Exception): ...


class ApiNotConfiguredError(ApiError): ...


class ApiHTTPError(ApiError):
    def __init__(self, error: HTTPStatusError):
        super().__init__()
        self.response = error.response

    def __str__(self) -> str:
        status_code = self.response.status_code
        try:
            detail = self.response.json()["detail"]
        except Exception:
            detail = self.response.text
        return f"{super().__str__()}: {status_code} {detail}"


class ApiClient:
    @dataclass
    class ApiConfig:
        api_url: str = config.project.services.components.url
        api_key: str | None = None

    @property
    @once
    def _cfg(self) -> ApiConfig:
        return self.ApiConfig()

    @property
    @once
    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": (
                f"atopile/{get_package_version('atopile')} "
                f"({sys.platform}; "
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
            ),
        }
        if self._cfg.api_key:
            headers["Authorization"] = f"Bearer {self._cfg.api_key}"
        return headers

    @property
    @once
    def _package_allowlists(self) -> dict[str, set[str]] | None:
        try:
            response = self._get("/v1/components/packages/allowlist", timeout=5)
        except ApiHTTPError as exc:
            if exc.response.status_code in {404, 405}:
                logger.info("components package allowlist endpoint unavailable")
                return None
            logger.warning("failed to fetch package allowlist: %s", exc)
            return None
        except Exception as exc:
            logger.warning("failed to fetch package allowlist: %s", exc)
            return None

        body = response.json()
        if not isinstance(body, dict):
            return None
        if body.get("available") is False:
            return {}

        raw_allowlists = body.get("allowlists")
        if not isinstance(raw_allowlists, dict):
            return None

        out: dict[str, set[str]] = {}
        for component_type, packages in raw_allowlists.items():
            if not isinstance(component_type, str) or not isinstance(packages, list):
                continue
            normalized: set[str] = set()
            for package in packages:
                if not isinstance(package, str):
                    continue
                normalized_package = _normalize_package_for_component(
                    component_type, package
                )
                if normalized_package:
                    normalized.add(normalized_package)
            out[component_type] = normalized
        return out

    def _enforce_package_allowlist(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload.get("package"), str):
            return
        allowlists = self._package_allowlists
        if allowlists is None:
            return
        _validate_payload_package_allowlist(payload, allowlists)

    def _get(self, url: str, timeout: float = 10) -> Response:
        try:
            with http_client(
                self._headers,
                verify=not config.project.dangerously_skip_ssl_verification,
            ) as client:
                response = client.get(f"{self._cfg.api_url}{url}", timeout=timeout)
                response.raise_for_status()
        except HTTPStatusError as e:
            raise ApiHTTPError(e) from e

        if API_LOG:
            logger.debug(
                "GET %s%s\n->\n%s",
                self._cfg.api_url,
                url,
                _response_debug_body(response),
            )
        else:
            logger.debug("GET %s%s", self._cfg.api_url, url)

        return response

    def _post(
        self, url: str, data: dict, timeout: float = DEFAULT_API_TIMEOUT_SECONDS
    ) -> Response:
        try:
            with http_client(
                self._headers,
                verify=not config.project.dangerously_skip_ssl_verification,
            ) as client:
                response = client.post(
                    f"{self._cfg.api_url}{url}", json=data, timeout=timeout
                )
                response.raise_for_status()
        except HTTPStatusError as e:
            raise ApiHTTPError(e) from e
        except TimeoutError as e:
            raise UserInfraError(
                "Fetching component data failed to complete in time. "
                "Please try again later."
            ) from e

        if API_LOG:
            logger.debug(
                "POST %s%s\n%s\n->\n%s",
                self._cfg.api_url,
                url,
                json.dumps(data, indent=2),
                _response_debug_body(response),
            )
        else:
            logger.debug(
                "POST %s%s\n%s", self._cfg.api_url, url, json.dumps(data, indent=2)
            )

        return response

    @once
    def fetch_part_by_lcsc(self, lcsc: int) -> list["Component"]:
        return self._fetch_components_v1([lcsc])

    @once
    def fetch_part_by_mfr(self, mfr: str, mfr_pn: str) -> list["Component"]:
        component_ids = self._lookup_component_ids_by_mfr(mfr, mfr_pn, limit=50)
        if not component_ids:
            return []
        return self._fetch_components_v1(component_ids)

    def query_parts(
        self, method: F.Pickable.is_pickable_by_type.Endpoint, params: BaseParams
    ) -> list["Component"]:
        return self._query_parts_v1(method, params)

    @once
    def fetch_parts(self, params: BaseParams) -> list["Component"]:
        assert params.endpoint
        return self.query_parts(params.endpoint, params)

    def fetch_parts_multiple(
        self,
        params: list[BaseParams | LCSCParams | ManufacturerPartParams] | list[dict],
    ) -> list[list["Component"]]:
        query_payloads: list[tuple[int, dict[str, Any]]] = []
        component_ids_by_query: dict[int, list[int]] = {}
        pick_parameters_by_query: dict[int, dict[int, dict[str, Any]]] = {}

        for idx, param in enumerate(params):
            if isinstance(param, BaseParams):
                assert param.endpoint
                payload = _build_v1_query_payload(method=param.endpoint, params=param)
                query_payloads.append((idx, payload))
                continue
            if isinstance(param, LCSCParams):
                component_ids_by_query[idx] = [param.lcsc]
                pick_parameters_by_query[idx] = {}
                continue
            if isinstance(param, ManufacturerPartParams):
                component_ids_by_query[idx] = self._lookup_component_ids_by_mfr(
                    param.manufacturer_name, param.part_number, limit=50
                )
                pick_parameters_by_query[idx] = {}
                continue
            if isinstance(param, dict):
                if "lcsc" in param:
                    try:
                        component_ids_by_query[idx] = [int(param["lcsc"])]
                    except Exception as exc:
                        raise ApiError(
                            f"Invalid lcsc query payload: {param!r}"
                        ) from exc
                    pick_parameters_by_query[idx] = {}
                    continue
                if "manufacturer_name" in param and "part_number" in param:
                    component_ids_by_query[idx] = self._lookup_component_ids_by_mfr(
                        str(param["manufacturer_name"]),
                        str(param["part_number"]),
                        limit=50,
                    )
                    pick_parameters_by_query[idx] = {}
                    continue
                endpoint = param.get("endpoint")
                if isinstance(endpoint, str) and endpoint in _V1_METHOD_TO_TYPE:
                    payload = _build_v1_query_payload_from_dict(
                        endpoint=endpoint, raw=param
                    )
                    query_payloads.append((idx, payload))
                    continue
                raise ApiError(f"Unsupported query payload: {param!r}")
            raise ApiError(f"Unsupported query type: {type(param)}")

        if query_payloads:
            for _, payload in query_payloads:
                self._enforce_package_allowlist(payload)
            batch_payload = {"queries": [payload for _, payload in query_payloads]}
            response = self._post(
                "/v1/components/parameters/query/batch",
                batch_payload,
            )
            body = response.json()
            raw_results = body.get("results")
            if not isinstance(raw_results, list):
                raise ApiError("Invalid v1 batch query response: results is not a list")
            if len(raw_results) != len(query_payloads):
                raise ApiError(
                    "Invalid v1 batch query response: mismatched results length"
                )
            for (idx, _), raw_result in zip(query_payloads, raw_results, strict=True):
                if not isinstance(raw_result, dict):
                    component_ids_by_query[idx] = []
                    pick_parameters_by_query[idx] = {}
                    continue
                ordered_ids, pick_parameters_by_id = _extract_candidate_pick_parameters(
                    raw_result.get("candidates", [])
                )
                component_ids_by_query[idx] = ordered_ids
                pick_parameters_by_query[idx] = pick_parameters_by_id

        all_component_ids: list[int] = []
        seen_component_ids: set[int] = set()
        for idx in range(len(params)):
            for component_id in component_ids_by_query.get(idx, []):
                if component_id <= 0 or component_id in seen_component_ids:
                    continue
                seen_component_ids.add(component_id)
                all_component_ids.append(component_id)
        rows_by_id = self._fetch_components_v1_rows(all_component_ids)

        results: list[list[Component]] = []
        for idx in range(len(params)):
            component_ids = component_ids_by_query.get(idx, [])
            pick_parameters_by_id = pick_parameters_by_query.get(idx, {})
            results.append(
                self._components_from_v1_rows(
                    component_ids=component_ids,
                    rows_by_id=rows_by_id,
                    pick_parameters_by_id=pick_parameters_by_id,
                )
            )

        if len(results) != len(params):
            raise ApiError(f"Expected {len(params)} results, got {len(results)}")
        return results

    def _query_parts_v1(
        self, method: F.Pickable.is_pickable_by_type.Endpoint, params: BaseParams
    ) -> list[Component]:
        payload = _build_v1_query_payload(method=method, params=params)
        self._enforce_package_allowlist(payload)
        response = self._post("/v1/components/parameters/query", payload)
        body = response.json()
        ordered_ids, pick_parameters_by_id = _extract_candidate_pick_parameters(
            body.get("candidates", [])
        )
        if not ordered_ids:
            return []
        return self._fetch_components_v1(
            ordered_ids,
            pick_parameters_by_id=pick_parameters_by_id,
        )

    def _fetch_components_v1(
        self,
        component_ids: list[int],
        *,
        pick_parameters_by_id: dict[int, dict[str, Any]] | None = None,
    ) -> list[Component]:
        rows_by_id = self._fetch_components_v1_rows(component_ids)
        return self._components_from_v1_rows(
            component_ids=component_ids,
            rows_by_id=rows_by_id,
            pick_parameters_by_id=pick_parameters_by_id or {},
        )

    def _fetch_parts_from_dict_query(self, query: dict[str, Any]) -> list[Component]:
        if "lcsc" in query:
            try:
                lcsc_id = int(query["lcsc"])
            except Exception as exc:
                raise ApiError(f"Invalid lcsc query payload: {query!r}") from exc
            return self.fetch_part_by_lcsc(lcsc_id)

        if "manufacturer_name" in query and "part_number" in query:
            return self.fetch_part_by_mfr(
                str(query["manufacturer_name"]),
                str(query["part_number"]),
            )

        endpoint = query.get("endpoint")
        if not isinstance(endpoint, str):
            raise ApiError(f"Unsupported query payload: {query!r}")

        if endpoint in _V1_METHOD_TO_TYPE:
            # Re-wrap into BaseParams-like shape and use v1 path.
            payload = _build_v1_query_payload_from_dict(endpoint=endpoint, raw=query)
            self._enforce_package_allowlist(payload)
            response = self._post("/v1/components/parameters/query", payload)
            body = response.json()
            ordered_ids, pick_parameters_by_id = _extract_candidate_pick_parameters(
                body.get("candidates", [])
            )
            if not ordered_ids:
                return []
            return self._fetch_components_v1(
                ordered_ids,
                pick_parameters_by_id=pick_parameters_by_id,
            )

        raise ApiError(f"Endpoint unsupported by v1 API: {endpoint}")

    def _lookup_component_ids_by_mfr(
        self, mfr: str, mfr_pn: str, *, limit: int
    ) -> list[int]:
        response = self._get(
            "/v1/components/mfr/"
            f"{quote(mfr, safe='')}/{quote(mfr_pn, safe='')}?limit={limit}"
        )
        body = response.json()
        raw_component_ids = body.get("component_ids")
        if not isinstance(raw_component_ids, list):
            raise ApiError(
                "Invalid v1 manufacturer lookup response: component_ids is not a list"
            )
        component_ids: list[int] = []
        for raw_component_id in raw_component_ids:
            try:
                component_id = int(raw_component_id)
            except Exception:
                continue
            if component_id > 0:
                component_ids.append(component_id)
        return component_ids

    def _fetch_components_v1_rows(
        self,
        component_ids: list[int],
        *,
        artifact_types: list[str] | None = None,
    ) -> dict[int, dict[str, Any]]:
        ordered_unique: list[int] = []
        seen: set[int] = set()
        for component_id in component_ids:
            if component_id <= 0 or component_id in seen:
                continue
            seen.add(component_id)
            ordered_unique.append(component_id)

        rows_by_id: dict[int, dict[str, Any]] = {}
        normalized_artifact_types: list[str] = []
        if artifact_types:
            seen_types: set[str] = set()
            for artifact_type in artifact_types:
                normalized = str(artifact_type).strip()
                if not normalized or normalized in seen_types:
                    continue
                seen_types.add(normalized)
                normalized_artifact_types.append(normalized)
        for start in range(0, len(ordered_unique), _FULL_COMPONENTS_MAX_IDS):
            chunk = ordered_unique[start : start + _FULL_COMPONENTS_MAX_IDS]
            payload = {"component_ids": chunk}
            if normalized_artifact_types:
                payload["artifact_types"] = normalized_artifact_types
            response = self._post("/v1/components/full", payload)
            metadata, bundle_files = _parse_v1_full_multipart(response)
            _materialize_v1_assets(metadata=metadata, bundle_files=bundle_files)

            components = metadata.get("components", [])
            if not isinstance(components, list):
                raise ApiError("Invalid v1 full response: components is not a list")
            for row in components:
                if not isinstance(row, dict):
                    continue
                raw_lcsc_id = row.get("lcsc_id")
                if isinstance(raw_lcsc_id, int) and raw_lcsc_id > 0:
                    rows_by_id[raw_lcsc_id] = row
        return rows_by_id

    def _components_from_v1_rows(
        self,
        *,
        component_ids: list[int],
        rows_by_id: dict[int, dict[str, Any]],
        pick_parameters_by_id: dict[int, dict[str, Any]],
    ) -> list[Component]:
        out: list[Component] = []
        for component_id in component_ids:
            row = rows_by_id.get(component_id)
            if row is None:
                continue
            out.append(
                _component_from_v1_row(
                    row,
                    pick_parameters=pick_parameters_by_id.get(component_id, {}),
                )
            )
        return out


@once
def get_api_client() -> ApiClient:
    return ApiClient()


def _response_debug_body(response: Response) -> str:
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        try:
            return json.dumps(response.json(), indent=2)
        except Exception:
            return response.text
    preview = response.text
    if len(preview) > 2048:
        preview = f"{preview[:2048]}..."
    return preview


def _build_v1_query_payload(
    *, method: F.Pickable.is_pickable_by_type.Endpoint, params: BaseParams
) -> dict[str, Any]:
    raw = params.serialize()
    return _build_v1_query_payload_from_dict(endpoint=str(method), raw=raw)


def _build_v1_query_payload_from_dict(
    *, endpoint: str, raw: dict[str, Any]
) -> dict[str, Any]:
    component_type = _V1_METHOD_TO_TYPE.get(endpoint)
    if component_type is None:
        raise ApiError(f"Endpoint unsupported by v1 API: {endpoint}")

    qty = int(raw.get("qty", raw.get("quantity", 1)) or 1)
    limit = int(raw.get("limit", raw.get("max_results", 50)) or 50)

    package = _extract_package_constraint(raw.get("package"))
    exact: dict[str, Any] = {}
    ranges: dict[str, dict[str, float | None]] = {}
    reserved = {"endpoint", "qty", "quantity", "limit", "max_results", "package"}
    for name, value in raw.items():
        if name in reserved or value is None:
            continue
        exact_value, range_value = _literal_to_exact_or_range(value)
        if range_value is not None:
            ranges[name] = range_value
            continue
        if exact_value is not None:
            exact[name] = exact_value

    payload: dict[str, Any] = {
        "component_type": component_type,
        "qty": qty,
        "limit": limit,
        "exact": exact,
        "ranges": ranges,
    }
    if package is not None:
        payload["package"] = package
    return payload


def _normalize_package_for_component(component_type: str, raw_package: str) -> str | None:
    normalized = raw_package.strip().upper()
    if not normalized:
        return None
    if component_type == "crystal":
        canonical = _PACKAGE_NON_ALNUM_RE.sub("", normalized)
        return canonical or normalized

    if component_type == "ferrite_bead":
        for prefix in ("L", "FB"):
            if normalized.startswith(prefix):
                suffix = normalized[len(prefix) :]
                if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
                    return suffix
        return normalized

    prefix = _COMPONENT_PACKAGE_PREFIX.get(component_type)
    if prefix is None:
        return normalized

    if normalized.startswith(prefix):
        suffix = normalized[len(prefix) :]
        if _PACKAGE_NUMERIC_RE.fullmatch(suffix):
            return suffix
    return normalized


def _validate_payload_package_allowlist(
    payload: dict[str, Any], allowlists: dict[str, set[str]]
) -> None:
    raw_package = payload.get("package")
    if not isinstance(raw_package, str):
        return
    component_type = str(payload.get("component_type") or "")
    if not component_type:
        return
    allowed = allowlists.get(component_type)
    if allowed is None:
        # Only enforce for known component types in the allowlist.
        return
    normalized = _normalize_package_for_component(component_type, raw_package)
    if normalized is None or normalized not in allowed:
        raise ApiError(
            f"Unsupported package '{raw_package}' for component type "
            f"'{component_type}'."
        )


def _extract_package_constraint(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    enum_values = _literal_enum_values(value)
    if len(enum_values) == 1:
        return enum_values[0]
    return None


def _literal_to_exact_or_range(
    value: Any,
) -> tuple[Any | None, dict[str, float | None] | None]:
    if isinstance(value, (str, int, float, bool)):
        return value, None
    if not isinstance(value, dict):
        return None, None

    bounds = _literal_numeric_bounds(value)
    if bounds is not None:
        minimum, maximum = bounds
        if minimum is None and maximum is None:
            return None, None
        return None, {"minimum": minimum, "maximum": maximum}

    enum_values = _literal_enum_values(value)
    if len(enum_values) == 1:
        return enum_values[0], None

    string_values = _literal_values(value, "StringSet")
    if len(string_values) == 1:
        return str(string_values[0]), None

    bool_values = _literal_values(value, "BooleanSet")
    if len(bool_values) == 1:
        return bool(bool_values[0]), None

    count_values = _literal_values(value, "CountSet")
    if len(count_values) == 1:
        try:
            return int(count_values[0]), None
        except Exception:
            return None, None

    return None, None


def _literal_values(value: dict[str, Any], expected_type: str) -> list[Any]:
    if value.get("type") != expected_type:
        return []
    data = value.get("data")
    if not isinstance(data, dict):
        return []
    raw_values = data.get("values")
    if not isinstance(raw_values, list):
        return []
    return raw_values


def _literal_enum_values(value: Any) -> list[str]:
    if not isinstance(value, dict) or value.get("type") != "EnumSet":
        return []
    data = value.get("data")
    if not isinstance(data, dict):
        return []
    elements = data.get("elements")
    if not isinstance(elements, list):
        return []
    out: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        name = element.get("name")
        if isinstance(name, str) and name:
            out.append(name)
    return out


def _literal_numeric_bounds(
    value: dict[str, Any],
) -> tuple[float | None, float | None] | None:
    literal_type = value.get("type")
    if literal_type in {"Quantity_Interval_Disjoint", "Quantity_Set_Discrete"}:
        data = value.get("data")
        if not isinstance(data, dict):
            return None
        return _interval_set_bounds(data.get("intervals"))
    if literal_type in {"Numeric_Interval_Disjoint", "Numeric_Interval"}:
        return _interval_set_bounds(value)
    return None


def _interval_set_bounds(
    payload: Any,
) -> tuple[float | None, float | None] | None:
    if not isinstance(payload, dict):
        return None
    payload_type = payload.get("type")
    data = payload.get("data")
    if payload_type == "Numeric_Interval":
        if not isinstance(data, dict):
            return None
        return (_as_float_or_none(data.get("min")), _as_float_or_none(data.get("max")))
    if payload_type != "Numeric_Interval_Disjoint" or not isinstance(data, dict):
        return None
    intervals = data.get("intervals")
    if not isinstance(intervals, list):
        return None
    mins: list[float] = []
    maxes: list[float] = []
    for interval in intervals:
        bounds = _interval_set_bounds(interval)
        if bounds is None:
            continue
        minimum, maximum = bounds
        if minimum is not None:
            mins.append(minimum)
        if maximum is not None:
            maxes.append(maximum)
    return (
        min(mins) if mins else None,
        max(maxes) if maxes else None,
    )


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _extract_candidate_pick_parameters(
    candidates: Any,
) -> tuple[list[int], dict[int, dict[str, Any]]]:
    if not isinstance(candidates, list):
        return [], {}

    ordered_ids: list[int] = []
    pick_parameters_by_id: dict[int, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        lcsc_id = candidate.get("lcsc_id")
        if not isinstance(lcsc_id, int) or lcsc_id <= 0:
            continue
        ordered_ids.append(lcsc_id)
        pick_parameters = candidate.get("pick_parameters")
        if isinstance(pick_parameters, dict):
            pick_parameters_by_id[lcsc_id] = pick_parameters
        else:
            pick_parameters_by_id[lcsc_id] = {}
    return ordered_ids, pick_parameters_by_id


def _parse_v1_full_multipart(
    response: Response,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    content_type = response.headers.get("content-type", "")
    if "multipart/mixed" not in content_type.lower():
        raise ApiError(f"Expected multipart/mixed response, got: {content_type!r}")

    mime_message = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        + response.content
    )
    msg = BytesParser(policy=email_policy_default).parsebytes(mime_message)
    if not msg.is_multipart():
        raise ApiError("Invalid multipart response from /v1/components/full")

    metadata: dict[str, Any] | None = None
    bundle: bytes | None = None
    for part in msg.iter_parts():
        body = part.get_payload(decode=True) or b""
        part_type = part.get_content_type().lower()
        if part_type == "application/json":
            metadata = json.loads(body.decode("utf-8"))
            continue
        if part_type in {"application/zstd", "application/octet-stream"}:
            bundle = body
            continue
        disposition = part.get("Content-Disposition", "")
        if 'name="metadata"' in disposition:
            metadata = json.loads(body.decode("utf-8"))
        if 'name="bundle"' in disposition:
            bundle = body

    if metadata is None:
        raise ApiError("Missing metadata part in /v1/components/full response")
    if bundle is None:
        raise ApiError("Missing bundle part in /v1/components/full response")

    try:
        tar_bytes = zstd.decompress(bundle)
    except Exception as exc:
        raise ApiError(
            "Failed to decompress zstd bundle from /v1/components/full"
        ) from exc

    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            if not _is_safe_tar_member(member.name):
                raise ApiError(f"Unsafe tar member path in bundle: {member.name!r}")
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            files[member.name] = extracted.read()

    return metadata, files


def _is_safe_tar_member(path: str) -> bool:
    if not path or path.startswith("/"):
        return False
    parts = Path(path).parts
    return ".." not in parts


def _materialize_v1_assets(
    *,
    metadata: dict[str, Any],
    bundle_files: dict[str, bytes],
) -> None:
    bundle_manifest_assets: dict[str, Any] = {}
    manifest_raw = bundle_files.get("manifest.json")
    if manifest_raw is not None:
        try:
            manifest = json.loads(manifest_raw.decode("utf-8"))
        except Exception:
            manifest = {}
        assets = manifest.get("assets") if isinstance(manifest, dict) else None
        if isinstance(assets, dict):
            bundle_manifest_assets = assets

    asset_manifest = (
        bundle_manifest_assets
        if bundle_manifest_assets
        else metadata.get("asset_manifest", {})
    )
    if not isinstance(asset_manifest, dict):
        return
    root = _components_api_cache_root()
    for raw_lcsc_id, records in asset_manifest.items():
        try:
            lcsc_id = int(raw_lcsc_id)
        except Exception:
            continue
        if not isinstance(records, list):
            continue
        part_dir = root / f"C{lcsc_id}"
        for record in records:
            if not isinstance(record, dict):
                continue
            bundle_path = record.get("bundle_path")
            if not isinstance(bundle_path, str) or bundle_path not in bundle_files:
                continue
            payload = bundle_files[bundle_path]
            artifact_type = str(record.get("artifact_type") or "asset")
            canonical_name = _canonical_asset_filename(artifact_type=artifact_type)
            if canonical_name is not None:
                _write_file_if_changed(part_dir / canonical_name, payload)
            basename = Path(bundle_path).name
            _write_file_if_changed(part_dir / basename, payload)


def _components_api_cache_root() -> Path:
    try:
        root = config.project.paths.build / "cache" / "components_api"
    except Exception:
        root = Path(tempfile.gettempdir()) / "atopile_components_api_cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_file_if_changed(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == payload:
        return
    path.write_bytes(payload)


def _canonical_asset_filename(*, artifact_type: str) -> str | None:
    if artifact_type == "kicad_footprint_mod":
        return "footprint.kicad_mod"
    if artifact_type == "model_step":
        return "model.step"
    if artifact_type == "model_glb":
        return "model.glb"
    if artifact_type == "model_obj":
        return "model.obj"
    if artifact_type == "part_image":
        return "image.jpg"
    if artifact_type == "datasheet_pdf":
        return "datasheet.pdf"
    if artifact_type == "easyeda_cad_json":
        return "easyeda_cad.json"
    return None


def _component_from_v1_row(
    row: dict[str, Any],
    *,
    pick_parameters: dict[str, Any],
) -> Component:
    lcsc_id = int(row["lcsc_id"])
    price = _parse_price_rows(row.get("price_json"))
    attributes = _build_literal_attributes_for_component(row, pick_parameters)
    return Component(
        lcsc=lcsc_id,
        manufacturer_name=str(row.get("manufacturer_name") or "Unknown"),
        part_number=str(row.get("part_number") or f"C{lcsc_id}"),
        package=str(row.get("package") or ""),
        datasheet_url=str(row.get("datasheet_url") or ""),
        description=str(row.get("description") or ""),
        is_basic=int(bool(row.get("is_basic"))),
        is_preferred=int(bool(row.get("is_preferred"))),
        stock=int(row.get("stock") or 0),
        price=price,
        attributes=attributes,
    )


def _parse_price_rows(raw: Any) -> list[Any]:
    if not isinstance(raw, list):
        return []
    out: list[ComponentPrice] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            ComponentPrice(
                qTo=_as_int_or_none(_first_non_none(item.get("qTo"), item.get("q_to"))),
                qFrom=_as_int_or_none(
                    _first_non_none(item.get("qFrom"), item.get("q_from"))
                ),
                price=_as_float_or_none(item.get("price")) or 0.0,
            )
        )
    return out


def _as_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _build_literal_attributes_for_component(
    row: dict[str, Any], pick_parameters: dict[str, Any]
) -> dict[str, dict[str, Any] | None]:
    component_type = str(row.get("component_type") or "").lower()
    attrs: dict[str, dict[str, Any] | None] = {}

    def _quantity_literal(value: Any, *, unit: str) -> dict[str, Any] | None:
        numeric = _as_float_or_none(value)
        if numeric is None:
            return None
        interval = {
            "type": "Numeric_Interval",
            "data": {"min": numeric, "max": numeric},
        }
        return {
            "type": "Quantity_Set_Discrete",
            "data": {
                "intervals": {
                    "type": "Numeric_Interval_Disjoint",
                    "data": {"intervals": [interval]},
                },
                "unit": unit,
            },
        }

    def _enum_literal(name: str) -> dict[str, Any]:
        return {
            "type": "EnumSet",
            "data": {
                "elements": [{"name": name}],
                "enum": {"name": "BackendEnum", "values": {name: name}},
            },
        }

    if component_type == "resistor":
        attrs["resistance"] = _quantity_literal(
            pick_parameters.get("resistance_ohm", row.get("resistance_ohm")),
            unit="ohm",
        )
        attrs["max_power"] = _quantity_literal(
            pick_parameters.get("max_power_w", row.get("max_power_w")),
            unit="watt",
        )
        attrs["max_voltage"] = _quantity_literal(
            pick_parameters.get("max_voltage_v", row.get("max_voltage_v")),
            unit="volt",
        )
    elif component_type == "capacitor":
        attrs["capacitance"] = _quantity_literal(
            pick_parameters.get("capacitance_f", row.get("capacitance_f")),
            unit="farad",
        )
        attrs["max_voltage"] = _quantity_literal(
            pick_parameters.get("max_voltage_v", row.get("max_voltage_v")),
            unit="volt",
        )
        tempco = pick_parameters.get("tempco_code", row.get("capacitor_tempco_code"))
        if isinstance(tempco, str) and tempco:
            attrs["temperature_coefficient"] = _enum_literal(tempco)
    elif component_type == "capacitor_polarized":
        attrs["capacitance"] = _quantity_literal(
            pick_parameters.get("capacitance_f", row.get("capacitance_f")),
            unit="farad",
        )
        attrs["max_voltage"] = _quantity_literal(
            pick_parameters.get("max_voltage_v", row.get("max_voltage_v")),
            unit="volt",
        )
    elif component_type == "inductor":
        attrs["inductance"] = _quantity_literal(
            pick_parameters.get("inductance_h", row.get("inductance_h")),
            unit="henry",
        )
        attrs["max_current"] = _quantity_literal(
            pick_parameters.get("max_current_a", row.get("max_current_a")),
            unit="ampere",
        )
        attrs["dc_resistance"] = _quantity_literal(
            pick_parameters.get("dc_resistance_ohm", row.get("dc_resistance_ohm")),
            unit="ohm",
        )
        attrs["saturation_current"] = _quantity_literal(
            pick_parameters.get(
                "saturation_current_a",
                row.get("saturation_current_a"),
            ),
            unit="ampere",
        )
        attrs["self_resonant_frequency"] = _quantity_literal(
            pick_parameters.get(
                "self_resonant_frequency_hz",
                row.get("self_resonant_frequency_hz"),
            ),
            unit="hertz",
        )
    elif component_type == "diode":
        attrs["forward_voltage"] = _quantity_literal(
            pick_parameters.get("forward_voltage_v", row.get("forward_voltage_v")),
            unit="volt",
        )
        attrs["reverse_working_voltage"] = _quantity_literal(
            pick_parameters.get(
                "reverse_working_voltage_v",
                row.get("reverse_working_voltage_v"),
            ),
            unit="volt",
        )
        attrs["reverse_leakage_current"] = _quantity_literal(
            pick_parameters.get(
                "reverse_leakage_current_a",
                row.get("reverse_leakage_current_a"),
            ),
            unit="ampere",
        )
        attrs["max_current"] = _quantity_literal(
            pick_parameters.get("max_current_a", row.get("max_current_a")),
            unit="ampere",
        )
    elif component_type == "led":
        color = pick_parameters.get("color_code", row.get("led_color_code"))
        if isinstance(color, str) and color:
            attrs["color"] = _enum_literal(color)
        attrs["forward_voltage"] = _quantity_literal(
            pick_parameters.get("forward_voltage_v", row.get("forward_voltage_v")),
            unit="volt",
        )
        attrs["max_current"] = _quantity_literal(
            pick_parameters.get("max_current_a", row.get("max_current_a")),
            unit="ampere",
        )
        attrs["max_brightness"] = _quantity_literal(
            pick_parameters.get("max_brightness_cd", row.get("max_brightness_cd")),
            unit="candela",
        )
    elif component_type == "bjt":
        doping = pick_parameters.get("doping_type", row.get("bjt_doping_type"))
        if isinstance(doping, str) and doping:
            attrs["doping_type"] = _enum_literal(doping)
        attrs["max_collector_emitter_voltage"] = _quantity_literal(
            pick_parameters.get(
                "max_collector_emitter_voltage_v",
                row.get("max_collector_emitter_voltage_v"),
            ),
            unit="volt",
        )
        attrs["max_collector_current"] = _quantity_literal(
            pick_parameters.get(
                "max_collector_current_a",
                row.get("max_collector_current_a"),
            ),
            unit="ampere",
        )
        attrs["max_power"] = _quantity_literal(
            pick_parameters.get("max_power_w", row.get("max_power_w")),
            unit="watt",
        )
        attrs["dc_current_gain"] = _quantity_literal(
            pick_parameters.get("dc_current_gain_hfe", row.get("dc_current_gain_hfe")),
            unit="dimensionless",
        )
    elif component_type == "mosfet":
        channel = pick_parameters.get("channel_type", row.get("mosfet_channel_type"))
        if isinstance(channel, str) and channel:
            attrs["channel_type"] = _enum_literal(channel)
        attrs["gate_source_threshold_voltage"] = _quantity_literal(
            pick_parameters.get(
                "gate_source_threshold_voltage_v",
                row.get("gate_source_threshold_voltage_v"),
            ),
            unit="volt",
        )
        attrs["max_drain_source_voltage"] = _quantity_literal(
            pick_parameters.get(
                "max_drain_source_voltage_v",
                row.get("max_drain_source_voltage_v"),
            ),
            unit="volt",
        )
        attrs["max_continuous_drain_current"] = _quantity_literal(
            pick_parameters.get(
                "max_continuous_drain_current_a",
                row.get("max_continuous_drain_current_a"),
            ),
            unit="ampere",
        )
        attrs["on_resistance"] = _quantity_literal(
            pick_parameters.get("on_resistance_ohm", row.get("on_resistance_ohm")),
            unit="ohm",
        )
    elif component_type == "crystal":
        attrs["frequency"] = _quantity_literal(
            pick_parameters.get("frequency_hz", row.get("frequency_hz")),
            unit="hertz",
        )
        attrs["load_capacitance"] = _quantity_literal(
            pick_parameters.get("load_capacitance_f", row.get("load_capacitance_f")),
            unit="farad",
        )
        attrs["frequency_temperature_tolerance"] = _quantity_literal(
            pick_parameters.get(
                "frequency_stability_ppm",
                row.get("frequency_stability_ppm"),
            ),
            unit="ppm",
        )
    elif component_type == "ferrite_bead":
        attrs["impedance_at_frequency"] = _quantity_literal(
            pick_parameters.get("impedance_ohm", row.get("ferrite_impedance_ohm")),
            unit="ohm",
        )
        attrs["current_rating"] = _quantity_literal(
            pick_parameters.get(
                "current_rating_a",
                _first_non_none(
                    row.get("ferrite_current_rating_a"),
                    row.get("max_current_a"),
                ),
            ),
            unit="ampere",
        )
        attrs["dc_resistance"] = _quantity_literal(
            pick_parameters.get("dc_resistance_ohm", row.get("dc_resistance_ohm")),
            unit="ohm",
        )
    elif component_type == "ldo":
        attrs["output_voltage"] = _quantity_literal(
            pick_parameters.get("output_voltage_v", row.get("ldo_output_voltage_v")),
            unit="volt",
        )
        attrs["max_input_voltage"] = _quantity_literal(
            pick_parameters.get(
                "max_input_voltage_v",
                row.get("ldo_max_input_voltage_v"),
            ),
            unit="volt",
        )
        attrs["output_current"] = _quantity_literal(
            pick_parameters.get("output_current_a", row.get("ldo_output_current_a")),
            unit="ampere",
        )
        attrs["dropout_voltage"] = _quantity_literal(
            pick_parameters.get(
                "dropout_voltage_v",
                row.get("ldo_dropout_voltage_v"),
            ),
            unit="volt",
        )
        output_type = pick_parameters.get("output_type", row.get("ldo_output_type"))
        if isinstance(output_type, str) and output_type:
            attrs["output_type"] = _enum_literal(output_type)

    return {key: value for key, value in attrs.items() if value is not None}


def test_build_v1_query_payload_from_dict_maps_literals() -> None:
    payload = _build_v1_query_payload_from_dict(
        endpoint="resistors",
        raw={
            "qty": 2,
            "max_results": 15,
            "package": {
                "type": "EnumSet",
                "data": {"elements": [{"name": "R0603"}], "enum": {"values": {}}},
            },
            "resistance": {
                "type": "Quantity_Interval_Disjoint",
                "data": {
                    "intervals": {
                        "type": "Numeric_Interval_Disjoint",
                        "data": {
                            "intervals": [
                                {
                                    "type": "Numeric_Interval",
                                    "data": {"min": 9_900.0, "max": 10_100.0},
                                }
                            ]
                        },
                    },
                    "unit": "ohm",
                },
            },
            "temperature_coefficient": {
                "type": "EnumSet",
                "data": {
                    "elements": [{"name": "C0G"}],
                    "enum": {"name": "TC", "values": {"C0G": "C0G"}},
                },
            },
        },
    )
    assert payload["component_type"] == "resistor"
    assert payload["qty"] == 2
    assert payload["limit"] == 15
    assert payload["package"] == "R0603"
    assert payload["ranges"]["resistance"] == {"minimum": 9_900.0, "maximum": 10_100.0}
    assert payload["exact"]["temperature_coefficient"] == "C0G"


def test_parse_v1_full_multipart_extracts_metadata_and_bundle_files() -> None:
    boundary = "components-test-boundary"
    metadata = {
        "components": [{"lcsc_id": 2040, "component_type": "resistor"}],
        "asset_manifest": {"2040": []},
    }

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        payload = b"footprint-data"
        info = tarfile.TarInfo("assets/2040/001_kicad_footprint_mod_foo.kicad_mod")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    bundle = zstd.compress(tar_buffer.getvalue(), 10)

    parts = [
        (
            "application/json",
            'Content-Disposition: inline; name="metadata"',
            json.dumps(metadata).encode("utf-8"),
        ),
        (
            "application/zstd",
            'Content-Disposition: attachment; name="bundle"; filename="bundle.tar.zst"',
            bundle,
        ),
    ]
    body = bytearray()
    for content_type, disposition, payload in parts:
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(f"Content-Type: {content_type}\r\n".encode("ascii"))
        body.extend(f"{disposition}\r\n\r\n".encode("ascii"))
        body.extend(payload)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("ascii"))

    response = Response(
        status_code=200,
        headers={"content-type": f"multipart/mixed; boundary={boundary}"},
        content=bytes(body),
    )
    out_metadata, out_files = _parse_v1_full_multipart(response)
    assert out_metadata["components"][0]["lcsc_id"] == 2040
    assert (
        out_files["assets/2040/001_kicad_footprint_mod_foo.kicad_mod"]
        == b"footprint-data"
    )


def test_build_v1_query_payload_supports_new_endpoints() -> None:
    payload = _build_v1_query_payload_from_dict(
        endpoint="inductors",
        raw={
            "qty": 3,
            "inductance": {
                "type": "Quantity_Interval_Disjoint",
                "data": {
                    "intervals": {
                        "type": "Numeric_Interval_Disjoint",
                        "data": {
                            "intervals": [
                                {
                                    "type": "Numeric_Interval",
                                    "data": {"min": 9e-6, "max": 11e-6},
                                }
                            ]
                        },
                    },
                    "unit": "henry",
                },
            },
        },
    )
    assert payload["component_type"] == "inductor"
    assert payload["qty"] == 3
    assert payload["ranges"]["inductance"] == {"minimum": 9e-06, "maximum": 1.1e-05}


def test_fetch_part_by_mfr_uses_v1_lookup_endpoint(monkeypatch) -> None:
    client = ApiClient()
    captured: dict[str, Any] = {}

    class _Response:
        def json(self):
            return {"component_ids": [2040]}

    def _fake_get(url: str, timeout: float = 10):
        captured["url"] = url
        return _Response()

    def _fake_fetch_components_v1(
        component_ids: list[int],
        *,
        pick_parameters_by_id: dict[int, dict[str, Any]] | None = None,
    ):
        captured["component_ids"] = component_ids
        return []

    monkeypatch.setattr(client, "_get", _fake_get)
    monkeypatch.setattr(client, "_fetch_components_v1", _fake_fetch_components_v1)

    out = client.fetch_part_by_mfr("Raspberry Pi", "RP2040")
    assert out == []
    assert captured["component_ids"] == [2040]
    assert captured["url"] == "/v1/components/mfr/Raspberry%20Pi/RP2040?limit=50"


def test_fetch_parts_multiple_uses_v1_batch_query(monkeypatch) -> None:
    client = ApiClient()
    captured: dict[str, Any] = {}

    class _BatchResponse:
        def json(self):
            return {
                "results": [
                    {
                        "component_type": "resistor",
                        "candidates": [
                            {
                                "lcsc_id": 1001,
                                "pick_parameters": {"resistance_ohm": 10_000.0},
                            }
                        ],
                        "total": 1,
                    },
                    {
                        "component_type": "capacitor",
                        "candidates": [{"lcsc_id": 2002, "pick_parameters": {}}],
                        "total": 1,
                    },
                ],
                "total_queries": 2,
            }

    def _fake_post(
        url: str, data: dict, timeout: float = DEFAULT_API_TIMEOUT_SECONDS
    ) -> _BatchResponse:
        captured["url"] = url
        captured["data"] = data
        return _BatchResponse()

    def _fake_fetch_components_v1_rows(
        component_ids: list[int],
    ) -> dict[int, dict[str, Any]]:
        captured["component_ids"] = component_ids
        return {
            1001: {"lcsc_id": 1001, "component_type": "resistor"},
            2002: {"lcsc_id": 2002, "component_type": "capacitor"},
        }

    monkeypatch.setattr(client, "_post", _fake_post)
    monkeypatch.setattr(
        client,
        "_fetch_components_v1_rows",
        _fake_fetch_components_v1_rows,
    )

    out = client.fetch_parts_multiple(
        [
            {"endpoint": "resistors", "qty": 1},
            {"endpoint": "capacitors", "qty": 1},
        ]
    )
    assert captured["url"] == "/v1/components/parameters/query/batch"
    assert len(captured["data"]["queries"]) == 2
    assert captured["component_ids"] == [1001, 2002]
    assert len(out) == 2
    assert out[0][0].lcsc == 1001
    assert out[1][0].lcsc == 2002


def test_fetch_parts_from_dict_query_rejects_non_v1_endpoints() -> None:
    client = ApiClient()
    try:
        client._fetch_parts_from_dict_query({"endpoint": "tvs", "qty": 1})
    except ApiError as exc:
        assert "unsupported by v1 API" in str(exc)
    else:
        raise AssertionError("Expected ApiError for unsupported endpoint")


def test_v1_method_mapping_covers_pickable_endpoints() -> None:
    endpoint_values = {
        str(value)
        for value in F.Pickable.is_pickable_by_type.Endpoint.__members__.values()
    }
    assert set(_V1_METHOD_TO_TYPE) == endpoint_values


def test_extract_candidate_pick_parameters() -> None:
    ids, pick_map = _extract_candidate_pick_parameters(
        [
            {"lcsc_id": 111, "pick_parameters": {"resistance_ohm": 10_000.0}},
            {"lcsc_id": "bad"},
            {"lcsc_id": 222},
            "bad",
            {"lcsc_id": 0},
            {"lcsc_id": 333, "pick_parameters": "bad"},
        ]
    )
    assert ids == [111, 222, 333]
    assert pick_map == {
        111: {"resistance_ohm": 10_000.0},
        222: {},
        333: {},
    }


def test_build_literal_attributes_for_component_new_types() -> None:
    mosfet = _build_literal_attributes_for_component(
        {"component_type": "mosfet"},
        {
            "channel_type": "N_CHANNEL",
            "max_drain_source_voltage_v": 30.0,
            "max_continuous_drain_current_a": 2.0,
            "on_resistance_ohm": 0.05,
        },
    )
    assert "channel_type" in mosfet
    assert "max_drain_source_voltage" in mosfet
    assert "on_resistance" in mosfet

    crystal = _build_literal_attributes_for_component(
        {"component_type": "crystal"},
        {
            "frequency_hz": 16_000_000.0,
            "load_capacitance_f": 18e-12,
            "frequency_tolerance_ppm": 20.0,
        },
    )
    assert "frequency" in crystal
    assert "load_capacitance" in crystal

    ferrite = _build_literal_attributes_for_component(
        {"component_type": "ferrite_bead"},
        {
            "impedance_ohm": 120.0,
            "current_rating_a": 2.0,
            "dc_resistance_ohm": 0.05,
        },
    )
    assert "impedance_at_frequency" in ferrite
    assert "current_rating" in ferrite
    assert "dc_resistance" in ferrite

    ldo = _build_literal_attributes_for_component(
        {"component_type": "ldo"},
        {
            "output_voltage_v": 3.3,
            "max_input_voltage_v": 6.0,
            "output_current_a": 0.2,
            "dropout_voltage_v": 0.3,
            "output_type": "FIXED",
        },
    )
    assert "output_voltage" in ldo
    assert "max_input_voltage" in ldo
    assert "output_current" in ldo
    assert "dropout_voltage" in ldo
    assert "output_type" in ldo


def test_materialize_v1_assets_uses_bundle_manifest_paths(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "faebryk.libs.picker.api.api._components_api_cache_root",
        lambda: tmp_path,
    )
    metadata = {
        "asset_manifest": {
            "21190": [
                {
                    "artifact_type": "model_step",
                    "bundle_path": None,
                }
            ]
        }
    }
    bundle_files = {
        "manifest.json": json.dumps(
            {
                "assets": {
                    "21190": [
                        {
                            "artifact_type": "model_step",
                            "bundle_path": "assets/21190/001_model_step_hash",
                        },
                        {
                            "artifact_type": "easyeda_cad_json",
                            "bundle_path": "assets/21190/002_easyeda_cad_hash",
                        },
                        {
                            "artifact_type": "model_glb",
                            "bundle_path": "assets/21190/003_model_glb_hash",
                        },
                        {
                            "artifact_type": "part_image",
                            "bundle_path": "assets/21190/004_part_image_hash",
                        },
                    ]
                }
            }
        ).encode("utf-8"),
        "assets/21190/001_model_step_hash": b"step-bytes",
        "assets/21190/002_easyeda_cad_hash": b'{"description":"test"}',
        "assets/21190/003_model_glb_hash": b"glb-bytes",
        "assets/21190/004_part_image_hash": b"img-bytes",
    }
    _materialize_v1_assets(metadata=metadata, bundle_files=bundle_files)
    assert (tmp_path / "C21190" / "model.step").read_bytes() == b"step-bytes"
    assert (tmp_path / "C21190" / "model.glb").read_bytes() == b"glb-bytes"
    assert (tmp_path / "C21190" / "image.jpg").read_bytes() == b"img-bytes"
    assert (tmp_path / "C21190" / "easyeda_cad.json").read_bytes() == (
        b'{"description":"test"}'
    )


def test_validate_payload_package_allowlist_accepts_normalized_passive_prefixes() -> None:
    payload = {"component_type": "resistor", "package": "R0603"}
    _validate_payload_package_allowlist(payload, {"resistor": {"0603"}})


def test_validate_payload_package_allowlist_rejects_unsupported_package() -> None:
    payload = {"component_type": "resistor", "package": "SOT-23"}
    try:
        _validate_payload_package_allowlist(payload, {"resistor": {"0603", "0805"}})
    except ApiError as exc:
        assert "Unsupported package" in str(exc)
    else:
        raise AssertionError("Expected ApiError for unsupported package")
