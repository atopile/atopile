---
name: ato
description: "Canonical ato language skill for runtime injection: mental model, syntax and feature gates, semantic rules, authoring patterns, and diagnostics workflow."
---

# ato Skill

This is one of exactly two runtime skills injected by the server.
It defines how to author and review `.ato` safely and effectively.

## Context Budget Spec

Target budget for this skill: about `40,000` tokens.

Recommended internal allocation:
1. Language Mental Model: `3,000`
2. Core Syntax Reference: `7,000`
3. Feature Gates / Experiments: `4,000`
4. Semantic Rules and Type Safety: `6,000`
5. Authoring Patterns (module-first): `6,000`
6. Constraints and Solver-Friendly Modeling: `4,000`
7. Library/Stdlib Usage Patterns: `4,000`
8. Diagnostics and Repair Playbooks: `4,000`
9. Anti-Patterns and Guardrails: `2,000`

Total: `40,000`

## Source of Truth

This document is the source of truth for language behavior in runtime contexts.
Do not assume access to repository files; any required rule should be stated explicitly here.

## Language Mental Model

ato is declarative graph authoring for electronics:
- `module` defines reusable design structure.
- `interface` defines connectable boundaries.
- `component` defines reusable concrete building blocks.
- `new` creates typed instances.
- `assert` constrains acceptable solutions.

Key rule: this is not imperative execution.
Write intent and constraints, not execution order.

## Core Syntax (Minimum Must-Know)

### Imports
```ato
import Foo
import A, B.Sub
from "path/to/file.ato" import Part
```

### Block Definitions
```ato
component C:
    pass

module M:
    pass

interface IF:
    pin io
```

### Inheritance
```ato
module Child from Parent:
    pass
```

### Instantiation
```ato
inst = new MyModule
arr = new MyModule[4]
```

### Connections
```ato
a ~ b
```

### Constraints
```ato
assert voltage > 3.0V
assert 3.0V < voltage < 3.6V
assert resistance within 10kohm +/- 5%
assert value is 1.0V to 1.2V
```

## Experiment-Gated Features

Supported experiments:
- `BRIDGE_CONNECT`
- `FOR_LOOP`
- `TRAITS`
- `MODULE_TEMPLATING`
- `INSTANCE_TRAITS`

Use explicit pragma when needed:
```ato
#pragma experiment("FOR_LOOP")
```

## Semantic Rules

1. Connect only compatible interfaces.
2. Keep module boundaries coherent.
3. Prefer interface-level wiring over pin sprawl.
4. Use realistic tolerances for pickable parts.
5. Reuse patterns with arrays/loops/templates where available.

## Authoring Defaults

Preferred design flow:
1. Create functional modules (power, MCU, sensors, IO, debug).
2. Connect modules through typed interfaces.
3. Keep passives generic with constraints.
4. Use explicit concrete parts for ICs/connectors/mechanical/protection when needed.
5. Refine constraints and validate.

## Constraints Guidance

- Favor ranges/tolerances over exact hard values.
- Keep units explicit and physically consistent.
- Avoid over-constraining early architecture drafts.
- Constrain for intent first, vendor selection second.

### `within` vs `is` (with examples)

Use `within` for bounds/domain constraints:

```ato
assert power.voltage within 3.3V +/- 5%
assert i2c.frequency within 100kHz to 400kHz
```

Use `is` for identity/equality between parameters or expressions:

```ato
assert addressor.address is i2c.address
assert v_out is v_in * r_bottom.resistance / r_total
```

## Diagnostics Workflow

When compile/build fails:
1. Read logs first.
2. Run diagnostics.
3. Fix the nearest root-cause blocker.
4. Rebuild.
5. Repeat until clean.

Common failure classes:
- Missing experiment pragma.
- Interface type mismatch.
- Invalid constraint expression.
- Unsupported syntax copied from other languages.

## Anti-Patterns

- Treating ato as Python runtime logic.
- Top-level monolithic pin-by-pin netlists for modular designs.
- Exact-value passive constraints without tolerance.
- Editing without reading existing file context first.

## Examples to Pull From

- `examples/quickstart/quickstart.ato`
- `examples/passives/passives.ato`
- `examples/equations/equations.ato`
- `examples/pick_parts/pick_parts.ato`
- `examples/i2c/i2c.ato`
- `examples/esp32_minimal/esp32_minimal.ato`
- `examples/layout_reuse/layout_reuse.ato`
- `examples/led_badge/led_badge.ato`

### Complex example project structure notes

For larger examples (especially `led_badge`), keep structure explicit:

- `main.ato`: top-level integration and module wiring only.
- `modules/power.ato`: USB input, charger, battery, regulator, rail constraints.
- `modules/compute.ato`: MCU module and digital bus breakout.
- `modules/leds.ato`: LED strip/grid composition and data-chain bridge behavior.
- `modules/peripherals.ato`: microphone/sensors and their interface constraints.
- `modules/connectors.ato`: external connectors and protection blocks.

Use this split to keep each file focused on one concern and make review/debug loops faster.

## Contract with Agent Skill

`agent` skill governs behavior and execution discipline.
`ato` skill governs language correctness and design modeling quality.
Both are always injected together.
