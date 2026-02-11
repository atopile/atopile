# Dogfood Bug Notes

## 2026-02-11

### Bug 001: Packages Project tab hidden by stale Browse search
- Report: Install package(s) in `Browse`, switch to `Project`, installed packages appear missing until search is cleared.
- Root cause: `searchQuery` from `Browse` was also applied to `Project` dependencies, even though `Project` has no visible search input.
- Fix: Stop applying `searchQuery` to `Project` dependencies in `src/ui-server/src/components/PackagesPanel.tsx`.
- Regression test: `src/ui-server/src/__tests__/PackagesPanel.test.tsx`.
- Structural notes: If we want search in both tabs, add a dedicated search box per tab and keep tab-local query state.

### Bug 002: LSP server crashes when deprecated warnings are downgraded
- Report: Intermittent language-server error: `Error in server: AttributeError: 'DeprecatedException' object has no attribute 'origin_start'`.
- Root cause: `exception_to_diagnostic` in `src/atopile/lsp/lsp_server.py` assumed all `UserException`s have source-location fields (`origin_start`, `origin_stop`, `code`), but `DeprecatedException` inherits plain `UserException` and has no location metadata.
- Fix: Handle non-source-located `UserException` types safely in `exception_to_diagnostic` and only access source fields for `SourceLocatedUserException`.
- Regression test: Ad-hoc runtime check via Python snippet calling `exception_to_diagnostic(DeprecatedException(...))`.
- Structural notes: Add a dedicated LSP unit test for downgraded non-source exceptions to prevent regressions.

### Bug 003: Deprecated warnings were often unlocated in diagnostics
- Report: Deprecation diagnostics frequently show without a source range, even when warning originates from parsed/visited source.
- Root cause: `DeprecatedException` did not carry source metadata by default, and deprecation callsites in visitors/overrides did not pass source location.
- Fix: Make `DeprecatedException` source-locatable; pass parser context in `antlr_visitor`, file-location metadata in `ast_visitor` and override registries, and teach LSP diagnostic conversion to use fallback file-location metadata.
- Regression test: Ad-hoc runtime checks for both located and unlocated `DeprecatedException` conversion.
- Structural notes: Add integration test coverage for deprecation diagnostics in LSP (range + file path expectations).

### Bug 004: Runtime ElectricPower alias deprecation warning missing source location
- Report: Deprecated `vcc/gnd` alias warnings can appear without source location in user diagnostics.
- Root cause: Runtime warning was emitted from `ElectricPower` design check without attempting to map back to source chunk metadata.
- Fix: Add best-effort `has_source_chunk` -> `SourceChunk.loc` lookup and attach file location to `DeprecatedException` in `src/faebryk/library/ElectricPower.py`.
- Regression test: `ruff check` + `py_compile` on modified file.
- Structural notes: Extend this pattern to other runtime-originated warnings where source chunks exist.
