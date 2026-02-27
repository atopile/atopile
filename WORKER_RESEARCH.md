# Task 3 Prep (No Implementation)

## Required files to touch
- `src/faebryk/core/zig/src/python/faebryk/faebryk_pyi.zig`
- `src/faebryk/core/zig/src/python/faebryk/manual/literals.pyi` (new)
- `src/faebryk/core/zig/src/python/faebryk/manual/parameters.pyi` (new)
- `src/faebryk/core/zig/src/python/faebryk/manual/expressions.pyi` (new)
- `src/faebryk/core/zig/src/python/faebryk/manual/units.pyi` (new)
- `src/faebryk/core/zig/gen/faebryk/` (generated `.pyi` outputs)
- `test/core/zig/graph/test_zig_graph.py`
- optionally `test/core/zig/test_zig_embedded.py` if adding focused runner/path-specific coverage helper

## API/stub generation flow
1. Runtime wrappers are provided by `src/faebryk/core/zig/src/python/faebryk/faebryk_py.zig`.
2. Stub generation entrypoint is `src/faebryk/core/zig/src/python/pyi.zig` -> `faebryk/faebryk_pyi.zig`.
3. `faebryk_pyi.zig` calls `pyzig.pyi.PyiGenerator.manualModuleStub(...)` per faebryk submodule.
4. Manual stubs are sourced from `src/faebryk/core/zig/src/python/faebryk/manual/*.pyi`.
5. Build pipeline (`build.zig` `python-ext`) emits generated stubs into `zig-out/lib/gen/faebryk/*.pyi`, then `src/faebryk/core/zig/__init__.py` copies/black/ruff-processes them into `src/faebryk/core/zig/gen/faebryk/*.pyi`.

## Test plan (specific)
- Import parity (new modules + key types):
  - `./.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q -k "faebryk or import or typegraph"`
  - add assertions for `faebryk.core.zig.gen.faebryk.{literals,parameters,expressions,units}` and representative classes.
- Embedded Zig regression sanity:
  - `./.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"`
- Full targeted binding smoke:
  - `./.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q`

## Top 3 risks and mitigations
1. Risk: runtime wrappers and manual stubs drift (module/type name mismatch).
   - Mitigation: add one test that imports each new submodule and checks specific class symbols exist.
2. Risk: generated stubs are not refreshed/committed, causing CI/import mismatch.
   - Mitigation: explicitly run python-ext generation step before test assertions and verify `src/faebryk/core/zig/gen/faebryk/*.pyi` diff.
3. Risk: extension build failure from library self-import wiring (`@import("faebryk")` in library zig files) blocks Task 3 verification.
   - Mitigation: resolve/import-fix that module wiring first or gate Task 3 verification with a known-failure note plus isolated non-build tests.

## Follow-up: Build blocker deep-dive

### Reproduction + exact failing stage
- Repro command (from `src/faebryk/core/zig`):
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build python-ext -Doptimize=ReleaseFast -Dpython-include=/usr/include/python3.14 -Dpython-lib=python3.14 --global-cache-dir /tmp/zig-global-cache -freference-trace=20`
- Build stage that fails:
  - `python-ext` -> `install pyzig` -> `compile lib pyzig ReleaseFast native`.
- Failing compile command root:
  - `zig build-lib ... -Mroot=.../src/python/py.zig ... -Mfaebryk=.../src/faebryk/lib.zig ...`
- Primary errors:
  - `src/faebryk/library/expressions.zig:4:25: error: no module named 'faebryk' available within module 'faebryk'`
  - `src/faebryk/library/literals.zig:5:25: error: no module named 'faebryk' available within module 'faebryk'`
  - `src/faebryk/library/parameters.zig:5:25: error: no module named 'faebryk' available within module 'faebryk'`
  - `src/faebryk/library/units.zig:4:25: error: no module named 'faebryk' available within module 'faebryk'`
- Reference trace confirms these are reached by new wrapper registration path:
  - `src/python/faebryk/faebryk_py.zig:6446`..`6449` (`wrap_literals_file`, `wrap_parameters_file`, `wrap_expressions_file`, `wrap_units_file`)
  - via `src/python/py.zig:56` (`add_module(..., "faebryk", faebryk_py)`).

### Minimal root cause
- `src/faebryk/core/zig/src/faebryk/lib.zig` exports `library/*` (`literals`, `parameters`, `expressions`, `units`, `unit_resolver`) at lines `15`..`19`.
- Inside those library files, code does `const faebryk = @import("faebryk");` (e.g. `src/faebryk/core/zig/src/faebryk/library/expressions.zig:4`, plus same pattern in `collections.zig`, `parameters.zig`, `literals.zig`, `units.zig`, `unit_resolver.zig`).
- During compilation of module `faebryk` itself (`-Mfaebryk=src/faebryk/lib.zig`), there is no import entry named `faebryk` *inside that same module namespace* (build wiring only injects `graph` into `faebryk_mod`, see `build.zig:258`), so self-import lookup fails once these declarations become reachable.

### Viable fix options (with tradeoffs)
1. Preferred: remove self-import usage from `library/*.zig` and import required siblings directly.
- Example direction: replace `const faebryk = @import("faebryk");` with explicit imports like `@import("../fabll.zig")`, `@import("../composition.zig")`, `@import("../pointer.zig")`, `@import("../typegraph.zig")`, etc., then update `faebryk.*` references.
- Pros: explicit dependencies, no special build wiring, robust across tooling/packaging contexts.
- Cons: broad mechanical edits across several files and many symbol reference rewrites.

2. Build-wiring fix: inject a self alias on the `faebryk` module in `build.zig`.
- Example direction: add `faebryk_mod.addImport("faebryk", faebryk_mod);` near `build.zig:258`.
- Pros: very small diff; keeps existing `library/*.zig` code largely unchanged.
- Cons: increases coupling to build-system module alias behavior; less explicit than direct imports and can hide dependency structure.

3. Structural split: create a dedicated internal module for shared core APIs consumed by library files.
- Example direction: extract needed symbols (`fabll`, `typegraph`, `composition`, `trait`, `pointer`, `node_type`, etc.) into a new module (or sub-root) that library files import, while `faebryk/lib.zig` re-exports library nodes.
- Pros: clean layering and clearer long-term ownership boundaries.
- Cons: highest refactor cost; likely touches more files than needed for unblock.

### Concrete verification checklist for Task 3 (after blocker fix)
1. Cleanly rebuild extension + stubs.
- Run from `src/faebryk/core/zig`:
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build python-ext -Doptimize=ReleaseFast -Dpython-include=/usr/include/python3.14 -Dpython-lib=python3.14 --global-cache-dir /tmp/zig-global-cache`
- Pass condition: no compile errors in `library/*.zig`; `zig-out/lib/pyzig.so` (or `.pyd`) and `zig-out/lib/gen/faebryk/{literals,parameters,expressions,units}.pyi` exist.

2. Verify generated/manual stub outputs are synchronized.
- Trigger editable import path once:
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -c 'import faebryk.core.zig as z; print("ok")'`
- Pass condition: `src/faebryk/core/zig/gen/faebryk/{literals,parameters,expressions,units}.pyi` present and included in `git diff` only as expected Task 3 outputs.

3. Run focused binding/import tests for new surfaces.
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q -k "faebryk or import or typegraph"`
- Pass condition: imports for `faebryk.core.zig.gen.faebryk.literals`, `.parameters`, `.expressions`, `.units` and representative symbols succeed.

4. Run embedded Zig regression slice for touched library domains.
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"`
- Pass condition: no regressions in targeted embedded cases.

5. Final sanity sweep for Task 3 handoff.
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q`
- Pass condition: full graph Zig test file passes with new module exposure + stubs.

## Decision applied
- Applied PM decision: Option 1 (direct import rewrite) across `src/faebryk/core/zig/src/faebryk/library/{collections,expressions,literals,parameters,units,unit_resolver}.zig`.
- Removed all `@import("faebryk")` occurrences from those files and replaced `faebryk.<module>.*` symbol references with explicit sibling module imports and aliases.
- Required build validation passed:
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build python-ext -Doptimize=ReleaseFast -Dpython-include=/usr/include/python3.14 -Dpython-lib=python3.14 --global-cache-dir /tmp/zig-global-cache`
- Focused checklist results:
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -c 'import faebryk.core.zig as z; print("ok")'` -> `ok`
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q -k "faebryk or import or typegraph"` -> `2 passed, 7 deselected`
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"` -> fails in per-file Zig test compile mode with `import of file outside module path` for `@import("../...")` paths.

## Follow-up: embedded compile compatibility

### Root-cause analysis (focused)
- Reproduced failure with:
  - `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"`
- Failing mode is `build.zig` `test-file`, which sets:
  - `-Mroot=.../src/faebryk/library/<file>.zig`
- With Option 1, these files now import parents via `@import("../...")`:
  - `src/faebryk/core/zig/src/faebryk/library/literals.zig`
  - `src/faebryk/core/zig/src/faebryk/library/parameters.zig`
  - `src/faebryk/core/zig/src/faebryk/library/expressions.zig`
  - `src/faebryk/core/zig/src/faebryk/library/units.zig`
  - helper chain also affected: `src/faebryk/core/zig/src/faebryk/library/collections.zig`, `src/faebryk/core/zig/src/faebryk/library/unit_resolver.zig`
- In per-file compile mode, module root path is `src/faebryk/library`, so `../typegraph.zig`, `../fabll.zig`, etc. are outside allowed module path -> `import of file outside module path`.
- `python-ext` does not hit this because those same files are compiled under `-Mfaebryk=.../src/faebryk/lib.zig` (module root path `src/faebryk`), where `../` from `library/*` stays inside module path.

### Validation notes used to de-risk fix direction
- Compiling `src/faebryk/lib.zig` directly for `test-file` is not sufficient (`All 0 tests passed`) because no target file tests are pulled in by default.
- A wrapper rooted inside `src/faebryk` that directly imports `library/expressions.zig` does include tests and accepts filter substring:
  - `library.expressions.test.expressions unary setup stores operand` matched by filter `expressions.test.expressions unary setup stores operand`.
- This confirms the compatibility fix should adjust per-file rooting/import strategy, not revert Option 1 imports.

### Concrete fix options (Option 1 preserved)
1. Build-level wrapper root for library files (recommended).
- Change `build.zig` `test-file` flow so when `-Dtest-file` is under `src/faebryk/library/`, compile a wrapper root under `src/faebryk/` that imports the target file path.
- Keep normal per-file flow for non-library files.
- Pros: keeps Option 1 imports unchanged; scoped to embedded compile mode; no runtime/python-ext impact.
- Cons: small build-logic complexity.

2. Test harness wrapper selection in Python (`test_zig_embedded.py`).
- For library files only, compile a dedicated wrapper file under `src/faebryk/` instead of the raw target path.
- Pros: no `build.zig` changes.
- Cons: test-only workaround; duplicates compile-mode policy in Python; less central than build-system fix.

3. Dual-mode import shim in library files.
- Add compile-mode switch so library files use sibling `../` imports normally but fallback to module imports in embedded per-file mode.
- Pros: can preserve current test command shape.
- Cons: touches multiple library files; highest code churn/risk; mixes build-mode conditionals into core library sources.

### Recommended option (minimal risk)
- Recommend Option 1: build-level wrapper root for `src/faebryk/library/*` in `test-file`.
- Why lowest risk:
  - Zero rollback of Option 1 implementation.
  - Constrains change to test compile wiring only.
  - Leaves python-ext and runtime bindings untouched.
  - Compatible with current test filter strategy.

### Exact files/changes needed for recommended option
1. `src/faebryk/core/zig/build.zig`
- In `test-file` block, detect `test_file_path` prefix `src/faebryk/library/`.
- For matching paths:
  - use wrapper root source file under `src/faebryk/` (e.g. `src/faebryk/test_file_wrapper.zig`);
  - provide the relative import path (`library/<name>.zig`) via build options import.
- For non-matching paths, keep existing root path behavior.

2. `src/faebryk/core/zig/src/faebryk/test_file_wrapper.zig` (new)
- Minimal wrapper that imports `build_options`, then imports the selected library file path so its tests are compiled under `src/faebryk` module root path.

3. Optional follow-up only if needed: `test/core/zig/test_zig_embedded.py`
- No functional change required for root-cause fix.
- Optional env override for local sandbox-only cache issue (`--global-cache-dir /tmp/zig-global-cache`) if AccessDenied noise blocks local verification.

### Tiny implementation slice decision
- Kept this pass research-only after validating behavior and narrowing the fix to the build/test-file path.
- No production source changes applied in this pass.

## Implementation + verification (2026-02-15)

### Implementation applied
1. `src/faebryk/core/zig/build.zig`
- Updated `test-file` flow to detect `-Dtest-file` values under `src/faebryk/library/`.
- For matching targets:
  - compile `src/faebryk/test_file_wrapper.zig` as root instead of the library file directly;
  - inject `build_options.test_file_import_path` with the selected `library/<name>.zig` path.
- For non-library targets, preserved existing direct root-file behavior unchanged.

2. `src/faebryk/core/zig/src/faebryk/test_file_wrapper.zig` (new)
- Added minimal wrapper importing `build_options`.
- Added comptime literal-dispatch imports for:
  - `library/collections.zig`
  - `library/expressions.zig`
  - `library/literals.zig`
  - `library/parameters.zig`
  - `library/unit_resolver.zig`
  - `library/units.zig`
- Added compile-time guard (`@compileError`) for unsupported library path keys.

### Verification results
1. Requested embedded slice (run exactly as requested first):
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"`
- Result in sandbox: fails during fixture/import phase because `compile_zig()` `python-ext` build hits Zig cache `AccessDenied` (`manifest_create AccessDenied`, unable to load `std.zig` from venv path).

2. Requested embedded slice with sandbox cache override:
- `ZIG_GLOBAL_CACHE_DIR=/tmp/zig-global-cache /home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"`
- Result: `30 passed, 76 deselected`.

3. Requested graph/import slice (run exactly as requested first):
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q -k "faebryk or import or typegraph"`
- Result in sandbox: collection-time failure for the same `python-ext` cache `AccessDenied`.

4. Requested graph/import slice with sandbox cache override:
- `ZIG_GLOBAL_CACHE_DIR=/tmp/zig-global-cache /home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q -k "faebryk or import or typegraph"`
- Result: `2 passed, 7 deselected`.

5. Additional direct compile sanity for wrapper pathing:
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build test-file -Dtest-file=src/faebryk/library/expressions.zig -Dtest-name=lib-expr-wrapper-check -Doptimize=ReleaseFast --global-cache-dir /tmp/zig-global-cache` -> pass.
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build test-file -Dtest-file=src/faebryk/library/units.zig -Dtest-name=lib-units-wrapper-check -Doptimize=ReleaseFast --global-cache-dir /tmp/zig-global-cache` -> pass.

6. Feasible python-ext rebuild with existing flags:
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build python-ext -Doptimize=ReleaseFast -Dpython-include=/usr/include/python3.14 -Dpython-lib=python3.14 --global-cache-dir /tmp/zig-global-cache`
- Result: pass.

## Library module split for pyi readiness

### What changed
- Added a core/library module boundary in Zig build wiring:
  - `faebryk_core` -> `src/faebryk/core.zig` (core graph/fabll/typegraph/edge APIs).
  - `faebryk_library` -> `src/faebryk/library/lib.zig` (collections/literals/parameters/expressions/units/unit_resolver).
  - `faebryk` -> compatibility aggregate at `src/faebryk/lib.zig`, re-exporting both module surfaces.
- `build.zig` now wires imports explicitly:
  - `faebryk_core` imports `graph`.
  - `faebryk_library` imports `graph` and binds `faebryk` to `faebryk_core`.
  - `faebryk` imports `faebryk_core` and `faebryk_library`.
- Library sources under `src/faebryk/core/zig/src/faebryk/library/*.zig` now use `const faebryk = @import("faebryk");` for core APIs again.

### Why this is pyi-ready
- The split creates a stable boundary where `.pyi` generation can choose one of two views:
  1. Compatibility/public aggregate view: `@import("faebryk")`.
  2. Library-focused view: `@import("faebryk_library")` (for future dedicated solver/library stub surfaces).
- This prevents forcing `.pyi` tooling to parse mixed core + library source ownership directly from path-relative imports.

### Recommended pyi interface points
- Keep existing `faebryk` pyi generation for backward compatibility of current Python imports.
- For upcoming library-specific `.pyi` work, read symbols from `faebryk_library` (`src/faebryk/library/lib.zig`) as the canonical library registry.
- Continue treating `src/faebryk/lib.zig` as compatibility aggregation, not the authoritative ownership boundary.

### Tradeoffs
- Pros:
  - Restores simple module imports (`@import("faebryk")`) in library files.
  - Clarifies ownership and keeps room for additional library submodules without flattening everything into one root.
  - Keeps current python-ext behavior by preserving `faebryk` aggregate API.
- Cons:
  - Aggregate module still exists, so there are now multiple entry points (`faebryk`, `faebryk_core`, `faebryk_library`) that future contributors must use intentionally.
  - Embedded test wrapper mode needs special handling to avoid module/file double-ownership; this is implemented in `build.zig` by mapping wrapper `faebryk` import to `faebryk_core`.

### Validation
- `/home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m ziglang build python-ext -Doptimize=ReleaseFast -Dpython-include=/usr/include/python3.14 -Dpython-lib=python3.14 --global-cache-dir /tmp/zig-global-cache` -> pass.
- `ZIG_GLOBAL_CACHE_DIR=/tmp/zig-global-cache /home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/test_zig_embedded.py -q -k "literals.zig or parameters.zig or expressions.zig or units.zig"` -> `30 passed, 76 deselected`.
- `ZIG_GLOBAL_CACHE_DIR=/tmp/zig-global-cache /home/ip/workspace/atopile_zig_fabll/.venv/bin/python -m pytest test/core/zig/graph/test_zig_graph.py -q -k "faebryk or import or typegraph"` -> `2 passed, 7 deselected`.

## First pyi slice on faebryk_library

### Mapping and surfacing point
- Current flow:
  - `src/faebryk/core/zig/build.zig` `build_pyi()` runs `src/faebryk/core/zig/src/python/pyi.zig`.
  - `src/python/pyi.zig` dispatches to module generators (`sexp`, `graph`, `faebryk`).
  - `src/python/faebryk/faebryk_pyi.zig` is the single choke point for `faebryk` submodule `.pyi` emission.
  - `pyzig.pyi.PyiGenerator.manualModuleStub(...)` copies stubs from `src/python/faebryk/manual/*.pyi` into `zig-out/lib/gen/faebryk/*.pyi`.
- Library boundary implication:
  - Runtime symbols are exposed via `faebryk` aggregate (`src/faebryk/lib.zig`) which now re-exports `faebryk_library` modules.
  - Therefore, the required `.pyi` surfacing point is `src/python/faebryk/faebryk_pyi.zig` by adding manual-stub emission entries for `faebryk.literals`, `faebryk.parameters`, `faebryk.expressions`, and `faebryk.units`.

### Interfaces exposed now
- Added `.pyi` wiring in `src/faebryk/core/zig/src/python/faebryk/faebryk_pyi.zig` for:
  - `literals`
  - `parameters`
  - `expressions`
  - `units`
- Added new manual stubs:
  - `src/faebryk/core/zig/src/python/faebryk/manual/literals.pyi`
  - `src/faebryk/core/zig/src/python/faebryk/manual/parameters.pyi`
  - `src/faebryk/core/zig/src/python/faebryk/manual/expressions.pyi`
  - `src/faebryk/core/zig/src/python/faebryk/manual/units.pyi`
- First-slice scope is symbol-level class presence (solver-critical classes), not full method parity.

### What remains
- Fill method signatures and return/arg typing for high-use classes in each new module to reach parity with runtime wrappers.
- Decide whether to keep these modules manual-only or add a hybrid generation path (auto skeleton + manual overrides).
- Optionally sync generated stubs into `src/faebryk/core/zig/gen/faebryk/` through the editable-install copy/format path for immediate repo-visible parity.
- Add dedicated tests that validate both:
  - importability of `faebryk.core.zig.gen.faebryk.{literals,parameters,expressions,units}`
  - expected typed members (beyond symbol existence).

### Risks/tradeoffs
- Tradeoff (chosen for first slice): symbol-level stubs are safe and low-risk but intentionally incomplete for IDE/type-check precision.
- Risk: method-level drift remains until signatures are added; users may still see `Any`-like behavior from these classes in tooling.
- Risk: manual stubs can diverge from runtime wrappers unless guarded by focused parity checks.
