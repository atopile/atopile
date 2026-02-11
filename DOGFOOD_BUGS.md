# Dogfood Bug Notes

## 2026-02-11

### Bug 001: Packages Project tab hidden by stale Browse search
- Report: Install package(s) in `Browse`, switch to `Project`, installed packages appear missing until search is cleared.
- Root cause: `searchQuery` from `Browse` was also applied to `Project` dependencies, even though `Project` has no visible search input.
- Fix: Stop applying `searchQuery` to `Project` dependencies in `src/ui-server/src/components/PackagesPanel.tsx`.
- Regression test: `src/ui-server/src/__tests__/PackagesPanel.test.tsx`.
- Structural notes: If we want search in both tabs, add a dedicated search box per tab and keep tab-local query state.
