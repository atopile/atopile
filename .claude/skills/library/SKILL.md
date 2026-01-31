---
name: Library
description: "How the Faebryk component library is structured, how `_F.py` is generated, and the conventions/invariants for adding new library modules."
---

# Library Module

The `library` module (located in `src/faebryk/library/`) contains the collection of reusable components, traits, and interfaces that form the "standard library" of the hardware design language.

## Quick Start

```python
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F

g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)

resistor = F.Resistor.bind_typegraph(tg=tg).create_instance(g=g)
```

## Relevant Files

- **Facade (auto-generated)**: `src/faebryk/library/_F.py`
  - Eagerly imports and re-exports library modules/types for the `import faebryk.library._F as F` pattern.
  - This file is generated; do not hand-edit it.
- **Generator**: `tools/library/gen_F.py`
  - Scans `src/faebryk/library/*.py`, detects whether the file contains a same-named class, and writes `_F.py`.
  - Orders exports via a topological sort of `F.<Name>` references to avoid import-order cycles.
- **Components**: `src/faebryk/library/` contains specific component definitions (e.g. `Resistor.py`, `Capacitor.py`, `LED.py`).
- **Traits/Interfaces**: Also contains trait definitions (e.g. `can_bridge.py`, `is_power.py`).

## Dependants (Call Sites)

- **User Code**: Atopile projects heavily import from `faebryk.library._F` (aliased as `F`).
- **Compiler**: The compiler maps `ato` built-ins to these classes.

## How to Work With / Develop / Test

### Core Concepts
- **Traits vs Components**: Use Traits for behavior (what it *can do* like `can_bridge`) and Components for physical things (what it *is* like `Resistor`).
- **Export model**: `_F.py` is a generated “barrel” module; importing it is intentionally convenient but can be heavyweight.

### Development Workflow
1.  **New Component**: Create a new file `MyComponent.py` in `src/faebryk/library/`. Inherit from `Node` (or a more specific base).
2.  **Naming Convention**: Class names should match the file basename (usually).
3.  **Regenerate `_F.py`**: run `python tools/library/gen_F.py` and commit the updated `src/faebryk/library/_F.py`.

### Testing
- Library tests live under `test/library/` (including `test/library/nodes/`).
- A good smoke test for new modules is:
  - `ato dev test --llm test/library/test_instance_library_modules.py -q`

## Best Practices
- **Atomic Parts**: Mark leaf components (specifically verified part numbers) with the `is_atomic_part` trait.
- **Parameters**: Use `F.Parameters` to define physical properties like `resistance`, `capacitance`, etc.
- **Documentation**: Add docstrings to components explaining their ports and parameters.
