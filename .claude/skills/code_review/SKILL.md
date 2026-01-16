---
name: Code Review
description: "LLM-focused code review process for this repo: what to check, how to ground feedback in invariants/tests, and how to verify changes efficiently (including test-report.json)."
---

# Code Review Skill

This skill is the canonical guidance for automated and interactive code reviews in this repo. It is written for LLM reviewers (CI bots and local agents).

## Quick Start

- Read the PR description and ensure it matches `.github/pull_request_template.md`.
- Review the diff focusing on invariants, correctness, and performance-sensitive hotspots.
- If you can run commands locally, prefer targeted verification:
  - `ato dev test -k <area>` (fast filter)
  - `ato dev compile` (if Zig/bindings changed)
  - `ato dev flags` (if behavior depends on ConfigFlags)
- When summarizing failures/regressions, prefer `artifacts/test-report.json` over HTML.

## What to Prioritize (In Order)

1) **Correctness + invariants**
   - Identify the invariants the changed code is supposed to preserve and check the code that enforces them.
   - If you can’t find an invariant in-code or in tests, flag it as “missing invariant coverage”.

2) **Performance / scalability**
   - This branch prioritizes speed and maintainability; watch for accidental `O(n^2)` walks, repeated graph traversals, excessive allocations, or debug logging in hot paths.
   - Zig/Python boundary changes are especially sensitive (ownership, lifetimes, deinit).

3) **Maintainability**
   - Prefer small, well-named units and clear boundaries (compiler vs graph vs solver vs library).
   - Avoid adding new “mini frameworks” unless the repo already uses that pattern.

4) **Test coverage**
   - If behavior changed, require a test (or a strong reason it can’t be tested).
   - Prefer targeted tests near the module; avoid broad end-to-end tests unless necessary.

## Repo-Specific Review Anchors

- **Dev workflow + reports**: `ato dev test` writes `artifacts/test-report.json` and optionally `artifacts/test-report.html` (see `test/runner/main.py`).
- **ConfigFlags**: inventory via `ato dev flags`; prefer code-driven discovery over hand-maintained docs.
- **Graph/fabll redesign**: see `AGENTS.md` and the relevant `.claude/skills/*` docs for the area you’re reviewing.
- **Solver invariants**: `src/faebryk/core/solver/README.md` + `src/faebryk/core/solver/symbolic/invariants.py`.

## How to Write Review Comments (LLM Style)

- Ground every non-trivial claim in the diff or a repo path (be explicit about file + symbol).
- Separate:
  - **Must-fix** (correctness/security/regression risks)
  - **Should-fix** (maintainability/perf improvements)
  - **Nice-to-have** (style/ergonomics)
- Prefer actionable suggestions (what to change + why + where).
- If you’re uncertain, ask a concrete question and point to the ambiguous code.

