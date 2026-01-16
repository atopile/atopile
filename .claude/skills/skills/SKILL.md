---
name: Skills
description: "How to write and maintain `.claude/skills/*/SKILL.md` files: source-of-truth-first process, verification steps, and conventions."
---

# Skills Skill (Maintaining Skill Docs)

This skill describes the process for maintaining the skill documentation under `.claude/skills/*/SKILL.md`.

The goal is that future LLM edits stay **accurate**, **actionable**, and **grounded in the repo** (not vibes).

## Quick Start

When updating any skill:

1) Find the module’s “source-of-truth” docs (README/design notes).
2) Verify claims directly in code (entrypoints + invariant-enforcing files).
3) Fix incorrect paths/APIs/tests by searching the repo.
4) Add/update a small `## Quick Start` that actually runs in this repo.
5) Validate frontmatter + referenced paths.

## What “Good” Looks Like

A good skill doc is:
- **Specific**: points at exact files and the *real* entrypoints.
- **Invariant-driven**: documents the correctness rules enforced by the code (not aspirational design).
- **Runnable**: Quick Start snippets compile/import (or at least match the current API surface).
- **Traceable**: any non-obvious claim can be traced to a file path in the repo.

## Standard Workflow (Source-of-Truth First)

### 1) Inventory the skill’s scope
- Identify the module boundary (directories, packages) and key consumers (“call sites”).
- Prefer using `rg` over memory: look for imports, entrypoints, and key classes/functions.

### 2) Read the docs, then the code that enforces invariants
Use this hierarchy:
1. A module README/design doc (if present)
2. The runtime entrypoint(s) used by the rest of the repo
3. The files that enforce invariants (the places that *must* remain correct)
4. Tests that codify behavior

Examples:
- Solver: `src/faebryk/core/solver/README.md` + `src/faebryk/core/solver/symbolic/invariants.py`
- Graph: `src/faebryk/core/zig/src/graph/graph.zig` + `src/faebryk/core/zig/src/python/graph/graph_py.zig` + generated stubs
- Library: `tools/library/gen_F.py` is the source-of-truth for `_F.py`

### 3) Fix wrong statements (don’t preserve broken history)
Common failure modes in skill docs:
- stale file paths (`atopile/src/...` vs `src/...`)
- renamed entrypoints (`lsp_server.py` vs imaginary `server.py`)
- test paths that no longer exist
- claims about behavior that conflict with the actual API surface (especially Zig bindings)

Rule: if you can’t prove it from the repo, either remove it or label it as a hypothesis with a pointer to where to verify.

### 4) Add a minimal, correct `## Quick Start`
Quick Start should be:
- 5–20 lines
- uses the *public* API surface as used elsewhere in the repo
- avoids placeholders like `src/.../something.zig`

Good patterns:
- CLI snippet for user-facing flows (`ato build`, `ato dev test`)
- Python snippet for core APIs (`GraphView.create()` / `TypeGraph.create(...)`)

### 5) Validation checklist (required)

- Frontmatter YAML parses and contains `name` and `description`.
- Every referenced `src/`, `tools/`, and `test/` path exists (exclude generated build outputs).
- Any code identifiers mentioned (classes/functions) exist (`rg` check).
- Quick Start uses correct import paths and function signatures.

## Style/Structure Conventions

Prefer this ordering:
1) One-paragraph summary
2) `## Quick Start`
3) `## Relevant Files`
4) `## Dependants (Call Sites)`
5) `## How to Work With / Develop / Test`
6) `## Best Practices` / `## Invariants` (when applicable)

Keep the doc concise and “repo-local”: avoid external links unless they’re stable standards docs.

