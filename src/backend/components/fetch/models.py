from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ArtifactType(StrEnum):
    DATASHEET_PDF = "datasheet_pdf"
    KICAD_FOOTPRINT_MOD = "kicad_footprint_mod"
    MODEL_OBJ = "model_obj"
    MODEL_STEP = "model_step"


class ArtifactEncoding(StrEnum):
    ZSTD = "zstd"


@dataclass(frozen=True)
class StoredBlob:
    key: str
    abs_path: str
    raw_sha256: str
    raw_size_bytes: int
    compressed_size_bytes: int
    encoding: ArtifactEncoding = ArtifactEncoding.ZSTD


@dataclass(frozen=True)
class FetchArtifactRecord:
    lcsc_id: int
    artifact_type: ArtifactType
    source_url: str
    raw_sha256: str
    raw_size_bytes: int
    stored_key: str
    fetched_at_utc: str
    source_meta: dict[str, Any] = field(default_factory=dict)
    mime: str | None = None
    encoding: ArtifactEncoding = ArtifactEncoding.ZSTD
    compare_ok: bool = True

    @classmethod
    def now(
        cls,
        *,
        lcsc_id: int,
        artifact_type: ArtifactType,
        source_url: str,
        raw_sha256: str,
        raw_size_bytes: int,
        stored_key: str,
        source_meta: dict[str, Any] | None = None,
        mime: str | None = None,
        compare_ok: bool = True,
        encoding: ArtifactEncoding = ArtifactEncoding.ZSTD,
    ) -> FetchArtifactRecord:
        return cls(
            lcsc_id=lcsc_id,
            artifact_type=artifact_type,
            source_url=source_url,
            raw_sha256=raw_sha256,
            raw_size_bytes=raw_size_bytes,
            stored_key=stored_key,
            fetched_at_utc=datetime.now(UTC).isoformat(),
            source_meta=source_meta or {},
            mime=mime,
            compare_ok=compare_ok,
            encoding=encoding,
        )


def test_fetch_artifact_record_now_uses_utc_iso8601() -> None:
    record = FetchArtifactRecord.now(
        lcsc_id=2040,
        artifact_type=ArtifactType.DATASHEET_PDF,
        source_url="https://example.com/ds.pdf",
        raw_sha256="abc",
        raw_size_bytes=123,
        stored_key="objects/datasheet_pdf/abc.zst",
    )
    assert record.lcsc_id == 2040
    assert record.artifact_type == ArtifactType.DATASHEET_PDF
    assert record.encoding == ArtifactEncoding.ZSTD
    assert record.fetched_at_utc.endswith("+00:00")
