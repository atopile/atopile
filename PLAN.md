# Zig Fabll Python API Plan

## Goal

Use Zig Fabll types from Python with the same ergonomics as Python Fabll types, with no per-type Python semantics shims.

Target end-state:

- `Strings = <zig path>.Strings` style usage is viable.
- `MakeChild`/`MakeEdge` work from Python for Zig-defined types.
- Behavior is defined once (in Zig), not duplicated in Python.

## Principles

- Single source of truth for literal semantics is Zig.
- Python keeps only orchestration/type-checking surface.
- Compatibility translation lives in `fabll_py.zig` (or its shared helpers), not in individual Python literal classes.
- Incremental migration with parity tests after each step.

## Scope

- In scope: `fabll_py.zig`, manual `.pyi` APIs, shared Zig binding helpers, Python type registration path, and literals migration.
- Out of scope (for now): full solver refactors unrelated to literal/type API parity.

## Milestones

### M1: `Strings` parity and ergonomics (in progress)

- [x] M1.1 Define strict API contract for `Strings` parity:
  - Class API: `bind_instance`, `create_instance`, `MakeChild`, `MakeChild_SetSuperset`, `deserialize`.
  - Instance API: `setup_from_values`, `get_values`, setic ops, serialization, pretty.
- [x] M1.2 Move remaining compatibility logic from Python `Literals.Strings` into Zig bindings.
- [x] M1.3 Ensure Zig `Strings` instances round-trip as proper Python Fabll nodes (`is_literal`, traits, casts).
- [x] M1.4 Keep order/behavior parity where tests depend on Python legacy behavior.
- [x] M1.5 Validate:
  - `pytest src/faebryk/library/Literals.py -q`
  - `ato dev test -k test_zig_embedded`

### M2: Shared binding framework (duplication removal)

- [x] M2.1 Introduce `src/faebryk/core/zig/src/python/fabll/common.zig` for reusable wrappers:
  - lifecycle helpers (alloc/dealloc/wrap),
  - argument conversion,
  - return conversion,
  - standardized error mapping.
- [x] M2.2 Refactor `fabll_py.zig` to use shared helpers for at least `String` + `Strings`.
- [x] M2.3 Add helper patterns for unary/binary/n-ary operation wrappers.

### M3: Construction API parity (`MakeChild` / `MakeEdge`)

- [x] M3.1 Define how Zig exposes construction metadata needed by Python.
- [x] M3.2 Implement binding-side constructors so Python can call Zig-defined construction APIs directly.
- [x] M3.3 Remove Python-only construction special-casing for migrated types.
- [x] M3.4 Add contract tests for typegraph construction parity (Python type vs Zig type).

### M4: Expand migration beyond `Strings`

- [x] M4.1 `Booleans`
- [x] M4.2 `Counts`
- [ ] M4.3 `AbstractEnums`
- [ ] M4.4 `Numbers` (largest surface; last)
- [x] M4.5 After each type: run parity test suite and embedded Zig tests.

### M5: Final cleanup

- [ ] M5.1 Remove temporary adapter paths that are no longer needed.
- [ ] M5.2 Keep one blessed integration pattern in docs/examples.
- [ ] M5.3 Final solver smoke validation with Zig-backed literals enabled.

## Acceptance Criteria

- [ ] Migrated literal types have no per-type Python semantics bodies.
- [ ] Zig binding layer provides all required methods with typed `.pyi` signatures.
- [ ] `ato dev test -k test_zig_embedded` passes.
- [ ] `pytest src/faebryk/library/Literals.py -q` passes.
- [ ] Relevant solver symbolic tests pass for migrated literal types.
- [ ] No custom Strings code in Literals.py, just an import from the zig-fabll type.

## Immediate Next Tasks (execute now, `Strings` first)

- [x] T1 Add/lock `Strings` API contract tests (explicitly check parity-critical behavior, incl. ordering and trait round-trip).
- [x] T2 Remove remaining Python `Strings.deserialize` bridge by exposing canonical Zig deserialize path compatible with Python Fabll expectations.
- [x] T3 Introduce first shared helper extraction in `fabll_py.zig` (for object wrap/alloc + binary op wrappers).
- [x] T4 Re-run validation suite and fix regressions before moving to next type.
