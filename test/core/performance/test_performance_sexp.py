# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest


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
