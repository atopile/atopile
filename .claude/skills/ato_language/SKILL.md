---
name: ATO Language
description: "LLM-focused reference for the `ato` declarative DSL: mental model, syntax surface, experiments/feature flags, and common pitfalls when editing `.ato` and `ato.yaml`."
---

# ATO Language

`ato` is a **declarative** DSL for electronics design in the atopile ecosystem. It is intentionally “Python-shaped”, but it is **not** Python: there is no procedural execution model and (most importantly) no user-defined side effects.

This skill is the canonical repo-local language guide (replacing various editor/assistant-specific duplicates).

## Quick Start

- When changing `.ato` files: keep everything **declarative** (no “do X then Y” assumptions).
- If you need syntax gated behind experiments, enable it with `#pragma experiment("<NAME>")` (see below).
- To validate a change quickly in-repo:
  - `ato build` (project-level build)
  - `ato dev test --llm -k ato` (if you’re touching compiler/lsp behavior; adjust `-k`)

## Mental Model (What ATO “Is”)

- **Blocks**: `module`, `interface`, `component`
  - `module`: a type that can be instantiated (`new ...`)
  - `interface`: a connectable interface type (electrical, buses, etc.)
  - `component`: “code-as-data” (often used for reusable fragments)
- **Instances**: created with `new`, can be single or container-sized (`new M[10]`).
- **Connections**: wiring between interfaces using `~` (direct) and `~>` (bridge/series) when enabled.
- **Parameters + constraints**: values constrained with `assert ...`, used for picking/validation.

## Experiments (Feature Flags)

Some syntax is gated behind `#pragma experiment(...)`. The authoritative list lives in `src/atopile/compiler/ast_visitor.py` (`ASTVisitor._Experiment`).

Currently:
- `BRIDGE_CONNECT`: enables `a ~> bridge ~> b` style “bridge operator” chains.
- `FOR_LOOP`: enables `for item in container:` syntax.
- `TRAITS`: enables `trait ...` syntax in ATO.
- `MODULE_TEMPLATING`: enables `new MyModule<param_=literal>` style instantiation templating.
- `INSTANCE_TRAITS`: enables instance-level trait constructs (see compiler implementation).

Enable example:
```ato
#pragma experiment("FOR_LOOP")
```

## Syntax Reference (Representative Examples)

### Imports
```ato
import ModuleName
import Module1, Module2.Submodule

from "path/to/source.ato" import SpecificModule
import AnotherModule; from "another/source.ato" import AnotherSpecific
```

### Top-level statements
```ato
pass
"docstring-like statement"
top_level_var = 123
pass; another_var = 456; "another docstring"
```

### Block definitions
```ato
component MyComponent:
    pass
    pass; internal_flag = True

module AnotherBaseModule:
    pin base_pin
    base_param = 10

interface MyInterface:
    pin io

module DemoModule from AnotherBaseModule:
    pin p1
    signal my_signal
    a_field: AnotherBaseModule
```

### Assignments
```ato
value = 1
value += 1; value -= 1
flags |= 1; flags &= 2
```

### Connections
```ato
p1 ~ base_pin
iface_a ~ iface_b
iface_a ~> bridge ~> iface_b     # requires BRIDGE_CONNECT
```

### Instantiation (and templating)
```ato
instance = new MyComponent
container = new MyComponent[10]

templated_instance = new MyComponent<int_=1, float_=2.5>  # requires MODULE_TEMPLATING
```

### Assertions / constraints
```ato
assert x > 5V
assert 5V < x < 10V
assert current within 1A +/- 10mA
assert resistance is 1kohm to 1.1kohm
```

### Loops (syntactic sugar)
```ato
for item in container:
    item ~ p1
```

## What Is *Not* In ATO

Do not write (or assume) any of these exist:
- `if` statements
- `while` loops
- user-defined functions (calls or defs)
- user-defined classes/objects
- exceptions/generators

## Relevant Files

- Compiler/visitor (experiments + syntax gating): `src/atopile/compiler/ast_visitor.py`
- Lexer/parser (grammar): `src/atopile/compiler/parser/` (ANTLR artifacts)
- LSP implementation (pragma parsing, editor features): `src/atopile/lsp/lsp_server.py`
- Codegen that emits experiment pragmas: `src/faebryk/libs/codegen/atocodegen.py`
- VSCode extension rule templates (editor-facing guidance): `src/vscode-atopile/resources/templates/rules/`

## Common Pitfalls (LLM Checklist)

- Don’t “invent” runtime semantics: ATO is declarative; ordering is not an execution model.
- Prefer constraints with tolerances when they drive selection (exact values can make picking impossible).
- If you introduce gated syntax, add the matching `#pragma experiment("...")` near the top of the file.
- When editing `.ato`, verify the change through the compiler surface (`ato build` / targeted tests), not by eyeballing.
