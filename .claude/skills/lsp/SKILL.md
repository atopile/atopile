---
name: LSP
description: "How the atopile Language Server works (pygls), how it builds per-document graphs for completion/hover/defs, and the invariants for keeping it fast and crash-proof."
---

# LSP Module

The `lsp` module (located in `src/atopile/lsp/`) implements the Language Server Protocol for Atopile. It provides IDE features like autocomplete, go-to-definition, and diagnostics (error reporting) for `ato` files.

## Quick Start

Run the server on stdio (what editors expect):

```bash
python -m atopile.lsp.lsp_server
```

## Relevant Files

- Server implementation: `src/atopile/lsp/lsp_server.py`
  - owns global `LSP_SERVER` (pygls `LanguageServer`)
  - maintains per-document `DocumentState` (graph/typegraph/build_result)
  - implements completion/hover/definition/diagnostics handlers
- Utilities: `src/atopile/lsp/lsp_utils.py`
- Optional debugging helper: `src/atopile/lsp/_debug_server.py`

## Dependants (Call Sites)

- **VSCode Extension**: The designated client for this server.
- **Compiler**: The LSP invokes the compiler (often in a partial or fault-tolerant mode) to understand the code structure.

## How to Work With / Develop / Test

### Core Concepts
- **Partial Compilation**: Unlike the CLI build, the LSP must handle broken or incomplete code without crashing.
- **Latency**: Features must be fast (<50ms for typing, <200ms for completion).
- **Per-document graphs**: each open document has an isolated `GraphView` + `TypeGraph` stored in `DocumentState`.
- **Keep last good build**: the server keeps the last successful `BuildFileResult` to power completion/hover even when the current edit has errors.

### Development Workflow
1) Edit handlers/helpers in `src/atopile/lsp/lsp_server.py`.
2) Run completion tests (fast loop) and verify GraphView cleanup paths.

### Testing
- Integration-style tests: `ato dev test --llm test/test_lsp_completion.py -q`

## Best Practices
- **Robustness**: Never let the server crash. Catch all exceptions in handlers and log them.
- **Debouncing**: Don't trigger expensive operations on every keystroke.

## Core Invariants (easy to regress)
- Always destroy old graphs on rebuild/reset (`DocumentState.reset_graph` calls `GraphView.destroy()`).
- Do not assume builds succeed; most features must handle:
  - syntax errors (ANTLR)
  - partial typegraphs
  - exceptions from linking/deferred execution
