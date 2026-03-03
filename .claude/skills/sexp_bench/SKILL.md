# SEXP Benchmark Strategy

## Goal
Measure and improve S-expression pipeline performance with a focus on:
- Throughput per stage
- Peak memory per stage
- End-to-end behavior on realistic KiCad PCB inputs

## Pipeline Stages
Benchmark these layers separately:
- `tokenizer`
- `ast`
- `parser` (typed decode)
- `encode` (typed encode to raw SEXP)
- `pretty` (formatting)

## Dataset Dimensions
Use a matrix over:
- `depth`: shallow vs deep nesting
- `size`: small, medium, large

Recommended size buckets:
- `small`: `< 64 KiB`
- `medium`: `64 KiB .. < 1 MiB`
- `large`: `1 MiB .. < 10 MiB`

## Measurement Model
For each stage and sample:
- `mean_ms` and percentile latency (`median`, `p80`)
- `mem_before`, `mem_after`, `mem_delta`
- `stage_peak_increment` (stage-local high watermark increase)
- `cumulative_pipeline_peak` and `cumulative_peak_over_start`

Key interpretation:
- Negative/near-zero `mem_delta` can still coexist with high `stage_peak_increment`.
- For allocator-heavy code, `peak` metrics are more informative than final deltas.

## Methodology
1. Warm caches with warmup runs.
2. Run at least one measured sample per cell (more for stable comparisons).
3. Keep run settings fixed when comparing commits:
   - same machine
   - same optimize mode
   - same dataset generator/inputs
4. Compare both synthetic matrix and a large real-world board.

## E2E Roundtrip Benchmark (panel.kicad_pcb)
Use this when validating real end-to-end impact (load -> dump -> reload) on a large board.

### Setup
1. Build `pyzig_sexp.so` in each checkout you want to compare:
```bash
source .venv/bin/activate
cd src/faebryk/core/zig
python -m ziglang build python-ext -Doptimize=ReleaseFast -Dpython-include=/usr/include/python3.14 -Dpython-lib=python3.14
```
2. For baseline vs current comparison, create a detached worktree for baseline:
```bash
git worktree add /tmp/atopile_pre_tokenizer_fix <baseline_commit>
```
3. Run the benchmark sequentially (not in parallel) to avoid cross-run CPU contention.

### Runner Pattern
Use Python with direct `importlib` loading of `pyzig_sexp.so` from each checkout. This avoids accidental rebuilds and keeps the comparison tied to the compiled artifact in that checkout.

```python
from pathlib import Path
from time import perf_counter
import gc, importlib.util, sys

spec = importlib.util.spec_from_file_location(
    "pyzig_sexp",
    "src/faebryk/core/zig/zig-out/lib/pyzig_sexp.so",
)
mod = importlib.util.module_from_spec(spec)
sys.modules["pyzig_sexp"] = mod
spec.loader.exec_module(mod)

text = Path("panel.kicad_pcb").read_text(encoding="utf-8")

# warmup
obj = mod.pcb.loads(text)
out = mod.pcb.dumps(obj)
obj2 = mod.pcb.loads(out)
del obj, out, obj2
gc.collect()

runs = []
for _ in range(5):
    gc.collect()
    t0 = perf_counter()
    obj = mod.pcb.loads(text)
    t1 = perf_counter()
    out = mod.pcb.dumps(obj)
    t2 = perf_counter()
    obj2 = mod.pcb.loads(out)
    t3 = perf_counter()
    runs.append((t1 - t0, t2 - t1, t3 - t2, t3 - t0))
    del obj, out, obj2

print("AVG", " ".join(f"{sum(r[i] for r in runs)/len(runs):.3f}" for i in range(4)))
```

### Report Format
Report at minimum:
- `load_avg_s`
- `dump_avg_s`
- `reload_avg_s`
- `total_roundtrip_avg_s`
- relative delta vs baseline (%)

## Optimization Approach
Prioritize stage-local wins first, then validate global effects:
1. Eliminate avoidable intermediate allocations.
2. Use streaming write paths for encode-heavy workloads.
3. Keep fast parse paths for success cases; fallback to richer diagnostics on error.
4. Re-check correctness via roundtrip and file-format tests after each change.

## Safety Checks
After each optimization pass:
- Build release artifacts.
- Run KiCad file-format tests.
- Run representative load-transform-dump flows.
- Re-run matrix + panel benchmark snapshots.

## Reporting
Summarize gains in two views:
- Matrix view: `(depth, size) x stage`
- Large-board view: stage timing + peak memory

Always report:
- absolute values
- speedup ratios
- peak-memory deltas vs baseline
