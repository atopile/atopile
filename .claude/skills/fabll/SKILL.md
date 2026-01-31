---
name: FabLL
description: "How FabLL (faebryk.core.node) maps Python node/trait declarations into the TypeGraph + instance graph, including field/trait invariants and instantiation patterns."
---

# FabLL (Fabric Low Level) Module

`fabll` (primarily `src/faebryk/core/node.py`) is the high-level Python API for defining and working with hardware components. It bridges the gap between Python classes and the underlying `TypeGraph` and instance graph.

## Quick Start

```python
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll

g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)

class _App(fabll.Node):
    pass

app = _App.bind_typegraph(tg=tg).create_instance(g=g)
```

## Relevant Files

- `src/faebryk/core/node.py` (Node/Traits/fields, type registration, binding/instantiation helpers)
- `src/faebryk/core/faebrykpy.py` (edge types used by FabLL under the hood)
- `src/faebryk/core/graph.py` (GraphView wrapper used by instances)

## Dependants (Call Sites)

- **Library (`src/faebryk/library/`)**: Every component (Resistor, Capacitor, etc.) inherits from `Node`.
- **Compiler**: Generates `Node` subclasses dynamically from `ato` files.
- **Solvers**: Operate on `Node` instances to extract parameters and constraints.

## How to Work With / Develop / Test

### Core Concepts
- **Nodes are wrappers over graph instances**: a `fabll.Node` is constructed with a `graph.BoundNode`.
- **Declaration via class attributes**:
  - structural children: `SomeType.MakeChild(...)`
  - trait attachments: `Traits.MakeEdge(SomeTrait.MakeChild().put_on_type())` (or similar)
- **Binding**:
  - type binding: `MyType.bind_typegraph(tg)`
  - instance creation: `.create_instance(g)`
- **Type identifiers**:
  - library types (`faebryk.library.*`) intentionally have short identifiers (class name) for ato imports
  - non-library types include a module-derived suffix; type IDs must be unique (enforced in `Node._register_type`)

### Development Workflow
1) Prefer adding behavior as a Trait rather than deepening class hierarchies.
2) If you need a new structural relation/field kind, it lives in `src/faebryk/core/node.py` (field system).
3) Keep an eye on invariants enforced at class creation time (metaclass + `__init_subclass__`).

### Testing
- Core tests: `ato dev test --llm test/core/test_node.py -q` and `ato dev test --llm test/library/test_traits.py -q`

## Best Practices
- **Prefer Traits**: Don't add methods to `Node` subclasses if they can be a Trait. This allows them to be applied to different component families.
- **Avoid deep inheritance**: FabLL enforces single-level subclassing for node types (`Node.__init_subclass__`).
- **Type-safe traversal**: when you must traverse trait edges manually, prefer `EdgeTrait.traverse(trait_type=...)`.

## Internals & Runtime Behavior

### Instantiation & Lifecycle
- **Don’t call `MyNode()` with no args**: instances are created from a bound type via `bind_typegraph(...).create_instance(...)`.
- **TypeGraph context is required**:
  ```python
  import faebryk.core.graph as graph
  import faebryk.core.faebrykpy as fbrk

  g = graph.GraphView.create()
  tg = fbrk.TypeGraph.create(g=g)
  inst = MyNode.bind_typegraph(tg).create_instance(g=g)
  ```
- **Single-level subclassing invariant**: `Node.__init_subclass__` forbids “deeper than one level” inheritance for node types.

### Trait Implementation
- **Traits are Nodes**: Traits are not just Python mixins; they are `Node` subclasses that typically contain an `ImplementsTrait` edge.
- **Trait Definition**:
  ```python
  class MyTrait(Node):
      is_trait = Traits.MakeEdge(ImplementsTrait.MakeChild().put_on_type())
  ```
- **Resolution**: Use `node_instance.get_trait(TraitType)` to retrieve a trait instance. This performs a graph traversal.

### Performance & Memory
- **Type Creation**: Creating a type involves significant overhead (executing fields, resolving dependencies). Once created, instantiating instances is faster but still involves allocation in the Zig backend.
- **Tree Structure**: Nodes are linked via `EdgeComposition`. `add_child` creates this edge. Large trees (10k+ nodes) should be constructed carefully to avoid Python loop overhead; the underlying graph is efficient, but Python interactions cost time.
