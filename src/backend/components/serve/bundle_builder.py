from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any, Sequence

import zstd

from .interfaces import (
    AssetLoadError,
    AssetRecord,
    BundleArtifact,
    BundleStore,
    DetailStore,
)


class TarZstdBundleBuilder(BundleStore):
    def __init__(self, detail_store: DetailStore, cache_root: Path):
        self.detail_store = detail_store
        self.cache_root = Path(cache_root).resolve()

    def build_bundle(
        self,
        lcsc_ids: Sequence[int],
        artifact_types: Sequence[str] | None = None,
    ) -> BundleArtifact:
        ordered_ids = _unique_ids(lcsc_ids)
        components_by_id = self.detail_store.get_components(ordered_ids)
        assets_by_id = self.detail_store.get_asset_manifest(
            ordered_ids,
            artifact_types=artifact_types,
        )

        manifest: dict[str, Any] = {
            "component_ids": list(ordered_ids),
            "components_found": sorted(int(key) for key in components_by_id.keys()),
            "assets": {},
        }

        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            for lcsc_id in sorted(components_by_id):
                payload = _canonical_json_bytes(components_by_id[lcsc_id])
                _tar_add_bytes(tar, f"components/{lcsc_id}.json", payload)

            for lcsc_id in sorted(assets_by_id):
                manifest_entries: list[dict[str, Any]] = []
                assets = sorted(
                    assets_by_id[lcsc_id],
                    key=lambda item: (item.artifact_type, item.stored_key or ""),
                )
                for index, asset in enumerate(assets, start=1):
                    bundle_path: str | None = None
                    if _is_bundleable_asset(asset):
                        bundle_path = _asset_bundle_path(lcsc_id, asset, index=index)
                        content = self._read_asset_content(asset)
                        _tar_add_bytes(tar, bundle_path, content)
                    manifest_entries.append(
                        {
                            "artifact_type": asset.artifact_type,
                            "stored_key": asset.stored_key,
                            "bundle_path": bundle_path,
                            "encoding": asset.encoding,
                            "mime": asset.mime,
                            "raw_sha256": asset.raw_sha256,
                            "raw_size_bytes": asset.raw_size_bytes,
                            "source_url": asset.source_url,
                            "metadata": asset.metadata,
                            "bundle_status": (
                                "embedded"
                                if bundle_path is not None
                                else "reference_only"
                            ),
                        }
                    )
                manifest["assets"][str(lcsc_id)] = manifest_entries

            _tar_add_bytes(tar, "manifest.json", _canonical_json_bytes(manifest))

        raw_tar = tar_buffer.getvalue()
        compressed = zstd.compress(raw_tar, 10)
        digest = hashlib.sha256(compressed).hexdigest()
        return BundleArtifact(
            data=compressed,
            filename="components-full.tar.zst",
            media_type="application/zstd",
            sha256=digest,
            manifest=manifest,
        )

    def _read_asset_content(self, asset: AssetRecord) -> bytes:
        if not asset.stored_key:
            raise AssetLoadError(f"asset has no stored_key: {asset.artifact_type}")
        abs_path = self._resolve_asset_path(asset.stored_key)
        if not abs_path.exists():
            raise AssetLoadError(f"asset blob not found for key: {asset.stored_key}")
        payload = abs_path.read_bytes()
        encoding = asset.encoding.lower()
        if encoding == "zstd":
            try:
                return zstd.decompress(payload)
            except Exception as exc:
                raise AssetLoadError(
                    f"failed to decompress zstd asset: {asset.stored_key}"
                ) from exc
        return payload

    def _resolve_asset_path(self, stored_key: str) -> Path:
        abs_path = (self.cache_root / stored_key).resolve()
        try:
            abs_path.relative_to(self.cache_root)
        except ValueError as exc:
            raise AssetLoadError(f"asset key escapes cache root: {stored_key}") from exc
        return abs_path


def _asset_bundle_path(lcsc_id: int, asset: AssetRecord, *, index: int) -> str:
    if not asset.stored_key:
        raise AssetLoadError(f"asset has no stored_key: {asset.artifact_type}")
    key_name = Path(asset.stored_key).name
    if asset.encoding.lower() == "zstd" and key_name.endswith(".zst"):
        key_name = key_name[: -len(".zst")]
    return f"assets/{lcsc_id}/{index:03d}_{asset.artifact_type}_{key_name}"


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _tar_add_bytes(tar: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(payload)
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    tar.addfile(info, io.BytesIO(payload))


def _unique_ids(values: Sequence[int]) -> tuple[int, ...]:
    seen: set[int] = set()
    out: list[int] = []
    for value in values:
        normalized = int(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return tuple(out)


def _is_bundleable_asset(asset: AssetRecord) -> bool:
    if not asset.stored_key:
        return False
    return asset.stored_key.startswith("objects/")


def test_tar_zstd_bundle_builder_builds_manifest_and_assets(tmp_path) -> None:
    captured: dict[str, Any] = {}

    class _DetailStore:
        def get_components(self, lcsc_ids):
            return {
                int(component_id): {"lcsc_id": int(component_id)}
                for component_id in lcsc_ids
            }

        def get_asset_manifest(self, lcsc_ids, artifact_types=None):
            captured["artifact_types"] = artifact_types
            out: dict[int, list[AssetRecord]] = {}
            for component_id in lcsc_ids:
                out[int(component_id)] = [
                    AssetRecord(
                        lcsc_id=int(component_id),
                        artifact_type="datasheet_pdf",
                        stored_key="objects/datasheet_pdf/abc.zst",
                    )
                ]
            return out

    cache_root = tmp_path
    object_path = cache_root / "objects" / "datasheet_pdf" / "abc.zst"
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(zstd.compress(b"pdf-bytes", 10))

    builder = TarZstdBundleBuilder(_DetailStore(), cache_root)
    artifact = builder.build_bundle([42], artifact_types=["datasheet_pdf"])
    assert captured["artifact_types"] == ["datasheet_pdf"]
    assert artifact.filename.endswith(".tar.zst")
    assert artifact.media_type == "application/zstd"
    assert len(artifact.sha256) == 64

    tar_bytes = zstd.decompress(artifact.data)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tar:
        names = sorted(tar.getnames())
        assert "manifest.json" in names
        asset_name = "assets/42/001_datasheet_pdf_abc"
        assert asset_name in names
        extracted = tar.extractfile(asset_name)
        assert extracted is not None
        assert extracted.read() == b"pdf-bytes"


def test_tar_zstd_bundle_builder_rejects_path_traversal(tmp_path) -> None:
    class _DetailStore:
        def get_components(self, _lcsc_ids):
            return {42: {"lcsc_id": 42}}

        def get_asset_manifest(self, _lcsc_ids, artifact_types=None):
            return {
                42: [
                    AssetRecord(
                        lcsc_id=42,
                        artifact_type="datasheet_pdf",
                        stored_key="objects/../../escape.zst",
                    )
                ]
            }

    builder = TarZstdBundleBuilder(_DetailStore(), tmp_path)
    try:
        builder.build_bundle([42])
    except AssetLoadError as exc:
        assert "escapes cache root" in str(exc)
    else:
        assert False, "Expected AssetLoadError"


def test_tar_zstd_bundle_builder_keeps_reference_only_assets(tmp_path) -> None:
    class _DetailStore:
        def get_components(self, _lcsc_ids):
            return {42: {"lcsc_id": 42}}

        def get_asset_manifest(self, _lcsc_ids, artifact_types=None):
            return {
                42: [
                    AssetRecord(
                        lcsc_id=42,
                        artifact_type="datasheet_url",
                        stored_key=None,
                        encoding="reference",
                        source_url="https://example.com/C42.pdf",
                    )
                ]
            }

    builder = TarZstdBundleBuilder(_DetailStore(), tmp_path)
    artifact = builder.build_bundle([42])
    manifest = artifact.manifest["assets"]["42"][0]
    assert manifest["bundle_path"] is None
    assert manifest["bundle_status"] == "reference_only"
