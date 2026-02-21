from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from .interfaces import (
    AssetRecord,
    DetailStore,
    SnapshotNotFoundError,
    SnapshotSchemaError,
)

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DETAIL_TABLE = "components_full"
_ASSET_TABLE = "component_assets"
_MFR_LOOKUP_TABLE = "component_mfr_lookup"


def _sqlite_readonly_uri(path: Path) -> str:
    resolved = str(path.resolve())
    escaped = quote(resolved, safe="/")
    return f"file:{escaped}?mode=ro&immutable=1"


def _quote_ident(identifier: str) -> str:
    if not _VALID_IDENTIFIER.fullmatch(identifier):
        raise SnapshotSchemaError(f"Unsafe SQL identifier: {identifier!r}")
    return f'"{identifier}"'


class SQLiteDetailStore(DetailStore):
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise SnapshotNotFoundError(f"detail snapshot DB not found: {self.db_path}")
        try:
            conn = sqlite3.connect(_sqlite_readonly_uri(self.db_path), uri=True)
        except sqlite3.Error as exc:
            raise SnapshotSchemaError(f"failed to open detail DB: {exc}") from exc
        conn.row_factory = sqlite3.Row
        conn.execute("pragma query_only=ON")
        conn.execute("pragma foreign_keys=OFF")
        conn.execute("pragma synchronous=OFF")
        conn.execute("pragma temp_store=MEMORY")
        return conn

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        rows = conn.execute(f"pragma table_info({_quote_ident(table)})").fetchall()
        if not rows:
            raise SnapshotSchemaError(f"Missing required table: {table}")
        return {str(row[1]) for row in rows}

    def get_components(self, lcsc_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
        ordered_ids = _unique_ids(lcsc_ids)
        if not ordered_ids:
            return {}

        placeholders = ",".join("?" for _ in ordered_ids)
        sql = f"""
            select *
            from {_quote_ident(_DETAIL_TABLE)}
            where {_quote_ident("lcsc_id")} in ({placeholders})
        """

        with self._connect() as conn:
            columns = self._table_columns(conn, _DETAIL_TABLE)
            if "lcsc_id" not in columns:
                raise SnapshotSchemaError(f"{_DETAIL_TABLE} missing required lcsc_id")
            try:
                rows = conn.execute(sql, list(ordered_ids)).fetchall()
            except sqlite3.Error as exc:
                raise SnapshotSchemaError(
                    f"failed querying components_full: {exc}"
                ) from exc

        out: dict[int, dict[str, Any]] = {}
        for row in rows:
            row_dict = _normalize_row(dict(row))
            lcsc_id = int(row_dict["lcsc_id"])
            out[lcsc_id] = row_dict
        return out

    def get_asset_manifest(
        self,
        lcsc_ids: Sequence[int],
        artifact_types: Sequence[str] | None = None,
    ) -> dict[int, list[AssetRecord]]:
        ordered_ids = _unique_ids(lcsc_ids)
        if not ordered_ids:
            return {}
        normalized_artifact_types = _normalize_artifact_types(artifact_types)

        placeholders = ",".join("?" for _ in ordered_ids)

        with self._connect() as conn:
            columns = self._table_columns(conn, _ASSET_TABLE)
            if "lcsc_id" not in columns:
                raise SnapshotSchemaError(f"{_ASSET_TABLE} missing required lcsc_id")
            supports_sql_artifact_filter = (
                normalized_artifact_types is not None and "artifact_type" in columns
            )
            params: list[Any] = list(ordered_ids)
            sql = f"""
                select *
                from {_quote_ident(_ASSET_TABLE)}
                where {_quote_ident("lcsc_id")} in ({placeholders})
            """
            if supports_sql_artifact_filter:
                type_placeholders = ",".join("?" for _ in normalized_artifact_types)
                sql += (
                    f" and {_quote_ident('artifact_type')} in ({type_placeholders})"
                )
                params.extend(normalized_artifact_types)
            sql += f" order by {_quote_ident('lcsc_id')} asc"
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.Error as exc:
                raise SnapshotSchemaError(
                    f"failed querying component_assets: {exc}"
                ) from exc

        grouped: dict[int, list[AssetRecord]] = defaultdict(list)
        for row in rows:
            assets = _asset_records_from_row(_normalize_row(dict(row)))
            if normalized_artifact_types is not None and not supports_sql_artifact_filter:
                assets = [
                    asset
                    for asset in assets
                    if asset.artifact_type in normalized_artifact_types
                ]
            grouped[int(row["lcsc_id"])].extend(assets)
        return dict(grouped)

    def lookup_component_ids_by_manufacturer_part(
        self,
        manufacturer_name: str,
        part_number: str,
        *,
        limit: int = 50,
    ) -> list[int]:
        if limit < 1:
            return []
        mfr_norm = _normalize_lookup_token(manufacturer_name)
        pn_norm = _normalize_lookup_token(part_number)
        if mfr_norm is None or pn_norm is None:
            return []

        sql = f"""
            select {_quote_ident("lcsc_id")}
            from {_quote_ident(_MFR_LOOKUP_TABLE)}
            where {_quote_ident("mfr_norm")} = ?
              and {_quote_ident("part_number_norm")} = ?
            order by {_quote_ident("lcsc_id")} asc
            limit ?
        """
        with self._connect() as conn:
            columns = self._table_columns(conn, _MFR_LOOKUP_TABLE)
            missing = {"mfr_norm", "part_number_norm", "lcsc_id"} - columns
            if missing:
                raise SnapshotSchemaError(
                    f"{_MFR_LOOKUP_TABLE} missing required columns: {sorted(missing)}"
                )
            try:
                rows = conn.execute(sql, [mfr_norm, pn_norm, limit]).fetchall()
            except sqlite3.Error as exc:
                raise SnapshotSchemaError(
                    f"failed querying {_MFR_LOOKUP_TABLE}: {exc}"
                ) from exc
        return [int(row["lcsc_id"]) for row in rows]


def _asset_records_from_row(row: dict[str, Any]) -> list[AssetRecord]:
    if any(
        row.get(key) not in (None, "")
        for key in ("artifact_type", "artifact", "type", "stored_key", "key")
    ):
        return [_asset_record_from_compact_row(row)]
    return _asset_records_from_reference_row(row)


def _asset_record_from_compact_row(row: dict[str, Any]) -> AssetRecord:
    lcsc_id = int(row["lcsc_id"])
    artifact_type = _first_non_empty(
        row,
        ("artifact_type", "artifact", "type"),
        default="unknown",
    )
    stored_key = _first_non_empty(row, ("stored_key", "object_key", "key"))
    if stored_key is not None:
        stored_key = str(stored_key)

    known_fields = {
        "lcsc_id",
        "artifact_type",
        "artifact",
        "type",
        "stored_key",
        "object_key",
        "key",
        "encoding",
        "mime",
        "raw_sha256",
        "raw_size_bytes",
        "source_url",
    }
    metadata = {key: value for key, value in row.items() if key not in known_fields}

    raw_size = row.get("raw_size_bytes")
    return AssetRecord(
        lcsc_id=lcsc_id,
        artifact_type=str(artifact_type),
        stored_key=stored_key,
        encoding=str(row.get("encoding") or "zstd"),
        mime=_as_optional_str(row.get("mime")),
        raw_sha256=_as_optional_str(row.get("raw_sha256")),
        raw_size_bytes=None if raw_size is None else int(raw_size),
        source_url=_as_optional_str(row.get("source_url")),
        metadata=metadata,
    )


def _asset_records_from_reference_row(row: dict[str, Any]) -> list[AssetRecord]:
    lcsc_id = int(row["lcsc_id"])
    out: list[AssetRecord] = []

    datasheet_url = _as_optional_str(row.get("datasheet_url"))
    if datasheet_url:
        out.append(
            AssetRecord(
                lcsc_id=lcsc_id,
                artifact_type="datasheet_url",
                source_url=datasheet_url,
                encoding="reference",
            )
        )

    data_manual_url = _as_optional_str(row.get("data_manual_url"))
    if data_manual_url:
        out.append(
            AssetRecord(
                lcsc_id=lcsc_id,
                artifact_type="data_manual_url",
                source_url=data_manual_url,
                encoding="reference",
            )
        )

    footprint_name = _as_optional_str(row.get("footprint_name"))
    if footprint_name:
        out.append(
            AssetRecord(
                lcsc_id=lcsc_id,
                artifact_type="footprint_name",
                encoding="reference",
                metadata={"footprint_name": footprint_name},
            )
        )

    model_3d_path = _as_optional_str(row.get("model_3d_path"))
    if model_3d_path:
        stored_key = model_3d_path if model_3d_path.startswith("objects/") else None
        out.append(
            AssetRecord(
                lcsc_id=lcsc_id,
                artifact_type="model_3d_path",
                stored_key=stored_key,
                encoding="zstd" if stored_key else "reference",
                metadata={"model_3d_path": model_3d_path},
            )
        )

    easyeda_model_uuid = _as_optional_str(row.get("easyeda_model_uuid"))
    if easyeda_model_uuid:
        out.append(
            AssetRecord(
                lcsc_id=lcsc_id,
                artifact_type="easyeda_model_uuid",
                encoding="reference",
                metadata={"easyeda_model_uuid": easyeda_model_uuid},
            )
        )

    return out


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, str) and key.endswith("_json"):
            normalized[key] = _decode_json(value)
            continue
        normalized[key] = value
    return normalized


def _decode_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _first_non_empty(
    row: dict[str, Any],
    keys: tuple[str, ...],
    *,
    default: Any = None,
) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return default


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


def _normalize_artifact_types(
    artifact_types: Sequence[str] | None,
) -> tuple[str, ...] | None:
    if artifact_types is None:
        return None
    seen: set[str] = set()
    out: list[str] = []
    for artifact_type in artifact_types:
        normalized = str(artifact_type).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return tuple(out)


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalize_lookup_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return None
    return normalized.casefold()


def test_sqlite_detail_store_reads_components_and_assets(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table components_full (
                lcsc_id integer primary key,
                category text,
                attributes_json text,
                price_json text
            )
        """)
        conn.execute("""
            create table component_assets (
                id integer primary key,
                lcsc_id integer not null,
                artifact_type text not null,
                stored_key text not null,
                encoding text,
                raw_sha256 text,
                raw_size_bytes integer
            )
        """)
        conn.execute(
            """
            insert into components_full (lcsc_id, category, attributes_json, price_json)
            values (?, ?, ?, ?)
            """,
            (
                2040,
                "Resistors",
                '{"resistance_ohm":1000.0}',
                '[{"qty":1,"price":0.01}]',
            ),
        )
        conn.execute(
            """
            insert into component_assets (
                lcsc_id,
                artifact_type,
                stored_key,
                encoding,
                raw_sha256,
                raw_size_bytes
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (
                2040,
                "datasheet_pdf",
                "objects/datasheet_pdf/abc.zst",
                "zstd",
                "abc",
                123,
            ),
        )

    store = SQLiteDetailStore(db_path)
    components = store.get_components([2040])
    assert components[2040]["attributes_json"]["resistance_ohm"] == 1000.0
    assert components[2040]["price_json"][0]["qty"] == 1

    assets = store.get_asset_manifest([2040])
    assert len(assets[2040]) == 1
    assert assets[2040][0].artifact_type == "datasheet_pdf"
    assert assets[2040][0].stored_key == "objects/datasheet_pdf/abc.zst"


def test_sqlite_detail_store_missing_db_raises(tmp_path) -> None:
    store = SQLiteDetailStore(tmp_path / "missing-detail.sqlite")
    try:
        store.get_components([1])
    except SnapshotNotFoundError as exc:
        assert "detail snapshot DB not found" in str(exc)
    else:
        assert False, "Expected SnapshotNotFoundError"


def test_sqlite_detail_store_reads_stage2_reference_assets(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table components_full (
                lcsc_id integer primary key,
                category text
            )
        """)
        conn.execute("""
            create table component_assets (
                lcsc_id integer primary key,
                datasheet_url text,
                data_manual_url text,
                footprint_name text,
                model_3d_path text,
                easyeda_model_uuid text
            )
        """)
        conn.execute(
            "insert into components_full (lcsc_id, category) values (?, ?)",
            (2040, "Resistors"),
        )
        conn.execute(
            """
            insert into component_assets (
                lcsc_id,
                datasheet_url,
                data_manual_url,
                footprint_name,
                model_3d_path,
                easyeda_model_uuid
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (
                2040,
                "https://example.com/C2040.pdf",
                "https://example.com/C2040-manual",
                "R0402",
                "/3d/C2040.step",
                "uuid-2040",
            ),
        )

    store = SQLiteDetailStore(db_path)
    assets = store.get_asset_manifest([2040])
    artifact_types = {asset.artifact_type for asset in assets[2040]}
    assert artifact_types == {
        "datasheet_url",
        "data_manual_url",
        "footprint_name",
        "model_3d_path",
        "easyeda_model_uuid",
    }


def test_sqlite_detail_store_filters_assets_by_artifact_type(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table components_full (
                lcsc_id integer primary key
            )
        """)
        conn.execute("""
            create table component_assets (
                id integer primary key,
                lcsc_id integer not null,
                artifact_type text not null,
                stored_key text not null
            )
        """)
        conn.execute("insert into components_full (lcsc_id) values (2040)")
        conn.execute(
            """
            insert into component_assets (lcsc_id, artifact_type, stored_key)
            values (?, ?, ?), (?, ?, ?)
            """,
            (
                2040,
                "datasheet_pdf",
                "objects/datasheet_pdf/a.zst",
                2040,
                "model_step",
                "objects/model_step/b.zst",
            ),
        )

    store = SQLiteDetailStore(db_path)
    assets = store.get_asset_manifest([2040], artifact_types=["model_step"])
    assert len(assets[2040]) == 1
    assert assets[2040][0].artifact_type == "model_step"


def test_sqlite_detail_store_lookup_by_manufacturer_part(tmp_path) -> None:
    db_path = tmp_path / "detail.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table components_full (
                lcsc_id integer primary key
            )
        """)
        conn.execute("""
            create table component_assets (
                lcsc_id integer primary key
            )
        """)
        conn.execute("""
            create table component_mfr_lookup (
                id integer primary key autoincrement,
                mfr_norm text not null,
                part_number_norm text not null,
                lcsc_id integer not null
            )
        """)
        conn.execute(
            """
            insert into component_mfr_lookup (
                mfr_norm,
                part_number_norm,
                lcsc_id
            ) values (?, ?, ?)
            """,
            ("raspberry pi", "rp2040", 2040),
        )

    store = SQLiteDetailStore(db_path)
    matches = store.lookup_component_ids_by_manufacturer_part(
        "  Raspberry   PI ",
        " RP2040 ",
    )
    assert matches == [2040]
