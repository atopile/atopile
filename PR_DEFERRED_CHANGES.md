# Deferred Changes Pulled From `feature/i2c_power_trees`

These items were removed from this PR to reduce scope/noise. They appear useful, but are not required for delivering the core features in this PR (schematic viewer, I2C tree, power tree, pinout viewer).

## 0) Pinout viewer slice (deferred)
Removed/disabled:
- `faebryk` pinout exporter files
- `ui-server` pinout entry/viewer files
- `vscode-atopile` pinout watcher/webview command wiring

Why deferred:
- Optional relative to the core branch goals (schematic + I2C tree + power tree).
- Removing this slice significantly reduces PR breadth and review burden.

Suggested follow-up PR:
- Re-introduce pinout as a standalone feature PR with exporter, webview, and UX wiring together.

## 1) UI-server test suite expansion (deferred)
Removed: new tests under `src/ui-server/src/__tests__/`.

Why deferred:
- Large file-count impact and review overhead.
- Core runtime behavior can ship independently.

Suggested follow-up PR:
- Re-introduce focused test coverage for:
  - schematic layout/routing utilities,
  - tree transform/layout logic,
  - parser/model transforms.

## 2) Build dedupe + request-shape expansion (deferred)
Removed changes in:
- `src/atopile/dataclasses.py`
- `src/atopile/model/build_queue.py`
- `src/atopile/model/builds.py`
- `src/atopile/server/domains/actions.py`

What was deferred:
- `keep_picked_parts` added to build request payloads.
- Duplicate-build matching expanded to include include/exclude targets and extra flags.

Why deferred:
- Valuable, but cross-cutting backend behavior not strictly required for viewer feature delivery.
- Better shipped as an isolated backend correctness PR with targeted tests.

## 3) Generic file watcher robustness tweak (deferred)
Removed change in:
- `src/vscode-atopile/src/common/file-resource-watcher.ts`

What was deferred:
- Synchronizing `exists` on read and forcing notify on change via refreshed resource.

Why deferred:
- Useful reliability improvement, but generic behavior change outside the minimum feature surface.
- Better validated in a dedicated watcher/reload reliability PR.
