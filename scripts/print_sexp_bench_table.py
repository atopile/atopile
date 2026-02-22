#!/usr/bin/env python
# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

SIZE_ORDER = {"small": 0, "medium": 1, "large": 2, "xlarge": 3}
LAYER_ORDER = ["tokenizer", "ast", "parser", "encode", "pretty"]


def _format(value: float | None, precision: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:.{precision}f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a rich table from sexp benchmark JSON."
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        default="artifacts/sexp-benchmark.json",
        help="Path to sexp benchmark JSON (default: artifacts/sexp-benchmark.json)",
    )
    args = parser.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Benchmark JSON not found: {json_path}")

    payload = json.loads(json_path.read_text())
    rows = payload.get("rows", [])
    metadata = payload.get("metadata", {})

    timing_table = Table(title=f"S-Expression Timing ({json_path})")
    timing_table.add_column("Profile")
    timing_table.add_column("Size")
    timing_table.add_column("Bytes", justify="right")
    timing_table.add_column("Depth", justify="right")
    timing_table.add_column("Tokenizer (ms)", justify="right")
    timing_table.add_column("AST (ms)", justify="right")
    timing_table.add_column("Parser (ms)", justify="right")
    timing_table.add_column("Encode (ms)", justify="right")
    timing_table.add_column("Pretty (ms)", justify="right")
    timing_table.add_column("Cum Peak KiB", justify="right")
    timing_table.add_column("Cum Peak>Start KiB", justify="right")

    memory_table = Table(title=f"S-Expression Stage Memory ({json_path})")
    memory_table.add_column("Profile")
    memory_table.add_column("Size")
    memory_table.add_column("Tok ΔKiB", justify="right")
    memory_table.add_column("AST ΔKiB", justify="right")
    memory_table.add_column("Par ΔKiB", justify="right")
    memory_table.add_column("Enc ΔKiB", justify="right")
    memory_table.add_column("Pre ΔKiB", justify="right")
    memory_table.add_column("Tok Peak+KiB", justify="right")
    memory_table.add_column("AST Peak+KiB", justify="right")
    memory_table.add_column("Par Peak+KiB", justify="right")
    memory_table.add_column("Enc Peak+KiB", justify="right")
    memory_table.add_column("Pre Peak+KiB", justify="right")

    grouped: dict[tuple[str, str], dict[str, float | int | str]] = {}
    for row in rows:
        key = (row["depth_profile"], row["size_label"])
        grouped.setdefault(
            key,
            {
                "bytes": row["bytes"],
                "max_depth": row["max_depth"],
            },
        )
        grouped[key][row["layer"]] = row["mean_ms"]
        grouped[key][f"{row['layer']}_mem_delta_kib"] = row.get(
            "mean_stage_mem_delta_kib",
            row.get("delta_mean_peak_kib_from_prev", 0.0),
        )
        grouped[key][f"{row['layer']}_peak_inc_kib"] = row.get(
            "mean_stage_peak_increment_kib",
            0.0,
        )
        grouped[key][f"{row['layer']}_cum_peak_kib"] = row.get(
            "mean_cumulative_pipeline_peak_kib",
            0.0,
        )
        grouped[key][f"{row['layer']}_cum_peak_over_start_kib"] = row.get(
            "mean_cumulative_pipeline_peak_over_start_kib",
            row.get("mean_cumulative_pipeline_peak_kib", 0.0),
        )

    sorted_keys = sorted(
        grouped.keys(),
        key=lambda k: (k[0], SIZE_ORDER.get(k[1], 99)),
    )

    for profile, size in sorted_keys:
        data = grouped[(profile, size)]
        timing_table.add_row(
            profile,
            size,
            f"{int(data['bytes']):,}",
            str(int(data["max_depth"])),
            _format(data.get("tokenizer")),  # type: ignore[arg-type]
            _format(data.get("ast")),  # type: ignore[arg-type]
            _format(data.get("parser")),  # type: ignore[arg-type]
            _format(data.get("encode")),  # type: ignore[arg-type]
            _format(data.get("pretty")),  # type: ignore[arg-type]
            _format(data.get("pretty_cum_peak_kib")),  # type: ignore[arg-type]
            _format(data.get("pretty_cum_peak_over_start_kib")),  # type: ignore[arg-type]
        )
        memory_table.add_row(
            profile,
            size,
            _format(data.get("tokenizer_mem_delta_kib")),  # type: ignore[arg-type]
            _format(data.get("ast_mem_delta_kib")),  # type: ignore[arg-type]
            _format(data.get("parser_mem_delta_kib")),  # type: ignore[arg-type]
            _format(data.get("encode_mem_delta_kib")),  # type: ignore[arg-type]
            _format(data.get("pretty_mem_delta_kib")),  # type: ignore[arg-type]
            _format(data.get("tokenizer_peak_inc_kib")),  # type: ignore[arg-type]
            _format(data.get("ast_peak_inc_kib")),  # type: ignore[arg-type]
            _format(data.get("parser_peak_inc_kib")),  # type: ignore[arg-type]
            _format(data.get("encode_peak_inc_kib")),  # type: ignore[arg-type]
            _format(data.get("pretty_peak_inc_kib")),  # type: ignore[arg-type]
        )

    console = Console()
    console.print(
        "Run metadata: "
        f"warmup={metadata.get('warmup', '?')}, "
        f"samples={metadata.get('samples', '?')}, "
        f"max_size_label={metadata.get('max_size_label', '?')}, "
        f"dataset_count={metadata.get('dataset_count', '?')}, "
        f"row_count={metadata.get('row_count', '?')}"
    )
    console.print(timing_table)
    console.print(memory_table)


if __name__ == "__main__":
    main()
