---
name: Graph
description: "How the Zig-backed instance graph works (GraphView/NodeReference/EdgeReference), the real Python API surface, and the invariants around allocation, attributes, and cleanup."
---

# Graph Module

The `faebryk.core.graph` module is a thin Python wrapper around the Zig graph implementation.

Source-of-truth for behavior is:
- Zig implementation: `src/faebryk/core/zig/src/graph/graph.zig`
- Python bindings: `src/faebryk/core/zig/src/python/graph/graph_py.zig`
- Public Python API surface (stubs): `src/faebryk/core/zig/gen/graph/graph.pyi`

## Quick Start

```python
from faebryk.core.graph import GraphView

g = GraphView.create()
try:
    _ = g.create_and_insert_node()
finally:
    g.destroy()
```

## Relevant Files

- Python wrapper/re-export: `src/faebryk/core/graph.py`
- Zig graph core: `src/faebryk/core/zig/src/graph/graph.zig`
- Zig → Python wrappers: `src/faebryk/core/zig/src/python/graph/graph_py.zig`
- Generated type stubs: `src/faebryk/core/zig/gen/graph/graph.pyi`

## Dependants (Call Sites)

- `src/faebryk/core/node.py` (FabLL: nodes/traits are graph-backed)
- `src/atopile/compiler/gentypegraph.py` (compiler constructs typegraphs/instances via graph APIs)
- `src/faebryk/core/graph_render.py` (graph visualization)

## How to Work With / Develop / Test

### Mental Model
- `NodeReference` / `EdgeReference`: value-like handles (UUIDs) into global backing storage in Zig.
- `GraphView`: a *membership + adjacency* view over those references (per-view arena + maps + bitsets).
- `BoundNode` / `BoundEdge`: “reference + owning GraphView pointer” wrappers used for traversal helpers.

### Core Invariants (do not violate)
- **No direct constructors**: `GraphView()`, `NodeReference()`, `EdgeReference()` are not meant to be called; use the exposed factory methods.
  - `GraphView.create()`
  - `NodeReference.create(**attrs)`
  - `EdgeReference.create(source=..., target=..., edge_type=..., **attrs)`
- **Explicit cleanup**: `GraphView.create()` allocates a Zig-side graph on the C allocator; it is freed only by `GraphView.destroy()`.
  - Do not rely on Python GC to reclaim Zig allocations.
- **Attribute limits**: node/edge dynamic attributes are fixed-capacity in Zig (currently 6 entries). Exceeding this is a hard failure.
- **Edge type width**: edge types are `u8` in Zig; treat them as `0..255` in Python (hashing/modulo happens on the Zig side).
- **Self node exists**: `GraphView.init` inserts a `self_node`; counts include it.

### API Cheatsheet (matches `src/faebryk/core/zig/gen/graph/graph.pyi`)

```python
from faebryk.core.graph import GraphView, Node, Edge

g = GraphView.create()
try:
    n1 = g.create_and_insert_node()           # -> BoundNode
    n2 = Node.create(name="n2")               # -> NodeReference (not inserted yet)
    bn2 = g.insert_node(node=n2)              # -> BoundNode

    e = Edge.create(source=n1.node(), target=bn2.node(), edge_type=7, name="link")
    _be = g.insert_edge(edge=e)               # -> BoundEdge
finally:
    g.destroy()
```

### Debugging
- `GraphView.__repr__()` prints `GraphView(id=..., |V|=..., |E|=...)` from Zig.
- Graph wrapper has a stress test: `python -m faebryk.core.graph` (runs `test_graph_garbage_collection`).

### Development Workflow
1) Zig changes: edit `src/faebryk/core/zig/src/graph/*`.
2) Rebuild: `ato dev compile` (imports `faebryk.core.zig`, which compiles in editable installs).
3) If you add/remove exposed methods: update the wrapper in `src/faebryk/core/zig/src/python/graph/graph_py.zig` and ensure stubs regenerate.

### Testing
Key test entrypoints:
- Python: `python -m faebryk.core.graph`
- Zig: `zig test src/faebryk/core/zig/src/graph/graph.zig`
