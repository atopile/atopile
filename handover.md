# Zig FabLL Handover

## Current Branch / Context
- Branch: `feature/zig_fabll`
- Recent commits:
  - `4702fb617` — deduplicate `is_trait` via shared `fabll` helper
  - `5e7bf01fe` — parameter and expression parity APIs
  - `4314885e3` — moved Zig library modules to `faebryk/library/`
  - `8194f124f` — trait attachment via `is_trait.MakeEdge` pattern

## Current State (What is done)

### 1) Library file reorganization is complete and working
- Moved:
  - `collections.zig`
  - `literals.zig`
  - `expressions.zig`
  - `units.zig`
  - `parameters.zig`
  - `unit_resolver.zig`
- New location: `src/faebryk/core/zig/src/faebryk/library/`
- Module-path/import issues were fixed by:
  - Exposing `fabll` from `src/faebryk/core/zig/src/faebryk/lib.zig`
  - Avoiding self-import cycle in `fabll.zig`
  - Using module-safe imports in moved files

### 2) Trait attachment pattern is aligned
- Code is now consistently using trait edges via `is_trait.MakeEdge(...)` instead of ad-hoc child attachment for traits.

### 3) `is_trait` is centralized
- Shared helper now lives in `src/faebryk/core/zig/src/faebryk/fabll.zig` as `pub const is_trait`.
- Duplicates removed from:
  - `library/parameters.zig`
  - `library/units.zig`
  - `library/expressions.zig`
  - `fabll.zig` test fixture section
- Library files import it as `const is_trait = fabll.is_trait;`.

### 4) Parity additions implemented (parameters / expressions)

#### Parameters
In `src/faebryk/core/zig/src/faebryk/library/parameters.zig`:
- Added `is_parameter` trait node.
- Extended `is_parameter_operatable` with typed superset APIs:
  - `set_superset_node(...)`
  - `try_get_superset_node()`
  - `try_extract_superset(LitType)`
  - `force_extract_superset(LitType)`
- Added latest-wins superset semantics via pointer indexing for repeat `set_superset`.
- Added:
  - `StringParameter`
  - `BooleanParameter`
- Added tests for string/boolean superset + singleton extraction.

#### Expressions
In `src/faebryk/core/zig/src/faebryk/library/expressions.zig`:
- Added expression nodes:
  - `Sqrt`
  - `Log` (default base `e` when omitted)
  - `Sin`
  - `Cos`
  - `Round`
- Extended unary setup test coverage to include these.

## Validation Status
- Full embedded Zig suite is green after latest changes:
  - `103 passed` via:
    - `python -m pytest test/core/zig/test_zig_embedded.py -q`
- Multiple short-loop targeted runs were used during iterations (`test_zig_embedded.py <file> <test-name>`).

## Design Intentions / Direction

### Core intent
- Keep Zig FabLL semantics aligned with Python where practical.
- Prefer explicit typegraph/edge semantics and compile-time safety.
- Keep loops short and verify frequently with `test_zig_embedded`.

### What was intentionally chosen
- Trait linking standardized through one shared helper (`fabll.is_trait`).
- Library modules grouped under `faebryk/library/` for maintainability.
- Superset linkage in parameters uses edge pointer indexing and resolves to latest set value to emulate overwrite behavior without immediate edge deletion support.

## Known Constraints / Caveats
- No general edge-removal helper is currently used for replacing superset pointers; behavior is implemented as latest-index wins.
- `expressions.zig` still covers only a subset of Python `Expressions.py` classes/traits.
- `parameters.zig` still lacks Python parity for `EnumParameter` and broader operatable constraints logic.

## Suggested Next Milestone

### Milestone: Enum + expression trait parity foundation
1. Implement `EnumParameter` parity in Zig:
   - Domain pointer setup
   - Typed enum extraction / setup
   - Domain literal generation parity hooks
2. Add expression trait-marker parity surface (incrementally):
   - `is_arithmetic`, `is_canonical`, `is_commutative`, etc. as needed by downstream code
3. Expand resolver/evaluator tests to cover new expression nodes (`Sqrt`, `Log`, trig, `Round`) as far as current evaluator supports.
4. Keep each substep validated with short embedded loops before broader runs.

## Practical Next Steps (Concrete)
- Start with `EnumParameter` in `library/parameters.zig`.
- If enum literals need more support, extend `library/literals.zig` minimally for required APIs.
- Add focused tests in `parameters.zig` first.
- Then wire any needed expression trait stubs in `expressions.zig`.
- Run:
  - targeted tests per file
  - then full `test/core/zig/test_zig_embedded.py -q`

## Useful Commands
- Single test:
  - `python test/core/zig/test_zig_embedded.py expressions.zig "expressions unary setup stores operand"`
- File-focused subset:
  - `python -m pytest test/core/zig/test_zig_embedded.py -q -k "parameters.zig or expressions.zig"`
- Full suite:
  - `python -m pytest test/core/zig/test_zig_embedded.py -q`

