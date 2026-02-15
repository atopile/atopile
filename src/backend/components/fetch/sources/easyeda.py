from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

from ..compression import compare_bytes, sha256_hex
from ..config import FetchConfig
from ..models import ArtifactType, FetchArtifactRecord
from ..storage.manifest_store import LocalManifestStore
from ..storage.object_store import LocalObjectStore

EASYEDA_COMPONENT_API = (
    "https://easyeda.com/api/products/{lcsc_component}/components?version=6.4.19.5"
)
EASYEDA_OBJ_API = "https://modules.easyeda.com/3dmodel/{uuid}"
EASYEDA_STEP_API = "https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/{uuid}"


class EasyedaFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class EasyedaCadPayload:
    cad_data: dict[str, Any]
    source_url: str
    source_meta: dict[str, object]


def fetch_easyeda_cad_payload(
    lcsc_id: int, *, timeout_s: float, client: httpx.Client
) -> EasyedaCadPayload:
    lcsc_component = f"C{lcsc_id}"
    url = EASYEDA_COMPONENT_API.format(lcsc_component=lcsc_component)
    response = client.get(url, timeout=timeout_s)
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise EasyedaFetchError("EasyEDA returned non-object JSON payload")

    if payload.get("success") is False and payload.get("code") == 404:
        raise EasyedaFetchError(f"EasyEDA component not found for {lcsc_component}")

    cad_data = payload.get("result")
    if not isinstance(cad_data, dict):
        raise EasyedaFetchError("EasyEDA payload missing object `result` field")

    return EasyedaCadPayload(
        cad_data=cad_data,
        source_url=url,
        source_meta={
            "status_code": response.status_code,
            "response_code": payload.get("code"),
            "response_success": payload.get("success"),
        },
    )


def extract_3d_uuid(cad_data: dict[str, Any]) -> str | None:
    try:
        shape = cad_data["packageDetail"]["dataStr"]["shape"]
    except KeyError:
        return None
    if not isinstance(shape, list):
        return None

    for line in shape:
        if not isinstance(line, str):
            continue
        if not line.startswith("SVGNODE~"):
            continue
        try:
            raw_json = line.split("~", 1)[1]
            svg_node = json.loads(raw_json)
            uuid = svg_node["attrs"]["uuid"]
            if isinstance(uuid, str) and uuid:
                return uuid
        except (IndexError, KeyError, TypeError, json.JSONDecodeError):
            continue
    return None


def convert_easyeda_cad_to_kicad_footprint(cad_data: dict[str, Any]) -> bytes:
    from easyeda2kicad.easyeda.easyeda_importer import EasyedaFootprintImporter
    from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad

    from faebryk.libs.kicad.fileformats import kicad

    try:
        easyeda_footprint = EasyedaFootprintImporter(
            easyeda_cp_cad_data=cad_data
        ).get_footprint()
    except Exception as ex:
        raise EasyedaFetchError("EasyEDA footprint parsing failed") from ex

    try:
        with tempfile.TemporaryDirectory(prefix="atopile-footprint-") as temp_dir:
            footprint_path = Path(temp_dir) / "footprint.kicad_mod"
            ExporterFootprintKicad(easyeda_footprint).export(str(footprint_path), "")
            raw_footprint = footprint_path.read_text(encoding="utf-8")
    except Exception as ex:
        raise EasyedaFetchError("EasyEDA footprint export to KiCad failed") from ex

    try:
        footprint_v5 = kicad.loads(kicad.footprint_v5.FootprintFile, raw_footprint)
        footprint = kicad.convert(footprint_v5)
        canonical_footprint = kicad.dumps(footprint)
    except Exception as ex:
        raise EasyedaFetchError("KiCad footprint normalization failed") from ex

    return canonical_footprint.encode("utf-8")


def _fetch_optional_binary(
    *,
    url: str,
    timeout_s: float,
    client: httpx.Client,
) -> tuple[bytes | None, dict[str, object]]:
    response = client.get(url, timeout=timeout_s)
    if response.status_code == 404:
        return None, {"status_code": 404}
    response.raise_for_status()
    return response.content, {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
    }


def _store_roundtrip_record(
    *,
    lcsc_id: int,
    artifact_type: ArtifactType,
    source_url: str,
    raw_payload: bytes,
    mime: str | None,
    source_meta: dict[str, object],
    object_store: LocalObjectStore,
    manifest_store: LocalManifestStore,
) -> FetchArtifactRecord:
    blob = object_store.put_raw(artifact_type, raw_payload)
    roundtrip_raw = object_store.get_raw(blob.key)
    compare_ok = compare_bytes(raw_payload, roundtrip_raw) and (
        sha256_hex(raw_payload) == sha256_hex(roundtrip_raw)
    )
    if not compare_ok:
        raise EasyedaFetchError(f"Round-trip compare failed for {artifact_type.value}")

    record = FetchArtifactRecord.now(
        lcsc_id=lcsc_id,
        artifact_type=artifact_type,
        source_url=source_url,
        raw_sha256=blob.raw_sha256,
        raw_size_bytes=blob.raw_size_bytes,
        stored_key=blob.key,
        source_meta=source_meta,
        mime=mime,
        compare_ok=compare_ok,
    )
    manifest_store.append(record)
    return record


def fetch_store_easyeda_assets_with_roundtrip(
    *,
    lcsc_id: int,
    config: FetchConfig,
    object_store: LocalObjectStore,
    manifest_store: LocalManifestStore,
    client: httpx.Client | None = None,
    footprint_converter: Callable[[dict[str, Any]], bytes] | None = None,
) -> list[FetchArtifactRecord]:
    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        cad_payload = fetch_easyeda_cad_payload(
            lcsc_id,
            timeout_s=config.request_timeout_s,
            client=http_client,
        )
        records: list[FetchArtifactRecord] = []

        if footprint_converter is None:
            footprint_converter = convert_easyeda_cad_to_kicad_footprint
        kicad_footprint = footprint_converter(cad_payload.cad_data)
        records.append(
            _store_roundtrip_record(
                lcsc_id=lcsc_id,
                artifact_type=ArtifactType.KICAD_FOOTPRINT_MOD,
                source_url=cad_payload.source_url,
                raw_payload=kicad_footprint,
                mime="application/x-kicad-footprint",
                source_meta=cad_payload.source_meta
                | {
                    "generated_from": "easyeda_cad",
                    "format": "kicad_mod",
                },
                object_store=object_store,
                manifest_store=manifest_store,
            )
        )

        uuid = extract_3d_uuid(cad_payload.cad_data)
        if uuid:
            obj_url = EASYEDA_OBJ_API.format(uuid=uuid)
            obj_payload, obj_meta = _fetch_optional_binary(
                url=obj_url,
                timeout_s=config.request_timeout_s,
                client=http_client,
            )
            if obj_payload is not None:
                records.append(
                    _store_roundtrip_record(
                        lcsc_id=lcsc_id,
                        artifact_type=ArtifactType.MODEL_OBJ,
                        source_url=obj_url,
                        raw_payload=obj_payload,
                        mime="text/plain",
                        source_meta=obj_meta,
                        object_store=object_store,
                        manifest_store=manifest_store,
                    )
                )

            step_url = EASYEDA_STEP_API.format(uuid=uuid)
            step_payload, step_meta = _fetch_optional_binary(
                url=step_url,
                timeout_s=config.request_timeout_s,
                client=http_client,
            )
            if step_payload is not None:
                records.append(
                    _store_roundtrip_record(
                        lcsc_id=lcsc_id,
                        artifact_type=ArtifactType.MODEL_STEP,
                        source_url=step_url,
                        raw_payload=step_payload,
                        mime="model/step",
                        source_meta=step_meta,
                        object_store=object_store,
                        manifest_store=manifest_store,
                    )
                )
        return records
    finally:
        if owns_client:
            http_client.close()


def test_fetch_store_easyeda_assets_with_roundtrip(tmp_path) -> None:
    uuid = "uuid-123"
    cad_data = {
        "packageDetail": {
            "dataStr": {"shape": [f'SVGNODE~{{"attrs":{{"uuid":"{uuid}"}}}}']},
        },
        "description": "test",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "easyeda.com":
            return httpx.Response(
                200,
                json={"code": 200, "success": True, "result": cad_data},
            )
        if request.url.path == f"/3dmodel/{uuid}":
            return httpx.Response(200, content=b"o model\nv 0 0 0\n")
        if request.url.path.endswith(f"/{uuid}"):
            return httpx.Response(200, content=b"ISO-10303-21;\nEND-ISO-10303-21;")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    config = FetchConfig.from_env()
    object_store = LocalObjectStore(tmp_path)
    manifest_store = LocalManifestStore(tmp_path)
    mock_footprint = b'(footprint "easyeda2kicad:R0603")\n'

    def mock_converter(cad: dict[str, Any]) -> bytes:
        assert cad == cad_data
        return mock_footprint

    records = fetch_store_easyeda_assets_with_roundtrip(
        lcsc_id=21190,
        config=config,
        object_store=object_store,
        manifest_store=manifest_store,
        client=client,
        footprint_converter=mock_converter,
    )
    client.close()

    artifact_types = {record.artifact_type for record in records}
    assert ArtifactType.KICAD_FOOTPRINT_MOD in artifact_types
    assert ArtifactType.MODEL_OBJ in artifact_types
    assert ArtifactType.MODEL_STEP in artifact_types


def test_fetch_store_easyeda_assets_partial_when_no_uuid(tmp_path) -> None:
    cad_data = {
        "packageDetail": {"dataStr": {"shape": []}},
        "description": "no-3d",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "easyeda.com":
            return httpx.Response(
                200,
                json={"code": 200, "success": True, "result": cad_data},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    config = FetchConfig.from_env()
    object_store = LocalObjectStore(tmp_path)
    manifest_store = LocalManifestStore(tmp_path)
    mock_footprint = b'(footprint "easyeda2kicad:R0603")\n'

    def mock_converter(cad: dict[str, Any]) -> bytes:
        assert cad == cad_data
        return mock_footprint

    records = fetch_store_easyeda_assets_with_roundtrip(
        lcsc_id=8545,
        config=config,
        object_store=object_store,
        manifest_store=manifest_store,
        client=client,
        footprint_converter=mock_converter,
    )
    client.close()

    artifact_types = {record.artifact_type for record in records}
    assert artifact_types == {
        ArtifactType.KICAD_FOOTPRINT_MOD,
    }


def test_fetch_store_easyeda_assets_fails_when_conversion_fails(tmp_path) -> None:
    cad_data = {
        "packageDetail": {"dataStr": {"shape": []}},
        "description": "conversion-fail",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "easyeda.com":
            return httpx.Response(
                200,
                json={"code": 200, "success": True, "result": cad_data},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    config = FetchConfig.from_env()
    object_store = LocalObjectStore(tmp_path)
    manifest_store = LocalManifestStore(tmp_path)

    def fail_converter(_cad: dict[str, Any]) -> bytes:
        raise EasyedaFetchError("conversion failed")

    with pytest.raises(EasyedaFetchError, match="conversion failed"):
        fetch_store_easyeda_assets_with_roundtrip(
            lcsc_id=8545,
            config=config,
            object_store=object_store,
            manifest_store=manifest_store,
            client=client,
            footprint_converter=fail_converter,
        )
    client.close()
