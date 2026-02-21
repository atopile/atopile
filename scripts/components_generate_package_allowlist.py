#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB = Path(
    "/home/jlc/stage1_fetch/snapshots/bootstrap-serve-20260216T223530Z/detail.sqlite"
)
DEFAULT_OUT = Path("src/backend/components/shared/package_allowlist.generated.json")


@dataclass(frozen=True)
class Policy:
    default_threshold: float = 0.80
    resistor_threshold: float = 0.99
    capacitor_threshold: float = 0.99

    def threshold_for(self, component_type: str) -> float:
        if component_type == "resistor":
            return self.resistor_threshold
        if component_type == "capacitor":
            return self.capacitor_threshold
        return self.default_threshold


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate package allowlists by component type from components_full coverage."
        )
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to detail.sqlite")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSON path",
    )
    parser.add_argument(
        "--default-threshold",
        type=float,
        default=0.80,
        help="Coverage threshold for all types except resistor/capacitor",
    )
    parser.add_argument(
        "--resistor-threshold",
        type=float,
        default=0.99,
        help="Coverage threshold for resistor",
    )
    parser.add_argument(
        "--capacitor-threshold",
        type=float,
        default=0.99,
        help="Coverage threshold for capacitor",
    )
    parser.add_argument(
        "--stock-only",
        action="store_true",
        help="Use only rows where stock > 0",
    )
    return parser.parse_args()


def _validate_threshold(name: str, value: float) -> None:
    if value <= 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in (0, 1], got {value}")


def _load_counts(db_path: Path, stock_only: bool) -> dict[str, list[tuple[str, int]]]:
    where_clause = "WHERE stock > 0" if stock_only else ""
    query = f"""
        SELECT component_type, package, COUNT(*) AS n
        FROM components_full
        {where_clause}
        GROUP BY component_type, package
    """

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        rows = cur.execute(query).fetchall()
    finally:
        con.close()

    by_type: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for component_type, package, n in rows:
        if not package:
            continue
        package_text = str(package).strip()
        if not package_text or package_text == "-":
            continue
        by_type[str(component_type)].append((package_text, int(n)))
    return by_type


def _build_allowlists(
    by_type: dict[str, list[tuple[str, int]]],
    policy: Policy,
) -> tuple[dict[str, object], dict[str, list[str]]]:
    stats: dict[str, object] = {}
    allowlists: dict[str, list[str]] = {}

    for component_type in sorted(by_type):
        package_counts = sorted(by_type[component_type], key=lambda row: row[1], reverse=True)
        total_parts = sum(n for _, n in package_counts)
        threshold = policy.threshold_for(component_type)
        target = total_parts * threshold

        cumulative = 0
        selected: list[tuple[str, int]] = []
        for package, n in package_counts:
            if cumulative >= target:
                break
            cumulative += n
            selected.append((package, n))

        selected_packages = [package for package, _ in selected]
        allowlists[component_type] = selected_packages
        stats[component_type] = {
            "threshold": threshold,
            "total_parts": total_parts,
            "total_packages": len(package_counts),
            "selected_packages": len(selected_packages),
            "coverage": (cumulative / total_parts) if total_parts else 0.0,
            "top_packages": [
                {"package": package, "count": n}
                for package, n in package_counts[:20]
            ],
        }

    return stats, allowlists


def main() -> int:
    args = _parse_args()
    _validate_threshold("default-threshold", args.default_threshold)
    _validate_threshold("resistor-threshold", args.resistor_threshold)
    _validate_threshold("capacitor-threshold", args.capacitor_threshold)

    policy = Policy(
        default_threshold=args.default_threshold,
        resistor_threshold=args.resistor_threshold,
        capacitor_threshold=args.capacitor_threshold,
    )

    by_type = _load_counts(db_path=args.db, stock_only=args.stock_only)
    stats, allowlists = _build_allowlists(by_type, policy)

    unique_packages = {
        package
        for packages in allowlists.values()
        for package in packages
    }

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_db": str(args.db),
        "source_scope": "stock>0" if args.stock_only else "all",
        "policy": {
            "default_threshold": policy.default_threshold,
            "resistor_threshold": policy.resistor_threshold,
            "capacitor_threshold": policy.capacitor_threshold,
        },
        "summary": {
            "component_types": len(allowlists),
            "selected_package_entries": sum(len(v) for v in allowlists.values()),
            "selected_unique_packages": len(unique_packages),
        },
        "component_type_stats": stats,
        "allowlists": allowlists,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")

    print(f"Wrote {args.out}")
    print(
        "Selected package entries:",
        payload["summary"]["selected_package_entries"],
        "unique:",
        payload["summary"]["selected_unique_packages"],
    )
    for component_type in sorted(allowlists):
        stat = stats[component_type]
        print(
            f"{component_type}: threshold={stat['threshold']:.2f} "
            f"selected={stat['selected_packages']}/{stat['total_packages']} "
            f"coverage={stat['coverage']:.4f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
