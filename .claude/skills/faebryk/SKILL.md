---
name: Faebryk
description: "How Faebryk’s TypeGraph works (GraphView + Zig edges), how to traverse/resolve references, and how FabLL types/traits map onto edge types."
---

# Faebryk Core Module

The Faebryk core here is the **TypeGraph** + edge types implemented in Zig and exposed to Python via `faebryk.core.faebrykpy`.

Source-of-truth for API + behavior:
- `src/faebryk/core/faebrykpy.py` (Python-facing wrapper + type-safe `EdgeTrait.traverse`)
- `src/faebryk/core/zig/gen/faebryk/typegraph.pyi` (public stubbed API surface)
- `src/faebryk/core/zig/src/faebryk/*` (Zig implementation)

## Quick Start

```python
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph

g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)
```

## Relevant Files

- `src/faebryk/core/faebrykpy.py` (re-exports + `EdgeTraversal` + type-safe `EdgeTrait.traverse`)
- `src/faebryk/core/zig/gen/faebryk/typegraph.pyi` (TypeGraph stub)
- Key edge types (imported by `faebrykpy.py`):
  - `EdgeComposition` (parent/child structure)
  - `EdgeTrait` / `Trait` (trait attachment)
  - `EdgePointer` (references)
  - `EdgeInterfaceConnection` (interface connections)
  - `EdgeOperand` (solver operand wiring)
  - `EdgeType` / `EdgeNext` (type graph plumbing)
- Linker:
  - `Linker` (used by compiler/linking stages)

## Dependants (Call Sites)

- FabLL: `src/faebryk/core/node.py` (binds Python classes into the TypeGraph; uses composition/trait edges)
- Compiler: `src/atopile/compiler/*` (creates and links TypeGraphs)
- Solver: `src/faebryk/core/solver/*` (operand edges and instance traversal)
- Build/export pipeline: `src/atopile/build_steps.py` (visits type/instance edges for PCB/layout features)

## How to Work With / Develop / Test

### Core Concepts
- **GraphView + TypeGraph**: a `TypeGraph` is created against a `GraphView`:
  ```python
  import faebryk.core.graph as graph
  import faebryk.core.faebrykpy as fbrk

  g = graph.GraphView.create()
  tg = fbrk.TypeGraph.create(g=g)
  ```
- **Type nodes vs instance nodes**:
  - TypeGraph stores type definitions (“what exists structurally on a type”)
  - GraphView also holds instances created from those types (“a concrete design graph”)
- **EdgeTraversal**: `TypeGraph.ensure_child_reference(..., path=[...])` uses `EdgeTraversal` items to walk references through the type graph.

### Development Workflow
1) Zig-side changes: edit `src/faebryk/core/zig/src/faebryk/*` (edges, typegraph internals).
2) Rebuild bindings: `ato dev compile` (imports `faebryk.core.zig`).
3) Python ergonomics: add wrappers/helpers in `src/faebryk/core/faebrykpy.py` (example: type-safe `EdgeTrait.traverse`).

### Testing
- TypeGraph-heavy tests live in compiler/runtime suites:
  - `ato dev test --llm test/compiler/test_typegraph.py -q`
  - `ato dev test --llm test/compiler/test_runtime.py -q`
- Zig-backed traversal tests:
  - `ato dev test --llm test/core/zig/test_interface_pathfinder.py -q`

## Best Practices
- Import edges/TypeGraph via `faebryk.core.faebrykpy` (so callers get Python helpers, not just raw generated types).
- Prefer type-safe trait traversal:
  - `EdgeTrait.traverse(trait_type=SomeTrait)` over stringly-typed `trait_type_name=...`.
- When building reference paths, be explicit about edge semantics (composition vs pointer vs trait) rather than relying on implicit string behavior.
