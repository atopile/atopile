from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .corpus import CorpusRecord, canonical_component_text
from .runtime import status


def _sqlite_readonly_uri(path: Path) -> str:
    resolved = str(path.resolve())
    escaped = quote(resolved, safe="/")
    return f"file:{escaped}?mode=ro&immutable=1"


def _component_type_from_group(group: str) -> str:
    if group == "sensor":
        return "sensor"
    if group == "mcu":
        return "mcu"
    if group == "interface":
        return "interface_ic"
    if group == "power":
        return "power_ic"
    return "unknown"


def _extract_attrs(extra_json: str | None) -> dict[str, Any]:
    if not extra_json:
        return {}
    try:
        parsed = json.loads(extra_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    attrs = parsed.get("attributes", {})
    if isinstance(attrs, dict):
        return attrs
    return {}


def export_balanced_stage1_corpus(
    *,
    cache_sqlite: Path,
    out_jsonl: Path,
    target_count: int = 10_000,
    per_subcategory_cap: int = 600,
) -> int:
    t0 = time.perf_counter()
    status("opening stage-1 cache sqlite")
    conn = sqlite3.connect(_sqlite_readonly_uri(cache_sqlite), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        status("building filtered candidate set (sensors/mcu/interface/power, in-stock)")
        conn.executescript(
            """
            DROP TABLE IF EXISTS tmp_candidates;
            DROP TABLE IF EXISTS tmp_selected;
            """
        )
        conn.execute(
            """
            CREATE TEMP TABLE tmp_candidates AS
            SELECT
                c.lcsc AS lcsc_id,
                cat.id AS category_id,
                cat.category AS category,
                cat.subcategory AS subcategory,
                m.name AS manufacturer_name,
                c.mfr AS part_number,
                c.package AS package,
                c.description AS description,
                c.stock AS stock,
                c.basic AS is_basic,
                c.preferred AS is_preferred,
                c.extra AS extra_json,
                CASE
                    WHEN lower(cat.category) LIKE '%sensor%' THEN 'sensor'
                    WHEN lower(cat.category) LIKE '%single chip microcomputer%'
                        OR lower(cat.category) LIKE '%embedded processors & controllers%'
                        OR lower(cat.subcategory) LIKE '%microcontroller%'
                    THEN 'mcu'
                    WHEN lower(cat.category) LIKE '%interface%'
                        OR lower(cat.category) LIKE '%communication interface%'
                    THEN 'interface'
                    WHEN lower(cat.category) LIKE '%power management%'
                        OR lower(cat.category) LIKE '%power supply chip%'
                    THEN 'power'
                    ELSE 'other'
                END AS query_group
            FROM components c
            JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
            WHERE c.stock > 0
              AND lower(cat.subcategory) NOT LIKE '%pre-ordered%'
              AND (
                    lower(cat.category) LIKE '%sensor%'
                 OR lower(cat.category) LIKE '%single chip microcomputer%'
                 OR lower(cat.category) LIKE '%embedded processors & controllers%'
                 OR lower(cat.subcategory) LIKE '%microcontroller%'
                 OR lower(cat.category) LIKE '%interface%'
                 OR lower(cat.category) LIKE '%communication interface%'
                 OR lower(cat.category) LIKE '%power management%'
                 OR lower(cat.category) LIKE '%power supply chip%'
              );
            """
        )
        total_candidates = int(
            conn.execute("SELECT COUNT(*) FROM tmp_candidates").fetchone()[0]
        )
        status(f"candidates={total_candidates}")

        status("selecting balanced seed set by per-subcategory stock rank")
        conn.execute(
            """
            CREATE TEMP TABLE tmp_selected AS
            WITH ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY category_id
                        ORDER BY stock DESC, lcsc_id ASC
                    ) AS rn
                FROM tmp_candidates
            )
            SELECT
                lcsc_id,
                category_id,
                category,
                subcategory,
                manufacturer_name,
                part_number,
                package,
                description,
                stock,
                is_basic,
                is_preferred,
                extra_json,
                query_group
            FROM ranked
            WHERE rn <= ?;
            """,
            (per_subcategory_cap,),
        )
        seed_count = int(conn.execute("SELECT COUNT(*) FROM tmp_selected").fetchone()[0])
        status(f"seed_rows={seed_count}")

        remainder = max(0, target_count - seed_count)
        if remainder > 0:
            status(f"filling remainder rows={remainder} by global stock ranking")
            conn.execute(
                """
                INSERT INTO tmp_selected
                SELECT *
                FROM tmp_candidates
                WHERE lcsc_id NOT IN (SELECT lcsc_id FROM tmp_selected)
                ORDER BY stock DESC, lcsc_id ASC
                LIMIT ?;
                """,
                (remainder,),
            )

        status("materializing final ordered selection")
        rows = conn.execute(
            """
            SELECT *
            FROM tmp_selected
            ORDER BY stock DESC, lcsc_id ASC
            LIMIT ?;
            """,
            (target_count,),
        ).fetchall()

        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        status(f"writing corpus jsonl: {out_jsonl}")
        with out_jsonl.open("w", encoding="utf-8") as f:
            for row in rows:
                attrs = _extract_attrs(row["extra_json"])
                attributes_json = json.dumps(attrs, ensure_ascii=True, sort_keys=True)
                record = CorpusRecord(
                    lcsc_id=int(row["lcsc_id"]),
                    component_type=_component_type_from_group(str(row["query_group"])),
                    category=str(row["category"]),
                    subcategory=str(row["subcategory"]),
                    manufacturer_name=row["manufacturer_name"],
                    part_number=str(row["part_number"]),
                    package=str(row["package"]),
                    description=str(row["description"]),
                    stock=int(row["stock"]),
                    is_basic=bool(row["is_basic"]),
                    is_preferred=bool(row["is_preferred"]),
                    attrs=attrs,
                    text=canonical_component_text(
                        lcsc_id=int(row["lcsc_id"]),
                        component_type=_component_type_from_group(
                            str(row["query_group"])
                        ),
                        category=str(row["category"]),
                        subcategory=str(row["subcategory"]),
                        manufacturer_name=row["manufacturer_name"],
                        part_number=str(row["part_number"]),
                        package=str(row["package"]),
                        description=str(row["description"]),
                        attributes_json=attributes_json,
                    ),
                )
                f.write(json.dumps(asdict(record), ensure_ascii=True, sort_keys=True))
                f.write("\n")
    finally:
        conn.close()

    dt = time.perf_counter() - t0
    status(f"done rows={len(rows)} elapsed_s={dt:.1f}")
    return len(rows)


def export_full_stage1_corpus(
    *,
    cache_sqlite: Path,
    out_jsonl: Path,
    in_stock_only: bool = False,
) -> int:
    t0 = time.perf_counter()
    status("opening stage-1 cache sqlite (full export)")
    conn = sqlite3.connect(_sqlite_readonly_uri(cache_sqlite), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        where_stock = "AND c.stock > 0" if in_stock_only else ""
        rows = conn.execute(
            f"""
            SELECT
                c.lcsc AS lcsc_id,
                cat.category AS category,
                cat.subcategory AS subcategory,
                m.name AS manufacturer_name,
                c.mfr AS part_number,
                c.package AS package,
                c.description AS description,
                c.stock AS stock,
                c.basic AS is_basic,
                c.preferred AS is_preferred,
                c.extra AS extra_json
            FROM components c
            JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
            WHERE lower(cat.subcategory) NOT LIKE '%pre-ordered%'
            {where_stock}
            ORDER BY c.lcsc ASC
            """
        ).fetchall()

        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        status(f"writing full corpus jsonl: {out_jsonl}")
        with out_jsonl.open("w", encoding="utf-8") as f:
            for row in rows:
                attrs = _extract_attrs(row["extra_json"])
                component_type = "unknown"
                category_l = str(row["category"]).lower()
                subcategory_l = str(row["subcategory"]).lower()
                if "sensor" in category_l:
                    component_type = "sensor"
                elif (
                    "single chip microcomputer" in category_l
                    or "embedded processors & controllers" in category_l
                    or "microcontroller" in subcategory_l
                ):
                    component_type = "mcu"
                elif "interface" in category_l or "communication interface" in category_l:
                    component_type = "interface_ic"
                elif "power management" in category_l or "power supply chip" in category_l:
                    component_type = "power_ic"
                attributes_json = json.dumps(attrs, ensure_ascii=True, sort_keys=True)
                record = CorpusRecord(
                    lcsc_id=int(row["lcsc_id"]),
                    component_type=component_type,
                    category=str(row["category"]),
                    subcategory=str(row["subcategory"]),
                    manufacturer_name=row["manufacturer_name"],
                    part_number=str(row["part_number"]),
                    package=str(row["package"]),
                    description=str(row["description"]),
                    stock=int(row["stock"]),
                    is_basic=bool(row["is_basic"]),
                    is_preferred=bool(row["is_preferred"]),
                    attrs=attrs,
                    text=canonical_component_text(
                        lcsc_id=int(row["lcsc_id"]),
                        component_type=component_type,
                        category=str(row["category"]),
                        subcategory=str(row["subcategory"]),
                        manufacturer_name=row["manufacturer_name"],
                        part_number=str(row["part_number"]),
                        package=str(row["package"]),
                        description=str(row["description"]),
                        attributes_json=attributes_json,
                    ),
                )
                f.write(json.dumps(asdict(record), ensure_ascii=True, sort_keys=True))
                f.write("\n")
    finally:
        conn.close()

    dt = time.perf_counter() - t0
    status(f"done rows={len(rows)} elapsed_s={dt:.1f}")
    return len(rows)
