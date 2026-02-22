# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from rich.console import Console
from rich.table import Table

SIZE_ORDER = {"small": 0, "medium": 1, "large": 2, "xlarge": 3}
app = typer.Typer(add_completion=False)


def _format_bench_value(value: float | None, precision: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:.{precision}f}"


def _print_benchmark_tables(report: dict, artifact_path: Path) -> None:
    rows = report.get("rows", [])
    metadata = report.get("metadata", {})

    timing_table = Table(title=f"S-Expression Timing ({artifact_path})")
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

    memory_table = Table(title=f"S-Expression Stage Memory ({artifact_path})")
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
        key=lambda key: (key[0], SIZE_ORDER.get(key[1], 99)),
    )

    for profile, size in sorted_keys:
        data = grouped[(profile, size)]
        timing_table.add_row(
            profile,
            size,
            f"{int(data['bytes']):,}",
            str(int(data["max_depth"])),
            _format_bench_value(data.get("tokenizer")),  # type: ignore[arg-type]
            _format_bench_value(data.get("ast")),  # type: ignore[arg-type]
            _format_bench_value(data.get("parser")),  # type: ignore[arg-type]
            _format_bench_value(data.get("encode")),  # type: ignore[arg-type]
            _format_bench_value(data.get("pretty")),  # type: ignore[arg-type]
            _format_bench_value(data.get("pretty_cum_peak_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("pretty_cum_peak_over_start_kib")),  # type: ignore[arg-type]
        )
        memory_table.add_row(
            profile,
            size,
            _format_bench_value(data.get("tokenizer_mem_delta_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("ast_mem_delta_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("parser_mem_delta_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("encode_mem_delta_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("pretty_mem_delta_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("tokenizer_peak_inc_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("ast_peak_inc_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("parser_peak_inc_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("encode_peak_inc_kib")),  # type: ignore[arg-type]
            _format_bench_value(data.get("pretty_peak_inc_kib")),  # type: ignore[arg-type]
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


@app.command("print-table")
def main(
    json_path: Path = typer.Argument(
        Path("artifacts/sexp-benchmark.json"),
        help="Path to benchmark JSON (default: artifacts/sexp-benchmark.json).",
    ),
) -> None:
    artifact_path = json_path
    if not artifact_path.exists():
        raise FileNotFoundError(f"Benchmark JSON not found: {artifact_path}")

    report = json.loads(artifact_path.read_text())
    _print_benchmark_tables(report, artifact_path)


@pytest.mark.slow
@pytest.mark.not_in_ci
def test_performance_sexp_synthetic_matrix(repo_root: Path):
    zig_dir = repo_root / "src" / "faebryk" / "core" / "zig"
    artifact_path = repo_root / "artifacts" / "sexp-benchmark.json"

    warmup = os.environ.get("SEXP_BENCH_WARMUP", "1")
    samples = os.environ.get("SEXP_BENCH_SAMPLES", "1")
    max_size_label = os.environ.get("SEXP_BENCH_MAX_SIZE_LABEL", "large")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "ziglang",
            "build",
            "sexp-bench",
            "-Doptimize=ReleaseFast",
        ],
        cwd=zig_dir,
        check=True,
    )

    bench_bin = zig_dir / "zig-out" / "bin" / "sexp_bench"
    if sys.platform == "win32":
        bench_bin = bench_bin.with_suffix(".exe")

    subprocess.run(
        [
            str(bench_bin),
            "--output-json",
            str(artifact_path),
            "--warmup",
            warmup,
            "--samples",
            samples,
            "--max-size-label",
            max_size_label,
        ],
        cwd=repo_root,
        check=True,
    )

    report = json.loads(artifact_path.read_text())
    assert report["metadata"]["max_size_label"] == max_size_label
    rows = report["rows"]
    assert rows, "benchmark produced no rows"

    expected_layers = {"tokenizer", "ast", "parser", "encode", "pretty"}
    size_order = ["small", "medium", "large", "xlarge"]
    max_idx = size_order.index(max_size_label)
    expected_sizes = set(size_order[: max_idx + 1])
    expected_profiles = {"shallow_tracks_like", "deep_footprint_like"}

    assert {row["layer"] for row in rows} == expected_layers
    assert {row["size_label"] for row in rows} == expected_sizes
    assert {row["depth_profile"] for row in rows} == expected_profiles

    # Ensure uniqueness for dataset+layer cells in the benchmark matrix.
    matrix_keys = {(row["dataset_id"], row["layer"]) for row in rows}
    assert len(matrix_keys) == len(rows)

    metric_keys_non_negative = (
        "mean_ms",
        "median_ms",
        "p80_ms",
        "min_ms",
        "max_ms",
        "mean_peak_kib",
        "median_peak_kib",
        "p80_peak_kib",
        "min_peak_kib",
        "max_peak_kib",
        "mean_cumulative_pipeline_peak_kib",
        "median_cumulative_pipeline_peak_kib",
        "p80_cumulative_pipeline_peak_kib",
        "min_cumulative_pipeline_peak_kib",
        "max_cumulative_pipeline_peak_kib",
        "mean_stage_mem_before_kib",
        "mean_stage_mem_after_kib",
        "mean_stage_peak_increment_kib",
        "mean_cumulative_pipeline_peak_over_start_kib",
    )
    metric_keys_any_sign = (
        "delta_mean_peak_kib_from_prev",
        "mean_stage_mem_delta_kib",
    )
    metric_keys_cumulative_delta = (
        "delta_mean_cumulative_pipeline_peak_kib_from_prev",
        "delta_mean_cumulative_pipeline_peak_over_start_kib_from_prev",
    )
    for row in rows:
        assert row["samples"] > 0
        assert row["bytes"] > 0
        assert row["max_depth"] > 0
        for key in metric_keys_non_negative:
            value = row[key]
            assert isinstance(value, int | float)
            assert math.isfinite(value)
            assert value >= 0
        for key in metric_keys_any_sign:
            value = row[key]
            assert isinstance(value, int | float)
            assert math.isfinite(value)
        for key in metric_keys_cumulative_delta:
            value = row[key]
            assert isinstance(value, int | float)
            assert math.isfinite(value)
            assert value >= 0

    # Print benchmark tables at the end for easier human review.
    _print_benchmark_tables(report, artifact_path)


if __name__ == "__main__":
    app()
