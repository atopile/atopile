from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import TransformConfig
from .detail_db_builder import DetailDbBuilder
from .fast_db_builder import FastLookupDbBuilder
from .models import (
    CAPACITOR_SUBCATEGORIES,
    RESISTOR_SUBCATEGORIES,
    ComponentType,
    SourceComponent,
    normalize_component,
)
from .validate_snapshot import validate_snapshot


@dataclass(frozen=True)
class SnapshotBuildResult:
    snapshot_dir: Path
    source_component_count: int
    fast_component_count: int
    detail_component_count: int


class JlcCacheSqliteSource:
    def __init__(self, source_sqlite_path: Path):
        self.source_sqlite_path = source_sqlite_path

    def iter_components(
        self,
        *,
        max_components: int | None = None,
    ):
        with sqlite3.connect(self.source_sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            category_map = self._load_target_category_map(conn)
            category_ids = sorted(category_map)
            placeholders = ",".join("?" for _ in category_ids)
            query = f"""
                SELECT
                    c.lcsc AS lcsc_id,
                    c.category_id AS category_id,
                    cat.category AS category,
                    cat.subcategory AS subcategory,
                    m.name AS manufacturer_name,
                    c.mfr AS part_number,
                    c.package AS package,
                    c.description AS description,
                    c.basic AS is_basic,
                    c.preferred AS is_preferred,
                    c.stock AS stock,
                    c.datasheet AS datasheet_url,
                    c.price AS price_json,
                    c.extra AS extra_json,
                    json_extract(c.extra, '$.attributes.Resistance') AS resistance_raw,
                    json_extract(c.extra, '$.attributes.Tolerance') AS tolerance_raw,
                    json_extract(c.extra, '$.attributes."Power(Watts)"') AS power_raw,
                    coalesce(
                        json_extract(c.extra, '$.attributes."Overload Voltage (Max)"'),
                        json_extract(c.extra, '$.attributes."Rated Voltage"'),
                        json_extract(c.extra, '$.attributes."Voltage Rating"')
                    ) AS resistor_voltage_raw,
                    json_extract(
                        c.extra,
                        '$.attributes."Temperature Coefficient"'
                    ) AS tempco_raw,
                    json_extract(
                        c.extra,
                        '$.attributes.Capacitance'
                    ) AS capacitance_raw,
                    coalesce(
                        json_extract(c.extra, '$.attributes."Voltage Rated"'),
                        json_extract(c.extra, '$.attributes."Rated Voltage"'),
                        json_extract(c.extra, '$.attributes."Voltage Rating"')
                    ) AS capacitor_voltage_raw,
                    json_extract(c.extra, '$.dataManualUrl') AS data_manual_url,
                    json_extract(c.extra, '$."3dModelPath"') AS model_3d_path,
                    json_extract(c.extra, '$.easyedaModelUUID') AS easyeda_model_uuid,
                    json_extract(c.extra, '$.footprint') AS footprint_name
                FROM components c
                JOIN categories cat ON c.category_id = cat.id
                LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
                WHERE c.category_id IN ({placeholders})
                ORDER BY c.lcsc
            """
            yielded = 0
            for row in conn.execute(query, category_ids):
                component_type = category_map[int(row["category_id"])]
                source_component = SourceComponent(
                    lcsc_id=int(row["lcsc_id"]),
                    component_type=component_type,
                    category=str(row["category"]),
                    subcategory=str(row["subcategory"]),
                    manufacturer_name=_to_optional_str(row["manufacturer_name"]),
                    part_number=str(row["part_number"]),
                    package=str(row["package"]),
                    description=str(row["description"]),
                    is_basic=bool(row["is_basic"]),
                    is_preferred=bool(row["is_preferred"]),
                    stock=int(row["stock"]),
                    datasheet_url=_to_optional_str(row["datasheet_url"]),
                    price_json=str(row["price_json"]),
                    extra_json=_to_optional_str(row["extra_json"]),
                    resistance_raw=_to_optional_str(row["resistance_raw"]),
                    tolerance_raw=_to_optional_str(row["tolerance_raw"]),
                    power_raw=_to_optional_str(row["power_raw"]),
                    resistor_voltage_raw=_to_optional_str(row["resistor_voltage_raw"]),
                    tempco_raw=_to_optional_str(row["tempco_raw"]),
                    capacitance_raw=_to_optional_str(row["capacitance_raw"]),
                    capacitor_voltage_raw=_to_optional_str(
                        row["capacitor_voltage_raw"]
                    ),
                    data_manual_url=_to_optional_str(row["data_manual_url"]),
                    model_3d_path=_to_optional_str(row["model_3d_path"]),
                    easyeda_model_uuid=_to_optional_str(row["easyeda_model_uuid"]),
                    footprint_name=_to_optional_str(row["footprint_name"]),
                )
                yield normalize_component(source_component)
                yielded += 1
                if max_components is not None and yielded >= max_components:
                    return

    def _load_target_category_map(
        self, conn: sqlite3.Connection
    ) -> dict[int, ComponentType]:
        resistor_placeholders = ",".join("?" for _ in RESISTOR_SUBCATEGORIES)
        capacitor_placeholders = ",".join("?" for _ in CAPACITOR_SUBCATEGORIES)
        query = f"""
            SELECT id, category, subcategory
            FROM categories
            WHERE (
                category = 'Resistors'
                AND subcategory IN ({resistor_placeholders})
            ) OR (
                category = 'Capacitors'
                AND subcategory IN ({capacitor_placeholders})
            )
        """
        params: list[Any] = list(RESISTOR_SUBCATEGORIES) + list(CAPACITOR_SUBCATEGORIES)
        rows = conn.execute(query, params).fetchall()
        if not rows:
            raise RuntimeError(
                "No matching resistor/capacitor categories found in source."
            )

        category_map: dict[int, ComponentType] = {}
        for row in rows:
            category = str(row["category"])
            component_type: ComponentType = (
                "resistor" if category == "Resistors" else "capacitor"
            )
            category_map[int(row["id"])] = component_type
        return category_map


def build_snapshot(
    config: TransformConfig,
    *,
    max_components: int | None = None,
) -> SnapshotBuildResult:
    if not config.source_sqlite_path.exists():
        raise FileNotFoundError(f"Source sqlite not found: {config.source_sqlite_path}")

    snapshot_dir = config.snapshot_dir
    if snapshot_dir.exists():
        raise FileExistsError(
            f"Snapshot directory already exists: {snapshot_dir}. "
            "Set a new ATOPILE_COMPONENTS_SNAPSHOT_NAME."
        )
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    try:
        stage1_assets_by_lcsc = _load_stage1_assets_by_lcsc(config.fetch_manifest_path)
        source = JlcCacheSqliteSource(config.source_sqlite_path)
        fast_builder = FastLookupDbBuilder(
            config.fast_db_path, batch_size=config.batch_size
        )
        detail_builder = DetailDbBuilder(
            config.detail_db_path,
            batch_size=config.batch_size,
            stage1_assets_by_lcsc=stage1_assets_by_lcsc,
        )

        source_count = 0
        for component in source.iter_components(max_components=max_components):
            fast_builder.add_component(component)
            detail_builder.add_component(component)
            source_count += 1

        fast_builder.finalize()
        detail_builder.finalize()
        validation = validate_snapshot(snapshot_dir)
    except Exception:
        shutil.rmtree(snapshot_dir, ignore_errors=True)
        raise

    metadata = {
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_sqlite_path": str(config.source_sqlite_path),
        "snapshot_name": config.snapshot_name,
        "max_components": max_components,
        "is_partial": max_components is not None,
        "source_component_count": source_count,
        "fast_component_count": fast_builder.inserted_count,
        "detail_component_count": detail_builder.inserted_count,
        "validation": {
            "fast_total_rows": validation.fast_total_rows,
            "detail_total_rows": validation.detail_total_rows,
            "resistor_rows": validation.resistor_rows,
            "capacitor_rows": validation.capacitor_rows,
        },
        "stage1_artifact_records": sum(
            len(records) for records in stage1_assets_by_lcsc.values()
        ),
    }
    (snapshot_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    return SnapshotBuildResult(
        snapshot_dir=snapshot_dir,
        source_component_count=source_count,
        fast_component_count=fast_builder.inserted_count,
        detail_component_count=detail_builder.inserted_count,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build stage-2 fast/detail SQLite snapshot from raw JLC sqlite."
    )
    parser.add_argument(
        "--source-sqlite",
        type=Path,
        default=None,
        help="Override source sqlite path (defaults from env config).",
    )
    parser.add_argument(
        "--snapshot-name",
        type=str,
        default=None,
        help="Override snapshot name (defaults from env config timestamp).",
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=None,
        help="Limit processed rows for local/dev smoke runs.",
    )
    args = parser.parse_args(argv)

    config = TransformConfig.from_env()
    if args.source_sqlite is not None:
        config = TransformConfig(
            source_sqlite_path=args.source_sqlite,
            fetch_manifest_path=config.fetch_manifest_path,
            snapshot_root_dir=config.snapshot_root_dir,
            snapshot_name=config.snapshot_name,
            batch_size=config.batch_size,
        )
    if args.snapshot_name is not None:
        config = TransformConfig(
            source_sqlite_path=config.source_sqlite_path,
            fetch_manifest_path=config.fetch_manifest_path,
            snapshot_root_dir=config.snapshot_root_dir,
            snapshot_name=args.snapshot_name,
            batch_size=config.batch_size,
        )

    result = build_snapshot(config, max_components=args.max_components)
    print(result.snapshot_dir)
    return 0


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _load_stage1_assets_by_lcsc(
    manifest_db_path: Path,
) -> dict[int, list[dict[str, Any]]]:
    if not manifest_db_path.exists():
        return {}

    with sqlite3.connect(manifest_db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "fetch_manifest" not in tables:
            return {}
        rows = conn.execute(
            """
            SELECT
                lcsc_id,
                artifact_type,
                source_url,
                raw_sha256,
                raw_size_bytes,
                mime,
                encoding,
                stored_key,
                source_meta_json
            FROM fetch_manifest
            WHERE compare_ok = 1
            ORDER BY id ASC
            """
        ).fetchall()

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        lcsc_id = int(row[0])
        grouped.setdefault(lcsc_id, []).append(
            {
                "artifact_type": str(row[1]),
                "source_url": str(row[2]),
                "raw_sha256": str(row[3]),
                "raw_size_bytes": int(row[4]),
                "mime": None if row[5] is None else str(row[5]),
                "encoding": str(row[6]),
                "stored_key": str(row[7]),
                "source_meta": json.loads(str(row[8])),
            }
        )
    return grouped


def test_build_snapshot(tmp_path) -> None:
    source_db = tmp_path / "raw.sqlite3"
    _create_test_source_sqlite(source_db)

    config = TransformConfig(
        source_sqlite_path=source_db,
        fetch_manifest_path=tmp_path / "fetch" / "manifest.sqlite3",
        snapshot_root_dir=tmp_path / "snapshots",
        snapshot_name="snap-1",
        batch_size=2,
    )
    result = build_snapshot(config)
    assert result.source_component_count == 2
    assert result.fast_component_count == 2
    assert result.detail_component_count == 2
    assert (result.snapshot_dir / "fast.sqlite").exists()
    assert (result.snapshot_dir / "detail.sqlite").exists()
    assert (result.snapshot_dir / "metadata.json").exists()
    metadata = json.loads((result.snapshot_dir / "metadata.json").read_text("utf-8"))
    assert metadata["max_components"] is None
    assert metadata["is_partial"] is False
    assert metadata["validation"]["fast_total_rows"] == 2
    assert metadata["validation"]["detail_total_rows"] == 2
    assert metadata["stage1_artifact_records"] == 0

    fast_conn = sqlite3.connect(result.snapshot_dir / "fast.sqlite")
    resistor_value = fast_conn.execute(
        "SELECT resistance_ohm FROM resistor_pick WHERE lcsc_id = 1001"
    ).fetchone()[0]
    capacitor_value = fast_conn.execute(
        "SELECT capacitance_f FROM capacitor_pick WHERE lcsc_id = 2001"
    ).fetchone()[0]
    assert resistor_value == 10_000.0
    assert abs(capacitor_value - 1e-07) < 1e-15
    fast_conn.close()


def test_build_snapshot_includes_stage1_manifest_assets(tmp_path) -> None:
    source_db = tmp_path / "raw.sqlite3"
    _create_test_source_sqlite(source_db)
    manifest_db = tmp_path / "fetch" / "manifest.sqlite3"
    manifest_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(manifest_db) as conn:
        conn.executescript(
            """
            CREATE TABLE fetch_manifest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lcsc_id INTEGER NOT NULL,
                artifact_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                raw_size_bytes INTEGER NOT NULL,
                mime TEXT,
                encoding TEXT NOT NULL,
                stored_key TEXT NOT NULL,
                fetched_at_utc TEXT NOT NULL,
                source_meta_json TEXT NOT NULL,
                compare_ok INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO fetch_manifest (
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1001,
                "datasheet_pdf",
                "https://example.com/r.pdf",
                "abc",
                123,
                "application/pdf",
                "zstd",
                "objects/datasheet_pdf/abc.zst",
                "2026-02-15T00:00:00+00:00",
                '{"status_code":200}',
                1,
            ),
        )
        conn.commit()

    config = TransformConfig(
        source_sqlite_path=source_db,
        fetch_manifest_path=manifest_db,
        snapshot_root_dir=tmp_path / "snapshots",
        snapshot_name="snap-with-assets",
        batch_size=2,
    )
    result = build_snapshot(config)
    detail_conn = sqlite3.connect(result.snapshot_dir / "detail.sqlite")
    row = detail_conn.execute(
        """
        SELECT artifact_type, stored_key
        FROM component_assets
        WHERE lcsc_id = 1001
          AND artifact_type = 'datasheet_pdf'
        """
    ).fetchone()
    detail_conn.close()
    assert row == ("datasheet_pdf", "objects/datasheet_pdf/abc.zst")


def test_build_snapshot_marks_partial_runs(tmp_path) -> None:
    source_db = tmp_path / "raw.sqlite3"
    _create_test_source_sqlite(source_db)

    config = TransformConfig(
        source_sqlite_path=source_db,
        fetch_manifest_path=tmp_path / "fetch" / "manifest.sqlite3",
        snapshot_root_dir=tmp_path / "snapshots",
        snapshot_name="snap-partial",
        batch_size=2,
    )
    result = build_snapshot(config, max_components=1)
    metadata = json.loads((result.snapshot_dir / "metadata.json").read_text("utf-8"))
    assert metadata["max_components"] == 1
    assert metadata["is_partial"] is True


def _create_test_source_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL
        );
        CREATE TABLE manufacturers (
            id INTEGER PRIMARY KEY NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE components (
            lcsc INTEGER PRIMARY KEY NOT NULL,
            category_id INTEGER NOT NULL,
            mfr TEXT NOT NULL,
            package TEXT NOT NULL,
            joints INTEGER NOT NULL,
            manufacturer_id INTEGER NOT NULL,
            basic INTEGER NOT NULL,
            description TEXT NOT NULL,
            datasheet TEXT NOT NULL,
            stock INTEGER NOT NULL,
            price TEXT NOT NULL,
            last_update INTEGER NOT NULL,
            extra TEXT,
            flag INTEGER NOT NULL DEFAULT 0,
            last_on_stock INTEGER NOT NULL DEFAULT 0,
            preferred INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX components_category ON components (category_id);
        """
    )
    conn.executemany(
        "INSERT INTO categories (id, category, subcategory) VALUES (?, ?, ?)",
        [
            (1, "Resistors", "Chip Resistor - Surface Mount"),
            (2, "Capacitors", "Multilayer Ceramic Capacitors MLCC - SMD/SMT"),
            (3, "Resistors", "Resistor Networks & Arrays"),
        ],
    )
    conn.execute("INSERT INTO manufacturers (id, name) VALUES (1, 'Test Mfr')")

    resistor_extra = json.dumps(
        {
            "attributes": {
                "Resistance": "10kΩ",
                "Tolerance": "±1%",
                "Power(Watts)": "62.5mW",
                "Overload Voltage (Max)": "50V",
                "Temperature Coefficient": "±100ppm/℃",
            }
        }
    )
    capacitor_extra = json.dumps(
        {
            "attributes": {
                "Capacitance": "100nF",
                "Tolerance": "±10%",
                "Voltage Rated": "16V",
                "Temperature Coefficient": "X7R",
            }
        }
    )
    ignored_extra = json.dumps({"attributes": {"Resistance": "1kΩ"}})
    conn.executemany(
        """
        INSERT INTO components (
            lcsc,
            category_id,
            mfr,
            package,
            joints,
            manufacturer_id,
            basic,
            description,
            datasheet,
            stock,
            price,
            last_update,
            extra,
            flag,
            last_on_stock,
            preferred
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                1001,
                1,
                "R-10K",
                "0402",
                2,
                1,
                1,
                "resistor",
                "https://example.com/r.pdf",
                100,
                "[]",
                0,
                resistor_extra,
                0,
                0,
                1,
            ),
            (
                2001,
                2,
                "C-100N",
                "0402",
                2,
                1,
                0,
                "capacitor",
                "https://example.com/c.pdf",
                200,
                "[]",
                0,
                capacitor_extra,
                0,
                0,
                0,
            ),
            (
                3001,
                3,
                "RN-1K",
                "0603",
                4,
                1,
                0,
                "network",
                "https://example.com/n.pdf",
                10,
                "[]",
                0,
                ignored_extra,
                0,
                0,
                0,
            ),
        ],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
