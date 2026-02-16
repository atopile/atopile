from __future__ import annotations

import json
import random
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CorpusRecord:
    lcsc_id: int
    component_type: str
    category: str
    subcategory: str
    manufacturer_name: str | None
    part_number: str
    package: str
    description: str
    stock: int
    is_basic: bool
    is_preferred: bool
    attrs: dict[str, Any]
    text: str


def _safe_attr_tokens(attributes_json: str, *, max_items: int = 24) -> list[str]:
    if not attributes_json:
        return []
    try:
        parsed = json.loads(attributes_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, dict):
        return []
    tokens: list[str] = []
    for key, value in parsed.items():
        if len(tokens) >= max_items:
            break
        key_str = str(key).strip()
        value_str = str(value).strip()
        if not key_str or not value_str:
            continue
        compact_value = re.sub(r"\s+", " ", value_str)
        tokens.append(f"{key_str}:{compact_value}")
    return tokens


def canonical_component_text(
    *,
    lcsc_id: int,
    component_type: str,
    category: str,
    subcategory: str,
    manufacturer_name: str | None,
    part_number: str,
    package: str,
    description: str,
    attributes_json: str,
) -> str:
    attr_tokens = _safe_attr_tokens(attributes_json)
    bits = [
        f"lcsc C{lcsc_id}",
        component_type,
        category,
        subcategory,
        manufacturer_name or "",
        part_number,
        package,
        description,
        " ".join(attr_tokens),
    ]
    return " | ".join(bit.strip() for bit in bits if bit and bit.strip())


def export_corpus(
    *,
    detail_db: Path,
    out_jsonl: Path,
    limit: int | None = None,
    seed: int = 7,
) -> int:
    conn = sqlite3.connect(detail_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                lcsc_id,
                component_type,
                category,
                subcategory,
                manufacturer_name,
                part_number,
                package,
                description,
                stock,
                is_basic,
                is_preferred,
                attributes_json
            FROM components_full
            """
        ).fetchall()
    finally:
        conn.close()

    if limit is not None and limit < len(rows):
        rng = random.Random(seed)
        rows = rng.sample(rows, k=limit)

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            attributes_json = row["attributes_json"] or "{}"
            attrs_obj: dict[str, Any]
            try:
                parsed = json.loads(attributes_json)
                attrs_obj = parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                attrs_obj = {}

            record = CorpusRecord(
                lcsc_id=int(row["lcsc_id"]),
                component_type=str(row["component_type"]),
                category=str(row["category"]),
                subcategory=str(row["subcategory"]),
                manufacturer_name=row["manufacturer_name"],
                part_number=str(row["part_number"]),
                package=str(row["package"]),
                description=str(row["description"]),
                stock=int(row["stock"]),
                is_basic=bool(row["is_basic"]),
                is_preferred=bool(row["is_preferred"]),
                attrs=attrs_obj,
                text=canonical_component_text(
                    lcsc_id=int(row["lcsc_id"]),
                    component_type=str(row["component_type"]),
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

    return len(rows)


def load_corpus(corpus_jsonl: Path) -> list[CorpusRecord]:
    records: list[CorpusRecord] = []
    with corpus_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            payload = json.loads(line)
            records.append(
                CorpusRecord(
                    lcsc_id=int(payload["lcsc_id"]),
                    component_type=str(payload["component_type"]),
                    category=str(payload["category"]),
                    subcategory=str(payload["subcategory"]),
                    manufacturer_name=payload.get("manufacturer_name"),
                    part_number=str(payload["part_number"]),
                    package=str(payload["package"]),
                    description=str(payload["description"]),
                    stock=int(payload["stock"]),
                    is_basic=bool(payload["is_basic"]),
                    is_preferred=bool(payload["is_preferred"]),
                    attrs=payload.get("attrs", {}),
                    text=str(payload["text"]),
                )
            )
    return records


def test_canonical_component_text_includes_id_and_tokens() -> None:
    text = canonical_component_text(
        lcsc_id=123,
        component_type="resistor",
        category="Passives",
        subcategory="Chip Resistor",
        manufacturer_name="Yageo",
        part_number="RC0402FR-0710KL",
        package="0402",
        description="10k 1% resistor",
        attributes_json='{"Resistance":"10kOhm","Tolerance":"1%"}',
    )
    assert "C123" in text
    assert "RC0402FR-0710KL" in text
    assert "Resistance:10kOhm" in text

