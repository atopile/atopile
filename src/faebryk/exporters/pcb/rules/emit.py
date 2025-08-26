from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _mm_str(value_mm: float) -> str:
    return f"{value_mm:.2f}mm"


def emit_rule(name: str, clauses: Iterable[str]) -> str:
    inner = "\n  ".join(clauses)
    return f"(rule {name}\n  {inner}\n)"


def write_rules_file(rules: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(["(version 1)", *rules]), encoding="utf-8")
