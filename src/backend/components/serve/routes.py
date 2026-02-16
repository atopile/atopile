from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder

from .interfaces import (
    AssetLoadError,
    BatchQueryValidationError,
    BundleStore,
    DetailStore,
    FastLookupStore,
    QueryValidationError,
    ServeError,
    SnapshotSchemaError,
)
from .query_normalization import normalize_package
from .schemas import (
    AssetRecordModel,
    ComponentCandidateModel,
    ComponentsSearchRequest,
    ComponentsSearchResponse,
    ComponentsSearchResultModel,
    ComponentsFullRequest,
    FullResponseMetadata,
    ManufacturerPartLookupResponse,
    ParametersBatchQueryRequest,
    ParametersBatchQueryResponse,
    ParametersQueryRequest,
    ParametersQueryResponse,
)
from .telemetry import get_request_id, log_event

router = APIRouter(prefix="/v1/components", tags=["components"])


@dataclass(frozen=True)
class ServeServices:
    fast_lookup: FastLookupStore
    detail_store: DetailStore
    bundle_store: BundleStore
    vector_search: Any | None = None


def get_services(request: Request) -> ServeServices:
    services = getattr(request.app.state, "components_services", None)
    if services is None:
        raise HTTPException(
            status_code=500, detail="Components services not configured"
        )
    return services


def _duration_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000.0, 3)


@router.post("/parameters/query", response_model=ParametersQueryResponse)
async def query_component_parameters(
    request: Request,
    payload: ParametersQueryRequest,
    services: ServeServices = Depends(get_services),
) -> ParametersQueryResponse:
    started_at = time.perf_counter()
    request_id = get_request_id(request)
    query = payload.to_domain_query()
    normalized_package: str | None = None
    if query.package is not None:
        normalized_package = normalize_package(
            str(payload.component_type),
            query.package,
        )
    try:
        candidates = await asyncio.to_thread(
            services.fast_lookup.query_component,
            str(payload.component_type),
            query,
        )
    except SnapshotSchemaError as exc:
        log_event(
            "serve.parameters.query_error",
            level=logging.ERROR,
            request_id=request_id,
            component_type=str(payload.component_type),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))
    except QueryValidationError as exc:
        log_event(
            "serve.parameters.query_error",
            level=logging.WARNING,
            request_id=request_id,
            component_type=str(payload.component_type),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except ServeError as exc:
        log_event(
            "serve.parameters.query_error",
            level=logging.ERROR,
            request_id=request_id,
            component_type=str(payload.component_type),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))

    response_items = [ComponentCandidateModel.from_domain(item) for item in candidates]
    log_event(
        "serve.parameters.query",
        request_id=request_id,
        component_type=str(payload.component_type),
        qty=query.qty,
        limit=query.limit,
        package_requested=query.package,
        package_requested_normalized=normalized_package,
        exact_filter_count=len(query.exact),
        range_filter_count=len(query.ranges),
        candidate_count=len(response_items),
        lookup_ms=_duration_ms(started_at),
    )
    return ParametersQueryResponse(
        component_type=payload.component_type,
        candidates=response_items,
        total=len(response_items),
    )


@router.post("/search", response_model=ComponentsSearchResponse)
async def search_components(
    request: Request,
    payload: ComponentsSearchRequest,
    services: ServeServices = Depends(get_services),
) -> ComponentsSearchResponse:
    started_at = time.perf_counter()
    request_id = get_request_id(request)
    if services.vector_search is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "vector search index is not configured; "
                "set ATOPILE_COMPONENTS_VECTOR_INDEX_DIR"
            ),
        )
    try:
        search_mode = (
            "raw_vector"
            if payload.raw_vector_only is True
            else payload.search_mode
        )
        results = await asyncio.to_thread(
            services.vector_search.search,
            query=payload.query,
            limit=payload.limit,
            component_type=payload.component_type,
            package=payload.package,
            in_stock_only=payload.in_stock_only,
            prefer_in_stock=payload.prefer_in_stock,
            prefer_basic=payload.prefer_basic,
            search_mode=search_mode,
        )
    except Exception as exc:
        log_event(
            "serve.search.error",
            level=logging.ERROR,
            request_id=request_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))

    response_results = [
        ComponentsSearchResultModel(
            lcsc_id=item.lcsc_id,
            score=item.score,
            cosine_score=item.cosine_score,
            reasons=item.reasons,
            component_type=item.component_type,
            manufacturer_name=item.manufacturer_name,
            part_number=item.part_number,
            package=item.package,
            description=item.description,
            stock=item.stock,
            is_basic=item.is_basic,
            is_preferred=item.is_preferred,
        )
        for item in results
    ]
    log_event(
        "serve.search",
        request_id=request_id,
        query=payload.query,
        limit=payload.limit,
        component_type=payload.component_type,
        package=payload.package,
        in_stock_only=payload.in_stock_only,
        search_mode=(
            "raw_vector"
            if payload.raw_vector_only is True
            else payload.search_mode
        ),
        result_count=len(response_results),
        lookup_ms=_duration_ms(started_at),
    )
    return ComponentsSearchResponse(
        query=payload.query,
        total=len(response_results),
        results=response_results,
    )


@router.post("/parameters/query/batch", response_model=ParametersBatchQueryResponse)
async def query_component_parameters_batch(
    request: Request,
    payload: ParametersBatchQueryRequest,
    services: ServeServices = Depends(get_services),
) -> ParametersBatchQueryResponse:
    started_at = time.perf_counter()
    request_id = get_request_id(request)
    queries: list[tuple[str, Any]] = []
    requested_package_counts: Counter[str] = Counter()
    for item in payload.queries:
        domain_query = item.to_domain_query()
        component_type = str(item.component_type)
        queries.append((component_type, domain_query))
        if domain_query.package is None:
            continue
        normalized_package = normalize_package(component_type, domain_query.package)
        if normalized_package:
            requested_package_counts[normalized_package] += 1
    try:
        batch_candidates = await asyncio.to_thread(
            services.fast_lookup.query_components_batch,
            queries,
        )
    except BatchQueryValidationError as exc:
        invalid_count = sum(error is not None for error in exc.errors)
        log_event(
            "serve.parameters.batch_error",
            level=logging.WARNING,
            request_id=request_id,
            total_queries=len(payload.queries),
            invalid_queries=invalid_count,
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [
                    {"message": error} if error is not None else None
                    for error in exc.errors
                ]
            },
        )
    except QueryValidationError as exc:
        log_event(
            "serve.parameters.batch_error",
            level=logging.WARNING,
            request_id=request_id,
            total_queries=len(payload.queries),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except SnapshotSchemaError as exc:
        log_event(
            "serve.parameters.batch_error",
            level=logging.ERROR,
            request_id=request_id,
            total_queries=len(payload.queries),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))
    except ServeError as exc:
        log_event(
            "serve.parameters.batch_error",
            level=logging.ERROR,
            request_id=request_id,
            total_queries=len(payload.queries),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))

    if len(batch_candidates) != len(payload.queries):
        log_event(
            "serve.parameters.batch_error",
            level=logging.ERROR,
            request_id=request_id,
            total_queries=len(payload.queries),
            error_type="BatchResultMismatch",
            returned_queries=len(batch_candidates),
        )
        raise HTTPException(status_code=500, detail="batch response size mismatch")

    ordered_results: list[ParametersQueryResponse] = []
    for item, candidates in zip(payload.queries, batch_candidates, strict=True):
        response_items = [
            ComponentCandidateModel.from_domain(candidate) for candidate in candidates
        ]
        ordered_results.append(
            ParametersQueryResponse(
                component_type=item.component_type,
                candidates=response_items,
                total=len(response_items),
            )
        )
    total_candidates = sum(result.total for result in ordered_results)
    log_event(
        "serve.parameters.batch",
        request_id=request_id,
        total_queries=len(ordered_results),
        total_candidates=total_candidates,
        package_filter_queries=sum(requested_package_counts.values()),
        top_packages_requested=[
            {"package": package, "count": count}
            for package, count in requested_package_counts.most_common(10)
        ],
        lookup_ms=_duration_ms(started_at),
    )
    return ParametersBatchQueryResponse(
        results=ordered_results,
        total_queries=len(ordered_results),
    )


@router.get(
    "/mfr/{manufacturer_name}/{part_number}",
    response_model=ManufacturerPartLookupResponse,
)
async def lookup_components_by_manufacturer_part(
    request: Request,
    manufacturer_name: str,
    part_number: str,
    limit: int = Query(default=50, ge=1, le=500),
    services: ServeServices = Depends(get_services),
) -> ManufacturerPartLookupResponse:
    started_at = time.perf_counter()
    request_id = get_request_id(request)
    try:
        component_ids = await asyncio.to_thread(
            services.detail_store.lookup_component_ids_by_manufacturer_part,
            manufacturer_name,
            part_number,
            limit=limit,
        )
    except SnapshotSchemaError as exc:
        log_event(
            "serve.mfr.lookup_error",
            level=logging.ERROR,
            request_id=request_id,
            limit=limit,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))
    except QueryValidationError as exc:
        log_event(
            "serve.mfr.lookup_error",
            level=logging.WARNING,
            request_id=request_id,
            limit=limit,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except ServeError as exc:
        log_event(
            "serve.mfr.lookup_error",
            level=logging.ERROR,
            request_id=request_id,
            limit=limit,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))

    if not component_ids:
        log_event(
            "serve.mfr.lookup_not_found",
            level=logging.WARNING,
            request_id=request_id,
            manufacturer_name=manufacturer_name,
            part_number=part_number,
            limit=limit,
            lookup_ms=_duration_ms(started_at),
        )
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching component for "
                f"manufacturer='{manufacturer_name}', part_number='{part_number}'"
            ),
        )

    log_event(
        "serve.mfr.lookup",
        request_id=request_id,
        manufacturer_name=manufacturer_name,
        part_number=part_number,
        limit=limit,
        result_count=len(component_ids),
        lookup_ms=_duration_ms(started_at),
    )

    return ManufacturerPartLookupResponse(
        manufacturer_name=manufacturer_name,
        part_number=part_number,
        component_ids=component_ids,
        total=len(component_ids),
    )


@router.post("/full")
async def get_full_components(
    request: Request,
    payload: ComponentsFullRequest,
    services: ServeServices = Depends(get_services),
) -> Response:
    started_at = time.perf_counter()
    request_id = get_request_id(request)
    lcsc_ids = payload.deduplicated_ids()
    try:
        detail_started = time.perf_counter()
        components_by_id = await asyncio.to_thread(
            services.detail_store.get_components,
            lcsc_ids,
        )
        detail_lookup_ms = _duration_ms(detail_started)
        missing = [
            component_id
            for component_id in lcsc_ids
            if component_id not in components_by_id
        ]
        if missing:
            log_event(
                "serve.components.full_missing",
                level=logging.WARNING,
                request_id=request_id,
                requested_count=len(lcsc_ids),
                missing_count=len(missing),
                missing_preview=missing[:10],
                detail_lookup_ms=detail_lookup_ms,
            )
            raise HTTPException(
                status_code=404,
                detail=f"Unknown component_ids: {missing}",
            )

        assets_started = time.perf_counter()
        assets_by_id = await asyncio.to_thread(
            services.detail_store.get_asset_manifest,
            lcsc_ids,
        )
        asset_lookup_ms = _duration_ms(assets_started)
        bundle_started = time.perf_counter()
        bundle = await asyncio.to_thread(services.bundle_store.build_bundle, lcsc_ids)
        bundle_build_ms = _duration_ms(bundle_started)
    except SnapshotSchemaError as exc:
        log_event(
            "serve.components.full_error",
            level=logging.ERROR,
            request_id=request_id,
            requested_count=len(lcsc_ids),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))
    except ServeError as exc:
        log_event(
            "serve.components.full_error",
            level=logging.ERROR,
            request_id=request_id,
            requested_count=len(lcsc_ids),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))

    metadata = FullResponseMetadata(
        components=[components_by_id[lcsc_id] for lcsc_id in lcsc_ids],
        asset_manifest={
            str(lcsc_id): [
                AssetRecordModel.from_domain(asset)
                for asset in assets_by_id.get(lcsc_id, [])
            ]
            for lcsc_id in lcsc_ids
        },
        bundle_filename=bundle.filename,
        bundle_media_type=bundle.media_type,
        bundle_sha256=bundle.sha256,
        bundle_size_bytes=len(bundle.data),
    )

    boundary = f"components-{uuid.uuid4().hex}"
    bundle_disposition = f'attachment; name="bundle"; filename="{bundle.filename}"'
    body = _encode_multipart(
        boundary=boundary,
        parts=[
            {
                "content_type": "application/json",
                "headers": {"Content-Disposition": 'inline; name="metadata"'},
                "body": json.dumps(jsonable_encoder(metadata)).encode("utf-8"),
            },
            {
                "content_type": bundle.media_type,
                "headers": {
                    "Content-Disposition": bundle_disposition,
                    "X-Bundle-SHA256": bundle.sha256,
                },
                "body": bundle.data,
            },
        ],
    )
    total_assets = sum(len(assets_by_id.get(lcsc_id, [])) for lcsc_id in lcsc_ids)
    embedded_assets = sum(
        1
        for lcsc_id in lcsc_ids
        for asset in assets_by_id.get(lcsc_id, [])
        if asset.stored_key is not None
    )
    package_counts = Counter(
        str(component.get("package", "")).strip() or "<unknown>"
        for component in components_by_id.values()
        if isinstance(component, dict)
    )
    top_packages = [
        {"package": package, "count": count}
        for package, count in package_counts.most_common(10)
    ]
    log_event(
        "serve.components.full",
        request_id=request_id,
        requested_count=len(lcsc_ids),
        returned_count=len(components_by_id),
        asset_count=total_assets,
        embedded_asset_count=embedded_assets,
        reference_asset_count=total_assets - embedded_assets,
        bundle_size_bytes=len(bundle.data),
        detail_lookup_ms=detail_lookup_ms,
        asset_lookup_ms=asset_lookup_ms,
        bundle_build_ms=bundle_build_ms,
        total_ms=_duration_ms(started_at),
        distinct_packages_returned=len(package_counts),
        top_packages_returned=top_packages,
    )
    return Response(
        content=body,
        media_type=f"multipart/mixed; boundary={boundary}",
    )


def _encode_multipart(
    *,
    boundary: str,
    parts: list[dict[str, Any]],
) -> bytes:
    out = bytearray()
    boundary_bytes = boundary.encode("ascii")
    for part in parts:
        out.extend(b"--")
        out.extend(boundary_bytes)
        out.extend(b"\r\n")
        out.extend(f"Content-Type: {part['content_type']}\r\n".encode("ascii"))
        for key, value in part["headers"].items():
            out.extend(f"{key}: {value}\r\n".encode("ascii"))
        out.extend(b"\r\n")
        out.extend(part["body"])
        out.extend(b"\r\n")
    out.extend(b"--")
    out.extend(boundary_bytes)
    out.extend(b"--\r\n")
    return bytes(out)


def test_parameters_query_route_returns_candidates() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import BundleArtifact, ComponentCandidate

    class _FastLookup:
        def query_component(self, component_type, _query):
            if component_type != "resistor":
                return []
            return [
                ComponentCandidate(
                    lcsc_id=1,
                    stock=10,
                    is_basic=True,
                    is_preferred=False,
                    pick_parameters={"package": "0603"},
                )
            ]

        def query_resistors(self, _query):
            return self.query_component("resistor", _query)

        def query_capacitors(self, _query):
            return self.query_component("capacitor", _query)

        def query_capacitors_polarized(self, _query):
            return self.query_component("capacitor_polarized", _query)

        def query_inductors(self, _query):
            return self.query_component("inductor", _query)

        def query_diodes(self, _query):
            return self.query_component("diode", _query)

        def query_leds(self, _query):
            return self.query_component("led", _query)

        def query_bjts(self, _query):
            return self.query_component("bjt", _query)

        def query_mosfets(self, _query):
            return self.query_component("mosfet", _query)

    class _Detail:
        def get_components(self, _ids):
            return {1: {"lcsc_id": 1}}

        def get_asset_manifest(self, _ids):
            return {1: []}

        def lookup_component_ids_by_manufacturer_part(
            self, _manufacturer_name, _part_number, *, limit=50
        ):
            return [1][:limit]

    class _Bundle:
        def build_bundle(self, _ids):
            return BundleArtifact(
                data=b"payload",
                filename="bundle.tar.zst",
                media_type="application/zstd",
                sha256="a" * 64,
                manifest={},
            )

    app = FastAPI()
    app.include_router(router)
    app.state.components_services = ServeServices(
        fast_lookup=_FastLookup(),
        detail_store=_Detail(),
        bundle_store=_Bundle(),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/components/parameters/query",
        json={"component_type": "resistor", "qty": 1, "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["candidates"][0]["lcsc_id"] == 1


def test_parameters_batch_query_route_returns_ordered_results() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import BundleArtifact, ComponentCandidate

    class _FastLookup:
        def query_components_batch(self, queries):
            return [
                self.query_component(component_type, query)
                for component_type, query in queries
            ]

        def query_component(self, component_type, _query):
            if component_type == "resistor":
                return [
                    ComponentCandidate(
                        lcsc_id=11,
                        stock=10,
                        is_basic=True,
                        is_preferred=False,
                        pick_parameters={"package": "0603"},
                    )
                ]
            if component_type == "capacitor":
                return [
                    ComponentCandidate(
                        lcsc_id=22,
                        stock=20,
                        is_basic=False,
                        is_preferred=True,
                        pick_parameters={"package": "0402"},
                    )
                ]
            return []

        def query_resistors(self, _query):
            return self.query_component("resistor", _query)

        def query_capacitors(self, _query):
            return self.query_component("capacitor", _query)

        def query_capacitors_polarized(self, _query):
            return self.query_component("capacitor_polarized", _query)

        def query_inductors(self, _query):
            return self.query_component("inductor", _query)

        def query_diodes(self, _query):
            return self.query_component("diode", _query)

        def query_leds(self, _query):
            return self.query_component("led", _query)

        def query_bjts(self, _query):
            return self.query_component("bjt", _query)

        def query_mosfets(self, _query):
            return self.query_component("mosfet", _query)

    class _Detail:
        def get_components(self, _ids):
            return {}

        def get_asset_manifest(self, _ids):
            return {}

        def lookup_component_ids_by_manufacturer_part(
            self, _manufacturer_name, _part_number, *, limit=50
        ):
            return [1][:limit]

    class _Bundle:
        def build_bundle(self, _ids):
            return BundleArtifact(
                data=b"payload",
                filename="bundle.tar.zst",
                media_type="application/zstd",
                sha256="a" * 64,
                manifest={},
            )

    app = FastAPI()
    app.include_router(router)
    app.state.components_services = ServeServices(
        fast_lookup=_FastLookup(),
        detail_store=_Detail(),
        bundle_store=_Bundle(),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/components/parameters/query/batch",
        json={
            "queries": [
                {"component_type": "resistor", "qty": 1, "limit": 10},
                {"component_type": "capacitor", "qty": 1, "limit": 10},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_queries"] == 2
    assert payload["results"][0]["component_type"] == "resistor"
    assert payload["results"][0]["candidates"][0]["lcsc_id"] == 11
    assert payload["results"][1]["component_type"] == "capacitor"
    assert payload["results"][1]["candidates"][0]["lcsc_id"] == 22


def test_full_route_returns_multipart() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import AssetRecord, BundleArtifact, ComponentCandidate

    class _FastLookup:
        def query_component(self, component_type, _query):
            if component_type != "resistor":
                return []
            return [
                ComponentCandidate(lcsc_id=1, stock=1, is_basic=None, is_preferred=None)
            ]

        def query_resistors(self, _query):
            return self.query_component("resistor", _query)

        def query_capacitors(self, _query):
            return self.query_component("capacitor", _query)

        def query_capacitors_polarized(self, _query):
            return self.query_component("capacitor_polarized", _query)

        def query_inductors(self, _query):
            return self.query_component("inductor", _query)

        def query_diodes(self, _query):
            return self.query_component("diode", _query)

        def query_leds(self, _query):
            return self.query_component("led", _query)

        def query_bjts(self, _query):
            return self.query_component("bjt", _query)

        def query_mosfets(self, _query):
            return self.query_component("mosfet", _query)

    class _Detail:
        def get_components(self, _ids):
            return {1: {"lcsc_id": 1, "category": "Resistors"}}

        def get_asset_manifest(self, _ids):
            return {
                1: [
                    AssetRecord(
                        lcsc_id=1,
                        artifact_type="datasheet_pdf",
                        stored_key="objects/datasheet_pdf/a.zst",
                    )
                ]
            }

        def lookup_component_ids_by_manufacturer_part(
            self, _manufacturer_name, _part_number, *, limit=50
        ):
            return [1][:limit]

    class _Bundle:
        def build_bundle(self, _ids):
            return BundleArtifact(
                data=b"bundle-bytes",
                filename="bundle.tar.zst",
                media_type="application/zstd",
                sha256="b" * 64,
                manifest={},
            )

    app = FastAPI()
    app.include_router(router)
    app.state.components_services = ServeServices(
        fast_lookup=_FastLookup(),
        detail_store=_Detail(),
        bundle_store=_Bundle(),
    )
    client = TestClient(app)

    response = client.post("/v1/components/full", json={"component_ids": [1]})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/mixed; boundary=")


def test_parameters_query_route_invalid_filter_returns_400() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import BundleArtifact

    class _FastLookup:
        def query_component(self, _component_type, _query):
            raise QueryValidationError("Unknown filter column: does_not_exist")

        def query_resistors(self, _query):
            return self.query_component("resistor", _query)

        def query_capacitors(self, _query):
            return self.query_component("capacitor", _query)

        def query_capacitors_polarized(self, _query):
            return self.query_component("capacitor_polarized", _query)

        def query_inductors(self, _query):
            return self.query_component("inductor", _query)

        def query_diodes(self, _query):
            return self.query_component("diode", _query)

        def query_leds(self, _query):
            return self.query_component("led", _query)

        def query_bjts(self, _query):
            return self.query_component("bjt", _query)

        def query_mosfets(self, _query):
            return self.query_component("mosfet", _query)

    class _Detail:
        def get_components(self, _ids):
            return {}

        def get_asset_manifest(self, _ids):
            return {}

        def lookup_component_ids_by_manufacturer_part(
            self, _manufacturer_name, _part_number, *, limit=50
        ):
            return []

    class _Bundle:
        def build_bundle(self, _ids):
            return BundleArtifact(
                data=b"",
                filename="bundle.tar.zst",
                media_type="application/zstd",
                sha256="a" * 64,
                manifest={},
            )

    app = FastAPI()
    app.include_router(router)
    app.state.components_services = ServeServices(
        fast_lookup=_FastLookup(),
        detail_store=_Detail(),
        bundle_store=_Bundle(),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/components/parameters/query",
        json={"component_type": "resistor"},
    )
    assert response.status_code == 400
    assert "Unknown filter column" in response.json()["detail"]


def test_full_route_bundle_error_returns_500() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import ComponentCandidate

    class _FastLookup:
        def query_component(self, component_type, _query):
            if component_type != "resistor":
                return []
            return [
                ComponentCandidate(
                    lcsc_id=1,
                    stock=1,
                    is_basic=True,
                    is_preferred=False,
                )
            ]

        def query_resistors(self, _query):
            return self.query_component("resistor", _query)

        def query_capacitors(self, _query):
            return self.query_component("capacitor", _query)

        def query_capacitors_polarized(self, _query):
            return self.query_component("capacitor_polarized", _query)

        def query_inductors(self, _query):
            return self.query_component("inductor", _query)

        def query_diodes(self, _query):
            return self.query_component("diode", _query)

        def query_leds(self, _query):
            return self.query_component("led", _query)

        def query_bjts(self, _query):
            return self.query_component("bjt", _query)

        def query_mosfets(self, _query):
            return self.query_component("mosfet", _query)

    class _Detail:
        def get_components(self, _ids):
            return {1: {"lcsc_id": 1}}

        def get_asset_manifest(self, _ids):
            return {1: []}

        def lookup_component_ids_by_manufacturer_part(
            self, _manufacturer_name, _part_number, *, limit=50
        ):
            return [1][:limit]

    class _Bundle:
        def build_bundle(self, _ids):
            raise AssetLoadError("asset blob not found for key: objects/missing.zst")

    app = FastAPI()
    app.include_router(router)
    app.state.components_services = ServeServices(
        fast_lookup=_FastLookup(),
        detail_store=_Detail(),
        bundle_store=_Bundle(),
    )
    client = TestClient(app)

    response = client.post("/v1/components/full", json={"component_ids": [1]})
    assert response.status_code == 500
    assert "asset blob not found" in response.json()["detail"]


def test_mfr_lookup_route_returns_lcsc_ids() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import BundleArtifact

    class _FastLookup:
        def query_component(self, _component_type, _query):
            return []

        def query_resistors(self, _query):
            return []

        def query_capacitors(self, _query):
            return []

        def query_capacitors_polarized(self, _query):
            return []

        def query_inductors(self, _query):
            return []

        def query_diodes(self, _query):
            return []

        def query_leds(self, _query):
            return []

        def query_bjts(self, _query):
            return []

        def query_mosfets(self, _query):
            return []

    class _Detail:
        def get_components(self, _ids):
            return {}

        def get_asset_manifest(self, _ids):
            return {}

        def lookup_component_ids_by_manufacturer_part(
            self, manufacturer_name, part_number, *, limit=50
        ):
            assert manufacturer_name == "Raspberry Pi"
            assert part_number == "RP2040"
            return [2040, 1234][:limit]

    class _Bundle:
        def build_bundle(self, _ids):
            return BundleArtifact(
                data=b"",
                filename="bundle.tar.zst",
                media_type="application/zstd",
                sha256="a" * 64,
                manifest={},
            )

    app = FastAPI()
    app.include_router(router)
    app.state.components_services = ServeServices(
        fast_lookup=_FastLookup(),
        detail_store=_Detail(),
        bundle_store=_Bundle(),
    )
    client = TestClient(app)

    response = client.get("/v1/components/mfr/Raspberry%20Pi/RP2040?limit=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["component_ids"] == [2040]
    assert payload["total"] == 1
