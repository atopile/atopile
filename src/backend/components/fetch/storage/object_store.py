from __future__ import annotations

from pathlib import Path

from ..compression import compress_zstd, decompress_zstd, sha256_hex
from ..models import ArtifactType, StoredBlob


class LocalObjectStore:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        (self.cache_dir / "objects").mkdir(parents=True, exist_ok=True)

    def _abs_path_from_key(self, key: str) -> Path:
        return self.cache_dir / key

    def _key_for(self, artifact_type: ArtifactType, raw_sha256: str) -> str:
        return f"objects/{artifact_type.value}/{raw_sha256}.zst"

    def put_raw(self, artifact_type: ArtifactType, raw: bytes) -> StoredBlob:
        raw_sha256 = sha256_hex(raw)
        key = self._key_for(artifact_type, raw_sha256)
        abs_path = self._abs_path_from_key(key)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        if not abs_path.exists():
            compressed = compress_zstd(raw)
            tmp_path = abs_path.with_suffix(".zst.tmp")
            tmp_path.write_bytes(compressed)
            tmp_path.replace(abs_path)

        return StoredBlob(
            key=key,
            abs_path=str(abs_path),
            raw_sha256=raw_sha256,
            raw_size_bytes=len(raw),
            compressed_size_bytes=abs_path.stat().st_size,
        )

    def get_compressed(self, key: str) -> bytes:
        return self._abs_path_from_key(key).read_bytes()

    def get_raw(self, key: str) -> bytes:
        return decompress_zstd(self.get_compressed(key))


def test_local_object_store_round_trip(tmp_path) -> None:
    store = LocalObjectStore(tmp_path)
    raw = b"datasheet-pdf-bytes"
    blob = store.put_raw(ArtifactType.DATASHEET_PDF, raw)
    assert blob.key.startswith("objects/datasheet_pdf/")
    assert store.get_raw(blob.key) == raw


def test_local_object_store_deduplicates_by_hash(tmp_path) -> None:
    store = LocalObjectStore(tmp_path)
    raw = b"same-binary"
    first = store.put_raw(ArtifactType.MODEL_STEP, raw)
    second = store.put_raw(ArtifactType.MODEL_STEP, raw)
    assert first.key == second.key
