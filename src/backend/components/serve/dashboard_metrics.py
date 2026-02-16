from __future__ import annotations

import hashlib
import ipaddress
import threading
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_BUCKET_SECONDS = 30
_MAX_EVENT_AGE_SECONDS = 24 * 60 * 60
_MAX_REQUEST_EVENTS = 200_000
_MAX_WEIGHTED_EVENTS = 200_000

_LOCAL_ORIGIN = {
    "label": "Local Network",
    "country": "Local",
    "lat": 37.7749,
    "lon": -122.4194,
    "geo_source": "local_override",
}
_APPROX_REGIONS: tuple[tuple[str, float, float], ...] = (
    ("US West", 37.7749, -122.4194),
    ("US East", 40.7128, -74.0060),
    ("Europe", 50.1109, 8.6821),
    ("India", 19.0760, 72.8777),
    ("East Asia", 35.6762, 139.6503),
    ("South America", -23.5505, -46.6333),
    ("Oceania", -33.8688, 151.2093),
)


@dataclass(frozen=True)
class _RequestEvent:
    ts: float
    route: str
    path: str
    method: str
    status_code: int
    duration_ms: float
    client_ip: str | None


@dataclass(frozen=True)
class _WeightedEvent:
    ts: float
    key: str
    count: int


def _to_iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).isoformat().replace("+00:00", "Z")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_nonempty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    out = value.strip()
    return out or None


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 3)
    q = max(0.0, min(1.0, q))
    index = int((len(sorted_values) - 1) * q)
    return round(sorted_values[index], 3)


def _is_dashboard_noise(path: str, route: str) -> bool:
    return (
        path.startswith("/dashboard")
        or route.startswith("/dashboard")
        or path == "/v1/dashboard/metrics"
    )


def _origin_from_ip(client_ip: str | None) -> dict[str, Any]:
    if client_ip is None:
        return {
            "id": "unknown",
            "label": "Unknown",
            "country": "Unknown",
            "lat": 0.0,
            "lon": 0.0,
            "geo_source": "unknown",
        }
    raw = client_ip.strip()
    if not raw:
        return {
            "id": "unknown",
            "label": "Unknown",
            "country": "Unknown",
            "lat": 0.0,
            "lon": 0.0,
            "geo_source": "unknown",
        }
    try:
        addr = ipaddress.ip_address(raw)
    except ValueError:
        return {
            "id": f"raw:{raw}",
            "label": "Unknown",
            "country": "Unknown",
            "lat": 0.0,
            "lon": 0.0,
            "geo_source": "invalid_ip",
        }
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        return {"id": "local", **_LOCAL_ORIGIN}

    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    region_name, base_lat, base_lon = _APPROX_REGIONS[digest[0] % len(_APPROX_REGIONS)]
    lat_jitter = ((digest[1] / 255.0) - 0.5) * 18.0
    lon_jitter = ((digest[2] / 255.0) - 0.5) * 24.0
    lat = max(-75.0, min(75.0, base_lat + lat_jitter))
    lon = max(-179.0, min(179.0, base_lon + lon_jitter))
    return {
        "id": f"ip:{raw}",
        "label": region_name,
        "country": "Approx",
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "geo_source": "hashed_ip_approx",
    }


class DashboardMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started_at = time.time()
        self._request_events: deque[_RequestEvent] = deque(maxlen=_MAX_REQUEST_EVENTS)
        self._component_hits: deque[_WeightedEvent] = deque(maxlen=_MAX_WEIGHTED_EVENTS)
        self._component_zero_hits: deque[_WeightedEvent] = deque(
            maxlen=_MAX_WEIGHTED_EVENTS
        )
        self._package_hits: deque[_WeightedEvent] = deque(maxlen=_MAX_WEIGHTED_EVENTS)
        self._package_returns: deque[_WeightedEvent] = deque(
            maxlen=_MAX_WEIGHTED_EVENTS
        )

    def observe(self, event: str, fields: dict[str, Any]) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            if event == "serve.http.request":
                self._observe_http_request(now, fields)
                return
            if event == "serve.parameters.query":
                self._observe_parameter_query(now, fields)
                return
            if event == "serve.parameters.batch":
                self._observe_parameter_batch(now, fields)
                return
            if event == "serve.components.full":
                self._observe_full_response(now, fields)
                return

    def snapshot(
        self,
        *,
        window_seconds: int,
        snapshot_package_stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        cutoff = now - max(60, window_seconds)
        with self._lock:
            self._prune(now)
            window_requests = [
                item
                for item in self._request_events
                if item.ts >= cutoff and not _is_dashboard_noise(item.path, item.route)
            ]
            component_hits = [
                item for item in self._component_hits if item.ts >= cutoff
            ]
            component_zero_hits = [
                item for item in self._component_zero_hits if item.ts >= cutoff
            ]
            package_hits = [item for item in self._package_hits if item.ts >= cutoff]
            package_returns = [
                item for item in self._package_returns if item.ts >= cutoff
            ]

        durations = sorted(item.duration_ms for item in window_requests)
        total_requests = len(window_requests)
        server_errors = sum(1 for item in window_requests if item.status_code >= 500)
        client_errors = sum(
            1 for item in window_requests if 400 <= item.status_code < 500
        )
        success_count = total_requests - server_errors - client_errors

        requests_per_min = 0.0
        if window_seconds > 0:
            requests_per_min = (total_requests / window_seconds) * 60.0

        p50_ms = _quantile(durations, 0.5)
        p95_ms = _quantile(durations, 0.95)
        error_rate_pct = (
            round((server_errors / total_requests) * 100.0, 3)
            if total_requests > 0
            else 0.0
        )
        success_rate_pct = (
            round((success_count / total_requests) * 100.0, 3)
            if total_requests > 0
            else 100.0
        )

        route_counts: Counter[str] = Counter()
        route_durations: dict[str, list[float]] = defaultdict(list)
        route_server_errors: Counter[str] = Counter()
        origin_counts: Counter[str] = Counter()
        for item in window_requests:
            route_key = item.route or item.path
            route_counts[route_key] += 1
            route_durations[route_key].append(item.duration_ms)
            if item.status_code >= 500:
                route_server_errors[route_key] += 1
            if item.client_ip:
                origin_counts[item.client_ip] += 1

        component_counts: Counter[str] = Counter()
        for item in component_hits:
            component_counts[item.key] += item.count

        component_zero_counts: Counter[str] = Counter()
        for item in component_zero_hits:
            component_zero_counts[item.key] += item.count

        package_hit_counts: Counter[str] = Counter()
        for item in package_hits:
            package_hit_counts[item.key] += item.count

        package_return_counts: Counter[str] = Counter()
        for item in package_returns:
            package_return_counts[item.key] += item.count

        top_routes: list[dict[str, Any]] = []
        for route, count in route_counts.most_common(12):
            route_latency = sorted(route_durations[route])
            route_errors = route_server_errors[route]
            top_routes.append(
                {
                    "route": route,
                    "count": count,
                    "p95_ms": _quantile(route_latency, 0.95),
                    "error_rate_pct": round((route_errors / count) * 100.0, 3),
                }
            )

        component_demand = [
            {"component_type": component_type, "count": count}
            for component_type, count in component_counts.most_common(12)
        ]
        component_zero_results = [
            {"component_type": component_type, "count": count}
            for component_type, count in component_zero_counts.most_common(12)
        ]
        package_hits_out = [
            {"package": package, "count": count}
            for package, count in package_hit_counts.most_common(16)
        ]
        package_returns_out = [
            {"package": package, "count": count}
            for package, count in package_return_counts.most_common(16)
        ]

        requests_timeline = self._build_timeline(
            window_requests=window_requests,
            cutoff=cutoff,
            now=now,
        )
        origins = self._build_origin_summary(origin_counts)

        return {
            "generated_at_utc": _to_iso_utc(now),
            "window_seconds": int(window_seconds),
            "uptime_seconds": int(now - self._started_at),
            "services": [
                {
                    "service": "components-serve",
                    "status": "online",
                    "requests": total_requests,
                    "requests_per_min": round(requests_per_min, 3),
                    "p50_ms": p50_ms,
                    "p95_ms": p95_ms,
                    "error_rate_pct": error_rate_pct,
                    "success_rate_pct": success_rate_pct,
                }
            ],
            "http": {
                "total_requests": total_requests,
                "success_count": success_count,
                "client_errors": client_errors,
                "server_errors": server_errors,
                "requests_per_min": round(requests_per_min, 3),
                "p50_ms": p50_ms,
                "p95_ms": p95_ms,
                "error_rate_pct": error_rate_pct,
                "success_rate_pct": success_rate_pct,
                "requests_timeline": requests_timeline,
            },
            "top_routes": top_routes,
            "component_demand": component_demand,
            "component_zero_results": component_zero_results,
            "package_hits": package_hits_out,
            "package_returns": package_returns_out,
            "origins": origins,
            "snapshot_package_stats": snapshot_package_stats or {},
        }

    def _prune(self, now: float) -> None:
        cutoff = now - _MAX_EVENT_AGE_SECONDS
        while self._request_events and self._request_events[0].ts < cutoff:
            self._request_events.popleft()
        while self._component_hits and self._component_hits[0].ts < cutoff:
            self._component_hits.popleft()
        while self._component_zero_hits and self._component_zero_hits[0].ts < cutoff:
            self._component_zero_hits.popleft()
        while self._package_hits and self._package_hits[0].ts < cutoff:
            self._package_hits.popleft()
        while self._package_returns and self._package_returns[0].ts < cutoff:
            self._package_returns.popleft()

    def _observe_http_request(self, now: float, fields: dict[str, Any]) -> None:
        route = _to_nonempty_str(fields.get("route")) or _to_nonempty_str(
            fields.get("path")
        )
        path = _to_nonempty_str(fields.get("path")) or route or "<unknown>"
        method = _to_nonempty_str(fields.get("method")) or "GET"
        status_code = _to_int(fields.get("status_code"), default=0)
        duration_ms = _to_float(fields.get("duration_ms"), default=0.0)
        client_ip = _to_nonempty_str(fields.get("client_ip"))
        self._request_events.append(
            _RequestEvent(
                ts=now,
                route=route or path,
                path=path,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
            )
        )

    def _observe_parameter_query(self, now: float, fields: dict[str, Any]) -> None:
        component_type = _to_nonempty_str(fields.get("component_type"))
        if component_type is not None:
            self._component_hits.append(
                _WeightedEvent(ts=now, key=component_type, count=1)
            )
            candidate_count = _to_int(fields.get("candidate_count"), default=-1)
            if candidate_count == 0:
                self._component_zero_hits.append(
                    _WeightedEvent(ts=now, key=component_type, count=1)
                )

        package = _to_nonempty_str(fields.get("package_requested_normalized"))
        if package is None:
            package = _to_nonempty_str(fields.get("package_requested"))
        if package is not None:
            self._package_hits.append(_WeightedEvent(ts=now, key=package, count=1))

    def _observe_parameter_batch(self, now: float, fields: dict[str, Any]) -> None:
        component_counts = fields.get("top_component_types_requested")
        if isinstance(component_counts, list):
            for entry in component_counts:
                if not isinstance(entry, dict):
                    continue
                component_type = _to_nonempty_str(entry.get("component_type"))
                if component_type is None:
                    continue
                count = max(1, _to_int(entry.get("count"), default=1))
                self._component_hits.append(
                    _WeightedEvent(ts=now, key=component_type, count=count)
                )

        component_zero_counts = fields.get("top_component_types_without_candidates")
        if isinstance(component_zero_counts, list):
            for entry in component_zero_counts:
                if not isinstance(entry, dict):
                    continue
                component_type = _to_nonempty_str(entry.get("component_type"))
                if component_type is None:
                    continue
                count = max(1, _to_int(entry.get("count"), default=1))
                self._component_zero_hits.append(
                    _WeightedEvent(ts=now, key=component_type, count=count)
                )

        raw = fields.get("top_packages_requested")
        if not isinstance(raw, list):
            return
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            package = _to_nonempty_str(entry.get("package"))
            if package is None:
                continue
            count = max(1, _to_int(entry.get("count"), default=1))
            self._package_hits.append(_WeightedEvent(ts=now, key=package, count=count))

    def _observe_full_response(self, now: float, fields: dict[str, Any]) -> None:
        raw = fields.get("top_packages_returned")
        if not isinstance(raw, list):
            return
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            package = _to_nonempty_str(entry.get("package"))
            if package is None:
                continue
            count = max(1, _to_int(entry.get("count"), default=1))
            self._package_returns.append(
                _WeightedEvent(ts=now, key=package, count=count)
            )

    def _build_timeline(
        self,
        *,
        window_requests: list[_RequestEvent],
        cutoff: float,
        now: float,
    ) -> list[dict[str, Any]]:
        bucket_start = int(cutoff // _BUCKET_SECONDS) * _BUCKET_SECONDS
        bucket_end = int(now // _BUCKET_SECONDS) * _BUCKET_SECONDS
        buckets: dict[int, dict[str, Any]] = {}
        current = bucket_start
        while current <= bucket_end:
            buckets[current] = {"count": 0, "errors": 0, "durations": []}
            current += _BUCKET_SECONDS

        for item in window_requests:
            key = int(item.ts // _BUCKET_SECONDS) * _BUCKET_SECONDS
            bucket = buckets.get(key)
            if bucket is None:
                continue
            bucket["count"] += 1
            if item.status_code >= 500:
                bucket["errors"] += 1
            bucket["durations"].append(item.duration_ms)

        out: list[dict[str, Any]] = []
        for key in sorted(buckets):
            bucket = buckets[key]
            durations = sorted(bucket["durations"])
            out.append(
                {
                    "timestamp": _to_iso_utc(float(key)),
                    "requests_per_min": round(
                        (bucket["count"] / _BUCKET_SECONDS) * 60.0, 3
                    ),
                    "error_count": int(bucket["errors"]),
                    "p95_ms": _quantile(durations, 0.95),
                }
            )
        return out

    def _build_origin_summary(
        self, origin_counts: Counter[str]
    ) -> list[dict[str, Any]]:
        total = sum(origin_counts.values())
        if total <= 0:
            return []
        out: list[dict[str, Any]] = []
        for ip, count in origin_counts.most_common(20):
            origin = _origin_from_ip(ip)
            origin["count"] = count
            origin["request_share_pct"] = round((count / total) * 100.0, 3)
            out.append(origin)
        return out


def test_dashboard_metrics_observes_requests_and_queries() -> None:
    metrics = DashboardMetrics()
    metrics.observe(
        "serve.http.request",
        {
            "route": "/v1/components/parameters/query",
            "path": "/v1/components/parameters/query",
            "method": "POST",
            "status_code": 200,
            "duration_ms": 1.7,
            "client_ip": "127.0.0.1",
        },
    )
    metrics.observe(
        "serve.parameters.query",
        {
            "component_type": "resistor",
            "package_requested_normalized": "0402",
        },
    )
    metrics.observe(
        "serve.components.full",
        {"top_packages_returned": [{"package": "0402", "count": 3}]},
    )

    payload = metrics.snapshot(window_seconds=900)
    assert payload["http"]["total_requests"] == 1
    assert payload["component_demand"] == [{"component_type": "resistor", "count": 1}]
    assert payload["component_zero_results"] == []
    assert payload["package_hits"] == [{"package": "0402", "count": 1}]
    assert payload["package_returns"] == [{"package": "0402", "count": 3}]
    assert payload["origins"][0]["label"] == "Local Network"


def test_dashboard_metrics_batch_includes_component_and_zero_result_counts() -> None:
    metrics = DashboardMetrics()
    metrics.observe(
        "serve.parameters.batch",
        {
            "top_component_types_requested": [
                {"component_type": "crystal", "count": 2},
                {"component_type": "resistor", "count": 1},
            ],
            "top_component_types_without_candidates": [
                {"component_type": "crystal", "count": 1},
            ],
            "top_packages_requested": [{"package": "HC49U", "count": 2}],
        },
    )

    payload = metrics.snapshot(window_seconds=900)
    assert payload["component_demand"] == [
        {"component_type": "crystal", "count": 2},
        {"component_type": "resistor", "count": 1},
    ]
    assert payload["component_zero_results"] == [
        {"component_type": "crystal", "count": 1}
    ]
    assert payload["package_hits"] == [{"package": "HC49U", "count": 2}]
