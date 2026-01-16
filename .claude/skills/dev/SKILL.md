---
name: Dev
description: "LLM-focused workflow for working in this repo: compile Zig, run the orchestrated test runner, consume test-report.json/html artifacts, and discover/debug ConfigFlags."
---

# Dev Module

This skill is written for LLMs working inside this repo. It focuses on the fastest, most reliable inner loop:

- rebuild Zig bindings when needed
- run the repo’s orchestrated test runner (not just raw `pytest`)
- use the generated test reports (`artifacts/test-report.json` and `artifacts/test-report.html`)
- discover and use `ConfigFlag`s correctly (and inventory them repo-wide)

## Quick Start

```bash
source .venv/bin/activate

ato dev compile
ato dev test -k solver
ato dev test --view HEAD --open
ato dev flags
```

## Relevant Files

- CLI commands: `src/atopile/cli/dev.py`
  - `ato dev compile` (triggers Zig build via `import faebryk.core.zig`)
  - `ato dev test` (runs `test/runner/main.py` with args; supports baseline/CI report helpers)
- Zig build-on-import glue: `src/faebryk/core/zig/__init__.py` (`ZIG_NORECOMPILE`, `ZIG_RELEASEMODE`)
- Config flags utility: `src/faebryk/libs/util.py` (`ConfigFlag`, `ConfigFlagInt`, …)
- Test runner + reports: `test/runner/main.py` (`artifacts/test-report.json`, `artifacts/test-report.html`)
- CI artifacts definition: `.github/workflows/pytest.yml` (`test-report.json`, `test-report.html`)

## Dependants (Call Sites)

- **CI/CD**: The `dev` commands are the primary interface for GitHub Actions workflows.
- **Local Development**: Developers use `ato dev compile` after modifying Zig code.

## How to Work With / Develop / Test

### Core Commands
- `ato dev compile`: compile native extensions (graph/typegraph/sexp bindings).
- `ato dev test`: runs pytest (defaults to `-p test -p src`); supports:
  - `-k` filter (`-- -k ...` also works via passthrough args)
  - `--baseline` comparisons (commit hash or `HEAD~N` style)
  - `--view` / `--open` to fetch and open the `test-report.html` artifact from GitHub Actions (requires `gh` CLI)
  - `--ci` to apply the CI marker expression (`not not_in_ci and not regression and not slow`)
  - `--direct -k <testname>` to run a single test via `test/runtest.py` (tight single-test loops)

### Test Reports (JSON first, HTML second)

Local test runs write:
- `artifacts/test-report.json` (canonical for machines/tools; outcomes/durations/memory/baseline compare status)
- `artifacts/test-report.html` (human dashboard; controlled by `FBRK_TEST_GENERATE_HTML=1`)

CI uploads both artifacts (see `.github/workflows/pytest.yml`):
- `test-report.json`
- `test-report.html`

Notes for LLM debugging:
- Prefer the JSON report when summarizing failures/regressions; it’s structured and includes baseline comparisons.
- The HTML is best for quickly scanning long-running tests, worker crashes, and per-test output.

Remote/baseline behavior:
- `ato dev test --baseline <commit>` uses the **CI `test-report.json` artifact** as the baseline (requires `gh` CLI).
- `ato dev test --view <commit> --open` currently fetches/opens **only** the HTML artifact; for JSON, download the `test-report.json` artifact via `gh run download`.

Useful test-runner environment variables (see `test/runner/main.py`):
- `FBRK_TEST_REPORT_INTERVAL` (seconds; report refresh cadence)
- `FBRK_TEST_LONG_THRESHOLD` (seconds; “long test” threshold)
- `FBRK_TEST_WORKERS` (`0` = cpu count, negative scales workers)
- `FBRK_TEST_GENERATE_HTML` (`1/0`)
- `FBRK_TEST_PERIODIC_HTML` (`1/0`)

### ConfigFlags (how to use + how to inventory)

`ConfigFlag` is the repo’s “toggle-by-env-var” mechanism. The environment variable name is the first argument to `ConfigFlag(...)`.

Usage:
```bash
export SOME_FLAG=1
```

Inventory all ConfigFlags in-tree (preferred over trying to maintain a manual list):
```bash
ato dev flags
```

Prefer using `ato dev flags` when you want the full picture (types/defaults/descriptions + callsite counts) in one place.

High-leverage flags you’ll use often:
- Zig build: `ZIG_NORECOMPILE`, `ZIG_RELEASEMODE`
- Solver debug: `SLOG`, `SVERBOSE_TABLE`, `SPRINT_START`, `SMAX_ITERATIONS`, `SSHOW_SS_IS`
- Logs: `COLOR_LOGS`, `LOG_TIME`, `LOG_FILEINFO`

### Development Workflow
1.  **Zig Changes**: Edit files under `src/faebryk/core/zig/src/` -> Run `ato dev compile`.
2.  **Profiling**: If something is slow, use `ato dev profile <command>` to generate a flamegraph or stats.

### Testing
- Main test entrypoint: `ato dev test` (or `pytest` directly).
- If you change CLI behavior, add/adjust tests under `test/` that exercise the command surface.

## Best Practices
- **Use ConfigFlags**: For experimental features or verbose debugging, use a `ConfigFlag` instead of commenting out code.
- **Compile often**: Zig errors won’t be caught by Python tooling.
