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
