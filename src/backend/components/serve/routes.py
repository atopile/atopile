from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder

from .interfaces import (
    AssetLoadError,
    BundleStore,
    ComponentType,
    DetailStore,
    FastLookupStore,
    QueryValidationError,
    ServeError,
    SnapshotSchemaError,
)
from .schemas import (
    AssetRecordModel,
    ComponentCandidateModel,
    ComponentsFullRequest,
    FullResponseMetadata,
    ParametersQueryRequest,
    ParametersQueryResponse,
)

router = APIRouter(prefix="/v1/components", tags=["components"])


@dataclass(frozen=True)
class ServeServices:
    fast_lookup: FastLookupStore
    detail_store: DetailStore
    bundle_store: BundleStore


def get_services(request: Request) -> ServeServices:
    services = getattr(request.app.state, "components_services", None)
    if services is None:
        raise HTTPException(
            status_code=500, detail="Components services not configured"
        )
    return services


@router.post("/parameters/query", response_model=ParametersQueryResponse)
async def query_component_parameters(
    payload: ParametersQueryRequest,
    services: ServeServices = Depends(get_services),
) -> ParametersQueryResponse:
    query = payload.to_domain_query()
    handler_by_type = {
        ComponentType.RESISTOR: services.fast_lookup.query_resistors,
        ComponentType.CAPACITOR: services.fast_lookup.query_capacitors,
        ComponentType.CAPACITOR_POLARIZED: services.fast_lookup.query_capacitors_polarized,  # noqa: E501
        ComponentType.INDUCTOR: services.fast_lookup.query_inductors,
        ComponentType.DIODE: services.fast_lookup.query_diodes,
        ComponentType.LED: services.fast_lookup.query_leds,
        ComponentType.BJT: services.fast_lookup.query_bjts,
        ComponentType.MOSFET: services.fast_lookup.query_mosfets,
    }
    handler = handler_by_type.get(payload.component_type)
    if handler is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported component_type: {payload.component_type}",
        )
    try:
        candidates = await asyncio.to_thread(handler, query)
    except SnapshotSchemaError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except QueryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ServeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    response_items = [ComponentCandidateModel.from_domain(item) for item in candidates]
    return ParametersQueryResponse(
        component_type=payload.component_type,
        candidates=response_items,
        total=len(response_items),
    )


@router.post("/full")
async def get_full_components(
    payload: ComponentsFullRequest,
    services: ServeServices = Depends(get_services),
) -> Response:
    lcsc_ids = payload.deduplicated_ids()
    try:
        components_by_id = await asyncio.to_thread(
            services.detail_store.get_components,
            lcsc_ids,
        )
        missing = [
            component_id
            for component_id in lcsc_ids
            if component_id not in components_by_id
        ]
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown component_ids: {missing}",
            )

        assets_by_id = await asyncio.to_thread(
            services.detail_store.get_asset_manifest,
            lcsc_ids,
        )
        bundle = await asyncio.to_thread(services.bundle_store.build_bundle, lcsc_ids)
    except SnapshotSchemaError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except ServeError as exc:
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
        def query_resistors(self, _query):
            return [
                ComponentCandidate(
                    lcsc_id=1,
                    stock=10,
                    is_basic=True,
                    is_preferred=False,
                    pick_parameters={"package": "0603"},
                )
            ]

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
            return {1: {"lcsc_id": 1}}

        def get_asset_manifest(self, _ids):
            return {1: []}

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


def test_full_route_returns_multipart() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from .interfaces import AssetRecord, BundleArtifact, ComponentCandidate

    class _FastLookup:
        def query_resistors(self, _query):
            return [
                ComponentCandidate(lcsc_id=1, stock=1, is_basic=None, is_preferred=None)
            ]

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
        def query_resistors(self, _query):
            raise QueryValidationError("Unknown filter column: does_not_exist")

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
        def query_resistors(self, _query):
            return [
                ComponentCandidate(
                    lcsc_id=1,
                    stock=1,
                    is_basic=True,
                    is_preferred=False,
                )
            ]

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
            return {1: {"lcsc_id": 1}}

        def get_asset_manifest(self, _ids):
            return {1: []}

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
