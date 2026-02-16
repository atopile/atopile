from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .embedding import Embedder
from .index import SearchFilters, VectorStore


@dataclass(frozen=True)
class EvalQuery:
    query: str
    expected_lcsc_ids: list[int]
    filters: SearchFilters
    limit: int = 10


@dataclass(frozen=True)
class EvalResult:
    query: str
    expected_lcsc_ids: list[int]
    returned_lcsc_ids: list[int]
    hit_at_1: bool
    hit_at_5: bool
    hit_at_10: bool
    reciprocal_rank: float
    latency_ms: float


def load_eval_queries(path: Path) -> list[EvalQuery]:
    out: list[EvalQuery] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            payload = json.loads(line)
            filters_obj = payload.get("filters", {})
            out.append(
                EvalQuery(
                    query=str(payload["query"]),
                    expected_lcsc_ids=[int(v) for v in payload["expected_lcsc_ids"]],
                    filters=SearchFilters(
                        component_type=filters_obj.get("component_type"),
                        package=filters_obj.get("package"),
                        in_stock_only=bool(filters_obj.get("in_stock_only", False)),
                    ),
                    limit=int(payload.get("limit", 10)),
                )
            )
    return out


def _reciprocal_rank(expected: set[int], actual: list[int]) -> float:
    for idx, candidate in enumerate(actual, start=1):
        if candidate in expected:
            return 1.0 / float(idx)
    return 0.0


def run_eval(
    *,
    index: VectorStore,
    embedder: Embedder,
    queries: list[EvalQuery],
    prefer_in_stock: bool = True,
    prefer_basic: bool = True,
) -> dict[str, Any]:
    per_query: list[EvalResult] = []
    for query in queries:
        t0 = time.perf_counter()
        results = index.search(
            query=query.query,
            embedder=embedder,
            limit=max(query.limit, 10),
            filters=query.filters,
            prefer_in_stock=prefer_in_stock,
            prefer_basic=prefer_basic,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        returned = [item.lcsc_id for item in results]
        expected = set(query.expected_lcsc_ids)
        per_query.append(
            EvalResult(
                query=query.query,
                expected_lcsc_ids=query.expected_lcsc_ids,
                returned_lcsc_ids=returned,
                hit_at_1=any(v in expected for v in returned[:1]),
                hit_at_5=any(v in expected for v in returned[:5]),
                hit_at_10=any(v in expected for v in returned[:10]),
                reciprocal_rank=_reciprocal_rank(expected, returned),
                latency_ms=dt_ms,
            )
        )

    latencies = [r.latency_ms for r in per_query] or [0.0]
    sorted_lat = sorted(latencies)
    p95_idx = min(len(sorted_lat) - 1, int(0.95 * (len(sorted_lat) - 1)))
    report = {
        "query_count": len(per_query),
        "hit_at_1": sum(1 for r in per_query if r.hit_at_1) / max(1, len(per_query)),
        "hit_at_5": sum(1 for r in per_query if r.hit_at_5) / max(1, len(per_query)),
        "hit_at_10": sum(1 for r in per_query if r.hit_at_10) / max(1, len(per_query)),
        "mrr": sum(r.reciprocal_rank for r in per_query) / max(1, len(per_query)),
        "latency_ms_p50": statistics.median(latencies),
        "latency_ms_p95": sorted_lat[p95_idx],
        "per_query": [asdict(r) for r in per_query],
    }
    return report


def test_reciprocal_rank() -> None:
    assert _reciprocal_rank({3}, [1, 3, 7]) == 0.5
    assert _reciprocal_rank({9}, [1, 3, 7]) == 0.0

