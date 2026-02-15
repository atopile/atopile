from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..models import ArtifactEncoding, ArtifactType, FetchArtifactRecord


class LocalManifestStore:
    def __init__(self, cache_dir: Path):
        self.db_path = cache_dir / "fetch" / "manifest.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                create table if not exists fetch_manifest (
                    id integer primary key autoincrement,
                    lcsc_id integer not null,
                    artifact_type text not null,
                    source_url text not null,
                    raw_sha256 text not null,
                    raw_size_bytes integer not null,
                    mime text,
                    encoding text not null,
                    stored_key text not null,
                    fetched_at_utc text not null,
                    source_meta_json text not null,
                    compare_ok integer not null
                )
            """)
            conn.execute("""
                create index if not exists fetch_manifest_lcsc_artifact_idx
                on fetch_manifest (lcsc_id, artifact_type)
            """)

    def append(self, record: FetchArtifactRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into fetch_manifest (
                    lcsc_id,
                    artifact_type,
                    source_url,
                    raw_sha256,
                    raw_size_bytes,
                    mime,
                    encoding,
                    stored_key,
                    fetched_at_utc,
                    source_meta_json,
                    compare_ok
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.lcsc_id,
                    record.artifact_type.value,
                    record.source_url,
                    record.raw_sha256,
                    record.raw_size_bytes,
                    record.mime,
                    record.encoding.value,
                    record.stored_key,
                    record.fetched_at_utc,
                    json.dumps(record.source_meta, ensure_ascii=True, sort_keys=True),
                    1 if record.compare_ok else 0,
                ),
            )

    def list_for_lcsc(self, lcsc_id: int) -> list[FetchArtifactRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select
                    lcsc_id,
                    artifact_type,
                    source_url,
                    raw_sha256,
                    raw_size_bytes,
                    mime,
                    encoding,
                    stored_key,
                    fetched_at_utc,
                    source_meta_json,
                    compare_ok
                from fetch_manifest
                where lcsc_id = ?
                order by id asc
                """,
                (lcsc_id,),
            ).fetchall()

        out: list[FetchArtifactRecord] = []
        for row in rows:
            out.append(
                FetchArtifactRecord(
                    lcsc_id=int(row[0]),
                    artifact_type=ArtifactType(str(row[1])),
                    source_url=str(row[2]),
                    raw_sha256=str(row[3]),
                    raw_size_bytes=int(row[4]),
                    mime=None if row[5] is None else str(row[5]),
                    encoding=ArtifactEncoding(str(row[6])),
                    stored_key=str(row[7]),
                    fetched_at_utc=str(row[8]),
                    source_meta=json.loads(str(row[9])),
                    compare_ok=bool(row[10]),
                )
            )
        return out


def test_manifest_store_append_and_read(tmp_path) -> None:
    store = LocalManifestStore(tmp_path)
    record = FetchArtifactRecord.now(
        lcsc_id=2289,
        artifact_type=ArtifactType.DATASHEET_PDF,
        source_url="https://example.com/C2289.pdf",
        raw_sha256="deadbeef",
        raw_size_bytes=42,
        stored_key="objects/datasheet_pdf/deadbeef.zst",
        source_meta={"status_code": 200},
        mime="application/pdf",
    )
    store.append(record)
    rows = store.list_for_lcsc(2289)
    assert len(rows) == 1
    assert rows[0].artifact_type == ArtifactType.DATASHEET_PDF
    assert rows[0].source_meta["status_code"] == 200
