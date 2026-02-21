#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import time
from pathlib import Path

import cadquery as cq
import zstd


def _resolve_gltf_transform_cmd() -> list[str]:
    try:
        direct = subprocess.run(
            ["gltf-transform", "--version"],
            capture_output=True,
            text=True,
        )
        if direct.returncode == 0:
            return ["gltf-transform"]
    except FileNotFoundError:
        pass

    try:
        npx = subprocess.run(
            ["npx", "--yes", "@gltf-transform/cli", "--version"],
            capture_output=True,
            text=True,
        )
        if npx.returncode == 0:
            return ["npx", "--yes", "@gltf-transform/cli"]
    except FileNotFoundError:
        pass
    raise RuntimeError(
        "Could not run gltf-transform (neither `gltf-transform` nor "
        "`npx --yes @gltf-transform/cli` succeeded)."
    )


def _p_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "p95": 0.0,
        }
    ordered = sorted(values)
    idx_95 = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return {
        "count": len(values),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p95": ordered[idx_95],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark STEP(.zst) -> GLB conversion with CadQuery and gltf-transform."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("/home/jlc/stage1_fetch/objects/model_step"),
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/step_glb_bench"))
    parser.add_argument(
        "--no-gltf-transform",
        action="store_true",
        help="Skip gltf-transform optimize benchmark.",
    )
    args = parser.parse_args(argv)

    files = sorted(args.source_dir.glob("*.zst"))
    if not files:
        raise FileNotFoundError(f"No .zst STEP files found in {args.source_dir}")
    rng = random.Random(args.seed)
    sample = files if len(files) <= args.sample_size else rng.sample(files, args.sample_size)
    sample = sorted(sample)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    step_dir = args.out_dir / "step_raw"
    glb_dir = args.out_dir / "glb_raw"
    opt_dir = args.out_dir / "glb_opt"
    step_dir.mkdir(parents=True, exist_ok=True)
    glb_dir.mkdir(parents=True, exist_ok=True)
    opt_dir.mkdir(parents=True, exist_ok=True)

    convert_times: list[float] = []
    convert_success = 0
    step_sizes: list[int] = []
    glb_sizes: list[int] = []
    failures: list[dict[str, str]] = []

    for i, zst_path in enumerate(sample, start=1):
        stem = zst_path.stem
        step_path = step_dir / f"{stem}.step"
        glb_path = glb_dir / f"{stem}.glb"
        try:
            raw = zstd.decompress(zst_path.read_bytes())
            step_path.write_bytes(raw)
            step_sizes.append(len(raw))

            t0 = time.perf_counter()
            wp = cq.importers.importStep(str(step_path))
            assy = cq.Assembly()
            assy.add(wp.val())
            assy.export(str(glb_path), exportType="GLTF")
            dt = time.perf_counter() - t0

            if not glb_path.exists():
                raise RuntimeError("GLB file missing after export")
            convert_times.append(dt)
            glb_sizes.append(glb_path.stat().st_size)
            convert_success += 1
        except Exception as ex:
            failures.append({"file": str(zst_path), "stage": "convert", "error": repr(ex)})

        if i % 10 == 0:
            print(
                json.dumps(
                    {
                        "progress": f"{i}/{len(sample)}",
                        "convert_success": convert_success,
                        "convert_failures": len(failures),
                    },
                    ensure_ascii=True,
                )
            )

    transform_times: list[float] = []
    transform_success = 0
    opt_sizes: list[int] = []
    transform_failures: list[dict[str, str]] = []
    gltf_cmd: list[str] | None = None

    if not args.no_gltf_transform:
        gltf_cmd = _resolve_gltf_transform_cmd()
        for i, glb_path in enumerate(sorted(glb_dir.glob("*.glb")), start=1):
            opt_path = opt_dir / glb_path.name
            try:
                t0 = time.perf_counter()
                proc = subprocess.run(
                    [*gltf_cmd, "optimize", str(glb_path), str(opt_path)],
                    capture_output=True,
                    text=True,
                )
                dt = time.perf_counter() - t0
                if proc.returncode != 0:
                    raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "optimize failed")
                if not opt_path.exists():
                    raise RuntimeError("optimized GLB missing")
                transform_times.append(dt)
                opt_sizes.append(opt_path.stat().st_size)
                transform_success += 1
            except Exception as ex:
                transform_failures.append(
                    {"file": str(glb_path), "stage": "gltf_transform", "error": repr(ex)}
                )

            if i % 10 == 0:
                print(
                    json.dumps(
                        {
                            "transform_progress": f"{i}/{len(list(glb_dir.glob('*.glb')))}",
                            "transform_success": transform_success,
                            "transform_failures": len(transform_failures),
                        },
                        ensure_ascii=True,
                    )
                )

    summary = {
        "sample_size_requested": args.sample_size,
        "sample_size_actual": len(sample),
        "source_dir": str(args.source_dir),
        "out_dir": str(args.out_dir),
        "cadquery_version": cq.__version__,
        "convert": {
            "success": convert_success,
            "failure": len(failures),
            "time_seconds": _p_stats(convert_times),
            "step_size_bytes": _p_stats([float(s) for s in step_sizes]),
            "glb_size_bytes": _p_stats([float(s) for s in glb_sizes]),
            "size_ratio_glb_over_step_mean": (
                (statistics.fmean(glb_sizes) / statistics.fmean(step_sizes))
                if step_sizes and glb_sizes
                else 0.0
            ),
        },
        "gltf_transform": {
            "enabled": not args.no_gltf_transform,
            "command": gltf_cmd,
            "success": transform_success,
            "failure": len(transform_failures),
            "time_seconds": _p_stats(transform_times),
            "optimized_glb_size_bytes": _p_stats([float(s) for s in opt_sizes]),
            "size_ratio_opt_over_raw_mean": (
                (statistics.fmean(opt_sizes) / statistics.fmean(glb_sizes))
                if glb_sizes and opt_sizes
                else 0.0
            ),
        },
        "failures": failures[:20],
        "transform_failures": transform_failures[:20],
    }

    summary_path = args.out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"summary_path": str(summary_path)}, ensure_ascii=True))
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
